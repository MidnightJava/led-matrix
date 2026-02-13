#!/bin/bash
for dev in $(ls /sys/bus/usb/devices/ | grep 'ttyACM'); do
    echo 0 | sudo tee /sys/bus/usb/devices/$dev/authorized
done

sleep 2

for dev in $(ls /sys/bus/usb/devices/ | grep 'ttyACM'); do
    echo 1 | sudo tee /sys/bus/usb/devices/$dev/authorized
done

inputmodule-control led-matrix --sleeping false

