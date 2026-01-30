# External Dependencies
from serial.tools import list_ports

def init_device(location = "1-4.2"):
    try:
        # VID = 1234
        # PID = 5678
        device_list = list_ports.comports()
        for device in device_list:
            if device.location and device.location.startswith(location):
                # s = serial.Serial(device.device, 115200)
                print(device)
                print(device, device.location, device.device, device.manufacturer, device.device_path, device.product, device.interface, device.description)
    except Exception as e:
        print(e)
        
init_device("1-3.")

""" 
Panels on right side
Left: 1-3.2, ACM0
Right: 1-3.3, ACM1
"""