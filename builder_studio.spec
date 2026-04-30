# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['builder_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('HeroJUVICKS.spec', '.'),  # Motor de compilação
        ('main.py', '.'),            # Script principal do app gerado
        ('installer.iss', '.'),      # Script do Inno Setup
        ('assets', 'assets'),        # Pasta de recursos (HTML, ico, js...)
    ],
    hiddenimports=['PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebChannel'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BuilderStudio_HTML2EXE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Sem janela preta de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='builder_icon.ico'
)
