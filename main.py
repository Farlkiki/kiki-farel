from microdot import Microdot, send_file
from machine import Pin, ADC
import time
import network
import _thread
import json

# ===== KONFIGURASI WIFI =====
SSID = "FAREL GANTENG"
PASSWORD = "jirolupat"

# ===== SETUP SENSOR =====
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
buzzer = Pin(13, Pin.OUT)
touch_sensor = Pin(14, Pin.IN)

# ===== VARIABEL SISTEM =====
system_state = {
    "system_active": False,
    "buzzer_active": False, 
    "intrusion_count": 0,
    "threshold": 2000,
    "last_touch_time": 0,
    "debounce_delay": 500
}

# ===== FUNGSI SENSOR =====
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(SSID, PASSWORD)
        for i in range(20):
            if wlan.isconnected():
                break
            print('.', end='')
            time.sleep(1)
        print()
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print('WiFi Connected! IP:', ip)
        return ip
    else:
        print('WiFi connection failed!')
        return None

def calibrate_ldr():
    print("Kalibrasi LDR... Pastikan laser menyinari LDR")
    time.sleep(2)
    
    readings = []
    for i in range(20):
        readings.append(ldr.read())
        time.sleep(0.05)
    
    baseline = sum(readings) / len(readings)
    system_state["threshold"] = int(baseline * 0.7)
    print(f"Baseline: {baseline}, Threshold: {system_state['threshold']}")

def check_touch_sensor():
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, system_state["last_touch_time"]) > system_state["debounce_delay"]:
        if touch_sensor.value() == 1:
            system_state["last_touch_time"] = current_time
            system_state["system_active"] = not system_state["system_active"]
            
            # Bunyi bip pendek
            buzzer.value(1)
            time.sleep(0.1)
            buzzer.value(0)
            
            print(f"Sistem {'AKTIF' if system_state['system_active'] else 'NON-AKTIF'}")
            return True
    return False

def detect_intrusion():
    ldr_value = ldr.read()
    if ldr_value < system_state["threshold"]:
        return True
    return False

def update_buzzer():
    if system_state["system_active"] and system_state["buzzer_active"]:
        buzzer.value(1)
    else:
        buzzer.value(0)

# ===== WEB SERVER =====
app = Microdot()

@app.route('/')
def index(request):
    return send_file('index.html')

@app.route('/api/status')
def api_status(request):
    return json.dumps(system_state), 200, {'Content-Type': 'application/json'}

@app.route('/api/toggle', methods=['POST'])
def api_toggle(request):
    system_state["system_active"] = not system_state["system_active"]
    buzzer.value(1)
    time.sleep(0.1)
    buzzer.value(0)
    return json.dumps(system_state), 200, {'Content-Type': 'application/json'}

@app.route('/api/reset', methods=['POST'])
def api_reset(request):
    system_state["intrusion_count"] = 0
    return json.dumps(system_state), 200, {'Content-Type': 'application/json'}

@app.route('/api/calibrate', methods=['POST'])
def api_calibrate(request):
    calibrate_ldr()
    return json.dumps(system_state), 200, {'Content-Type': 'application/json'}

# ===== MAIN LOOP =====
def sensor_loop():
    last_intrusion_state = False
    
    while True:
        try:
            # Cek sensor touch fisik
            check_touch_sensor()
            
            if system_state["system_active"]:
                # Deteksi intrusi
                intrusion_detected = detect_intrusion()
                
                # Deteksi perubahan state (rising edge)
                if intrusion_detected and not last_intrusion_state:
                    system_state["intrusion_count"] += 1
                    system_state["buzzer_active"] = True
                    print(f"ALARM! Intrusion #{system_state['intrusion_count']}")
                
                # Jika tidak ada gangguan, matikan buzzer
                elif not intrusion_detected and system_state["buzzer_active"]:
                    system_state["buzzer_active"] = False
                
                last_intrusion_state = intrusion_detected
            
            else:
                # Sistem non-aktif
                system_state["buzzer_active"] = False
                last_intrusion_state = False
            
            # Update buzzer
            update_buzzer()
            time.sleep(0.1)
            
        except Exception as e:
            print("Error in sensor loop:", e)
            time.sleep(1)

def main():
    print("Starting Bank Security System...")
    
    # Kalibrasi awal
    calibrate_ldr()
    
    # Connect WiFi
    ip_address = connect_wifi()
    if ip_address:
        print(f"Server: http://{ip_address}")
    else:
        print("Running in offline mode")
    
    # Jalankan sensor loop di background
    _thread.start_new_thread(sensor_loop, ())
    
    # Jalankan web server
    print("Starting web server on port 80...")
    try:
        app.run(host='0.0.0.0', port=80)
    except Exception as e:
        print("Server error:", e)
        # Restart server on error
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
