import subprocess
import json
from core._path import Paths

class UpdateAllHandler:
    @staticmethod
    def run(venv_path, log_callback=None):
        python_exe = Paths.get_venv_python_exe_path(venv_path)
        CREATE_NO_WINDOW = 0x08000000
        
        if log_callback: log_callback("Hľadám zastarané balíčky...")

        # 1. Získame zoznam outdated
        try:
            cmd_list = [python_exe, "-m", "pip", "list", "--outdated", "--format=json"]
            result = subprocess.run(cmd_list, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                if log_callback: log_callback("Chyba pri hľadaní aktualizácií.")
                return False
                
            outdated = json.loads(result.stdout)
            packages_to_update = [item['name'] for item in outdated]
            
            if not packages_to_update:
                if log_callback: log_callback("Všetky balíčky sú aktuálne.")
                return True

        except Exception as e:
            if log_callback: log_callback(f"Chyba: {str(e)}")
            return False

        # 2. Aktualizujeme ich naraz
        pkg_str = ", ".join(packages_to_update)
        if log_callback: log_callback(f"Aktualizujem: {pkg_str}")
        
        cmd_update = [python_exe, "-m", "pip", "install", "--upgrade"] + packages_to_update
        
        try:
            process = subprocess.Popen(
                cmd_update, 
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
                if log_callback: log_callback("--- VŠETKO AKTUALIZOVANÉ ---")
                return True
            else:
                if log_callback: log_callback("--- CHYBA PRI HROMADNEJ AKTUALIZÁCII ---")
                return False

        except Exception as e:
            if log_callback: log_callback(f"KRITICKÁ CHYBA: {str(e)}")
            return False