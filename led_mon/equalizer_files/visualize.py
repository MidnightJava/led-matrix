
# Built-in Dependencies
import subprocess
import time
import os
import re
import threading
from threading import Timer
import argparse
import logging
from enum import Enum
import shutil
import signal
import sys

# Internal Dependencies
from led_mon.led_system_monitor import discover_led_devices

# External ependencies
import numpy as np
import sounddevice as sd
from scipy.signal import butter, sosfiltfilt
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

class DeviceType(Enum):
    SOURCE = 1
    SINK = 2

SOURCE_CHECK_INTERVAL_SEC = 1

# Configuration
SAMPLE_RATE = 48000
CHUNK_SIZE = 1024
UPDATE_RATE = 0.03 # 33 fps

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



# Shared audio buffer and lock
audio_buffer = np.zeros((CHUNK_SIZE, 2), dtype=np.float32)
buffer_lock = threading.Lock()
# Lock for writing to LED matrix device
device_lock = threading.Lock()

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
    
def draw_source_change_cue(source, device_name):
    pattern = get_notification_pattern(source)
    devices= discover_led_devices()
    # Only one instance will detect the source change, so it notifies both devices
    cmd_1 = [
            MODUE_CONTROL_APP,
            '--serial-dev', devices[0][1],
            'led-matrix',
            '--pattern',
            pattern
    ]
    if len(devices) > 1:
        cmd_2 = [
                MODUE_CONTROL_APP,
                '--serial-dev', devices[1][1],
                'led-matrix',
                '--pattern',
                pattern
        ]
    else:
        cmd_2 = None
    with device_lock:
        for _ in range(7):
            subprocess.call(cmd_1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if cmd_2:
                subprocess.call(cmd_2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
def get_default_device(dev_type: DeviceType):
    with Pulse() as pulse_tmp:  # Temporary connection to query
        server_info = pulse_tmp.server_info()
        new_dev = \
            server_info.default_source_name if dev_type == DeviceType.SOURCE \
            else server_info.default_sink_name if dev_type == DeviceType.SINK \
            else None
        return new_dev
    
class Equalizer():
    
    def __init__(self):
        self.done = False
        
    def stop(self):
        self.done = True
    
    # Pipewire is supposed to automatically make the default source track the default sink's monitor, but the
    # capability is fragile and can sometimes be permanently broken. So we track sink changes and set the default
    # source to its monitor, to ensure continued data flow. We also draw a visual cue identifying the new source.
    def force_monitor_source(self):
        last_known_sink = None
        try:
            current_sink = get_default_device(DeviceType.SINK)

            if current_sink == last_known_sink or current_sink is None:
                Timer(SOURCE_CHECK_INTERVAL_SEC, self.force_monitor_source).start()
                return

            expected_source = f"{current_sink}.monitor"
            current_source = get_default_device(DeviceType.SOURCE)

            if current_source != expected_source and current_source is not None:
                log.info(f"New sink detected: {current_sink}")
                subprocess.run(
                    ['pactl', 'set-default-source', expected_source],
                    check=True,
                    capture_output=True,
                    text=True
                )
                #time.sleep(0.2)  # tiny settle time, may not be needed
                verified = get_default_device(DeviceType.SOURCE)
                if verified == expected_source:
                    log.info(f"Default source changed: {current_source} → {expected_source}")
                    draw_source_change_cue(expected_source, self.device_name)
                else:
                    log.warning(f"Failed to change default source: still {verified}")

            last_known_sink = current_sink

        except subprocess.CalledProcessError as e:
            log.error(f"Failed to check/fix default source: {e}")
        except Exception as e:
            log.error(f"Unexpected error in force_monitor_source: {e}")
        Timer(SOURCE_CHECK_INTERVAL_SEC, self.force_monitor_source).start()
        
    def cleanup(self, sig=None, frame=None):
            self.stop()

    def run(self, channel, external_filter, device_name):
        self.device_name = device_name
        def update_leds():
            global event_queue, current_source
            while not self.done:
                with buffer_lock:
                    chunk = audio_buffer[:, channel]  # extract left or right channel only

                levels = []

                if external_filter:
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
                    '--serial-dev', device_name,
                    'led-matrix',
                    '--eq',
                ] + [str(l) for l in levels]
                # print(f"{device_name} {levels}")
                with device_lock:
                    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                time.sleep(UPDATE_RATE)
        Timer(SOURCE_CHECK_INTERVAL_SEC, self.force_monitor_source).start()
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=2,
            blocksize=CHUNK_SIZE,
            callback=audio_callback,
            device='default'
        )

        update_thread = threading.Thread(target=update_leds, daemon=True)
        update_thread.start()

        with stream:
            log.debug(f"Running equalizer for {channel} channel on {device_name} with {'EasyEffects' if external_filter else 'Python'} filter")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.cleanup()
            
if __name__ == '__main__':
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

    if args.channel == 'left':
        channel = 0  # left = column 0 in stereo buffer
        serial_dev = args.serial_dev_left
    else:
        channel = 1  # right = column 1
        serial_dev = args.serial_dev_right

    use_external_filter = args.use_easyeffects
    eq = Equalizer()
    eq.run(channel=channel, external_filter=use_external_filter, device_name=serial_dev)
    def stop_and_exit(sig=None, frame=None):
        eq.cleanup()
        sys.exit(0)
    signal.signal(signal.SIGINT, stop_and_exit )
    signal.signal(signal.SIGTERM, stop_and_exit)