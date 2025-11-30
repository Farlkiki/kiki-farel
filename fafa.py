from machine import Pin, ADC, PWM
import network
import socket
import time
import ujson

# ===== KONFIGURASI PIN =====
LDR_PIN = 34          # Pin ADC untuk sensor LDR
TOUCH_PIN = 14        # Pin Touch Sensor
BUZZER_PIN = 26       # Pin Buzzer

# ===== KONFIGURASI WIFI =====
SSID = "Hotspot-SMK"           # Ganti dengan nama WiFi Anda
PASSWORD = ""   # Ganti dengan password WiFi Anda

# ===== INISIALISASI HARDWARE =====
ldr = ADC(Pin(LDR_PIN))
ldr.atten(ADC.ATTN_11DB)  # Range 0-3.3V
ldr.width(ADC.WIDTH_12BIT)  # Resolution 0-4095

touch = Pin(TOUCH_PIN, Pin.IN)
buzzer = PWM(Pin(BUZZER_PIN))
buzzer.duty(0)  # Mati di awal

# ===== VARIABEL GLOBAL =====
system_active = False
intrusion_count = 0
ldr_threshold = 2000  # Nilai ambang batas (akan dikalibrasi)
last_state = False
ip_address = "Tidak terhubung"

# ===== FUNGSI KONEKSI WIFI =====
def connect_wifi():
    global ip_address
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Menghubungkan ke WiFi...')
        wlan.connect(SSID, PASSWORD)
        
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print('.', end='')
        
        if wlan.isconnected():
            ip_address = wlan.ifconfig()[0]
            print(f'\nTerhubung! IP: {ip_address}')
            return True
        else:
            print('\nGagal terhubung ke WiFi')
            ip_address = "Gagal koneksi WiFi"
            return False
    else:
        ip_address = wlan.ifconfig()[0]
        return True

# ===== FUNGSI BUZZER =====
def alarm_on():
    """Aktifkan alarm buzzer"""
    buzzer.freq(2000)  # Frekuensi 2kHz
    buzzer.duty(512)   # 50% duty cycle

def alarm_off():
    """Matikan alarm buzzer"""
    buzzer.duty(0)

def beep(duration=0.1):
    """Beep singkat"""
    alarm_on()
    time.sleep(duration)
    alarm_off()

# ===== FUNGSI KALIBRASI LDR =====
def calibrate_ldr():
    """Kalibrasi sensor LDR"""
    global ldr_threshold
    print("Kalibrasi LDR...")
    
    # Ambil 10 sampel
    samples = []
    for i in range(10):
        samples.append(ldr.read())
        time.sleep(0.1)
    
    # Hitung rata-rata
    avg = sum(samples) // len(samples)
    # Set threshold 80% dari nilai normal (terang)
    ldr_threshold = int(avg * 0.8)
    
    print(f"Kalibrasi selesai. Threshold: {ldr_threshold}")
    beep(0.1)
    time.sleep(0.1)
    beep(0.1)

# ===== FUNGSI DETEKSI INTRUSI =====
def check_intrusion():
    """Cek apakah ada intrusi (laser terhalang)"""
    global intrusion_count, last_state
    
    if not system_active:
        alarm_off()
        return False
    
    current_ldr = ldr.read()
    is_dark = current_ldr < ldr_threshold
    
    # Deteksi perubahan dari terang ke gelap (laser terhalang)
    if is_dark and not last_state:
        intrusion_count += 1
        print(f"⚠️ INTRUSI TERDETEKSI! Total: {intrusion_count}")
        alarm_on()
        last_state = True
        return True
    elif not is_dark and last_state:
        alarm_off()
        last_state = False
    
    return is_dark

# ===== FUNGSI TOGGLE SISTEM (TOUCH SENSOR) =====
def check_touch():
    """Cek apakah touch sensor ditekan"""
    global system_active
    
    if touch.value() == 1:  # Touch sensor tersentuh
        system_active = not system_active
        
        if system_active:
            print("✅ Sistem AKTIF")
            beep(0.1)
        else:
            print("⛔ Sistem MATI")
            alarm_off()
            beep(0.2)
        
        time.sleep(0.5)  # Debounce

