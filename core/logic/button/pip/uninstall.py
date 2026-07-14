import subprocess
from core._path import Paths

class UninstallHandler:
    @staticmethod
    def run(venv_path, package_name, log_callback=None):
        python_exe = Paths.get_venv_python_exe_path(venv_path)
        CREATE_NO_WINDOW = 0x08000000
        
        if log_callback: log_callback(f"Odinštalujem balíček: {package_name}...")

        # Pridáme -y pre automatické potvrdenie
        cmd = [python_exe, "-m", "pip", "uninstall", "-y", package_name]

        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                creationflags=CREATE_NO_WINDOW
            )
            
            for line in process.stdout:
                if log_callback:
                    log_callback(line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                if log_callback: log_callback("--- ÚSPEŠNE ODSTRÁNENÉ ---")
                return True
            else:
                if log_callback: log_callback("--- CHYBA PRI ODINŠTALÁCII ---")
                return False

        except Exception as e:
            if log_callback: log_callback(f"KRITICKÁ CHYBA: {str(e)}")
            return False