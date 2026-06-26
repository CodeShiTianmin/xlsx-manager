# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：把 PyQt 界面打成单文件 Windows exe。

构建：pyinstaller xlsx-manager.spec
产物：dist/xlsx-manager.exe
"""

block_cipher = None

a = Analysis(
    ["app/__main__.py"],
    pathex=[],
    binaries=[],
    # 只读资源（输出模板）随包带入，运行时通过 sys._MEIPASS 定位。
    datas=[("app/templates/output_template.xlsx", "templates")],
    hiddenimports=["openpyxl", "xlrd"],
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
    name="xlsx-manager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
