#----------------------------------------
# Súbor: core/logic/button/pip/pip_command_worker.py
#----------------------------------------

import os
import subprocess
import re
from PyQt6.QtCore import QObject, pyqtSignal
from core.logic.birth_certificate import BirthCertificateGenerator
from core.logic.language_manager import LanguageManager
from core.logic.commands.command_factory import PackageManagerFactory

class PipCommandWorker(QObject):
    """
    Univerzálny worker, ktorý na pozadí spustí ľubovoľný príkaz
    (dostane ho už poskladaný z Factory) a priebežne posiela výstup.
    """
    started = pyqtSignal()
    output_line = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, venv_path, full_command, manager_type="pip"):
        super().__init__()
        self.venv_path = venv_path
        self.manager_type = manager_type
        # Očakáva komplet zoznam, napr. ['uv', 'pip', 'install', 'numpy', '--python', '...']
        self.full_command = full_command 

    def run(self):
        try:
            self.started.emit()
            CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            process = subprocess.Popen(
                self.full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                creationflags=CREATE_NO_WINDOW
            )

            for line in process.stdout:
                self.output_line.emit(line.strip())

            process.wait()

            if process.returncode == 0:
                # --- KONTROLA ZÁVISLOSTÍ PRE UV VETVU ---
                if self.manager_type == "uv":
                    self.output_line.emit(LanguageManager.get("uv_checking_deps", "--- Vykonávam UV kontrolu závislostí... ---"))
                    dispatcher = PackageManagerFactory.get_dispatcher("uv", self.venv_path)
                    cmd_check = dispatcher.get("check")
                    check_proc = subprocess.run(cmd_check, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                    
                    if check_proc.returncode != 0:
                        output_text = check_proc.stdout + "\n" + check_proc.stderr
                        conflicts = list(set(re.findall(r"requires\s+`([^`]+)`", output_text)))
                        
                        if conflicts:
                            self.output_line.emit(LanguageManager.get("uv_found_conflicts", "Zistené konflikty: {0}").format(', '.join(conflicts)))
                            self.output_line.emit(LanguageManager.get("uv_fixing_downgrade", "Pokúšam sa o automatickú opravu (downgrade/inštaláciu presných verzií)..."))
                            
                            cmd_fix = dispatcher.get("install_multiple_exact", packages=conflicts)
                            fix_proc = subprocess.Popen(
                                cmd_fix, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.STDOUT, 
                                text=True, 
                                encoding='utf-8',
                                bufsize=1,
                                creationflags=CREATE_NO_WINDOW
                            )
                            for line in fix_proc.stdout:
                                self.output_line.emit(line.strip())
                            fix_proc.wait()
                            
                            if fix_proc.returncode == 0:
                                self.output_line.emit(LanguageManager.get("uv_verifying", "Overujem stav po oprave..."))
                                check2_proc = subprocess.run(cmd_check, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                                if check2_proc.returncode == 0 or "All installed packages are compatible" in check2_proc.stdout:
                                    self.output_line.emit(LanguageManager.get("uv_fix_ok", "✅ Všetky konflikty boli úspešne vyriešené."))
                                else:
                                    self.output_line.emit(LanguageManager.get("uv_fix_fail_check_log", "⚠️ Nepodarilo sa vyriešiť všetky konflikty. Skontrolujte log."))
                            else:
                                self.output_line.emit(LanguageManager.get("uv_fix_error_manual", "⚠️ Automatická oprava zlyhala. Opravte závislosti manuálne."))
                        else:
                            self.output_line.emit(LanguageManager.get("uv_parse_error_worker", "⚠️ Boli nájdené problémy so závislosťami, ale aplikácia ich nedokázala automaticky vyparsovať."))
                    else:
                        self.output_line.emit(LanguageManager.get("uv_compatible", "✅ Všetky závislosti sú kompatibilné."))

                BirthCertificateGenerator.update_venv_certificate(self.venv_path)
            
            self.finished.emit(process.returncode)

        except Exception as e:
            err_msg = LanguageManager.get("pip_worker_err_critical", "Nastala kritická chyba pri spúšťaní príkazu: {error}").format(error=e)
            self.error.emit(err_msg)