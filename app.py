import os
import qrcode
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from pygwan import WhatsApp
from datetime import datetime
import logging

app = FastAPI()

# Initialize WhatsApp Messenger (from pygwan)
messenger = WhatsApp(
    token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
    phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID")
)
logging.info("WhatsApp initialized successfully with id " + os.getenv("WHATSAPP_PHONE_NUMBER_ID"))

# Whitelist of users allowed to interact
whitelist = [os.getenv("ADMIN_PHONE_NUMBER"), "263717474333"]

# Verification token for WhatsApp webhook (set this as an environment variable)
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

# Directory to store generated QR codes
QR_CODE_DIR = "qr_codes"

# Ensure the directory exists
if not os.path.exists(QR_CODE_DIR):
    os.makedirs(QR_CODE_DIR)

# Generate a QR code for the name and return the file path
def generate_qr_code(name: str) -> str:
    qr_data = f"Invitation for {name}"
    img = qrcode.make(qr_data)
    file_name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    file_path = os.path.join(QR_CODE_DIR, file_name)
    img.save(file_path)
    return file_path

# Serve the QR code image
@app.get("/qr/{file_name}")
async def serve_qr(file_name: str):
    file_path = os.path.join(QR_CODE_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "QR code not found"}, 404

# WhatsApp webhook verification endpoint
@app.get("/endpoint")
async def verify_token(request: Request):
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")
    if hub_verify_token == VERIFY_TOKEN:
        logging.info("Verified webhook")
        return Response(content=hub_challenge, media_type="text/plain")
    logging.error("Webhook Verification failed")
    return "Invalid verification token"

# WhatsApp webhook endpoint for handling incoming messages
@app.post("/endpoint")
async def webhook(request: Request):
    data = await request.json()
    changed_field = messenger.changed_field(data)
    if changed_field == "messages":
        new_message = messenger.is_message(data)
        if new_message:
            recipient = "".join(filter(str.isdigit, (messenger.get_mobile(data))))
            name = messenger.get_name(data)
            message = messenger.get_message(data)
            message_id = messenger.get_message_id(data=data)

            # Check if the message is to generate an invitation
            if message.lower().startswith("generate invitation for"):
                if recipient not in whitelist:
                    messenger.reply_to_message(message="Sorry, you don't have access to this service. App Tarmica and ask him nicely", recipient_id=recipient, message_id=message_id)
                    return "OK", 200
                
                # Extract the name from the message
                invitation_name = message.split("for", 1)[-1].strip()

                # Generate the QR code for the invitation name
                qr_code_path = generate_qr_code(invitation_name)
                qr_code_filename = os.path.basename(qr_code_path)

                # Construct the URL to serve the QR code
                qr_code_url = f"https://rsvp.up.railway.app/qr/{qr_code_filename}"

                # Send the image URL via WhatsApp
                messenger.send_image(recipient_id=recipient, image_url=qr_code_url, caption=f"Here is the invitation QR code for {invitation_name}")
                return "OK", 200

    return "OK", 200
