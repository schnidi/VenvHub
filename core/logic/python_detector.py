#----------------------------------------
# Súbor: core/logic/python_detector.py
#----------------------------------------

import subprocess
import re
import sys
import os

from core.logic.language_manager import LanguageManager
from core._path import Paths
from core.logic.sluzby.reload import DirectoryReloader

class PythonDetector:
    _cached_pythons = None  # --- PAMÄŤ NA ULOŽENIE ZOZNAMU PYTHONOV ---

    @staticmethod
    def get_installed_pythons(force_refresh=False):
        """Vráti zoznam Pythonov. Ak nepožadujeme force_refresh, vráti údaje rýchlo z pamäte."""
        if PythonDetector._cached_pythons is not None and not force_refresh:
            return PythonDetector._cached_pythons

        pythons = []
        CREATE_NO_WINDOW = 0x08000000
        
        # 1. ČASŤ: Hľadanie SYSTÉMOVÝCH verzií
        try:
            output = subprocess.check_output(["py", "--list-paths"], text=True, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
            for line in output.strip().split('\n'):
                match = re.search(r'-V:([\d\.]+).*?\s+([a-zA-Z]:\\.*)', line)
                if match:
                    pythons.append({
                        'display': f"Python {match.group(1)}",
                        'path': match.group(2).strip(),
                        'is_local': False,
                        'pip_status': "OK"  # Systémové pipy považujeme predvolene za OK
                    })
        except Exception:
            pass
        
        # Ak nič nenájde cez py launcher, pridá aspoň sys.executable
        if not any(p['path'] == sys.executable for p in pythons):
            sys_default_text = LanguageManager.get("txt_sys_default", "System Default")
            pythons.append({
                'display': sys_default_text,
                'path': sys.executable,
                'is_local': False,
                'pip_status': "OK"
            })

        # 2. ČASŤ: Hľadanie LOKÁLNYCH (embed) verzií v PyRuntimes
        try:
            install_dir = Paths.get_python_runtimes_install_dir()
            if os.path.exists(install_dir):
                valid_folders = DirectoryReloader.get_subdirectories(target_dir=install_dir, required_file="install.ini")
                for folder_data in valid_folders:
                    local_exe = os.path.join(folder_data['path'], 'python.exe')
                    if os.path.exists(local_exe):
                        pythons.append({
                            'display': f"[Local] {folder_data['name']}",
                            'path': local_exe,
                            'is_local': True,
                            'pip_status': "checking"  # Bude skontrolované neskôr asynchrónne
                        })
        except Exception as e:
            print(f"Chyba pri načítaní lokálnych Pythonov: {e}")
        
        PythonDetector._cached_pythons = pythons
        return pythons

    # --- NOVÉ METÓDY NA ÚPRAVU PAMÄTE BEZ SKENOVANIA DISKU ---
    
    @staticmethod
    def add_local_python(folder_name, python_path, pip_status="OK"):
        if PythonDetector._cached_pythons is None:
            PythonDetector.get_installed_pythons(force_refresh=True)
        PythonDetector._cached_pythons.append({
            'display': f"[Local] {folder_name}",
            'path': python_path,
            'is_local': True,
            'pip_status': pip_status
        })

    @staticmethod
    def remove_local_python(python_path):
        if PythonDetector._cached_pythons:
            PythonDetector._cached_pythons = [
                p for p in PythonDetector._cached_pythons 
                if os.path.normpath(p['path']).lower() != os.path.normpath(python_path).lower()
            ]

    @staticmethod
    def update_pip_status(python_path, status_text):
        if PythonDetector._cached_pythons:
            for p in PythonDetector._cached_pythons:
                if os.path.normpath(p['path']).lower() == os.path.normpath(python_path).lower():
                    p['pip_status'] = status_text
                    break