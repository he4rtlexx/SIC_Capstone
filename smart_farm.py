from gpiozero import MCP3008, OutputDevice
import board
import busio
import adafruit_sht31d
import time

soil_sensor = MCP3008(channel=0)

pump = OutputDevice(27, active_high=True, initial_value=False)

i2c = busio.I2C(board.SCL, board.SDA)
sht31 = adafruit_sht31d.SHT31D(i2c)

# Function to read temperature and humidity from SHT31 sensor
def read_sht31():
    try:
        temp = sht31.temperature
        hum = sht31.relative_humidity
        return round(temp, 2), round(hum, 2)
    except Exception as e:
        print("ERROR SHT31:", e)
        return None, None

# Function to read soil moisture from analog sensor
# Returns percentage of moisture
def read_soil_analog():
    value = soil_sensor.value  
    percent = round(value * 100, 2)
    return percent

# Function to set the pump state
def set_pump(state):
    if state == "on":
        pump.on()
    else:
        pump.off()

# Function to get the current pump state
def get_pump_state():
    return "on" if pump.value else "off"

if __name__ == "__main__":
    while True:
        t, h = read_sht31()
        s = read_soil_analog()
        print(f"Nhiệt độ: {t}°C, Độ ẩm không khí: {h}%, Độ ẩm đất: {s}%")
        time.sleep(2)
