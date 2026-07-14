import subprocess
from core._path import Paths
from core.logic.language_manager import LanguageManager

class InstallHandler:
    @staticmethod
    def run(venv_path, package_name, version=None, log_callback=None):
        """
        Nainštaluje balíček. Ak je zadaná verzia, nainštaluje konkrétnu verziu.
        log_callback je funkcia, ktorá prijíma text (napr. pre výpis do konzoly v okne).
        """
        python_exe = Paths.get_venv_python_exe_path(venv_path)
        CREATE_NO_WINDOW = 0x08000000
        
        cmd = [python_exe, "-m", "pip", "install"]
        
        if version:
            target = f"{package_name}=={version}"
            if log_callback: 
                log_callback(LanguageManager.get("install_log_version", "Inštalujem verziu: {target}...").format(target=target))
        else:
            target = package_name
            if log_callback: 
                log_callback(LanguageManager.get("install_log_package", "Inštalujem balíček: {target}...").format(target=target))
            
        cmd.append(target)

        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                creationflags=CREATE_NO_WINDOW
            )
            
            # Čítanie výstupu v reálnom čase
            for line in process.stdout:
                if log_callback:
                    log_callback(line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                if log_callback: 
                    log_callback(LanguageManager.get("install_log_success", "--- ÚSPEŠNE DOKONČENÉ ---"))
                return True
            else:
                if log_callback: 
                    log_callback(LanguageManager.get("install_log_error", "--- CHYBA PRI INŠTALÁCII ---"))
                return False

        except Exception as e:
            if log_callback: 
                log_callback(LanguageManager.get("install_err_critical", "KRITICKÁ CHYBA: {error}").format(error=str(e)))
            return False