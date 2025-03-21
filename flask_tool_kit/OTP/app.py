from flask import Flask, request, render_template, redirect, url_for, flash
from twilio.rest import Client
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

# Twilio credentials (replace with your actual values)
TWILIO_ACCOUNT_SID = "your_sid"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE_NUMBER = "+1234.........."    

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory OTP store (for demo purposes only)
otp_store = {}

@app.route("/", methods=["GET", "POST"])
def send_otp():
    if request.method == "POST":
        phone = request.form.get("phone")
        if not phone:
            flash("Phone number is required.", "error")
            return redirect(url_for("send_otp"))
        
        # Generate a random 6-digit OTP
        otp = str(random.randint(100000, 999999))
        otp_store[phone] = otp  # Store OTP for this phone number
        
        message_body = f"Your OTP code is: {otp}"
        try:
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=phone
            )
            flash("OTP sent successfully!", "success")
            return redirect(url_for("verify_otp", phone=phone))
        except Exception as e:
            flash(f"Error sending OTP: {e}", "error")
            return redirect(url_for("send_otp"))
    
    return render_template("index.html")

@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    phone = request.args.get("phone")
    if not phone:
        flash("No phone number provided.", "error")
        return redirect(url_for("send_otp"))
    
    if request.method == "POST":
        otp = request.form.get("otp")
        if not otp:
            flash("Please enter the OTP.", "error")
            return redirect(url_for("verify_otp", phone=phone))
        
        # Check the OTP stored for this phone number
        if otp_store.get(phone) == otp:
            # OTP verified; remove from store
            otp_store.pop(phone, None)
            flash("OTP verified successfully!", "success")
            return redirect(url_for("success"))
        else:
            flash("Invalid OTP. Please try again.", "error")
            return redirect(url_for("verify_otp", phone=phone))
    
    return render_template("verify.html", phone=phone)

@app.route("/success")
def success():
    return render_template("success.html")

if __name__ == "__main__":
    app.run(debug=True)
