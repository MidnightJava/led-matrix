key_press_active = False
foreground_value = 0

from serial.tools import list_ports
import re

def discover_led_devices():
    locations = []
    try:
        device_list = list_ports.comports()
        for device in device_list:
            if 'LED Matrix Input Module' in str(device):
                locations.append((device.location, device.device))
        #location is of form: <bus>-<port>[-<port>]  (port is of form x.y:n.m)
        # Example: 1-3.3:1.0 (right device) , 1-3.2:1.0 (left device)
        # Sort by y:n.m to get the devices in left-right order
        return sorted(locations, key = lambda x: re.sub(r'^\d+\-\d+\.', '', x[0]))
    except Exception as e:
        print(f"An Exception occured while tring to locate LED Matrix devices. {e}")