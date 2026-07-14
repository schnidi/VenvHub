#----------------------------------------
# Súbor: core/logic/pip_manager.py
#----------------------------------------

import os
import subprocess
import threading
import re
from PyQt6.QtCore import QObject, pyqtSignal

from core.logic.language_manager import LanguageManager
from core._path import Paths
# --- IMPORT FACTORY NAMIESTO PRIAMEHO DISPEČERA ---
from core.logic.commands.command_factory import PackageManagerFactory
from core.logic.birth_certificate import BirthCertificateGenerator

class PipSignalEmitter(QObject):
    log_message = pyqtSignal(str)
    finished = pyqtSignal()

class PipWorker:
    def __init__(self, cmd, start_msg, venv_path=None):
        self.cmd = cmd
        self.start_msg = start_msg
        self.venv_path = venv_path
        self.signals = PipSignalEmitter()
        
    def run(self):
        self.signals.log_message.emit(f"\n--- {self.start_msg} ---")
        try:
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=CREATE_NO_WINDOW)
            for line in process.stdout: 
                self.signals.log_message.emit(line.strip())
            process.wait()
            
            if process.returncode == 0 and self.venv_path:
                BirthCertificateGenerator.update_venv_certificate(self.venv_path)

            msg_done = LanguageManager.get("msg_done", "--- HOTOVO ---")
            self.signals.log_message.emit(msg_done)
            
        except FileNotFoundError: 
            msg = LanguageManager.get("err_cmd_not_found", "KRITICKÁ CHYBA: Príkaz nebol nájdený: {0}").format(' '.join(self.cmd))
            self.signals.log_message.emit(msg)
        except Exception as e: 
            msg = LanguageManager.get("err_critical", "KRITICKÁ CHYBA: {0}").format(str(e))
            self.signals.log_message.emit(msg)
        finally: 
            self.signals.finished.emit()

