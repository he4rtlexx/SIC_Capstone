from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import smart_farm
import threading
import time
from werkzeug.security import generate_password_hash, check_password_hash
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

# Global variables for pump control
pump_mode = "manual"  # "auto" or "manual"
auto_pump_thread = None
auto_pump_running = False

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