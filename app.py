from flask import Flask, render_template, jsonify, request
import smart_farm
import threading
import time
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash

auth = HTTPBasicAuth()

# Dummy user for basic authentication
users = {
    "admin": generate_password_hash("12345")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

app = Flask(__name__)

# Global variables for pump control
pump_mode = "manual"  # "auto" or "manual"
auto_pump_thread = None
auto_pump_running = False

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
@auth.login_required
def index():
    return render_template('index.html')

# API endpoint to get sensor data and pump state
@app.route('/api/data')
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