# ===== HTML DASHBOARD =====
HTML = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bank Security System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            min-height: 100vh; padding: 20px; 
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { 
            text-align: center; color: white; 
            margin-bottom: 20px; padding: 20px;
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
        }
        .card { 
            background: white; border-radius: 10px; 
            padding: 20px; margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .status-light { 
            width: 50px; height: 50px; border-radius: 50%;
            display: inline-block; margin-right: 15px;
        }
        .active { background: #4CAF50; box-shadow: 0 0 20px #4CAF50; }
        .inactive { background: #f44336; }
        .control-button { 
            width: 100%; padding: 15px; 
            border: none; border-radius: 8px;
            font-size: 16px; font-weight: bold; cursor: pointer;
            margin: 5px 0;
        }
        .on { background: #4CAF50; color: white; }
        .off { background: #f44336; color: white; }
        .counter { 
            font-size: 3em; font-weight: bold; 
            text-align: center; margin: 10px 0;
        }
        .log-entry { 
            padding: 8px; border-left: 3px solid #667eea;
            margin: 5px 0; background: #f5f5f5;
        }
        .ip-display {
            background: rgba(255,255,255,0.2);
            padding: 10px 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-family: monospace;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.3);
        }
        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        @media (max-width: 768px) {
            .status-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏦 SISTEM KEAMANAN BANK</h1>
            <p>Laser Security & LDR Sensor Monitoring</p>
            <div class="ip-display">
                <strong>IP Address:</strong> 
                <span id="ipAddress">Mengambil IP...</span>
            </div>
        </div>
        <div class="status-grid">
            <div class="card">
                <h2>🛡️ Kontrol Sistem</h2>
                <div style="margin: 15px 0;">
                    <span id="statusLight" class="status-light inactive"></span>
                    <span id="statusText" style="font-weight: bold;">SISTEM MATI</span>
                </div>
                <div style="margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <small>Nilai LDR: <span id="ldrValue">0</span></small><br>
                    <small>Status Cahaya: <span id="lightStatus">-</span></small>
                </div>
                <button id="toggleButton" class="control-button on" onclick="toggleSystem()">
                    AKTIFKAN SISTEM
                </button>
                <button class="control-button" onclick="calibrateSensor()" style="background: #2196F3; color: white;">
                    🔧 Kalibrasi Sensor
                </button>
            </div>
            <div class="card">
                <h2>👤 Deteksi Pengunjung</h2>
                <div style="background: #667eea; color: white; padding: 20px; border-radius: 10px; text-align: center;">
                    <div>TOTAL TERDETEKSI</div>
                    <div id="counterDisplay" class="counter">0</div>
                    <div>Orang Melewati Laser</div>
                </div>
                <button class="control-button" onclick="resetCounter()" style="background: #ff9800; color: white;">
                    🔄 Reset Counter
                </button>
            </div>
        </div>
        <div class="card">
            <h2>📋 Log Aktivitas</h2>
            <div id="logContainer" style="max-height: 200px; overflow-y: auto;"></div>
        </div>
    </div>
    <script>
        let systemActive = false;
        let currentIP = "Mengambil IP...";
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                systemActive = data.system_active;
                updateUI(systemActive);
                document.getElementById('counterDisplay').textContent = data.intrusion_count;
                if (data.ip_address && data.ip_address !== currentIP) {
                    currentIP = data.ip_address;
                    document.getElementById('ipAddress').textContent = currentIP;
                    if (currentIP !== "Tidak terhubung" && currentIP !== "Gagal koneksi WiFi") {
                        addLog(`🌐 Terhubung ke: ${currentIP}`);
                    }
                }
                document.getElementById('ldrValue').textContent = data.current_ldr || 0;
                document.getElementById('lightStatus').textContent = data.is_dark ? "🔴 GELAP (Alarm)" : "🟢 TERANG (Aman)";
                document.getElementById('lightStatus').style.color = data.is_dark ? "#f44336" : "#4CAF50";
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('ipAddress').textContent = "Gagal terkoneksi";
                document.getElementById('ipAddress').style.color = "#ff9800";
                addLog('❌ Gagal terhubung ke ESP32');
            }
        }
        async function toggleSystem() {
            try {
                const response = await fetch('/api/toggle', { method: 'POST' });
                const data = await response.json();
                systemActive = data.system_active;
                updateUI(systemActive);
                addLog(systemActive ? '✅ Sistem diaktifkan' : '⛔ Sistem dimatikan');
            } catch (error) {
                console.error('Error:', error);
                addLog('❌ Gagal mengontrol sistem');
            }
        }
        async function resetCounter() {
            try {
                await fetch('/api/reset', { method: 'POST' });
                document.getElementById('counterDisplay').textContent = 0;
                addLog('🔄 Counter direset');
            } catch (error) {
                console.error('Error:', error);
                addLog('❌ Gagal mereset counter');
            }
        }
        async function calibrateSensor() {
            try {
                addLog('🔧 Kalibrasi sensor...');
                await fetch('/api/calibrate', { method: 'POST' });
                addLog('✅ Kalibrasi selesai');
            } catch (error) {
                console.error('Error:', error);
                addLog('❌ Gagal mengkalibrasi sensor');
            }
        }
        function updateUI(isActive) {
            const statusLight = document.getElementById('statusLight');
            const statusText = document.getElementById('statusText');
            const toggleButton = document.getElementById('toggleButton');
            if (isActive) {
                statusLight.className = 'status-light active';
                statusText.textContent = 'SISTEM AKTIF';
                statusText.style.color = '#4CAF50';
                toggleButton.className = 'control-button off';
                toggleButton.textContent = 'MATIKAN SISTEM';
            } else {
                statusLight.className = 'status-light inactive';
                statusText.textContent = 'SISTEM MATI';
                statusText.style.color = '#f44336';
                toggleButton.className = 'control-button on';
                toggleButton.textContent = 'AKTIFKAN SISTEM';
            }
        }
        function addLog(message) {
            const logContainer = document.getElementById('logContainer');
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            const time = new Date().toLocaleTimeString();
            logEntry.innerHTML = `<small>${time}</small> - ${message}`;
            logContainer.prepend(logEntry);
            if (logContainer.children.length > 10) {
                logContainer.removeChild(logContainer.lastChild);
            }
        }
        setInterval(updateStatus, 1000);
        updateStatus();
        addLog('💼 Sistem siap digunakan');
        addLog('📡 Mencoba koneksi ke ESP32...');
    </script>
</body>
</html>"""

# ===== FUNGSI WEB SERVER =====
def handle_request(client):
    global system_active, intrusion_count
    
    try:
        request = client.recv(1024).decode('utf-8')
        
        # Parsing request
        if 'GET / ' in request or 'GET /index' in request:
            # Kirim halaman HTML
            client.send('HTTP/1.1 200 OK\r\n')
            client.send('Content-Type: text/html\r\n')
            client.send('Connection: close\r\n\r\n')
            client.sendall(HTML)
        
        elif 'GET /api/status' in request:
            # Status API
            current_ldr = ldr.read()
            is_dark = current_ldr < ldr_threshold
            
            status = {
                'system_active': system_active,
                'intrusion_count': intrusion_count,
                'current_ldr': current_ldr,
                'threshold': ldr_threshold,
                'is_dark': is_dark,
                'ip_address': ip_address
            }
            
            client.send('HTTP/1.1 200 OK\r\n')
            client.send('Content-Type: application/json\r\n')
            client.send('Connection: close\r\n\r\n')
            client.send(ujson.dumps(status))
        
        elif 'POST /api/toggle' in request:
            # Toggle sistem
            system_active = not system_active
            if not system_active:
                alarm_off()
            
            response = {'system_active': system_active}
            client.send('HTTP/1.1 200 OK\r\n')
            client.send('Content-Type: application/json\r\n')
            client.send('Connection: close\r\n\r\n')
            client.send(ujson.dumps(response))
        
        elif 'POST /api/reset' in request:
            # Reset counter
            intrusion_count = 0
            
            response = {'intrusion_count': intrusion_count}
            client.send('HTTP/1.1 200 OK\r\n')
            client.send('Content-Type: application/json\r\n')
            client.send('Connection: close\r\n\r\n')
            client.send(ujson.dumps(response))
        
        elif 'POST /api/calibrate' in request:
            # Kalibrasi sensor
            calibrate_ldr()
            
            response = {'threshold': ldr_threshold}
            client.send('HTTP/1.1 200 OK\r\n')
            client.send('Content-Type: application/json\r\n')
            client.send('Connection: close\r\n\r\n')
            client.send(ujson.dumps(response))
        
        else:
            # 404
            client.send('HTTP/1.1 404 Not Found\r\n')
            client.send('Connection: close\r\n\r\n')
    
    except Exception as e:
        print(f"Error handling request: {e}")
    
    finally:
        client.close()

# ===== FUNGSI UTAMA =====
def main():
    print("=" * 50)
    print("🏦 SISTEM KEAMANAN BANK - ESP32")
    print("=" * 50)
    
    # Koneksi WiFi
    if not connect_wifi():
        print("❌ Gagal memulai - Periksa koneksi WiFi")
        return
    
    # Kalibrasi awal
    print("\n📡 Kalibrasi sensor awal...")
    calibrate_ldr()
    
    # Setup web server
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    s.setblocking(False)
    
    print(f"\n✅ Server berjalan di http://{ip_address}")
    print("👆 Sentuh sensor untuk mengaktifkan/menonaktifkan sistem")
    print("=" * 50)
    
    last_check = time.time()
    
    # Loop utama
    while True:
        try:
            # Cek touch sensor setiap saat
            check_touch()
            
            # Cek intrusi setiap 100ms
            current_time = time.time()
            if current_time - last_check > 0.1:
                check_intrusion()
                last_check = current_time
            
            # Handle web request (non-blocking)
            try:
                client, addr = s.accept()
                handle_request(client)
            except OSError:
                pass  # No client
            
            time.sleep(0.01)  # Small delay
            
        except KeyboardInterrupt:
            print("\n\n⛔ Sistem dihentikan")
            alarm_off()
            s.close()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

# ===== JALANKAN PROGRAM =====
if __name__ == '__main__':
    main()
