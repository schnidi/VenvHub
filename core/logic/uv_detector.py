#----------------------------------------
# Súbor: core/logic/uv_detector.py
#----------------------------------------

import shutil
import os
import subprocess
import re
from pathlib import Path
from core._path import Paths  # <--- PRIDANÝ IMPORT

class UVDetector:
    _cached_path: str | None = None
    _was_searched: bool = False

    @staticmethod
    def get_uv_path() -> str | None:
        if UVDetector._was_searched:
            return UVDetector._cached_path

        exe_name = "uv.exe" if os.name == "nt" else "uv"

        # --- Stratégia 0: Hľadanie priamo v ZABALENOM .exe ---
        # Paths.get_base_path() vráti sys._MEIPASS, keď beží ako exe
        internal_uv_path = os.path.join(Paths.get_base_path(), exe_name)
        if os.path.exists(internal_uv_path):
            return UVDetector._cache_and_return(internal_uv_path)

        # --- Stratégia 1: Štandardné systémové príkazy (rýchle a efektívne) ---
        path = shutil.which("uv")
        if path and os.path.exists(path):
            return UVDetector._cache_and_return(path)
        
        try:
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            cmd = "where uv" if os.name == 'nt' else "command -v uv"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, check=False)
            if result.returncode == 0 and result.stdout.strip():
                first_path = result.stdout.strip().splitlines()[0].strip()
                if os.path.exists(first_path):
                    return UVDetector._cache_and_return(first_path)
        except Exception:
            pass

        # --- Stratégia 2: Priama otázka na 'pip' (rieši problém s --user inštaláciami) ---
        try:
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            cmd_pip_show = ["py", "-m", "pip", "show", "uv"]
            result_pip = subprocess.run(cmd_pip_show, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, check=False)

            if result_pip.returncode == 0:
                location_match = re.search(r"Location:\s*(.+)", result_pip.stdout)
                if location_match:
                    site_packages_path = location_match.group(1).strip()
                    scripts_dir = Path(site_packages_path).parent / ("Scripts" if os.name == 'nt' else "bin")
                    potential_path = scripts_dir / exe_name
                    
                    if potential_path.exists():
                        return UVDetector._cache_and_return(str(potential_path))
        except Exception:
            pass

        # --- Stratégia 3: Posledná záchrana - manuálne hľadanie v bežných lokalitách ---
        search_dirs = []
        home_dir = str(Path.home())
        search_dirs.append(os.path.join(home_dir, ".cargo", "bin")) 
        search_dirs.append(os.path.join(home_dir, ".local", "bin")) 

        for dir_path in search_dirs:
            potential_path = os.path.join(dir_path, exe_name)
            if os.path.exists(potential_path):
                return UVDetector._cache_and_return(potential_path)
        
        UVDetector._was_searched = True
        UVDetector._cached_path = None
        return None

    @staticmethod
    def is_uv_installed() -> bool:
        return UVDetector.get_uv_path() is not None

    @staticmethod
    def reset_cache():
        UVDetector._was_searched = False
        UVDetector._cached_path = None
    
    @staticmethod
    def _cache_and_return(path: str) -> str:
        UVDetector._cached_path = path
        UVDetector._was_searched = True
        return path