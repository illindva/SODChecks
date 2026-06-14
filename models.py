from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255))
    
    checks = db.relationship('HealthCheck', backref='category', lazy=True)

class HealthCheck(db.Model):
    __tablename__ = 'health_check'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    dashboard_name = db.Column(db.String(50), nullable=False, default="US SOD")
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    # Target Configuration
    os_type = db.Column(db.String(20), nullable=False, default="linux")
    host = db.Column(db.String(255), nullable=False) # e.g., 'localhost', '10.0.0.5'
    target_path = db.Column(db.String(500), nullable=False) # Log file path or Process Name/PID
    search_pattern = db.Column(db.String(255), nullable=True) # Used for logs
    ssh_user = db.Column(db.String(50), nullable=True) # SSH username
    ssh_key_path = db.Column(db.String(255), nullable=True) # Path to SSH key on host
    encrypted_password = db.Column(db.String(500), nullable=True) # Encrypted password for Windows
    
    # Scheduling Configuration
    is_scheduled = db.Column(db.Boolean, default=False)
    schedule_type = db.Column(db.String(20)) # 'hourly', 'daily', 'weekly', 'custom_cron'
    cron_expression = db.Column(db.String(50), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = db.relationship('CheckResult', backref='health_check', lazy=True, order_by="desc(CheckResult.execution_time)")

class CheckResult(db.Model):
    __tablename__ = 'check_result'
    id = db.Column(db.Integer, primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey('health_check.id'), nullable=False)
    
    status = db.Column(db.String(20), nullable=False) # 'PASS', 'FAIL', 'WARNING', 'ERROR'
    message = db.Column(db.Text, nullable=True)
    metrics_json = db.Column(db.Text, nullable=True) # e.g. {"uptime": 120, "memory_mb": 50.5}
    
    execution_time = db.Column(db.DateTime, default=datetime.utcnow)
    date_recorded = db.Column(db.Date, default=datetime.utcnow().date) # Useful for daily rollups
    
    def get_metrics(self):
        if self.metrics_json:
            return json.loads(self.metrics_json)
        return {}
