#----------------------------------------
# Súbor: core/logic/sluzby/python_runtime_inspector.py
#----------------------------------------

import os
import glob
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

class PipStatusWorker(QObject):
    """
    Asynchrónny pracovník na kontrolu stavu PIPu na pozadí.
    Zabraňuje sekaniu GUI (tzv. presýpacie hodiny).
    """
    result_ready = pyqtSignal(str, bool)  # (python_exe_path, is_functional)
    finished = pyqtSignal()

    def __init__(self, python_paths: list[str]):
        super().__init__()
        self.python_paths = python_paths

    def run(self):
        for path in self.python_paths:
            is_ok = PythonRuntimeInspector.is_pip_functional(path)
            self.result_ready.emit(path, is_ok)
        self.finished.emit()


class PythonRuntimeInspector:
    """
    Inteligentná služba na kontrolu a opravu Python runtime prostredí.
    """

    @staticmethod
    def is_pip_functional(python_exe_path: str) -> bool:
        """
        Overí, či je PIP nainštalovaný a spustiteľný pre daný python.exe.
        """
        if not os.path.exists(python_exe_path):
            return False
            
        command = [python_exe_path, "-m", "pip", "--version"]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def ensure_site_packages_enabled(runtime_path: str) -> bool:
        """
        Nájde ._pth súbor a zabezpečí, aby bol odkomentovaný riadok 'import site'.
        Toto je kľúčové pre funkčnosť pip v embeddable verziách.
        """
        pth_files = glob.glob(os.path.join(runtime_path, "python*._pth"))
        if not pth_files:
            return False

        pth_file_path = pth_files[0]
        
        try:
            with open(pth_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            needs_change = True
            for line in lines:
                if line.strip() == "import site":
                    needs_change = False
                    break
            
            if not needs_change:
                return True

            new_lines = []
            was_changed = False
            for line in lines:
                if line.strip() == "#import site":
                    new_lines.append("import site\n")
                    was_changed = True
                else:
                    new_lines.append(line)

            if was_changed:
                with open(pth_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            return True

        except (IOError, PermissionError) as e:
            print(f"Chyba pri úprave ._pth súboru: {e}")
            return False