#----------------------------------------
# Súbor: core/logic/python_detector.py
#----------------------------------------

import subprocess
import re
import sys
import os
import time

from core.logic.language_manager import LanguageManager
from core._path import Paths
from core.logic.sluzby.reload import DirectoryReloader

class PythonDetector:
    _cached_pythons = None  # --- PAMÄŤ NA ULOŽENIE ZOZNAMU PYTHONOV ---
    _active_python_path = None

    @staticmethod
    def set_active_python_path(python_path: str):
        """Nastaví aktuálne aktívny systémový Python."""
        if python_path:
            PythonDetector._active_python_path = os.path.normpath(python_path)

    @staticmethod
    def get_active_python_path() -> str:
        """Vráti aktívny Python, alebo ako zálohu spustený Python aplikácie."""
        return PythonDetector._active_python_path or os.path.normpath(sys.executable)

    @staticmethod
    def resolve_parent_python(venv_path: str) -> str:
        """
        Vyparsuje zo súboru pyvenv.cfg cestu k materskému Pythonu.
        Číta vždy čerstvé dáta z disku, ošetruje Windows blokovanie súboru a BOM bajty.
        """
        fallback_path = os.path.normpath(sys.executable)

        if not venv_path or not os.path.exists(venv_path):
            return fallback_path

        cfg_path = os.path.join(venv_path, "pyvenv.cfg")
        if not os.path.exists(cfg_path):
            return fallback_path

        max_retries = 3
        retry_delay = 0.1  # 100 ms pauza pri zamknutom súbore

        for attempt in range(max_retries):
            try:
                # 'utf-8-sig' automaticky odstrihne skryté BOM bajty na Windows
                with open(cfg_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("home ="):
                            parts = line.split("=", 1)
                            if len(parts) > 1:
                                home_dir = parts[1].strip()
                                if home_dir:
                                    exe_name = "python.exe" if os.name == 'nt' else "python"
                                    return os.path.normpath(os.path.join(home_dir, exe_name))
                break  # Ak prečítal súbor a 'home =' nenašiel, vyskoč z cyklu
            except (PermissionError, OSError):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except Exception:
                break

        return fallback_path

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

    # --- METÓDY NA ÚPRAVU PAMÄTE BEZ SKENOVANIA DISKU ---
    
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