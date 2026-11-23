# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('src/lplab/static', 'lplab/static'),
    ('labs', 'labs'),
]
binaries = []
hiddenimports = [
    'lplab',
    'lplab.paths',
    'lplab.config',
    'lplab.models',
    'lplab.gui',
    'lplab.gui_server',
    'lplab.cli',
    'lplab.tui',
    'lplab.lab_engine',
    'lplab.wsl_manager',
    'lplab.ai_generator',
    'lplab.rootfs_builder',
    'lplab.safety_linter',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan.on',
    'fastapi',
    'pydantic',
    'httpx',
    'yaml',
    'starlette',
    'textual',
    'rich',
    'typer',
    'clr_loader',
    'pythonnet',
    'webview',
]

webview_datas, webview_binaries, webview_hiddenimports = collect_all('webview')
datas += webview_datas
binaries += webview_binaries
hiddenimports += webview_hiddenimports

a = Analysis(
    ['src/lplab/entrypoint.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lplab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/lplab.ico',
)
