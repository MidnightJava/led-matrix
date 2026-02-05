
# Internal Dependencies
import subprocess
import time
import os
import re
import threading
import argparse
import logging
import queue
import shutil
import signal
import sys

# External ependencies
import numpy as np
import sounddevice as sd
from scipy.signal import butter, sosfiltfilt
import pulsectl
from pulsectl import Pulse


level = logging.WARNING
if os.getenv("LOG_LEVEL", "").lower() == "debug":
    level = logging.DEBUG
elif os.getenv("LOG_LEVEL", "").lower() == "error":
    level = logging.ERROR
elif os.getenv("LOG_LEVEL", "").lower() == "info":
    level = logging.INFO

logging.basicConfig(
    level=level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

log = logging.getLogger(__name__)



# Configuration
SAMPLE_RATE = 48000
CHUNK_SIZE = 1024
UPDATE_RATE = 0.03  # ~33 updates/sec

# 9 frequency bands (If you use an EasyEffects filter, match the centers as closely as possible)
BAND_CENTERS = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]  # Hz
Q = 1.414

MODUE_CONTROL_APP = shutil.which('inputmodule-control')

# Pre-compute bandpass filters (used in python file mode)
filters = []
for fc in BAND_CENTERS:
    low = fc / Q
    high = fc * Q
    sos = butter(4, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')
    filters.append(sos)

# Scale RMS to 0–34 range for --eq
def scale_rms(rms, min_db=-60, max_db=0):
    db = 20 * np.log10(rms + 1e-10)
    normalized = np.clip((db - min_db) / (max_db - min_db), 0, 1)
    return int(normalized * 34)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="LED Matrix Audio Visualizer - Single Channel")
parser.add_argument(
    '--channel',
    choices=['left', 'right'],
    required=True,
    help="Which channel and device to process: 'left' or 'right'"
)
parser.add_argument(
    '--use-easyeffects',
    action='store_true',
    help="Use EasyEffects upstream processing (skip Python bandpass filters)"
)
parser.add_argument(
    '--serial-dev-left',
    default='/dev/ttyACM0',   # ← customize these defaults or override via args
    help="Serial device for left channel"
)
parser.add_argument(
    '--serial-dev-right',
    default='/dev/ttyACM1',
    help="Serial device for right channel"
)
args = parser.parse_args()

# Determine channel index and serial device
if args.channel == 'left':
    CHANNEL_INDEX = 0  # left = column 0 in stereo buffer
    SERIAL_DEV = args.serial_dev_left
else:
    CHANNEL_INDEX = 1  # right = column 1
    SERIAL_DEV = args.serial_dev_right

USE_EASY_EFFECTS = args.use_easyeffects

# Shared audio buffer and lock
audio_buffer = np.zeros((CHUNK_SIZE, 2), dtype=np.float32)
buffer_lock = threading.Lock()
# Lock for writing to LED matrix device
device_lock = threading.Lock()

### Pulse Audio Event listener to detect changes to default source ###
######################################################################
event_queue = queue.Queue()  # to send events to main thread

def pulse_event_handler(ev):
    event_queue.put(ev)  # send to main thread

def pulse_listener_thread():
    with pulsectl.Pulse('led-visualizer-events') as pulse:
        pulse.event_mask_set('server')  # only server changes (includes default source/sink)
        pulse.event_callback_set(pulse_event_handler)
        while True:
            try:
                pulse.event_listen(timeout=5)  # blocks 5s at a time; check queue or stop flag
            except KeyboardInterrupt:
                break
            except pulsectl.PulseError as e:
                print(f"Pulse error: {e}")
                break

# Start listener in background
listener = threading.Thread(target=pulse_listener_thread, daemon=True)
listener.start()
######################################################################

def audio_callback(indata, frames, time_info, status):
    global audio_buffer
    with buffer_lock:
        audio_buffer = indata.copy()

def get_notification_pattern(source):
    if re.match(".*headphone.*|.*Audio_Expansion.*", source):
        # Wired headphones
        return 'zigzag'
    elif re.match(".*analog-stereo.*", source):
        # Speakers
        return 'all-on'
    elif re.match(".*bluez.*", source):
        # BlueTooth device
        return 'gradient'
    else:
        # Other
        return 'gradient'
    
def get_default_source():
    with Pulse() as pulse_tmp:  # Temporary connection to query
                server_info = pulse_tmp.server_info()
                new_source = server_info.default_source_name
                return new_source
            
current_source = get_default_source()
original_source = current_source
log.debug(f"Original default source: {original_source}")

def update_leds():
    global event_queue, current_source
    while True:
        if not event_queue.empty():
            ev = event_queue.get(timeout=1)  # non-blocking check
            if ev.t == 'change':
                new_source = get_default_source()
                if new_source != current_source:
                    log.debug(f"New default source: {new_source}")
                    pattern = get_notification_pattern(new_source)
                    cmd = [
                        MODUE_CONTROL_APP,
                        '--serial-dev', SERIAL_DEV,
                        'led-matrix',
                        '--pattern',
                        pattern
                    ]
                    with device_lock:
                        for _ in range(7):
                            subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    current_source = new_source

        with buffer_lock:
            chunk = audio_buffer[:, CHANNEL_INDEX]  # extract left or right channel only

        levels = []

        if USE_EASY_EFFECTS:
            # EasyEffects mode: audio already EQ'd → measure energy in each band
            for center_freq in BAND_CENTERS:
                # Use wide-ish windows to capture EasyEffects' output without double-filtering
                low = center_freq * 0.75
                high = center_freq * 1.35
                sos = butter(2, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')
                filtered = sosfiltfilt(sos, chunk)
                rms = np.sqrt(np.mean(filtered ** 2))
                level = scale_rms(rms)
                levels.append(level)

        else:
            # Python mode: apply our fixed narrow bandpass filters
            for sos in filters:
                filtered = sosfiltfilt(sos, chunk)
                rms = np.sqrt(np.mean(filtered ** 2))
                level = scale_rms(rms)
                levels.append(level)

        cmd = [
            MODUE_CONTROL_APP,
            '--serial-dev', SERIAL_DEV,
            'led-matrix',
            '--eq',
        ] + [str(l) for l in levels]
        print(f"Levels {levels}")
        with device_lock:
            subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(UPDATE_RATE)

# Start audio capture from default source, and it will follow output device selection changes.
# With device="default" PortAudio will connect to a virtual source, a .monitor source
# created by PipeWire that dynamically follows the default sink as it changes.
stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=2,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    device='default'
)

update_thread = threading.Thread(target=update_leds, daemon=True)
update_thread.start()

cleanup_flag = False

def cleanup(sig=None, frame=None):
    sys.exit(0)
    
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


with stream:
    log.debug(f"Running equalizer for {args.channel} channel on {SERIAL_DEV} with {'EasyEffects' if USE_EASY_EFFECTS else 'Python'} filter")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()