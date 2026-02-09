# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('led_mon/plugins', 'led_mon/plugins'), ('led_mon/snapshot_files', 'led_mon/snapshot_files'), ('led_mon/config.yaml', 'led_mon'), ('led_mon/equalizer_files', 'led_mon/equalizer_files')],
    hiddenimports=['yaml', 'pynput', 'requests', 'zoneinfo', 'iplocate', 'sounddevice', 'pulsectl', 'dotenv', 'scipy', 'scipy._distributor_init', 'scipy._lib.messagestream', 'scipy.special._ufuncs', 'scipy.linalg._flapack', 'scipy.signal'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='led_mon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='led_mon',
)
