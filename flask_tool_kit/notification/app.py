from flask import Flask, request, render_template, jsonify
from twilio.rest import Client
import os

app = Flask(__name__)
#TEST NUMBER : +919484985185
# Replace these with your Twilio account credentials
TWILIO_ACCOUNT_SID = "YOUR_SID"
TWILIO_AUTH_TOKEN = "YOUR_AUTH_TOKEN"
TWILIO_PHONE_NUMBER = "+1234......"  # Your Twilio phone number

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send_sms", methods=["POST"])
def send_sms():
    # Get the phone number and message from the form
    to_number = request.form.get("to_number")
    message_body = request.form.get("message")
    
    try:
        # Create and send the SMS message
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        return jsonify({"status": "success", "message_sid": message.sid})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
