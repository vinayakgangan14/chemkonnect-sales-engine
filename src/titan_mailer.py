# src/titan_mailer.py
"""
Titan Mail (GoDaddy) SMTP Dispatcher for Chemkonnect Global
Connects to smtp.titan.email (port 465 SSL or 587 TLS) to send personalized
B2B quotes, wholesale proposals, and track delivery status.
"""
import sys
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "titan_creds.json")

class TitanMailer:
    def __init__(self, creds_path: str = CREDS_PATH):
        self.creds_path = creds_path

    def get_credentials(self) -> Dict[str, Any]:
        """
        Retrieves SMTP credentials in priority order:
        1. Environment variables (Render / Cloud production)
        2. Local data/titan_creds.json (saved via UI)
        """
        user = os.environ.get("TITAN_SMTP_USER", "").strip()
        password = os.environ.get("TITAN_SMTP_PASSWORD", "").strip()
        host = os.environ.get("TITAN_SMTP_HOST", "smtp.titan.email").strip()
        port = int(os.environ.get("TITAN_SMTP_PORT", 465))
        sender_name = os.environ.get("TITAN_SENDER_NAME", "Chemkonnect Global Sales Desk").strip()

        if user and password:
            return {
                "user": user,
                "password": password,
                "host": host,
                "port": port,
                "sender_name": sender_name,
                "source": "environment"
            }

        if os.path.exists(self.creds_path):
            try:
                with open(self.creds_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("user") and data.get("password"):
                        return {
                            "user": data.get("user", "").strip(),
                            "password": data.get("password", "").strip(),
                            "host": data.get("host", "smtp.titan.email").strip(),
                            "port": int(data.get("port", 465)),
                            "sender_name": data.get("sender_name", "Chemkonnect Global Sales Desk").strip(),
                            "source": "file"
                        }
            except Exception as e:
                print(f"[!] Warning reading titan_creds.json: {e}")

        return {
            "user": "",
            "password": "",
            "host": host,
            "port": port,
            "sender_name": sender_name,
            "source": "none"
        }

    def save_credentials(self, user: str, password: str, host: str = "smtp.titan.email", 
                         port: int = 465, sender_name: str = "Chemkonnect Global Sales Desk") -> Dict[str, Any]:
        """
        Saves credentials to data/titan_creds.json securely.
        """
        os.makedirs(os.path.dirname(self.creds_path), exist_ok=True)
        payload = {
            "user": user.strip(),
            "password": password.strip(),
            "host": host.strip() or "smtp.titan.email",
            "port": int(port) if port else 465,
            "sender_name": sender_name.strip() or "Chemkonnect Global Sales Desk"
        }
        with open(self.creds_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return {"status": "success", "message": "Titan Mail credentials saved successfully."}

    def test_connection(self, user: Optional[str] = None, password: Optional[str] = None, 
                        host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
        """
        Tests SMTP handshake and login authentication against Titan Mail servers.
        """
        creds = self.get_credentials()
        test_user = user or creds.get("user")
        test_pass = password or creds.get("password")
        test_host = host or creds.get("host", "smtp.titan.email")
        test_port = port or creds.get("port", 465)

        if not test_user or not test_pass:
            return {
                "success": False,
                "error": "Missing Titan Mail username or password. Please configure them in Settings."
            }

        try:
            if int(test_port) == 465:
                with smtplib.SMTP_SSL(test_host, int(test_port), timeout=15) as server:
                    server.login(test_user, test_pass)
            else:
                with smtplib.SMTP(test_host, int(test_port), timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(test_user, test_pass)

            return {
                "success": True,
                "user": test_user,
                "host": test_host,
                "port": test_port,
                "message": f"Successfully authenticated with Titan Mail ({test_user}) via {test_host}:{test_port}"
            }
        except smtplib.SMTPAuthenticationError as e:
            return {
                "success": False,
                "error": f"Authentication failed for '{test_user}'. Please check your Titan Mail password or generate an App Password in GoDaddy Titan Webmail. Details: {e.smtp_error.decode() if hasattr(e, 'smtp_error') else str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection to {test_host}:{test_port} failed: {str(e)}"
            }

    def get_status(self) -> Dict[str, Any]:
        creds = self.get_credentials()
        configured = bool(creds.get("user") and creds.get("password"))
        user = creds.get("user", "")
        masked_user = ""
        if user and "@" in user:
            name_part, domain_part = user.split("@", 1)
            masked_name = name_part[:2] + "***" if len(name_part) > 2 else name_part + "***"
            masked_user = f"{masked_name}@{domain_part}"

        return {
            "configured": configured,
            "sender_email": user,
            "masked_email": masked_user,
            "sender_name": creds.get("sender_name", "Chemkonnect Global Sales Desk"),
            "host": creds.get("host", "smtp.titan.email"),
            "port": creds.get("port", 465),
            "source": creds.get("source", "none")
        }

    def build_html_pitch(self, recipient_name: str, subject: str, body_text: str) -> str:
        """
        Wraps plain text pitch into a sleek, professional B2B email template.
        """
        # Convert plain text newlines to clean HTML paragraphs
        formatted_body = body_text.replace("\n\n", "</p><p style='margin: 12px 0; color: #334155; line-height: 1.6;'>")
        formatted_body = formatted_body.replace("\n", "<br/>")

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
  .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
  .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px; color: #ffffff; border-bottom: 3px solid #06b6d4; }}
  .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }}
  .header p {{ margin: 4px 0 0 0; font-size: 13px; color: #94a3b8; }}
  .badge {{ display: inline-block; background: rgba(6, 182, 212, 0.15); color: #06b6d4; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; margin-top: 8px; border: 1px solid rgba(6, 182, 212, 0.3); }}
  .content {{ padding: 28px 24px; font-size: 14px; line-height: 1.6; color: #334155; }}
  .highlight-box {{ background: #f0fdf4; border-left: 4px solid #10b981; padding: 14px 18px; margin: 20px 0; border-radius: 0 8px 8px 0; font-size: 13px; color: #166534; }}
  .footer {{ background: #f1f5f9; padding: 20px 24px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; line-height: 1.5; }}
  .footer strong {{ color: #0f172a; }}
  .cta-btn {{ display: inline-block; background: #0284c7; color: #ffffff !important; padding: 10px 20px; font-weight: 600; text-decoration: none; border-radius: 6px; margin-top: 16px; font-size: 13px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>CHEMKONNECT GLOBAL</h1>
    <p>Authorized B2B Material Supply & Project Procurement</p>
    <div class="badge">Dyson &bull; Pidilite &bull; Gypsum &bull; Marine Ply &bull; JSW Joints &bull; Solvents</div>
  </div>
  <div class="content">
    <p style="margin: 0 0 14px 0; color: #334155; font-size: 14px; line-height: 1.6;">{formatted_body}</p>
    <div class="highlight-box">
      <strong>Fast Dispatch Hub:</strong> Dombivli / Thane Warehouse with dedicated fleet dispatch across Mumbai MMR, Pune, Gujarat, and Pan-India. GST compliant wholesale billing on all orders.
    </div>
  </div>
  <div class="footer">
    <strong>Chemkonnect Global Sales Desk</strong><br/>
    Phone / WhatsApp: +91 76780 51141 &bull; Email: info@chemkonnect.com<br/>
    Industrial Logistics Hub: Dombivli / Thane, Maharashtra, India<br/>
    <a href="https://chemkonnect.com" style="color: #0284c7; text-decoration: none;">www.chemkonnect.com</a>
  </div>
</div>
</body>
</html>"""
        return html

    def send_pitch_email(self, to_email: str, subject: str, body_text: str, 
                         recipient_name: str = "", lead_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Dispatches email through Titan Mail SMTP.
        Returns outcome dict: {"success": bool, "error": str, "message_id": str}
        """
        creds = self.get_credentials()
        user = creds.get("user")
        password = creds.get("password")
        host = creds.get("host", "smtp.titan.email")
        port = creds.get("port", 465)
        sender_name = creds.get("sender_name", "Chemkonnect Global Sales Desk")

        if not user or not password:
            return {
                "success": False,
                "error": "Titan Mail credentials not configured. Please add your GoDaddy Titan email and password in Settings."
            }

        to_clean = to_email.strip()
        if not to_clean or "@" not in to_clean:
            return {
                "success": False,
                "error": f"Invalid recipient email address: '{to_email}'"
            }

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{user}>"
        msg["To"] = to_clean
        msg["Subject"] = subject
        msg["Reply-To"] = user

        # Attach text part
        text_part = MIMEText(body_text, "plain", "utf-8")
        msg.attach(text_part)

        # Attach HTML part
        html_content = self.build_html_pitch(recipient_name=recipient_name, subject=subject, body_text=body_text)
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        try:
            if int(port) == 465:
                with smtplib.SMTP_SSL(host, int(port), timeout=20) as server:
                    server.login(user, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, int(port), timeout=20) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(user, password)
                    server.send_message(msg)

            return {
                "success": True,
                "recipient_email": to_clean,
                "sender_email": user,
                "subject": subject,
                "message": f"Email pitch successfully dispatched to {to_clean} via Titan Mail."
            }
        except smtplib.SMTPAuthenticationError as e:
            return {
                "success": False,
                "error": f"Titan Mail authentication failed for {user}: {e.smtp_error.decode() if hasattr(e, 'smtp_error') else str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"SMTP Dispatch Error ({host}:{port}): {str(e)}"
            }

if __name__ == "__main__":
    tm = TitanMailer()
    status = tm.get_status()
    print("Titan Mailer Initialized. Status:", status)
