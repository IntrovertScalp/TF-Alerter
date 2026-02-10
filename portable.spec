# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Bundle app data (sounds, logo) into the dist folder
app_datas = [
    ('Logo', 'Logo'),
    ('Sounds', 'Sounds'),
    ('Other_Sounds', 'Other_Sounds'),
]

qt_datas = collect_data_files('PyQt6')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=app_datas + qt_datas,
    hiddenimports=[
        'ctypes',
        'PyQt6',
        'PyQt6.sip',
        'pynput',
        'pygame',
        'qrcode',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='TF-Alerter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Logo/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TF-Alerter',
)
