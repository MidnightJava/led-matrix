#!/bin/bash

# Auto-detect distribution and install dependencies
if command -v apt >/dev/null 2>&1; then
    echo "Detected Ubuntu/Debian system, installing dependencies with apt..."
    sudo apt update
    sudo apt install -y python3-numpy python3-psutil python3-serial python3-evdev
elif command -v dnf >/dev/null 2>&1; then
    echo "Detected Fedora system, installing dependencies with dnf..."
    sudo dnf install -y python3-numpy python3-psutil python3-pyserial python3-evdev
elif command -v yum >/dev/null 2>&1; then
    echo "Detected CentOS/RHEL system, installing dependencies with yum..."
    sudo yum install -y python3-numpy python3-psutil python3-pyserial python3-evdev
else
    echo "Warning: Could not detect package manager. Please install dependencies manually:"
    echo "  - python3-numpy"
    echo "  - python3-psutil" 
    echo "  - python3-pyserial (or python3-serial on some distributions)"
    echo "  - python3-evdev"
    echo ""
fi

echo "Starting LED Matrix Monitor..."
python3 ./led_system_monitor.py 
