# src/whatsapp_meta.py
"""
Meta Official WhatsApp Business Cloud API Dispatcher for Chemkonnect Global
Connects to Meta Graph API (v19.0) to send outbound templates and text messages
directly from the company's official WhatsApp Business number.
"""
import os
import sys
import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "whatsapp_creds.json")

class MetaWhatsAppClient:
    def __init__(self, creds_path: str = CREDS_PATH):
        self.creds_path = creds_path

    def get_credentials(self) -> Dict[str, Any]:
        phone_id = os.environ.get("META_WA_PHONE_NUMBER_ID", "").strip()
        token = os.environ.get("META_WA_ACCESS_TOKEN", "").strip()
        waba_id = os.environ.get("META_WA_BUSINESS_ACCOUNT_ID", "").strip()
        template_name = os.environ.get("META_WA_TEMPLATE_NAME", "").strip()
        template_lang = os.environ.get("META_WA_TEMPLATE_LANG", "en").strip()

        if phone_id and token:
            return {
                "phone_number_id": phone_id,
                "access_token": token,
                "waba_id": waba_id,
                "template_name": template_name,
                "template_lang": template_lang,
                "source": "environment"
            }

        if os.path.exists(self.creds_path):
            try:
                with open(self.creds_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("phone_number_id") and data.get("access_token"):
                        return {
                            "phone_number_id": data.get("phone_number_id", "").strip(),
                            "access_token": data.get("access_token", "").strip(),
                            "waba_id": data.get("waba_id", "").strip(),
                            "template_name": data.get("template_name", "").strip(),
                            "template_lang": data.get("template_lang", "en").strip(),
                            "source": "file"
                        }
            except Exception as e:
                print(f"[!] Warning reading whatsapp_creds.json: {e}")

        return {
            "phone_number_id": "",
            "access_token": "",
            "waba_id": "",
            "template_name": "",
            "template_lang": "en",
            "source": "none"
        }

    def save_credentials(self, phone_number_id: str, access_token: str, 
                         waba_id: str = "", template_name: str = "", template_lang: str = "en") -> bool:
        try:
            os.makedirs(os.path.dirname(self.creds_path), exist_ok=True)
            payload = {
                "phone_number_id": phone_number_id.strip(),
                "access_token": access_token.strip(),
                "waba_id": waba_id.strip(),
                "template_name": template_name.strip(),
                "template_lang": template_lang.strip() or "en"
            }
            with open(self.creds_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception as e:
            print(f"[!] Error saving WhatsApp credentials: {e}")
            return False

    def test_connection(self, phone_number_id: Optional[str] = None, 
                        access_token: Optional[str] = None) -> Dict[str, Any]:
        creds = self.get_credentials()
        pid = (phone_number_id or creds.get("phone_number_id", "")).strip()
        tok = (access_token or creds.get("access_token", "")).strip()

        if not pid or not tok:
            return {
                "success": False,
                "error": "Missing Meta Phone Number ID or Access Token."
            }

        url = f"https://graph.facebook.com/v19.0/{pid}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {tok}",
            "User-Agent": "ChemkonnectSalesEngine/2.1"
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                verified_name = data.get("verified_name") or data.get("display_phone_number") or pid
                return {
                    "success": True,
                    "phone_number_id": pid,
                    "display_phone_number": data.get("display_phone_number", ""),
                    "verified_name": verified_name,
                    "quality_rating": data.get("quality_rating", "UNKNOWN")
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(error_body)
                msg = err_json.get("error", {}).get("message", error_body)
            except Exception:
                msg = error_body
            return {"success": False, "error": f"Meta Graph API error ({e.code}): {msg}"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def format_recipient_phone(self, raw_phone: str) -> str:
        clean = re.sub(r'[^\d]', '', raw_phone)
        if len(clean) == 10:
            clean = "91" + clean
        elif len(clean) == 11 and clean.startswith("0"):
            clean = "91" + clean[1:]
        return clean

    def send_whatsapp_pitch(self, recipient_phone: str, lead_name: str, 
                            product_category: str, contact_person: str = "",
                            custom_message: Optional[str] = None) -> Dict[str, Any]:
        creds = self.get_credentials()
        pid = creds.get("phone_number_id")
        tok = creds.get("access_token")
        template_name = creds.get("template_name")
        template_lang = creds.get("template_lang", "en")

        if not pid or not tok:
            return {
                "success": False,
                "error": "Meta WhatsApp API not configured. Please enter Phone Number ID and Access Token in Settings."
            }

        formatted_phone = self.format_recipient_phone(recipient_phone)
        if not formatted_phone or len(formatted_phone) < 11:
            return {
                "success": False,
                "error": f"Invalid recipient phone number: '{recipient_phone}'."
            }

        url = f"https://graph.facebook.com/v19.0/{pid}/messages"

        if template_name:
            salutation = contact_person.split("(")[0].strip() if contact_person else "Sir/Ma'am"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": formatted_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": template_lang},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": salutation},
                                {"type": "text", "text": lead_name},
                                {"type": "text", "text": product_category}
                            ]
                        }
                    ]
                }
            }
        else:
            salutation = f"Dear {contact_person.split('(')[0].strip()}" if contact_person else f"Attention: Procurement Desk, {lead_name}"
            default_body = (
                f"{salutation},\n\n"
                f"We understand your ongoing commercial requirements for *{product_category}* in Maharashtra.\n\n"
                f"Chemkonnect Global is an authorized B2B wholesale distributor supplying direct from our Dombivli/Thane logistics hub with certified factory-sealed inventory and same-day dispatch.\n\n"
                f"Could we share our wholesale price index and commercial catalog for your current project?\n\n"
                f"Best regards,\n"
                f"*Chemkonnect Global Sales Desk*\n"
                f"🌐 https://chemkonnect.com | 📞 Dombivli/Thane Hub"
            )
            body_text = custom_message.strip() if custom_message else default_body
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": formatted_phone,
                "type": "text",
                "text": {"preview_url": True, "body": body_text}
            }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "User-Agent": "ChemkonnectSalesEngine/2.1"
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                messages = resp_data.get("messages", [])
                message_id = messages[0].get("id") if messages else "sent"
                return {
                    "success": True,
                    "message_id": message_id,
                    "recipient": formatted_phone,
                    "status": "delivered_to_meta",
                    "details": resp_data
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(error_body)
                error_detail = err_json.get("error", {}).get("message", error_body)
            except Exception:
                error_detail = error_body
            return {
                "success": False,
                "error": f"Meta WhatsApp API Error ({e.code}): {error_detail}",
                "raw_response": error_body
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Network or execution error: {str(e)}"
            }

    def get_status(self) -> Dict[str, Any]:
        creds = self.get_credentials()
        tok = creds.get("access_token", "")
        masked_tok = f"{tok[:6]}...{tok[-4:]}" if len(tok) > 10 else ("Configured" if tok else "Not Set")
        return {
            "configured": bool(creds.get("phone_number_id") and creds.get("access_token")),
            "phone_number_id": creds.get("phone_number_id", ""),
            "waba_id": creds.get("waba_id", ""),
            "template_name": creds.get("template_name", ""),
            "template_lang": creds.get("template_lang", "en"),
            "token_masked": masked_tok,
            "source": creds.get("source", "none")
        }
