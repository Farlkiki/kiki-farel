from machine import Pin, ADC
import time

# Inisialisasi pin
ldr = ADC(Pin(34))          # LDR di pin GPIO34 (ADC)
ldr.atten(ADC.ATTN_11DB)    # Rentang 0-3.3V
buzzer = Pin(26, Pin.OUT)   # Buzzer di pin GPIO13
touch_sensor = Pin(14, Pin.IN)  # Touch sensor di pin GPIO14

# Variabel sistem
system_active = False       # Status sistem (on/off)
buzzer_active = False       # Status buzzer
threshold = 1000           # Threshold nilai LDR (sesuaikan)
debounce_delay = 500       # Delay untuk debounce touch sensor
last_touch_time = 0

# Kalibrasi otomatis untuk nilai baseline LDR
def calibrate_ldr():
    print("Kalibrasi LDR...")
    print("Pastikan laser MENYINARI LDR langsung (tidak ada halangan)")
    time.sleep(3)
    
    readings = []
    for i in range(50):
        readings.append(ldr.read())
        time.sleep(0.1)
    
    baseline = sum(readings) / len(readings)
    threshold = baseline * 0.6  # 40% drop dari baseline dianggap gangguan
    print(f"Baseline: {baseline}, Threshold: {threshold}")
    return int(threshold)

# Fungsi untuk membaca status touch sensor dengan debounce
def check_touch():
    global last_touch_time, system_active
    
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_touch_time) > debounce_delay:
        if touch_sensor.value() == 1:
            last_touch_time = current_time
            system_active = not system_active  # Toggle status sistem
            print(f"Sistem {'AKTIF' if system_active else 'NON-AKTIF'}")
            
            # Bunyi bip pendek saat toggle
            buzzer.on()
            time.sleep(0.1)
            buzzer.off()
            return True
    return False

# Fungsi untuk mendeteksi gangguan laser/LDR
def detect_intrusion():
    ldr_value = ldr.read()
    
    # Jika LDR tertutup/tidak kena laser (nilai rendah = gelap), ada gangguan
    if ldr_value < threshold:
        return True
    return False

# Setup awal
threshold = calibrate_ldr()  # Kalibrasi saat startup
print("Sistem Keamanan Bank IoT dengan Laser Mainan")
print("Touch sensor untuk mengaktifkan/nonaktifkan sistem")
print("Laser mainan harus dinyalakan MANUAL dan diarahkan ke LDR")
print("=" * 50)

# Main loop
try:
    while True:
        # Cek status touch sensor
        check_touch()
        
        if system_active:
            # Sistem aktif - monitor gangguan
            if detect_intrusion():
                if not buzzer_active:
                    buzzer.on()
                    buzzer_active = True
                    print("ALARM! Terdeteksi gangguan! Laser terputus!")
                    print(f"Nilai LDR: {ldr.read()}")
            
            else:
                # Tidak ada gangguan, matikan buzzer jika sedang aktif
                if buzzer_active:
                    buzzer.off()
                    buzzer_active = False
                    print("Status: Aman - Laser menyinari LDR")
        
        else:
            # Sistem non-aktif - pastikan buzzer mati
            if buzzer_active:
                buzzer.off()
                buzzer_active = False
                print("Sistem non-aktif")
        
        time.sleep(0.1)  # Delay untuk stabilisasi

except KeyboardInterrupt:
    # Cleanup saat program dihentikan
    buzzer.off()
    print("Program dihentikan")
