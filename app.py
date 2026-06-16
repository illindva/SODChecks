import os
import logging
from flask import Flask, render_template, request, jsonify
from models import db, Category, HealthCheck, CheckResult, init_db
import runners
from scheduler_setup import init_scheduler, sync_scheduler, scheduler
from datetime import datetime, timedelta
from encryption_utils import encrypt_password
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize logging for production
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Secure Configuration for Banking Environment
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
    
    try:
        from flask_talisman import Talisman
        # Setting CSP to None to allow current inline scripts/styles to function,
        # but enabling all other secure headers (HSTS, X-Frame-Options, etc.)
        Talisman(app, content_security_policy=None)
    except ImportError:
        logger.warning("Flask-Talisman not installed. Security headers will not be enforced.")
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'healthchecks.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Initialize DB and create all objects/categories
    init_db(app)
            
    # Initialize scheduler
    # When using Flask's reloader, it spawns two processes. We only want the scheduler to run in the worker process.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        init_scheduler(app)

    # --- HTML Routes ---
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')
        
    @app.route('/config')
    def config_page():
        return render_template('config.html')
        
    @app.route('/history')
    def history_page():
        return render_template('history.html')

    @app.route('/dashboard/<name>')
    def dashboard_detail(name):
        return render_template('dashboard_detail.html', dashboard_name=name)

    # --- API Routes ---
    @app.route('/api/status', methods=['GET'])
    def get_status():
        checks = HealthCheck.query.filter_by(is_active=True).all()
        overall_status = "PASS"
        checks_summary = []
        
        for check in checks:
            # Get latest result
            latest_result = CheckResult.query.filter_by(check_id=check.id).order_by(CheckResult.execution_time.desc()).first()
            status = latest_result.status if latest_result else "UNKNOWN"
            if status in ("FAIL", "ERROR"):
                overall_status = "FAIL" # Strict failure logic as requested
            
            checks_summary.append({
                "id": check.id,
                "name": check.name,
                "description": getattr(check, 'description', ''),
                "dashboard_name": getattr(check, 'dashboard_name', 'US SOD'),
                "category": check.category.name,
                "host": check.host,
                "status": status,
                "last_run": latest_result.execution_time.isoformat() if latest_result else None,
                "message": latest_result.message if latest_result else ""
            })
            
        return jsonify({
            "overall_status": overall_status,
            "total_checks": len(checks),
            "checks": checks_summary
        })

    @app.route('/api/checks', methods=['GET', 'POST'])
    def handle_checks():
        if request.method == 'GET':
            checks = HealthCheck.query.all()
            return jsonify([{
                "id": c.id, "name": c.name, 
                "description": getattr(c, 'description', ''),
                "dashboard_name": getattr(c, 'dashboard_name', 'US SOD'),
                "category_id": c.category_id,
                "category_name": c.category.name,
                "host": c.host, "target_path": c.target_path,
                "search_pattern": c.search_pattern, "ssh_user": c.ssh_user,
                "ssh_key_path": c.ssh_key_path, "is_scheduled": c.is_scheduled,
                "schedule_type": c.schedule_type, "cron_expression": c.cron_expression,
                "is_active": c.is_active, "os_type": getattr(c, "os_type", "linux")
            } for c in checks])
            
        elif request.method == 'POST':
            data = request.json
            cat = Category.query.filter_by(name=data.get('category')).first()
            if not cat:
                return jsonify({"error": "Invalid category"}), 400
            pwd = data.get('password')
            enc_pwd = encrypt_password(pwd) if pwd else None
                
            new_check = HealthCheck(
                name=data.get('name'),
                description=data.get('description', ''),
                dashboard_name=data.get('dashboard_name', 'US SOD'),
                category_id=cat.id,
                host=data.get('host', 'localhost'),
                target_path=data.get('target_path'),
                search_pattern=data.get('search_pattern'),
                ssh_user=data.get('ssh_user'),
                ssh_key_path=data.get('ssh_key_path'),
                is_scheduled=data.get('is_scheduled', False),
                schedule_type=data.get('schedule_type'),
                cron_expression=data.get('cron_expression'),
                is_active=data.get('is_active', True),
                os_type=data.get('os_type', 'linux'),
                encrypted_password=enc_pwd
            )
            db.session.add(new_check)
            db.session.commit()
            sync_scheduler(app)
            return jsonify({"message": "Check created", "id": new_check.id}), 201

    @app.route('/api/checks/<int:check_id>', methods=['PUT', 'DELETE'])
    def update_delete_check(check_id):
        check = HealthCheck.query.get_or_404(check_id)
        if request.method == 'DELETE':
            # Also delete results to prevent constraint issues, or cascade in DB
            CheckResult.query.filter_by(check_id=check.id).delete()
            db.session.delete(check)
            db.session.commit()
            sync_scheduler(app)
            return jsonify({"message": "Deleted"})
            
        elif request.method == 'PUT':
            data = request.json
            if 'name' in data: check.name = data['name']
            if 'description' in data: check.description = data['description']
            if 'dashboard_name' in data: check.dashboard_name = data['dashboard_name']
            if 'host' in data: check.host = data['host']
            if 'target_path' in data: check.target_path = data['target_path']
            if 'search_pattern' in data: check.search_pattern = data['search_pattern']
            if 'ssh_user' in data: check.ssh_user = data['ssh_user']
            if 'ssh_key_path' in data: check.ssh_key_path = data['ssh_key_path']
            if 'is_scheduled' in data: check.is_scheduled = data['is_scheduled']
            if 'schedule_type' in data: check.schedule_type = data['schedule_type']
            if 'cron_expression' in data: check.cron_expression = data['cron_expression']
            if 'is_active' in data: check.is_active = data['is_active']
            if 'os_type' in data: check.os_type = data['os_type']
            if 'password' in data and data['password']: 
                check.encrypted_password = encrypt_password(data['password'])
            if 'category' in data:
                cat = Category.query.filter_by(name=data['category']).first()
                if cat: check.category_id = cat.id
                
            db.session.commit()
            sync_scheduler(app)
            return jsonify({"message": "Updated"})

    @app.route('/api/checks/<int:check_id>/run', methods=['POST'])
    def run_check_manual(check_id):
        check = HealthCheck.query.get_or_404(check_id)
        status, message, metrics = runners.execute_check(check)
        
        import json
        result = CheckResult(
            check_id=check.id,
            status=status,
            message=message,
            metrics_json=json.dumps(metrics) if metrics else None
        )
        db.session.add(result)
        db.session.commit()
        
        return jsonify({
            "status": status,
            "message": message,
            "metrics": metrics
        })

    @app.route('/api/test_connection', methods=['POST'])
    def test_connection():
        data = request.json
        cat = Category.query.filter_by(name=data.get('category')).first()
        if not cat:
            return jsonify({"error": "Invalid category"}), 400
            
        pwd = data.get('password')
        enc_pwd = encrypt_password(pwd) if pwd else None
        
        if not pwd and data.get('id'):
            existing_check = HealthCheck.query.get(data.get('id'))
            if existing_check:
                enc_pwd = existing_check.encrypted_password
                
        temp_check = HealthCheck(
            name="Test Connection",
            category=cat,
            host=data.get('host', 'localhost'),
            target_path=data.get('target_path'),
            search_pattern=data.get('search_pattern'),
            ssh_user=data.get('ssh_user'),
            ssh_key_path=data.get('ssh_key_path'),
            os_type=data.get('os_type', 'linux'),
            encrypted_password=enc_pwd
        )
        
        status, message, metrics = runners.execute_check(temp_check)
        return jsonify({
            "status": status,
            "message": message,
            "metrics": metrics
        })

    @app.route('/api/history', methods=['GET'])
    def get_history():
        # Get last 30 days of data
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        results = CheckResult.query.filter(CheckResult.execution_time >= thirty_days_ago).order_by(CheckResult.execution_time.desc()).limit(1000).all()
        
        history_data = []
        for r in results:
            history_data.append({
                "id": r.id,
                "check_name": r.health_check.name,
                "status": r.status,
                "execution_time": r.execution_time.isoformat(),
                "message": r.message,
                "date": r.date_recorded.isoformat()
            })
        return jsonify(history_data)

    @app.route('/api/categories', methods=['GET'])
    def get_categories():
        cats = Category.query.all()
        return jsonify([{"id": c.id, "name": c.name, "description": c.description} for c in cats])

    @app.route('/api/send_report', methods=['POST'])
    def send_report():
        data = request.json
        to_email = data.get('email')
        if not to_email:
            return jsonify({"error": "Email is required"}), 400
            
        dashboard_name = data.get('dashboard_name')
        
        checks = HealthCheck.query.filter_by(is_active=True)
        if dashboard_name:
            checks = checks.filter_by(dashboard_name=dashboard_name)
        checks = checks.all()
        
        report_data = []
        for check in checks:
            latest_result = CheckResult.query.filter_by(check_id=check.id).order_by(CheckResult.execution_time.desc()).first()
            report_data.append({
                "Check Name": check.name,
                "Dashboard": getattr(check, 'dashboard_name', 'US SOD'),
                "Category": check.category.name,
                "Host": check.host,
                "Status": latest_result.status if latest_result else "UNKNOWN",
                "Last Run": latest_result.execution_time.strftime("%Y-%m-%d %H:%M:%S") if latest_result else "Never",
                "Message": latest_result.message if latest_result else "No details"
            })
            
        import utils
        html_table = utils.json_to_html_table(report_data)
        subject = f"Health Checks Report - {dashboard_name or 'All Dashboards'}"
        body_html = f"<h2>{subject}</h2>" + html_table
        
        try:
            utils.send_email(subject, body_html, [to_email])
            return jsonify({"message": "Report sent successfully to " + to_email})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)
