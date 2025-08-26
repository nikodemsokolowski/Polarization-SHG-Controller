# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# --- Basic Application Info ---
app_name = "PolarizationScanController"
script_path = 'main_app.py'
icon_path = None # Optional: 'path/to/your/icon.ico'

# --- Collect Data Files ---
# Add data files needed by dependencies (e.g., customtkinter themes, matplotlib data)
datas = []
datas += collect_data_files('customtkinter')
datas += collect_data_files('matplotlib')

# --- Add LightField DLLs ---
lf_sdk_path = r"C:\ProgramData\Documents\Princeton Instruments\LightField\Add-in and Automation SDK\Samples\Binaries"
# Define required DLLs
automation_dll = 'PrincetonInstruments.LightField.AutomationV5.dll'
support_dll = 'PrincetonInstruments.LightFieldAddInSupportServices.dll'
view_dll = 'PrincetonInstruments.LightFieldViewV5.dll' # Added based on working example

lf_dlls = [
    (automation_dll, lf_sdk_path, 'lib'), # Copy DLL to 'lib' subdir
    (support_dll, lf_sdk_path, 'lib'), # Copy DLL to 'lib' subdir
    (view_dll, lf_sdk_path, 'lib') # Copy DLL to 'lib' subdir
]
# Check if the path and ALL required DLLs exist before adding
if os.path.isdir(lf_sdk_path) and \
   os.path.isfile(os.path.join(lf_sdk_path, automation_dll)) and \
   os.path.isfile(os.path.join(lf_sdk_path, support_dll)) and \
   os.path.isfile(os.path.join(lf_sdk_path, view_dll)):
    datas.extend(lf_dlls)
    print(f"INFO: Added LightField DLLs from {lf_sdk_path} to datas.")
else:
    print(f"WARNING: LightField SDK path or DLLs not found at {lf_sdk_path}. DLLs will NOT be included in the build.")
# --- End Add LightField DLLs ---

# Add Kinesis DLLs? Might be needed if ctypes doesn't find them relative to installed path
# kinesis_path = r"C:\Program Files\Thorlabs\Kinesis"
# kinesis_dlls = [
#     ('Thorlabs.MotionControl.DeviceManager.dll', kinesis_path, 'kinesis'),
#     ('Thorlabs.MotionControl.KCube.DCServo.dll', kinesis_path, 'kinesis')
# ]
# datas.extend(kinesis_dlls) # Add DLLs to be bundled in a 'kinesis' subdir

# --- Hidden Imports ---
# List modules that PyInstaller might miss
hiddenimports = [
    'matplotlib.backends.backend_tkagg',
    'scipy.optimize', # Used in analysis_module
    'scipy.special', # Often a dependency of scipy.optimize
    'clr', # For pythonnet
    # Add any specific namespaces needed from LightField DLLs if clr doesn't find them
    # 'PrincetonInstruments.LightField.Automation',
    # 'PrincetonInstruments.LightField.AddIns',
]

# --- Analysis ---
a = Analysis(
    [script_path],
    pathex=[], # Add project root if needed: [os.getcwd()]
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- PYC Generation ---
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- Executable ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Set to False if UPX causes issues
    console=True,         # Set to True for debugging console output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,       # Add icon here
)

# --- Bundle ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

# --- Mac Specific (Optional) ---
# app = BUNDLE(...) # Use BUNDLE for macOS .app creation if needed
