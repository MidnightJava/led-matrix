./install_deps.sh
python -m pip install -r requirements.txt
python -m PyInstaller --onedir --name led_mon \
    --add-data led_mon/plugins:led_mon/plugins --add-data led_mon/snapshot_files:led_mon/snapshot_files \
    --add-data led_mon/config.yaml:led_mon --add-data led_mon/equalizer_files:led_mon/equalizer_files  \
    --hidden-import=yaml --hidden-import=pynput --hidden-import=requests \
    --hidden-import=zoneinfo --hidden-import=iplocate --hidden-import=sounddevice  --hidden-import=pulsectl \
    --hidden-import=dotenv --hidden-import=scipy --hidden-import=scipy._distributor_init \
    --hidden-import=scipy._lib.messagestream --hidden-import=scipy.special._ufuncs --hidden-import=scipy.linalg._flapack  \
    --hidden-import=scipy.signal --clean --noconfirm \
    main.py \
&& ./install_service.sh
