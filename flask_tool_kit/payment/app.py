import os
import qrcode
import base64
from io import BytesIO
from flask import Flask, request, render_template, redirect, jsonify
from square.client import Client
import uuid
app = Flask(__name__)
#TEST DATA:
#JOE_DOE@GMAIL.COM
#JOE DOE
#4111 1111 1111 1111
#CVV : 111
#07/29
#38001
# Configure Square client (use sandbox environment for testing)
client = Client(
    access_token="YOUR_ACCESS_TOKEN",
    environment="sandbox"
)

# Your Square location ID and your domain for redirection
LOCATION_ID = "YOUR_LOCATION_ID"
YOUR_DOMAIN = "http://localhost:5000"  # Update if using a public domain

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        amount = request.form.get("amount")
        try:
            amount_cents = int(float(amount) * 100)  # Convert dollars to cents
        except ValueError:
            return "Invalid amount", 400

        # Create a unique idempotency key for the transaction
        idempotency_key = str(uuid.uuid4())

        # Build the request body for the checkout API
        body = {
            "idempotency_key": idempotency_key,
            "order": {
                "order": {
                    "location_id": LOCATION_ID,
                    "line_items": [
                        {
                            "name": "BOOK YOUR TICKET   ",
                            "quantity": "1",
                            "base_price_money": {
                                "amount": amount_cents,
                                "currency": "USD"
                            }
                        }
                    ]
                }
            },
            "ask_for_shipping_address": False,
            "redirect_url": YOUR_DOMAIN + "/success"
        }

        # Create the checkout session using Square's Checkout API
        response = client.checkout.create_checkout(location_id=LOCATION_ID, body=body)
        if response.is_success():
            checkout_url = response.body["checkout"]["checkout_page_url"]

            # Generate a QR code for the checkout URL
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(checkout_url)
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

            return render_template("payment.html", qr_code=qr_code_base64, checkout_url=checkout_url)
        else:
            return jsonify(response.body), 400

    return render_template("index.html")

@app.route("/success")
def success():
    # Square will redirect here after payment completion.
    # You can also verify payment details using Square's API or webhooks.
    return render_template("success.html")

# Example webhook endpoint (configure in your Square dashboard)
@app.route("/webhook", methods=["POST"])
def square_webhook():
    event = request.get_json()
    # You can verify the event type and process accordingly.
    if event and event.get("type") == "payment.updated":
        # Process the payment update event here.
        print("Received payment update:", event)
    return "Webhook received", 200

if __name__ == "__main__":
    app.run(debug=True)
