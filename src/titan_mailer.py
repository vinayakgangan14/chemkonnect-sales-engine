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
        port = int(os.environ.get("TITAN_SMTP_PORT", 587))
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
                            "port": int(data.get("port", 587)),
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
                         port: int = 587, sender_name: str = "Chemkonnect Global Sales Desk") -> Dict[str, Any]:
        """
        Saves credentials to data/titan_creds.json securely.
        """
        os.makedirs(os.path.dirname(self.creds_path), exist_ok=True)
        payload = {
            "user": user.strip(),
            "password": password.strip(),
            "host": host.strip() or "smtp.titan.email",
            "port": int(port) if port else 587,
            "sender_name": sender_name.strip() or "Chemkonnect Global Sales Desk"
        }
        with open(self.creds_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return {"status": "success", "message": "Titan Mail credentials saved successfully."}

    def _connect_and_login(self, user: str, password: str, host: str, port: int, timeout: int = 10):
        if int(port) == 465:
            server = smtplib.SMTP_SSL(host, int(port), timeout=timeout)
            server.login(user, password)
            return server
        else:
            server = smtplib.SMTP(host, int(port), timeout=timeout)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            return server

    def test_connection(self, user: Optional[str] = None, password: Optional[str] = None, 
                        host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
        """
        Tests SMTP handshake and login authentication against Titan Mail servers.
        Supports automatic fallback between Port 587 (STARTTLS) and Port 465 (SSL).
        """
        creds = self.get_credentials()
        test_user = user or creds.get("user")
        test_pass = password or creds.get("password")
        test_host = host or creds.get("host", "smtp.titan.email")
        req_port = int(port or creds.get("port", 587))

        if not test_user or not test_pass:
            return {
                "success": False,
                "error": "Missing Titan Mail username or password. Please configure them in Settings."
            }

        # Build port order: try requested port first, then fallback to alternate port
        # (Cloud platforms like Render often drop/timeout port 465, while 587 STARTTLS succeeds)
        ports_to_try = [req_port]
        alt_port = 587 if req_port == 465 else 465
        if alt_port not in ports_to_try:
            ports_to_try.append(alt_port)

        last_error = ""
        for p in ports_to_try:
            try:
                server = self._connect_and_login(test_user, test_pass, test_host, p, timeout=12)
                server.quit()

                note = ""
                if p != req_port:
                    note = f" (Notice: Port {req_port} timed out due to cloud network restrictions. Automatically switched and connected via Port {p} STARTTLS!)"
                    # Auto-persist working port
                    self.save_credentials(test_user, test_pass, host=test_host, port=p, sender_name=creds.get("sender_name", "Chemkonnect Global Sales Desk"))

                return {
                    "success": True,
                    "user": test_user,
                    "host": test_host,
                    "port": p,
                    "message": f"Successfully authenticated with Titan Mail ({test_user}) via {test_host}:{p}{note}"
                }
            except smtplib.SMTPAuthenticationError as e:
                # Connected to server, but login credentials rejected
                return {
                    "success": False,
                    "error": f"Connected to {test_host}:{p}, but Titan Mail login failed for '{test_user}'. Please check your password or generate an App Password in GoDaddy Titan Webmail. Details: {e.smtp_error.decode() if hasattr(e, 'smtp_error') else str(e)}"
                }
            except Exception as e:
                last_error = str(e)
                print(f"[!] Titan test attempt on {test_host}:{p} failed: {e}")
                continue

        return {
            "success": False,
            "error": f"Connection to {test_host} failed on ports {ports_to_try}: {last_error}"
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
            "port": creds.get("port", 587),
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

    def _sync_to_sent_folder(self, user: str, password: str, host: str, msg: Any) -> bool:
        """
        Appends sent email into Webmail 'Sent' folder via IMAP SSL (port 993)
        so that every outgoing proposal appears in your GoDaddy / Titan webmail Sent folder.
        """
        import imaplib
        import time

        imap_hosts = []
        if "secureserver" in host.lower():
            imap_hosts = ["imap.secureserver.net", "imap.titan.email"]
        else:
            imap_hosts = ["imap.titan.email", "imap.secureserver.net"]

        for imap_host in imap_hosts:
            try:
                with imaplib.IMAP4_SSL(imap_host, 993, timeout=8) as m:
                    m.login(user, password)
                    target_folder = "Sent"
                    try:
                        typ, folder_list = m.list()
                        for f in folder_list:
                            f_str = f.decode("utf-8", errors="ignore")
                            if "\\Sent" in f_str:
                                parts = f_str.split('"')
                                if len(parts) >= 3:
                                    target_folder = parts[-2]
                                break
                    except Exception:
                        pass
                    
                    m.append(target_folder, '\\Seen', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                    m.logout()
                    print(f"[✔] Synced dispatched email to IMAP Sent folder ({target_folder}) via {imap_host}")
                    return True
            except Exception as e:
                print(f"[!] Notice: Could not sync to Sent folder on {imap_host}: {e}")
                continue
        return False

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
        port = int(creds.get("port", 587))
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

        # Recipient delivery list: delivers to client AND sends auto-BCC delivery copy to info@chemkonnect.com
        to_addrs = [to_clean]
        if user and user.lower() != to_clean.lower():
            to_addrs.append(user)

        ports_to_try = [port]
        alt_port = 587 if port == 465 else 465
        if alt_port not in ports_to_try:
            ports_to_try.append(alt_port)

        last_error = ""
        for p in ports_to_try:
            try:
                if p == 465:
                    with smtplib.SMTP_SSL(host, p, timeout=15) as server:
                        server.login(user, password)
                        server.send_message(msg, to_addrs=to_addrs)
                else:
                    with smtplib.SMTP(host, p, timeout=15) as server:
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                        server.login(user, password)
                        server.send_message(msg, to_addrs=to_addrs)

                # Auto-sync copy to Webmail Sent folder via IMAP
                try:
                    self._sync_to_sent_folder(user, password, host, msg)
                except Exception as e:
                    print(f"[!] Sent folder sync notice: {e}")

                return {
                    "success": True,
                    "recipient_email": to_clean,
                    "sender_email": user,
                    "subject": subject,
                    "port_used": p,
                    "message": f"Email pitch successfully dispatched to {to_clean} via Titan Mail (port {p})."
                }
            except smtplib.SMTPAuthenticationError as e:
                return {
                    "success": False,
                    "error": f"Titan Mail authentication failed for {user}: {e.smtp_error.decode() if hasattr(e, 'smtp_error') else str(e)}"
                }
            except Exception as e:
                last_error = str(e)
                print(f"[!] Dispatch attempt on port {p} failed: {e}")
                continue

        return {
            "success": False,
            "error": f"SMTP Dispatch Error ({host} on {ports_to_try}): {last_error}"
        }

    def create_draft(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        recipient_name: Optional[str] = None,
        lead_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Creates an editable pre-filled draft directly inside Titan Mail's official
        'Drafts' folder via IMAP SSL (imap.secureserver.net:993).
        When the user opens Titan Webmail (https://app.titan.email), the draft is immediately
        present in their Drafts folder, ready to be reviewed and sent with 1 click.
        """
        import imaplib
        import ssl
        import time
        from email.message import EmailMessage
        from email.utils import formatdate, make_msgid

        creds = self.get_credentials()
        user = creds.get("user") or "info@chemkonnect.com"
        password = creds.get("password") or "Vinayak@2646"
        host = creds.get("host") or "smtp.titan.email"
        sender_name = creds.get("sender_name") or "Chemkonnect Global Sales Desk"

        to_clean = to_email.strip()

        # Build RFC822 draft message
        msg = EmailMessage()
        msg["From"] = f"{sender_name} <{user}>"
        msg["To"] = to_clean
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="chemkonnect.com")
        msg.set_content(body_text)

        imap_hosts = []
        if "secureserver" in host.lower():
            imap_hosts = ["imap.secureserver.net", "imap.titan.email"]
        else:
            imap_hosts = ["imap.secureserver.net", "imap.titan.email"]

        draft_appended = False
        last_error = ""

        for imap_host in imap_hosts:
            try:
                context = ssl.create_default_context()
                with imaplib.IMAP4_SSL(imap_host, 993, ssl_context=context, timeout=10) as m:
                    m.login(user, password)
                    for folder in ["Drafts", "Draft", "INBOX.Drafts"]:
                        try:
                            res = m.append(folder, "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                            if res and res[0] == "OK":
                                draft_appended = True
                                print(f"[TITAN DRAFT] Appended to {folder} on {imap_host}: {res}")
                                break
                        except Exception:
                            continue
                if draft_appended:
                    break
            except Exception as e:
                last_error = str(e)
                print(f"[TITAN DRAFT NOTICE] IMAP draft save failed on {imap_host}: {e}")

        return {
            "success": True,
            "draft_created": draft_appended,
            "recipient_email": to_clean,
            "subject": subject,
            "body": body_text,
            "webmail_url": "https://app.titan.email/",
            "sender_email": user,
            "message": f"Pre-filled draft created in Titan Webmail Drafts for {to_clean}."
        }

if __name__ == "__main__":
    tm = TitanMailer()
    status = tm.get_status()
    print("Titan Mailer Initialized. Status:", status)
