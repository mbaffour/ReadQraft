# Build with: pyinstaller backend/pyinstaller.spec
block_cipher = None

a = Analysis(
    ["app/serve.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=["uvicorn", "uvicorn.lifespan.on", "uvicorn.protocols.http.h11_impl"],
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
    name="readqraft-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
