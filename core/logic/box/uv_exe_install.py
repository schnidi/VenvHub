#----------------------------------------
# Súbor: core/logic/box/uv_exe_install.py
#----------------------------------------

import os
import subprocess
from core._path import Paths
from core.logic.language_manager import LanguageManager

class UVExeInstaller:
    """
    Logika pre automatické pribalenie 'uv' nástroja do výsledného .exe.
    Sleduje, či sa uv.exe nachádza vo vybranom Venv-e a generuje parameter pre PyInstaller.
    """

    @staticmethod
    def get_uv_path_in_venv(venv_path: str) -> str:
        """Vráti presnú a znormalizovanú cestu k uv.exe vo vnútri zadaného venvu."""
        if not venv_path:
            return ""
        exe_name = "uv.exe" if os.name == "nt" else "uv"
        
        # Zložíme cestu dokopy
        raw_path = os.path.join(venv_path, Paths.VENV_SCRIPTS_DIR_NAME, exe_name)
        
        # --- KĽÚČOVÁ OPRAVA: ZNORMALIZUJEME LOMÍTKA ---
        # os.path.normpath() zaručí, že všetky lomítka budú správne pre daný OS (na Windows to budú \).
        normalized_path = os.path.normpath(raw_path)
        
        return normalized_path

    @staticmethod
    def is_uv_in_venv(venv_path: str) -> bool:
        """Skontroluje, či je 'uv' fyzicky nainštalované priamo v danom venve."""
        uv_path = UVExeInstaller.get_uv_path_in_venv(venv_path)
        return os.path.exists(uv_path)

    @staticmethod
    def install_uv_to_venv(venv_path: str) -> tuple[bool, str]:
        """
        Nainštaluje 'uv' priamo do vybraného venvu pomocou jeho vlastného pipu.
        Vracia (True/False, Popis chyby).
        Bezpečné aj bez internetu - proste vráti False.
        """
        python_exe = Paths.get_venv_python_exe_path(venv_path)
        if not os.path.exists(python_exe):
            err_msg = LanguageManager.get("uv_err_no_python", "Python interpreter nebol nájdený: {path}").format(path=python_exe)
            return False, err_msg

        try:
            creation_flags = 0x08000000 if os.name == 'nt' else 0
            
            process = subprocess.run(
                [python_exe, "-m", "pip", "install", "uv"],
                capture_output=True,
                text=True,
                creationflags=creation_flags
            )
            
            if process.returncode == 0:
                success_msg = LanguageManager.get("uv_install_success", "UV bolo úspešne nainštalované.")
                return True, success_msg
            else:
                error_output = process.stderr if process.stderr else process.stdout
                return False, error_output
                
        except Exception as e:
            return False, str(e)