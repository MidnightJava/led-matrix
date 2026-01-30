#!/bin/bash
set -x
dsp=${DISPLAY:-:0}
xauthority=$XAUTHORITY
wayland_display = ${WAYLAND_DISPLAY:-wayland-1}

sudo rm -f /etc/systemd/system/fwledmonitor.service
sudo tee /etc/systemd/system/fwledmonitor.service > /dev/null <<EOF
[Unit]
Description=Framework 16 LED System Monitor
After=network.service
Wants=network-online.target

[Service]
Type=simple
User=led_mon
Group=led_mon
Environment=DISPLAY=${dsp} XAUTHORITY=${xauthority} WAYLAND_DISPLAY=${wayland_display} LOG_LEVEL=debug
EnvironmentFile=/etc/led_mon/led_mon.env
Restart=always
# ExecStartPre=/usr/bin/xhost +SI:localuser:led_mon
ExecStart=/usr/local/bin/led_mon

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

if ! id -u "led_mon" &>/dev/null 2>&1; then
    sudo useradd   --system   --home /var/lib/led_mon  -G input,dialout --shell /usr/sbin/nologin   led_mon
fi

sudo mkdir -p /etc/led_mon
sudo chown -R root /etc/led_mon
# Copy led_mon/.env-example to led_mon/.env and set API Key env variables
sudo cp led_mon/.env /etc/led_mon/led_mon.env
sudo chmod -R 755 /etc/led_mon
sudo mkdir -p /opt/led_mon
sudo chown -R root /opt/led_mon
sudo chmod -R 755 /opt/led_mon
sudo rm -rf /opt/led_mon/*
sudo cp -r ./dist/led_mon/* /opt/led_mon/
sudo ln -sf /opt/led_mon/led_mon /usr/local/bin/led_mon
sudo systemctl daemon-reload
sudo systemctl stop fwledmonitor.service
sudo systemctl enable --now fwledmonitor.service
