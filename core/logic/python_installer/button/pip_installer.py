#----------------------------------------
# Súbor: core/logic/python_installer/button/pip_installer.py
#----------------------------------------

import os
import subprocess
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core._path import Paths
from core.logic.sluzby.downloader import Downloader
from core.logic.sluzby.python_runtime_inspector import PythonRuntimeInspector
from core.logic.sluzby.win_admin import WinAdmin
from core.logic.python_detector import PythonDetector
from core.logic.language_manager import LanguageManager

class PipInstallWorker(QObject):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(dict)
    
    def __init__(self, python_exe_path: str):
        super().__init__()
        self.python_exe_path = os.path.normpath(python_exe_path)
        self.get_pip_url = "https://bootstrap.pypa.io/get-pip.py"

    def run(self):
        if not os.path.exists(self.python_exe_path):
            error_msg = LanguageManager.get("err_py_exe_not_found", "Fatal Error: python.exe not found at the expected path: {0}").format(self.python_exe_path)
            self.finished.emit({'success': False, 'error': error_msg})
            return

        self.progress_log.emit(LanguageManager.get("msg_downloading_get_pip", "Sťahujem inštalačný skript get-pip.py..."))
        temp_dir = Paths.get_python_downloads_dir()
        script_path = os.path.join(temp_dir, "get-pip.py")
        
        download_result = Downloader.download_file(self.get_pip_url, script_path)
        if not download_result['success']:
            error_msg = LanguageManager.get("msg_download_err", "Chyba pri sťahovaní: {0}").format(download_result['error'])
            self.finished.emit({'success': False, 'error': error_msg})
            return
            
        runtime_path = os.path.dirname(self.python_exe_path)
        
        if WinAdmin.needs_admin_for_path(self.python_exe_path):
            self.progress_log.emit(LanguageManager.get("msg_uac_needed", "Vyžadujú sa práva Administrátora. Prosím, potvrďte systémové UAC okno..."))
            marker_file = os.path.join(temp_dir, "pip_done.marker")
            
            pth_fix_code = "import os, glob; [open(p, 'w', encoding='utf-8').write(open(p, 'r', encoding='utf-8').read().replace('#import site', 'import site')) for p in glob.glob('*._pth')]"
            
            # --- ZMENA: Vložili sme echovanie stavov medzi jednotlivé kroky ---
            cmd_string = (
                f'cd /d "{runtime_path}"\n'
                f'echo [STATUS] INSTALLING_PIP > "{marker_file}"\n'
                f'"{self.python_exe_path}" "{script_path}"\n'
                f'if %errorlevel% neq 0 exit /b %errorlevel%\n'
                f'echo [STATUS] FIXING_PTH > "{marker_file}"\n'
                f'"{self.python_exe_path}" -c "{pth_fix_code}"\n'
                f'if %errorlevel% neq 0 exit /b %errorlevel%\n'
                f'echo [STATUS] INSTALLING_VENV > "{marker_file}"\n'
                f'"{self.python_exe_path}" -m pip install virtualenv\n'
            )
            
            # --- ZMENA: Live čítanie stavov zo skrytého procesu ---
            def on_state_changed(state_str):
                if state_str == "[STATUS] UAC_APPROVED":
                    self.progress_log.emit(LanguageManager.get("msg_pip_uac_approved", "✅ UAC schválené. Inštalátor prevzal kontrolu..."))
                elif state_str == "[STATUS] INSTALLING_PIP":
                    self.progress_log.emit(LanguageManager.get("msg_pip_installing_base", "Inštalujem základný balíček PIP..."))
                elif state_str == "[STATUS] FIXING_PTH":
                    self.progress_log.emit(LanguageManager.get("msg_pip_fixing_pth", "Aktivujem prístup k balíčkom (site-packages)..."))
                elif state_str == "[STATUS] INSTALLING_VENV":
                    self.progress_log.emit(LanguageManager.get("msg_pip_installing_venv_admin", "Inštalujem modul 'virtualenv'..."))
                elif state_str == "[STATUS] DONE":
                    self.progress_log.emit(LanguageManager.get("msg_pip_done", "✅ Oprava administrátorom úspešne dokončená."))
                elif state_str == "[STATUS] ERROR":
                    self.progress_log.emit(LanguageManager.get("msg_pip_error_admin", "❌ Proces zlyhal počas vykonávania administrátorských opráv."))

            success = WinAdmin.run_cmd_with_uac_and_wait(cmd_string, marker_file, state_callback=on_state_changed)
            
            if os.path.exists(script_path):
                try: os.remove(script_path)
                except: pass

            if not success:
                self.finished.emit({'success': False, 'error': LanguageManager.get("msg_pip_install_fail_uac", "Inštalácia zlyhala (UAC zamietnuté alebo proces havaroval).")})
                return
                
            self.progress_log.emit(LanguageManager.get("msg_pip_activated_admin", "PIP, site-packages a virtualenv boli plne aktivované."))
            self.progress_log.emit(LanguageManager.get("msg_pip_repair_complete", "Oprava hotová. Runtime je sebestačný."))
            
            PythonDetector.update_pip_status(self.python_exe_path, "OK")
            self.finished.emit({'success': True})
            return

        try:
            self.progress_log.emit(LanguageManager.get("msg_pip_script_downloaded", "Skript stiahnutý. Začína sa inštalácia PIPu..."))
            pip_command = [self.python_exe_path, script_path]
            subprocess.run(
                pip_command, 
                check=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.progress_log.emit(LanguageManager.get("msg_pip_installed_ok", "PIP bol úspešne nainštalovaný."))

            self.progress_log.emit(LanguageManager.get("msg_pip_activating_site", "Aktivujem prístup k balíčkom (site-packages)..."))
            if not PythonRuntimeInspector.ensure_site_packages_enabled(runtime_path):
                self.progress_log.emit(LanguageManager.get("msg_pip_site_fail_warn", "UPOZORNENIE: Nepodarilo sa automaticky aktivovať site-packages."))
            else:
                self.progress_log.emit(LanguageManager.get("msg_pip_site_activated", "Prístup bol aktivovaný."))

            self.progress_log.emit(LanguageManager.get("msg_pip_installing_venv", "Inštalujem balíček 'virtualenv'..."))
            virtualenv_command = [self.python_exe_path, "-m", "pip", "install", "virtualenv"]
            subprocess.run(
                virtualenv_command,
                check=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.progress_log.emit(LanguageManager.get("msg_pip_venv_installed", "'virtualenv' úspešne nainštalovaný."))
            
            self.progress_log.emit(LanguageManager.get("msg_pip_repair_complete", "Oprava hotová. Runtime je sebestačný."))
            
            PythonDetector.update_pip_status(self.python_exe_path, "OK")
            self.finished.emit({'success': True})

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else LanguageManager.get("err_unknown", "Neznáma chyba.")
            self.finished.emit({'success': False, 'error': LanguageManager.get("msg_pip_install_fail", "Inštalácia zlyhala: {0}").format(error_msg)})
        
        finally:
            if os.path.exists(script_path):
                try: os.remove(script_path)
                except: pass


class PipInstaller(QObject):
    installation_finished = pyqtSignal(dict)

    def __init__(self, log_widget, repair_button):
        super().__init__()
        self.log_widget = log_widget
        self.repair_button = repair_button
        self.thread = None
        self.worker = None

    def install(self, python_exe_path: str):
        if self.thread and self.thread.isRunning():
            self.log_widget.append(LanguageManager.get("msg_pip_repair_in_progress", "! Iná oprava už prebieha."))
            return

        self.repair_button.setEnabled(False)
        self.repair_button.setText(LanguageManager.get("txt_repairing", "⏳ OPRAVUJEM..."))

        self.thread = QThread()
        self.worker = PipInstallWorker(python_exe_path)
        self.worker.moveToThread(self.thread)

        self.worker.progress_log.connect(self.log_widget.append)
        self.worker.finished.connect(self.on_install_finished)
        self.thread.started.connect(self.worker.run)
        
        self.thread.start()

    def on_install_finished(self, result: dict):
        if not result['success']:
            self.log_widget.append(f"CHYBA: {result['error']}")
        
        self.repair_button.setEnabled(True)
        self.repair_button.setText(LanguageManager.get("btn_repair", "✅ Opraviť PIP"))
        
        self.installation_finished.emit(result)
        
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.worker.deleteLater()
            self.thread.deleteLater()
            self.thread = None
            self.worker = None