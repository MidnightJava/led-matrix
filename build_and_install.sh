./install_deps.sh
python -m pip install -r requirements.txt
python -m PyInstaller --onedir --name led_mon \
    --add-data plugins:plugins --add-data snapshot_files:snapshot_files \
    --add-data config.yaml:. --add-data config-local.yaml:.\
    --hidden-import=yaml --hidden-import=pynput --hidden-import=requests \
    --hidden-import=zoneinfo --hidden-import=iplocate \
    --hidden-import=dotenv --clean --noconfirm \
    main.py
./install_service.sh
