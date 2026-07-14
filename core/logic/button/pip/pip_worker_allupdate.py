#----------------------------------------
# Súbor: core/logic/button/pip/pip_worker_allupdate.py
#----------------------------------------

import subprocess
import json
import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
from core.logic.language_manager import LanguageManager
from core.logic.commands.command_factory import PackageManagerFactory
from core.logic.birth_certificate import BirthCertificateGenerator

class PipWorkerAllUpdate(QObject):
    started = pyqtSignal()
    output_line = pyqtSignal(str)
    finished = pyqtSignal(bool) 
    error = pyqtSignal(str)

    def __init__(self, venv_path, manager_type="pip"):
        super().__init__()
        self.venv_path = venv_path
        self.manager_type = manager_type

    def run(self):
        self.started.emit()
        CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
        
        # POUŽITIE FACTORY NA ZÍSKANIE DISPEČERA
        dispatcher = PackageManagerFactory.get_dispatcher(self.manager_type, self.venv_path)

        self.output_line.emit(LanguageManager.get("update_all_searching", "--- Hľadám zastarané balíčky... ---"))

        try:
            # 1. Získame zoznam zastaraných balíčkov
            cmd_list = dispatcher.get("list_outdated_json")
            result = subprocess.run(cmd_list, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                self.error.emit(LanguageManager.get("update_all_err_searching", "Chyba pri hľadaní aktualizácií."))
                self.output_line.emit(result.stderr)
                self.finished.emit(False)
                return
                
            try:
                outdated = json.loads(result.stdout)
            except json.JSONDecodeError:
                self.error.emit(LanguageManager.get("update_all_err_json", "Nepodarilo sa spracovať výstup JSON."))
                self.output_line.emit(result.stdout)
                self.finished.emit(False)
                return

            packages_to_update = [item['name'] for item in outdated]
            
            if not packages_to_update:
                self.output_line.emit(LanguageManager.get("update_all_uptodate", "Všetky balíčky sú aktuálne."))
                self.finished.emit(True)
                return

        except Exception as e:
            err_msg = LanguageManager.get("update_all_err_critical_search", "Kritická chyba pri hľadaní: {0}").format(str(e))
            self.error.emit(err_msg)
            self.finished.emit(False)
            return

        # 2. Aktualizujeme ich naraz
        pkg_str = ", ".join(packages_to_update)
        msg_found = LanguageManager.get("update_all_found", "Nájdené balíčky na aktualizáciu: {0}").format(pkg_str)
        self.output_line.emit(msg_found)
        self.output_line.emit(LanguageManager.get("update_all_starting", "--- Spúšťam aktualizáciu... ---"))
        
        # Generovanie príkazu pre update z dispečera
        cmd_update = dispatcher.get("upgrade_multiple", packages=packages_to_update)
        
        try:
            process = subprocess.Popen(
                cmd_update, 
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
                self.output_line.emit(LanguageManager.get("update_all_success", "--- VŠETKO ÚSPEŠNE AKTUALIZOVANÉ ---"))
                
                # --- KONTROLA ZÁVISLOSTÍ PRE UV VETVU ---
                if self.manager_type == "uv":
                    self.output_line.emit(LanguageManager.get("uv_checking_deps", "--- Vykonávam UV kontrolu závislostí... ---"))
                    cmd_check = dispatcher.get("check")
                    check_proc = subprocess.run(cmd_check, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                    
                    if check_proc.returncode != 0:
                        output_text = check_proc.stdout + "\n" + check_proc.stderr
                        
                        # Hľadá text typu: requires `balicek==verzia`
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
                            for line in output_text.splitlines():
                                if line.strip():
                                    self.output_line.emit(line.strip())
                    else:
                        self.output_line.emit(LanguageManager.get("uv_compatible", "✅ Všetky závislosti sú kompatibilné."))

                # --- FINÁLNY ZÁPIS RODNÉHO LISTU ---
                BirthCertificateGenerator.update_venv_certificate(self.venv_path)
                self.finished.emit(True)
            else:
                self.output_line.emit(LanguageManager.get("update_all_error_bulk", "--- CHYBA PRI HROMADNEJ AKTUALIZÁCII ---"))
                self.finished.emit(False)

        except Exception as e:
            err_msg = LanguageManager.get("update_all_err_critical_update", "Kritická chyba pri aktualizácii: {0}").format(str(e))
            self.error.emit(err_msg)
            self.finished.emit(False)