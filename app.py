from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import threading
import time
import json
from werkzeug.security import generate_password_hash, check_password_hash
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os


load_dotenv()
app = Flask(__name__)

# Configuration for Flask app and database
app.secret_key = os.getenv('APP_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and login manager
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Global dictionary to hold sensor data and pump state
sensor_data = { 
    'temperature': None,
    'humidity': None,
    'soil_percent': None,
    'pump': 'off',
    'mode': 'manual'
}

# MQTT setup
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883

def on_connect(client, userdata, flags, rc):
    client.subscribe('farm/sensor')
    client.subscribe('farm/pump_state')

def on_message(client, userdata, msg):
    global sensor_data
    if msg.topic == 'farm/sensor':
        try:
            data = json.loads(msg.payload.decode())
            sensor_data.update(data)
        except Exception as e:
            print(f"Error parsing sensor data: {e}")
    elif msg.topic == 'farm/pump_state':
        sensor_data['pump'] = msg.payload.decode()

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

def mqtt_thread():
    mqtt_client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()


# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Create the database and a default admin user
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        user = User(username='admin')
        user.set_password('admin')
        db.session.add(user)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!')
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
        if current_user.check_password(current_pass):
            current_user.set_password(new_pass)
            db.session.commit()
            return redirect(url_for('index'))
        else:
            flash('Current password incorrect!')
    return render_template('change_password.html')


# Flask routes for web interface and API
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# API endpoint to get sensor data and pump state
@app.route('/api/data')
@login_required
def api_data():
    return jsonify(sensor_data)

# API endpoint to control the pump and mode
@app.route('/api/pump', methods=['POST'])
@login_required
def api_pump():
    data = request.json
    action = data.get('action')
    if action == 'toggle' and sensor_data['mode'] == "manual":
        # Toggle pump
        new_state = "off" if sensor_data['pump'] == "on" else "on"
        mqtt_client.publish('farm/pump_control', new_state)
        return jsonify({'status': 'ok', 'pump': new_state, 'mode': sensor_data['mode']})
    elif action == 'set_mode':
        new_mode = data.get('mode')
        if new_mode in ['auto', 'manual']:
            sensor_data['mode'] = new_mode
            mqtt_client.publish('farm/mode', new_mode)
            return jsonify({'status': 'ok', 'mode': new_mode})
    return jsonify({'status': 'error', 'message': 'Invalid action'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

