import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

# Load email credentials from .env file
load_dotenv()
EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

def send_email(recipient_email, subject, body_text, attachment_path=None):
    """Send email with optional attachment"""
    # Create message
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # Add body text
    msg.attach(MIMEText(body_text))
    
    # Add attachment if provided
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
            attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(attachment)
    
    # Send email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✓ Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"× Error sending email: {str(e)}")
        return False