from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_pymongo import PyMongo
import secrets
import qrcode
import base64
from io import BytesIO
import datetime

app = Flask(__name__)

# Configure MongoDB connection (update the URI if needed)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/ev_rental_db'
mongo = PyMongo(app)

# Define collections
users_collection = mongo.db.users
ev_collection = mongo.db.ev
rides_collection = mongo.db.rides

# -------------------------------
# Home page
# -------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# -------------------------------
# Registration & EV Booking (assign vehicle tag)
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get user details from form
        username = request.form.get('username')
        phone_number = request.form.get('phone_number')
        
        # Find an available EV (one that is not assigned)
        available_ev = ev_collection.find_one({"is_assigned": False})
        if not available_ev:
            return "No available EV at the moment. Please try again later."
        
        # Get the EV's tag
        ev_token = available_ev['ev_code']
        
        # Mark the EV as assigned
        ev_collection.update_one(
            {"_id": available_ev["_id"]},
            {"$set": {"is_assigned": True}}
        )
        
        # Save the user along with the assigned EV token
        user_data = {
            "username": username,
            "phone_number": phone_number,
            "ev_token": ev_token
        }
        users_collection.insert_one(user_data)
        
        # Generate a QR code containing the EV token (vehicle tag)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(ev_token)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        
        # Encode the image to Base64 so it can be embedded in HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Render the profile page with the assigned EV token and QR code
        return render_template('profile.html', ev_token=ev_token, qr_code=qr_base64)
    
    return render_template('register.html')

# -------------------------------
# Scan and Unlock EV (compare scanned tag with assigned tag)
# -------------------------------
@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        # Retrieve username and scanned code from the form
        username = request.form.get('username')
        scanned_code = request.form.get('scanned_code')
        
        # Fetch the user from the database
        user = users_collection.find_one({"username": username})
        if not user:
            return jsonify({"success": False, "message": "User not found."})
        
        # Get the assigned EV code from the user document
        assigned_ev_code = user.get('ev_token')
        if not assigned_ev_code:
            return jsonify({"success": False, "message": "No EV assigned to this user."})
        
        # Compare the scanned code with the user's assigned EV code
        if scanned_code != assigned_ev_code:
            return jsonify({"success": False, "message": "Scanned EV code does not match the assigned EV."})
        
        # (Optional) Further check: verify the EV exists in the EV collection.
        ev = ev_collection.find_one({"ev_code": scanned_code})
        if not ev:
            return jsonify({"success": False, "message": "Invalid EV tag."})
        
        # Optionally, check if the EV is locked
        if not ev.get('is_locked', True):
            return jsonify({"success": False, "message": "EV is already unlocked."})
        
        # Unlock the EV: update its status
        ev_collection.update_one(
            {"ev_code": scanned_code},
            {"$set": {"is_locked": False}}
        )
        
        return jsonify({"success": True, "message": "EV unlocked successfully!"})
    
    return render_template('scan.html')

# -------------------------------
# Start a Ride (log start time)
# -------------------------------
@app.route('/start_ride', methods=['POST'])
def start_ride():
    ev_token = request.form.get('ev_token')
    
    # Ensure the EV exists and is unlocked
    ev = ev_collection.find_one({"ev_code": ev_token})
    if not ev:
        return jsonify({"success": False, "message": "Invalid EV token."})
    if ev.get('is_locked', True):
        return jsonify({"success": False, "message": "EV is locked. Please unlock it first."})
    
    # Create a ride log with start time
    ride = {
        "ev_code": ev_token,
        "user_id": ev_token,  # In production, this should be the authenticated user's ID.
        "start_time": datetime.datetime.utcnow(),
        "end_time": None
    }
    rides_collection.insert_one(ride)
    return jsonify({"success": True, "message": "Ride started!"})

# -------------------------------
# End a Ride (log end time and re-lock EV)
# -------------------------------
@app.route('/end_ride', methods=['POST'])
def end_ride():
    ev_token = request.form.get('ev_token')
    
    # Find the active ride for this EV
    ride = rides_collection.find_one({"ev_code": ev_token, "end_time": None})
    if not ride:
        return jsonify({"success": False, "message": "No active ride found for this EV."})
    
    end_time = datetime.datetime.utcnow()
    rides_collection.update_one({"_id": ride["_id"]}, {"$set": {"end_time": end_time}})
    
    # Re-lock the EV
    ev_collection.update_one(
        {"ev_code": ev_token},
        {"$set": {"is_locked": True}}
    )
    return jsonify({"success": True, "message": "Ride ended and EV locked.", "end_time": end_time.isoformat()})

@app.route('/return_ev', methods=['GET'])
def return_ev():
    return render_template('drop_vehicle.html')
@app.route('/drop_vehicle', methods=['POST'])
def drop_vehicle():
    # Retrieve form data: username.
    username = request.form.get('username')
    
    # Find the user by username.
    user = users_collection.find_one({"username": username})
    if not user:
        return "User not found", 404
    
    # Retrieve the stored EV token from the user document.
    stored_ev_code = user.get("ev_token")
    if not stored_ev_code:
        return "No EV is currently assigned to this user.", 400

    # Update the EV document: mark it as locked and not assigned.
    ev_update_result = ev_collection.update_one(
        {"ev_code": stored_ev_code},
        {"$set": {"is_locked": True, "is_assigned": False}}
    )
    
    # Delete the user from the users_collection.
    user_delete_result = users_collection.delete_one({"username": username})
    
    if user_delete_result.deleted_count == 1:
        message = "EV dropped successfully, and your account has been removed."
        return render_template('drop_success.html', message=message)
    else:
        return "Failed to delete the user", 500


if __name__ == '__main__':
    app.run(debug=True)
