import numpy as np
import sounddevice as sd  # For audio capture
from scipy.signal import butter, sosfiltfilt  # For bandpass filters
import subprocess
import time
import os
import threading

# Configuration
SAMPLE_RATE = 48000  # Match your system's audio rate (check with `pw-dump | grep default.clock.rate`)
CHUNK_SIZE = 1024    # Audio chunk size (adjust for latency; smaller = more responsive, but higher CPU)
UPDATE_RATE = 0.03   # Seconds between LED updates (e.g., ~33 FPS)

# 9 frequency bands (octave centers, log-spaced from ~32 Hz to ~16 kHz)
BAND_CENTERS = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]  # Hz
Q = 1.414  # For octave bandwidth; increase for narrower bands

# Pre-compute bandpass filters (second-order sections for stability)
filters = []
for fc in BAND_CENTERS:
    low = fc / Q
    high = fc * Q
    sos = butter(4, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')  # 4th order Butterworth
    filters.append(sos)

# Scale function: Convert RMS to 0-255 integer for LED height (adjust sensitivity)
def scale_rms(rms, min_db=-60, max_db=0):
    db = 20 * np.log10(rms + 1e-10)  # dBFS
    normalized = np.clip((db - min_db) / (max_db - min_db), 0, 1)
    return int(normalized * 34)  # Assuming --eq takes 0-34 per column

# Audio callback: Process chunks in real-time
audio_buffer = np.zeros((CHUNK_SIZE, 2), dtype=np.float32)  # Stereo buffer
lock = threading.Lock()

def audio_callback(indata, frames, time_info, status):
    global audio_buffer
    with lock:
        audio_buffer = indata.copy()  # Copy latest chunk

# Function to compute band levels and update LEDs
USE_EXTERNAL_FILTER = os.environ.get("EXTERNAL_FILTER", "false").lower() == 'true'
def update_leds():
    while True:
        with lock:
            chunk = audio_buffer.mean(axis=1)  # mono

        levels = []

        if USE_EXTERNAL_FILTER:
            # EasyEffects is already applying the 9-band EQ upstream
            # → We just measure RMS in the same frequency ranges to get post-EQ bucket levels
            for sos in filters:                      # ← still using the same filter definitions!
                filtered = sosfiltfilt(sos, chunk)   # Measure energy in this band *after* EasyEffects
                rms = np.sqrt(np.mean(filtered ** 2))
                level = scale_rms(rms)
                levels.append(level)

        else:
            # Python mode: apply the filters ourselves (fixed parameters)
            for sos in filters:
                filtered = sosfiltfilt(sos, chunk)
                rms = np.sqrt(np.mean(filtered ** 2))
                level = scale_rms(rms)
                levels.append(level)

        cmd = [
            '/usr/local/bin/inputmodule-control',
            'led-matrix',
            '--eq',
        ] + [str(l) for l in levels]

        subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(UPDATE_RATE)

stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=2,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    device='default'  # or sd.default.device[0] — this follows pactl default source
    # No extra_settings needed
)

update_thread = threading.Thread(target=update_leds, daemon=True)
update_thread.start()

with stream:
    print("Running... Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")