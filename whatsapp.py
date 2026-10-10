import time
import requests


GRAPH_API_BASE = "https://graph.facebook.com"


def parse_csv_values(value):
    return [item.strip() for item in str(value).split(",") if item.strip()]


def build_messages_url(phone_number_id, api_version="v25.0"):
    version = str(api_version or "v25.0").strip() or "v25.0"
    phone_id = str(phone_number_id or "").strip()
    return f"{GRAPH_API_BASE}/{version}/{phone_id}/messages"


def send_whatsapp_text(
    access_token,
    phone_number_id,
    recipients,
    body,
    api_version="v25.0",
    preview_url=False,
):
    recipient_list = recipients if isinstance(recipients, list) else parse_csv_values(recipients)
    if not access_token or not phone_number_id or not recipient_list or not body:
        return 0

    url = build_messages_url(phone_number_id, api_version=api_version)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    session = requests.Session()
    session.trust_env = False

    sent_count = 0
    for recipient in recipient_list:
        try:
            response = session.post(
                url,
                headers=headers,
                json={
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "text",
                    "text": {
                        "preview_url": bool(preview_url),
                        "body": str(body)[:4096],
                    },
                },
                timeout=30,
            )
            response.raise_for_status()
            sent_count += 1
            time.sleep(0.5)
        except Exception as exc:
            print(f"WhatsApp text send failed to {recipient}: {exc}")
    return sent_count


def send_whatsapp_image(
    access_token,
    phone_number_id,
    recipients,
    image_link,
    caption="",
    api_version="v25.0",
):
    recipient_list = recipients if isinstance(recipients, list) else parse_csv_values(recipients)
    if not access_token or not phone_number_id or not recipient_list or not image_link:
        return 0

    url = build_messages_url(phone_number_id, api_version=api_version)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    session = requests.Session()
    session.trust_env = False

    sent_count = 0
    for recipient in recipient_list:
        try:
            response = session.post(
                url,
                headers=headers,
                json={
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "image",
                    "image": {
                        "link": image_link,
                        "caption": str(caption)[:1024],
                    },
                },
                timeout=30,
            )
            response.raise_for_status()
            sent_count += 1
            time.sleep(0.5)
        except Exception as exc:
            print(f"WhatsApp image send failed to {recipient}: {exc}")
    return sent_count
