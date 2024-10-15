import os
import qrcode
import uvicorn
from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pygwan import WhatsApp
from datetime import datetime
import logging
import time

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()

# Directory to store HTML templates
templates = Jinja2Templates(directory="templates")

# Initialize WhatsApp Messenger (from pygwan)
messenger = WhatsApp(
    token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
    phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID")
)
logging.info("WhatsApp initialized successfully with id " + os.getenv("WHATSAPP_PHONE_NUMBER_ID"))

# Whitelist of users allowed to interact
whitelist = ["263779281345", "263717474333"]

# Verification token for WhatsApp webhook (set this as an environment variable)
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

# Directory to store generated QR codes
QR_CODE_DIR = "qr_codes"

# In-memory store to track QR code usage
used_qr_codes = set()

# Ensure the directory exists
if not os.path.exists(QR_CODE_DIR):
    os.makedirs(QR_CODE_DIR)

# Generate a QR code for the name and return the file path
def generate_qr_code(name: str) -> str:
    qr_data = f"https://rsvp-production.up.railway.app/invite/{name}"
    img = qrcode.make(qr_data)
    file_name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    file_path = os.path.join(QR_CODE_DIR, file_name)
    img.save(file_path)
    return file_path

# Default route
@app.get("/")
async def root():
    return {"message": "Hello World"}

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
    logging.info("Received a new message")
    data = await request.json()
    changed_field = messenger.changed_field(data)
    if changed_field == "messages":
        new_message = messenger.is_message(data)
        if new_message:
            recipient = "".join(filter(str.isdigit, (messenger.get_mobile(data))))
            name = messenger.get_name(data)
            logging.info(f"New message from {name} ({recipient}): {messenger.get_message(data)}")
            message = messenger.get_message(data)

            message_id = messenger.get_message_id(data=data)
            messenger.mark_as_read(message_id=message_id)

            # Check if the message is to generate an invitation
            if message.lower().startswith("generate invitation for"):
                if recipient not in whitelist:
                    messenger.reply_to_message(
                        message="Sorry, you don't have access to this service. Ask Tarmica nicely.",
                        recipient_id=recipient,
                        message_id=message_id
                    )
                    return "OK", 200

                # Extract the name from the message
                invitation_name = message.split("for", 1)[-1].strip()

                # Generate the QR code for the invitation name
                qr_code_path = generate_qr_code(invitation_name)
                qr_code_filename = os.path.basename(qr_code_path)

                if os.path.exists(qr_code_path) and os.path.isfile(qr_code_path):
                    # Construct the URL to serve the QR code
                    qr_code_url = f"https://rsvp-production.up.railway.app/qr/{qr_code_filename}"
                    logging.info(f"Generated QR code for {invitation_name} at {qr_code_url}\npath: {qr_code_path}")

                    # Send the image URL via WhatsApp
                    response = messenger.upload_pic(media_path=qr_code_path, mime_type="image/png")
                    id = response["id"]
                    logging.info(f"Uploaded QR code image with ID {id}")

                    time.sleep(3)  # Wait for the image to be uploaded

                    messenger.send_image(
                        recipient_id=recipient,
                        image=id,
                        link=False,
                        caption=f"Here is the invitation QR code for {invitation_name}"
                    )
                    return "OK", 200
                else:
                    logging.error(f"File not found or invalid: {qr_code_path}")
                    return "Error: QR code file not found", 404

    return "OK", 200

# POST endpoint when a QR code is scanned and the user accepts the invitation
@app.get("/invite/{name}")
async def invite_person(name: str, request: Request):
    qr_code_filename = f"{name}.png"  # Assuming the filename follows a pattern based on the name
    qr_code_url = f"https://rsvp-production.up.railway.app/qr/{qr_code_filename}"
    
    if name in used_qr_codes:
        return templates.TemplateResponse("already_used.html", {
            "request": request,
            "name": name,
            "qr_code_url": qr_code_url
        })
    
    used_qr_codes.add(name)
    
    return templates.TemplateResponse("invitation.html", {
        "request": request,
        "name": name,
        "qr_code_url": qr_code_url
    })

# Accept invitation form processing
@app.post("/accept")
async def accept_invitation(name: str = Form(...)):
    return HTMLResponse(f"<h1>Thank you, {name}. You have accepted the invitation.</h1>")

# Main function to start the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # If deploying, ensure this uses a valid port
    uvicorn.run("app:app", host="0.0.0.0", port=port)
