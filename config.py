import os

# Teams Configuration
TEAMS_WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL', 'https://your-webhook-url-here')

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.example.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'sodchecks@example.com')
