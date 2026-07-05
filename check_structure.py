import os
from pathlib import Path

required_folders = [
    'utils',
    'data_collector',
    'strategies',
    'signal_generator',
    'risk_management',
    'statistics',
    'backtesting',
    'ai_ml'
]

print("Checking project structure...")
for folder in required_folders:
    path = Path(folder)
    init_file = path / '__init__.py'
    
    if not path.exists():
        print(f"❌ MISSING FOLDER: {folder}")
    elif not init_file.exists():
        print(f"⚠️  MISSING __init__.py in: {folder}")
    else:
        print(f"✅ OK: {folder}")

if Path('main.py').exists():
    print("✅ OK: main.py found")
else:
    print("❌ MISSING: main.py")

if Path('config.yaml').exists():
    print("✅ OK: config.yaml found")
else:
    print("❌ MISSING: config.yaml")