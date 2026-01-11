./install_deps.sh
python3 -m pip install -r requirements.txt
python3 -m PyInstaller --onedir --name led_mon --add-data plugins:plugins --add-data snapshot_files:snapshot_files --add-data config.yaml:. --hidden-import=yaml --hidden-import=pynput --clean --noconfirm main.py
./install_service.sh
