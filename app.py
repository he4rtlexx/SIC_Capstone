from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import smart_farm
import threading
import time
import os
import json

app = Flask(__name__)

app.secret_key = 'NSi8Q4EuDEbBFjGoSwTHDjU/dJ8eGGaiNiKW9qY+qJQx73gvL7WZU/3iF37E8Rdl'  

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Global variables for pump control
pump_mode = "manual"  # "auto" or "manual"
auto_pump_thread = None
auto_pump_running = False

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

USER_FILE = 'user.json'

# Load user from JSON file
def load_user():
    if not os.path.exists(USER_FILE):
        return {'username': 'admin', 'password': 'admin'}
    with open(USER_FILE) as f:
        return json.load(f)
        
# Save user to JSON file
def save_user(user):
    with open(USER_FILE, 'w') as f:
        json.dump(user, f)

# Load user data
@login_manager.user_loader
def load_user_from_id(user_id):
    user = load_user()
    if user_id == user['username']:
        return User(id=user['username'], username=user['username'], password=user['password'])
    return None

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = load_user()
        username = request.form['username']
        password = request.form['password']
        if username == user['username'] and password == user['password']:
            login_user(User(id=username, username=username, password=password))
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials!')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Change password route
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pass = request.form['current_password']
        new_pass = request.form['new_password']
        user = load_user()
        if current_pass == user['password']:
            user['password'] = new_pass
            save_user(user)
            flash('Password changed successfully!')
            return redirect(url_for('index'))
        else:
            flash('Current password incorrect!')
    return render_template('change_password.html')


# Function to handle automatic pump control in a background thread
def auto_pump_control():
    global auto_pump_running
    while auto_pump_running and pump_mode == "auto":
        try:
            soil = smart_farm.read_soil_analog()
            current_state = smart_farm.get_pump_state()
            
            if soil is not None:
                if soil < 20 and current_state == "off":
                    smart_farm.set_pump("on")
                    print(f"Auto pump ON - Soil moisture: {soil}%")
                elif soil > 60 and current_state == "on":
                    smart_farm.set_pump("off")
                    print(f"Auto pump OFF - Soil moisture: {soil}%")
            
            time.sleep(5)  
        except Exception as e:
            print(f"Auto pump control error: {e}")
            time.sleep(5)

# Flask routes for web interface and API
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# API endpoint to get sensor data and pump state
@app.route('/api/data')
@login_required
def api_data():
    temp, hum = smart_farm.read_sht31()
    soil = smart_farm.read_soil_analog()
    pump_state = smart_farm.get_pump_state()
    return jsonify({
        'temperature': temp,
        'humidity': hum,
        'soil_percent': soil,
        'pump': pump_state,
        'mode': pump_mode
    })

# API endpoint to control the pump
@app.route('/api/pump', methods=['POST'])
@login_required
def api_pump():
    global pump_mode, auto_pump_thread, auto_pump_running
    
    data = request.json
    action = data.get('action')
    
    if action == 'toggle' and pump_mode == "manual":
        # Manual pump toggle
        current_state = smart_farm.get_pump_state()
        new_state = "off" if current_state == "on" else "on"
        smart_farm.set_pump(new_state)
        return jsonify({'status': 'ok', 'pump': new_state, 'mode': pump_mode})
    
    elif action == 'set_mode':
        new_mode = data.get('mode')
        if new_mode in ['auto', 'manual']:
            pump_mode = new_mode
            
            if pump_mode == "auto":
                # Start auto control thread
                auto_pump_running = True
                if auto_pump_thread is None or not auto_pump_thread.is_alive():
                    auto_pump_thread = threading.Thread(target=auto_pump_control)
                    auto_pump_thread.daemon = True
                    auto_pump_thread.start()
            else:
                # Stop auto control
                auto_pump_running = False
            
            return jsonify({'status': 'ok', 'mode': pump_mode})
    
    return jsonify({'status': 'error', 'message': 'Invalid action'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

