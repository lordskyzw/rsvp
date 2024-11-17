import os
import json
import uvicorn
from fastapi import FastAPI, Request, Response
from pygwan import WhatsApp
import logging
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1, hashes
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from Crypto.PublicKey import RSA

private_key_content = """-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFJDBWBgkqhkiG9w0BBQ0wSTAxBgkqhkiG9w0BBQwwJAQQsOYObTR5aJsZb+x3
QQsnQQICCAAwDAYIKoZIhvcNAgkFADAUBggqhkiG9w0DBwQIisHHhMrfFW8EggTI
ZSLLBhVHmLrDYedIRtWfLFiA+IaNSlkIYMtsP74VZCAmZ6NL5UxdP8uVeHjuiKZ0
RIcquVz4hn98Zfi1WT2Bhs49Bqx1l6KExdrMf1n1IW5/WBq4pH6ZCzV1J1ePqwvb
WcqI8equDXkeElpLPDdSPHqCaFBLy6Y8WjvkucPdb50O1hQXwFapLwX8QnPUAhKe
NwYHafmWBHtsWiWIlW+aUJ7t2XR5d7dgbJQuU8H5bfeLRLLI4ayUJmS9vVEy+agy
sf4DKWPO8AqnVpMcEajS6X6SncvaWJFdF0PDxRyNzCH0xg0YL3+A6sUH69llzK24
IDvkLeqSZdVNPyy0BWlUmVHHVRGqEtpwnih2yK7q6de/occNBkfaOXYZkxxMQ0+d
/rKDheQT/ycRFPraR8zfYQ1JEIiWunTPOlFxnFwHF5by6vy+nv9DeiIykD5nT7ZR
Xa7Ap5/KMnN0gQ+IuSKRoBt0a0GOSZsMTEAt9DxwZNb7ZmEqsKKvmI0nfcGqpXX1
RzZcSZnvzItr06jnu+ZyVE6DM+uMsDi0smgitFaj3fcfA0RrRIhBWVA+ttvBfIQ5
9FIQWZtkWyOOnuQ/uePEPki9rD5uTEUxcFe82oV+89ReF2Mi5fmQHndJeqx/TeaZ
R8QGIcplf7Y4vfJ7UrZf3f0BZAP4hkZAF8dCqchCbBelIc1Zz87MBp3wvxG8ZmLq
KwIGK6tHtnHMmTf4RXDgxKlX6JvzYg/BJAnl47Sfe3wWdfuAQT66DfpOfm7eLucL
RCYVGy5sV81WH1eGs2Dukijwe6zt3KM8fZlnaoiyqRjD41pobT2iJunUobzABb42
AyPA9GVSxyyK0TtpkRjJNaPJCWJJimx/4CF6DQ9LFr+xxgn8lY4WfHMOWctM1Dho
5wJ6RaFITw7H4hIA1kpGK3XFxvVpRn/PzzyY++1jgZ45NQ9I6f9K7iVOTS4Ql/Ta
crX9sQSMPl0C/JVq94ewdo12PLNAG+wKcabPGNtOKNiJIl47s1t0oLltiEIX6EQE
yOFhaJmUeHgEYYyjifbVksPAtPHa8sbqHOodMV8hpEb/+cVfjN9tKezw9TAd98oY
2YXM/Zv8NkjbLwbGXCZFMf6s/elY9fE/PgWd58dqHrc5tP75FoBkylnK50FQRa4Y
gL6gwhczqix1Dgpji1ZfFMV+bQjVyu6fAeOCA75DsJwLJHEbrnwZfY+5W10xN7Yi
fXdZYo6Y8a+V98EW7TMmI2sC9rT7cCCzxXRNJ8pasj+OzZCCaqOLBhcrTiuNpQqs
RzbP6u7eVuJrblEZyEJ/N/0uPeKJfaER1ifzLjWxycwxwvRFspdrL89V9ZSNv8j9
xB85H+yy9rIrnCL4y3zKj48sBP/2ajrmwIYiAWi1YSuqvcmal0iu3jcCPVCsfhST
vqAloYdD2M47iscS6PLJlSPopcvxBbc9AYVGGQjnMbq9WfzrCJDI8K3XeLggObv8
0d20xHPSuKc21BPBRF1FlhbZ4ZGjf9b8k2F//A19FdKxLpGVVV7dpp9ueWvFPRXA
AeRlTqhn0jF00lnw+XYY8QEFTNm815xjkQ0gJcLABkPYbWAA2Pfab2Onjl6z2k7b
iSIx9rg1R0lPZQZP+F4Oo7cDSBMVJ2Kf
-----END ENCRYPTED PRIVATE KEY-----"""
#private_key = load_pem_private_key(private_key_content.encode('utf-8'), passphrase="12580")


# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()


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




def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
    flow_data = b64decode(encrypted_flow_data_b64)
    iv = b64decode(initial_vector_b64)

    # Decrypt the AES encryption key
    encrypted_aes_key = b64decode(encrypted_aes_key_b64)
    private_key = load_pem_private_key(
        private_key_content.encode('utf-8'), password=b'12580')
    aes_key = private_key.decrypt(encrypted_aes_key, OAEP(
        mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

    # Decrypt the Flow data
    encrypted_flow_data_body = flow_data[:-16]
    encrypted_flow_data_tag = flow_data[-16:]
    decryptor = Cipher(algorithms.AES(aes_key),
                       modes.GCM(iv, encrypted_flow_data_tag)).decryptor()
    decrypted_data_bytes = decryptor.update(
        encrypted_flow_data_body) + decryptor.finalize()
    decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
    return decrypted_data, aes_key, iv


def encrypt_response(response, aes_key, iv):
    # Flip the initialization vector
    flipped_iv = bytearray()
    for byte in iv:
        flipped_iv.append(byte ^ 0xFF)

    # Encrypt the response data
    encryptor = Cipher(algorithms.AES(aes_key),
                       modes.GCM(flipped_iv)).encryptor()
    return b64encode(
        encryptor.update(json.dumps(response).encode("utf-8")) +
        encryptor.finalize() +
        encryptor.tag
    ).decode("utf-8")


# Default route
@app.get("/")
async def root():
    logging.info("Hello World Endpoint")
    return {"message": "Hello World"}

@app.post("/")
async def root(request: Request):
    data = await request.json()
    logging.info(data)
    encrypted_flow_data_b64 = data['encrypted_flow_data']
    encrypted_aes_key_b64 = data['encrypted_aes_key']
    initial_vector_b64 = data['initial_vector']

    # Step 1: Decrypt AES key using RSA
    try:
        decrypted_data, aes_key, iv = decrypt_request(
            encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64)
        logging.info(f"Decrypted flow data: {decrypted_data}")
    except Exception as e:
        logging.error(f"Error decrypting data: {e}")
        return Response(content="Error decrypting AES key", media_type="text/plain")

    # Step 2: Process the request
    # this is the part where we implement the business logic
    
    # Step 3: Encrypt the response
    try:
        encrypted_response = encrypt_response({"data": {"status": "active"}}, aes_key, iv)
    except Exception as e:
        logging.error(f"Error encrypting response: {e}")
        return Response(content="Error encrypting response", media_type="text/plain")

    # Return the encrypted response
    return Response(content=encrypted_response, media_type="text/plain")



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



# Main function to start the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # If deploying, ensure this uses a valid port
    uvicorn.run("app:app", host="0.0.0.0", port=port)
