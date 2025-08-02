from flask import Flask, render_template, jsonify, request
import smart_farm
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)

# Configure logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/smartfarm.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Smart Farm startup')

# Global variables for pump control
pump_mode = "manual"  # "auto" or "manual"
auto_pump_thread = None
auto_pump_running = False

# Function to control the pump in auto mode
# This will run in a separate thread
def auto_pump_control():
    global auto_pump_running
    while auto_pump_running and pump_mode == "auto":
        try:
            soil = smart_farm.read_soil_analog()
            current_state = smart_farm.get_pump_state()
            
            if soil is not None:
                if soil < 20 and current_state == "off":
                    smart_farm.set_pump("on")
                    app.logger.info(f"Auto pump ON - Soil moisture: {soil}%")
                elif soil > 60 and current_state == "on":
                    smart_farm.set_pump("off")
                    app.logger.info(f"Auto pump OFF - Soil moisture: {soil}%")
            
            time.sleep(5)
        except Exception as e:
            app.logger.error(f"Auto pump control error: {e}")
            time.sleep(5)

# Route for the main dashboard
@app.route('/')
def index():
    return render_template('index.html')

# API to get sensor data and pump status
@app.route('/api/data')
def api_data():
    try:
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
    except Exception as e:
        app.logger.error(f"Error fetching sensor data: {e}")
        return jsonify({'error': 'Failed to fetch sensor data'}), 500

# API to control the pump
@app.route('/api/pump', methods=['POST'])
def api_pump():
    global pump_mode, auto_pump_thread, auto_pump_running
    
    try:
        data = request.json
        action = data.get('action')
        
        if action == 'toggle' and pump_mode == "manual":
            current_state = smart_farm.get_pump_state()
            new_state = "off" if current_state == "on" else "on"
            smart_farm.set_pump(new_state)
            app.logger.info(f"Manual pump {new_state}")
            return jsonify({'status': 'ok', 'pump': new_state, 'mode': pump_mode})
        
        elif action == 'set_mode':
            new_mode = data.get('mode')
            if new_mode in ['auto', 'manual']:
                pump_mode = new_mode
                app.logger.info(f"Pump mode changed to: {new_mode}")
                
                if pump_mode == "auto":
                    auto_pump_running = True
                    if auto_pump_thread is None or not auto_pump_thread.is_alive():
                        auto_pump_thread = threading.Thread(target=auto_pump_control)
                        auto_pump_thread.daemon = True
                        auto_pump_thread.start()
                else:
                    auto_pump_running = False
                
                return jsonify({'status': 'ok', 'mode': pump_mode})
        
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
        
    except Exception as e:
        # Log the error and return a 500 status code
        app.logger.error(f"Error in pump control: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