class UpdateAllWorker:
    def __init__(self, venv_path, manager_type):
        self.venv_path = venv_path
        self.manager_type = manager_type
        self.signals = PipSignalEmitter()

    def run(self):
        CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
        try:
            # POUŽITIE FACTORY!
            dispatcher = PackageManagerFactory.get_dispatcher(self.manager_type, self.venv_path)
            
            msg_step1 = LanguageManager.get("msg_step1_pip", "\n--- Krok 1: Kontrolujem a aktualizujem inštalátor... ---")
            self.signals.log_message.emit(msg_step1)
            
            cmd_update_pip = dispatcher.get("upgrade_pip")
            pip_process = subprocess.run(cmd_update_pip, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if pip_process.returncode == 0:
                BirthCertificateGenerator.update_venv_certificate(self.venv_path)

            full_output = (pip_process.stdout + pip_process.stderr).strip()
            for line in full_output.split('\n'):
                if line: self.signals.log_message.emit(line)

            msg_step2 = LanguageManager.get("msg_step2_outdated", "\n--- Krok 2: Hľadám ostatné zastarané balíčky... ---")
            self.signals.log_message.emit(msg_step2)
            
            cmd_list = dispatcher.get("list_outdated")
            list_process = subprocess.run(cmd_list, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)

            if list_process.returncode != 0:
                msg_err = LanguageManager.get("err_list_failed", "CHYBA: Nepodarilo sa získať zoznam balíčkov.")
                self.signals.log_message.emit(msg_err)
                self.signals.log_message.emit(list_process.stderr)
                return

            lines = list_process.stdout.strip().split('\n')[2:]
            outdated_packages = [line.split()[0] for line in lines if line.strip()]

            if not outdated_packages:
                msg_all_ok = LanguageManager.get("msg_all_pkgs_ok", ">>> Zhrnutie: Všetky ostatné balíčky sú aktuálne. Niet čo robiť.")
                msg_done = LanguageManager.get("msg_done", "--- HOTOVO ---")
                self.signals.log_message.emit(msg_all_ok)
                self.signals.log_message.emit(msg_done)
                return

            msg_found = LanguageManager.get("msg_found_outdated", "Nájdené zastarané balíčky: {0}").format(', '.join(outdated_packages))
            self.signals.log_message.emit(msg_found)
            
            cmd_upgrade = dispatcher.get("upgrade_multiple", packages=outdated_packages)
            
            msg_step3 = LanguageManager.get("msg_step3_upgrade", "\n--- Krok 3: Aktualizujem nájdené balíčky... ---")
            self.signals.log_message.emit(msg_step3)
            
            upgrade_process = subprocess.Popen(cmd_upgrade, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=CREATE_NO_WINDOW)
            for line in upgrade_process.stdout: self.signals.log_message.emit(line.strip())
            upgrade_process.wait()

            if upgrade_process.returncode == 0:
                
                # --- KROK 4: KONTROLA A OPRAVA UV ZÁVISLOSTÍ ---
                if self.manager_type == "uv":
                    self.signals.log_message.emit("\n--- Krok 4: Kontrola a oprava závislostí (UV Check) ---")
                    cmd_check = dispatcher.get("check")
                    check_proc = subprocess.run(cmd_check, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                    
                    if check_proc.returncode != 0:
                        output_text = check_proc.stdout + "\n" + check_proc.stderr
                        
                        # Vytiahne z logu: requires `google-ai-generativelanguage==0.6.15`
                        conflicts = list(set(re.findall(r"requires\s+`([^`]+)`", output_text)))
                        
                        if conflicts:
                            self.signals.log_message.emit(LanguageManager.get("uv_found_conflicts", "Zistené konflikty: {0}").format(', '.join(conflicts)))
                            self.signals.log_message.emit(LanguageManager.get("uv_fixing", "Pokúšam sa o automatickú opravu (downgrade na presné verzie)..."))
                            
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
                                self.signals.log_message.emit(line.strip())
                            fix_proc.wait()
                            
                            if fix_proc.returncode == 0:
                                self.signals.log_message.emit(LanguageManager.get("uv_verifying", "Overujem stav po oprave..."))
                                check2_proc = subprocess.run(cmd_check, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                                if check2_proc.returncode == 0 or "All installed packages are compatible" in check2_proc.stdout:
                                    self.signals.log_message.emit(LanguageManager.get("uv_fix_ok", "✅ Všetky konflikty boli úspešne vyriešené."))
                                else:
                                    self.signals.log_message.emit(LanguageManager.get("uv_fix_fail", "⚠️ Nepodarilo sa vyriešiť všetky konflikty."))
                            else:
                                self.signals.log_message.emit(LanguageManager.get("uv_fix_error", "⚠️ Automatická oprava zlyhala."))
                        else:
                            self.signals.log_message.emit(LanguageManager.get("uv_parse_error", "⚠️ Našli sa problémy, ale aplikácia ich nedokázala vyparsovať."))
                            for line in output_text.splitlines():
                                if line.strip(): self.signals.log_message.emit(line.strip())
                    else:
                        self.signals.log_message.emit(LanguageManager.get("uv_compatible", "✅ Všetky závislosti sú kompatibilné."))

                BirthCertificateGenerator.update_venv_certificate(self.venv_path)
            
            msg_all_updated = LanguageManager.get("msg_all_updated", "--- Všetko aktualizované ---")
            self.signals.log_message.emit(msg_all_updated)

        except Exception as e:
            msg_crit = LanguageManager.get("err_critical", "KRITICKÁ CHYBA: {0}").format(str(e))
            self.signals.log_message.emit(msg_crit)
        finally:
            self.signals.finished.emit()


class PipManager:
    _current_thread = None
    _current_worker = None

    @staticmethod
    def _run_pip_task(worker, log_widget):
        if PipManager._current_thread and PipManager._current_thread.is_alive():
            msg = LanguageManager.get("msg_busy", "!!! Už prebieha iná operácia, počkajte na jej dokončenie. !!!")
            log_widget.append(msg)
            return
        worker.signals.log_message.connect(log_widget.append)
        PipManager._current_worker = worker
        PipManager._current_thread = threading.Thread(target=worker.run, daemon=True)
        PipManager._current_thread.start()
        
    @staticmethod
    def install_package(venv_path, package_name, log_widget, manager_type="pip"):
        try:
            dispatcher = PackageManagerFactory.get_dispatcher(manager_type, venv_path)
            cmd = dispatcher.get("install", package_name=package_name)
        except (ValueError, KeyError) as e:
            log_widget.append(f"CHYBA: {e}")
            return
            
        start_msg = LanguageManager.get("msg_installing", "Inštalujem {0}...").format(package_name)
        worker = PipWorker(cmd, start_msg, venv_path)
        PipManager._run_pip_task(worker, log_widget)
        
    @staticmethod
    def uninstall_package(venv_path, package_name, log_widget, manager_type="pip"):
        try:
            dispatcher = PackageManagerFactory.get_dispatcher(manager_type, venv_path)
            cmd = dispatcher.get("uninstall", package_name=package_name)
        except (ValueError, KeyError) as e:
            log_widget.append(f"CHYBA: {e}")
            return
            
        start_msg = LanguageManager.get("msg_uninstalling", "Odinštalujem {0}...").format(package_name)
        worker = PipWorker(cmd, start_msg, venv_path)
        PipManager._run_pip_task(worker, log_widget)

    @staticmethod
    def install_requirements(venv_path, project_root, log_widget, manager_type="pip"):
        req_path = Paths.get_requirements_txt_path(project_root)
        if not os.path.exists(req_path):
            msg = LanguageManager.get("err_req_not_found", "CHYBA: Súbor 'requirements.txt' nebol nájdený.")
            log_widget.append(msg)
            return
        
        try:
            dispatcher = PackageManagerFactory.get_dispatcher(manager_type, venv_path)
            cmd = dispatcher.get("install_requirements", project_root=project_root)
        except (ValueError, KeyError) as e:
            log_widget.append(f"CHYBA: {e}")
            return
            
        start_msg = LanguageManager.get("msg_installing_req", "Inštalujem z requirements.txt...")
        worker = PipWorker(cmd, start_msg, venv_path)
        PipManager._run_pip_task(worker, log_widget)
        
    @staticmethod
    def update_all_packages(venv_path, log_widget, manager_type="pip"):
        worker = UpdateAllWorker(venv_path, manager_type)
        PipManager._run_pip_task(worker, log_widget)