#!/bin/bash
set -x
dsp=${DISPLAY:-:0}
xauthority=$XAUTHORITY
wayland_display = ${WAYLAND_DISPLAY:-wayland-1}

sudo rm -f /etc/systemd/system/fwledmonitor.service
sudo tee $HOME/.config/systemd/user/fwledmonitor.service > /dev/null <<EOF
[Unit]
Description=Framework 16 LED System Monitor
After=network.service
Wants=network-online.target

[Service]
Type=simple
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
sudo mkdir -p /var/lib/led_mon/.config
sudo chown led_mon:led_mon /var/ib/led_mon/.config
sudo chmod 777 /var/lib/led_mon/.config

sudo mkdir -p /etc/led_mon
sudo chown -R root /etc/led_mon
# Copy .env-example to .env and set API Key env variables
sudo cp .env /etc/led_mon/led_mon.env
# PyInsatller does not include config-local.yaml with --add-data because it may not exist
if [[ -f led_mon/config-local.yaml ]];then
    cp led_mon/config-local.yaml ./dist/led_mon/_internal/led_mon/config-local.yaml
fi
sudo chmod -R 755 /etc/led_mon
sudo mkdir -p /opt/led_mon
sudo chown -R root /opt/led_mon
sudo chmod -R 755 /opt/led_mon
sudo rm -rf /opt/led_mon/*
sudo cp -r ./dist/led_mon/* /opt/led_mon/
sudo ln -sf /opt/led_mon/led_mon /usr/local/bin/led_mon
systemctl --user daemon-reload
systemctl --user stop fwledmonitor.service
systemctl --user enable --now fwledmonitor.service
