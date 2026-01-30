# Illustrative of bus architecture. The values may change after reboot or re-plug

#  lsusb -t

# Bus 001
# └── Port 003 (hub)
#     ├── Port 002 → Dev 020  ← LED module #1
#     └── Port 003 → Dev 022  ← LED module #2

# /sys/bus/usb/devices/1-3.2   # Dev 020
# /sys/bus/usb/devices/1-3.3   # Dev 022

for d in 1-3.2 1-3.3; do
  echo 0 | sudo tee /sys/bus/usb/devices/$d/authorized
done

sleep 2

for d in 1-3.2 1-3.3; do
  echo 1 | sudo tee /sys/bus/usb/devices/$d/authorized
done

