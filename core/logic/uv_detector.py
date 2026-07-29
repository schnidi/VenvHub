#----------------------------------------
# Súbor: core/logic/uv_detector.py
#----------------------------------------

import os
import shutil
from pathlib import Path
from core.logic.python_detector import PythonDetector
from core._path import Paths

class UVDetector:
    _cached_path: str | None = None
    _was_searched: bool = False

    @staticmethod
    def get_uv_path() -> str | None:
        """
        Zistí cestu k uv binárke.
        Poradie hľadania:
        1. Zabalené v aplikácii (PyInstaller MEIPASS)
        2. V aktívnom Python prostredí (Scripts / bin)
        3. Štandardné inštalačné zložky (Cargo, Local binaries)
        4. Systémová PATH (shutil.which)
        """
        if UVDetector._was_searched:
            return UVDetector._cached_path

        exe_name = "uv.exe" if os.name == "nt" else "uv"

        # --- Stratégia 0: Vstavané UV priamo v zabalenej aplikácii ---
        internal_uv_path = os.path.join(Paths.get_base_path(), exe_name)
        if os.path.exists(internal_uv_path):
            return UVDetector._cache_and_return(internal_uv_path)

        # --- Stratégia 1: Hľadanie v aktívne vybranom Pythone ---
        try:
            active_py = PythonDetector.get_active_python_path()
            if active_py:
                active_dir = os.path.dirname(active_py)
                scripts_dir = "Scripts" if os.name == "nt" else "bin"
                potential_path = os.path.join(active_dir, scripts_dir, exe_name)
                if os.path.exists(potential_path):
                    return UVDetector._cache_and_return(potential_path)
        except Exception:
            pass

        # --- Stratégia 2: Manuálne hľadanie v známych lokalitách (Cargo / Local / Standalone) ---
        home_dir = Path.home()
        search_dirs = [
            home_dir / ".cargo" / "bin",
            home_dir / ".local" / "bin",
        ]
        
        if os.name == "nt":
            # Windows špecifická cesta pre standalone uv inštalátor
            search_dirs.append(home_dir / "AppData" / "Local" / "bin")

        for dir_path in search_dirs:
            potential_path = dir_path / exe_name
            if potential_path.exists():
                return UVDetector._cache_and_return(str(potential_path))

        # --- Stratégia 3: Systémová PATH ---
        sys_path = shutil.which("uv")
        if sys_path and os.path.exists(sys_path):
            return UVDetector._cache_and_return(sys_path)

        # Ak sa nikde nenašlo
        UVDetector._was_searched = True
        UVDetector._cached_path = None
        return None

    @staticmethod
    def is_uv_installed() -> bool:
        """Pomocná metóda pre zistenie, či je UV prítomné."""
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