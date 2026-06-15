import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import subprocess
import paramiko
import os
import json
import winrm
from bs4 import BeautifulSoup
import config

def send_email(subject, body_html, to_emails, from_email=None, smtp_server=None, smtp_port=None, smtp_user=None, smtp_password=None, attachments=None):
    from_email = from_email or config.DEFAULT_FROM_EMAIL
    smtp_server = smtp_server or config.SMTP_SERVER
    smtp_port = smtp_port or config.SMTP_PORT
    smtp_user = smtp_user or config.SMTP_USER
    smtp_password = smtp_password or config.SMTP_PASSWORD

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ", ".join(to_emails) if isinstance(to_emails, list) else to_emails

    msg.attach(MIMEText(body_html, 'html'))

    if attachments:
        for attachment in attachments:
            if os.path.exists(attachment):
                with open(attachment, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment)}"'
                msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        if smtp_user and smtp_password:
            server.starttls()
            server.login(smtp_user, smtp_password)
        server.send_message(msg)

def sendChat(message, webhook_url=None):
    webhook_url = webhook_url or config.TEAMS_WEBHOOK_URL
    payload = json.dumps({"text": message})
    cmd = ['curl', '-H', 'Content-Type: application/json', '-d', payload, webhook_url]
    
    # Run the curl command
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Teams notification failed: {result.stderr}")
    return result.stdout

def run_linux_command(host, command, user, password=None, key_path=None):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    
    connect_kwargs = {'username': user, 'timeout': 10}
    if password:
        connect_kwargs['password'] = password
    else:
        if not key_path or not os.path.exists(key_path):
            key_path = os.path.expanduser('~/.ssh/id_rsa')
        connect_kwargs['key_filename'] = key_path
    
    try:
        ssh.connect(host, **connect_kwargs)
        stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        exit_status = stdout.channel.recv_exit_status()
        return out, err, exit_status
    finally:
        ssh.close()

def run_windows_command(host, command, user, password):
    # Using basic auth and HTTP for pywinrm as a simple default.
    # In production, this should ideally use NTLM/Kerberos and HTTPS.
    session = winrm.Session(host, auth=(user, password))
    r = session.run_cmd(command)
    return r.std_out.decode('utf-8'), r.std_err.decode('utf-8'), r.status_code

def json_to_html_table(json_data):
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError:
            return "<p>Invalid JSON string</p>"
            
    if not json_data:
        return "<p>No data</p>"
        
    if isinstance(json_data, dict):
        json_data = [json_data]
        
    if not isinstance(json_data, list) or not all(isinstance(i, dict) for i in json_data):
        return "<p>Data must be a list of dictionaries</p>"

    headers = list(json_data[0].keys())
    
    html = "<table border='1'>\n"
    html += "  <tr>\n"
    for header in headers:
        html += f"    <th>{header}</th>\n"
    html += "  </tr>\n"
    
    for row in json_data:
        html += "  <tr>\n"
        for header in headers:
            html += f"    <td>{row.get(header, '')}</td>\n"
        html += "  </tr>\n"
        
    html += "</table>"
    return html

def html_table_to_json(html_data):
    soup = BeautifulSoup(html_data, 'html.parser')
    table = soup.find('table')
    if not table:
        return "[]"

    rows = table.find_all('tr')
    if not rows:
        return "[]"

    headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
    
    data = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if not cols:
            continue
        row_data = {headers[i]: col.text.strip() for i, col in enumerate(cols) if i < len(headers)}
        data.append(row_data)

    return json.dumps(data)

def run_oracle_query(host, port, service_name, user, password, query):
    import oracledb
    dsn = f"{host}:{port}/{service_name}"
    try:
        with oracledb.connect(user=user, password=password, dsn=dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                return json_to_html_table(data)
    except Exception as e:
        raise Exception(f"Oracle Query Failed: {str(e)}")

def run_mssql_query(host, port, database, user, password, query):
    import pymssql
    try:
        with pymssql.connect(server=host, port=port, user=user, password=password, database=database) as conn:
            with conn.cursor(as_dict=True) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                return json_to_html_table(rows)
    except Exception as e:
        raise Exception(f"MSSQL Query Failed: {str(e)}")

def run_sybase_query(host, port, database, user, password, query):
    import pyodbc
    # Common FreeTDS/Sybase connection string. The exact driver name varies by system.
    # We will use 'FreeTDS' as the standard driver on Linux for Sybase.
    # On Windows, it could be 'Adaptive Server Enterprise'. We'll try to keep it configurable or standard.
    # A generic approach is to construct the DSN string.
    # In a real environment, they might use DSN=MySybaseDB.
    # For now, we will construct a DSN-less connection string using FreeTDS.
    # For cross-platform compatibility without knowing the exact driver name, 
    # the user might need to ensure they have an ODBC driver named "FreeTDS" or "Sybase ASE ODBC Driver".
    # We will default to standard FreeTDS parameters.
    driver_name = "{FreeTDS}" if os.name != 'nt' else "{Adaptive Server Enterprise}"
    conn_str = f"DRIVER={driver_name};Server={host};Port={port};Database={database};UID={user};PWD={password};"
    try:
        with pyodbc.connect(conn_str, timeout=30) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                return json_to_html_table(data)
    except Exception as e:
        raise Exception(f"Sybase Query Failed: {str(e)}\nEnsure ODBC driver '{driver_name}' is installed.")

def run_gemfire_oql(host, user, password, query):
    import requests
    from requests.auth import HTTPBasicAuth
    
    # Ensure host has http/https prefix
    if not host.startswith('http'):
        host = 'http://' + host
        
    url = f"{host}/gemfire-api/v1/queries/adhoc"
    params = {'q': query}
    
    try:
        if user and password:
            response = requests.get(url, params=params, auth=HTTPBasicAuth(user, password), timeout=30)
        else:
            response = requests.get(url, params=params, timeout=30)
            
        response.raise_for_status()
        data = response.json()
        
        # GemFire adhoc query response is typically a list of objects or values
        if isinstance(data, list) and len(data) > 0:
            # If the results are dictionaries, we can directly format them
            if isinstance(data[0], dict):
                return json_to_html_table(data)
            else:
                # Wrap scalar values into dictionaries for the table
                formatted = [{"Result": item} for item in data]
                return json_to_html_table(formatted)
        elif isinstance(data, list) and len(data) == 0:
            return json_to_html_table([{"Result": "No results found"}])
        else:
            # Unexpected format, try to parse what we have
            return json_to_html_table([{"Response": str(data)}])
            
    except Exception as e:
        raise Exception(f"GemFire OQL Query Failed: {str(e)}")
