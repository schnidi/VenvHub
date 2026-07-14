#----------------------------------------
# Súbor: core/logic/python_installer/button/python_install.py
#----------------------------------------

import os
import shutil
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt

from core._path import Paths
from core.logic.sluzby.downloader import Downloader
from core.logic.sluzby.unzip import ZipExtractor
from core.logic.sluzby.win_admin import WinAdmin
from core.logic.python_detector import PythonDetector
from core.logic.language_manager import LanguageManager 

class PythonInstallWorker(QObject):
    progress_log = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(dict) 

    def __init__(self, source_info: dict):
        super().__init__()
        self.source_info = source_info
        self.is_cancelled = False

    def run(self):
        source_path = self.source_info['path']
        downloaded_zip_path = None
        temp_dir = Paths.get_python_downloads_dir()
        base_install_dir = Paths.get_python_runtimes_install_dir()

        # === KONTROLA EŠTE PRED SŤAHOVANÍM ===
        filename = os.path.basename(source_path)
        folder_name = os.path.splitext(filename)[0]
        final_destination_dir = os.path.join(base_install_dir, folder_name)
        install_marker_path = os.path.join(final_destination_dir, "install.ini")

        # Ak zložka existuje a má marker, ukončíme bez sťahovania
        if os.path.exists(final_destination_dir) and os.path.exists(install_marker_path):
            self.finished.emit({'success': False, 'error': LanguageManager.get("msg_py_already_installed", "Táto verzia Pythonu je už nainštalovaná: {0}").format(folder_name)})
            return

        # Sťahovanie alebo použitie lokálneho súboru
        if self.source_info['type'] == 'url':
            self.progress_log.emit(LanguageManager.get("msg_downloading_from", "Sťahujem súbor z: {0}").format(source_path))
            downloaded_zip_path = os.path.join(temp_dir, filename)

            def download_progress(downloaded, total):
                if self.is_cancelled: raise Exception("Download cancelled")
                percent = int((downloaded / total) * 100) if total > 0 else 0
                self.progress_percent.emit(percent)

            result = Downloader.download_file(source_path, downloaded_zip_path, download_progress)
            if not result['success']:
                self.finished.emit({'success': False, 'error': LanguageManager.get("msg_download_err", "Chyba pri sťahovaní: {0}").format(result['error'])})
                return
            
            self.progress_log.emit(LanguageManager.get("msg_download_success", "Súbor bol úspešne stiahnutý."))
            source_zip_to_extract = downloaded_zip_path
        else:
            source_zip_to_extract = source_path
        
        if self.is_cancelled: return

        # Hodnoty už máme definované vyššie, ale pre istotu si ich znovu zadefinujeme z konkrétneho ZIP súboru
        zip_filename = os.path.basename(source_zip_to_extract)
        folder_name = os.path.splitext(zip_filename)[0]
        final_destination_dir = os.path.join(base_install_dir, folder_name)
        install_marker_path = os.path.join(final_destination_dir, "install.ini")

        temp_extract_dir = os.path.join(temp_dir, f"temp_{folder_name}")
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir, ignore_errors=True)

        self.progress_log.emit(LanguageManager.get("msg_extracting", "Rozbaľujem archív..."))
        self.progress_percent.emit(0)
        
        def unzip_progress(current, total, unzip_filename):
            if self.is_cancelled: raise Exception("Unzip cancelled")
            percent = int((current / total) * 100) if total > 0 else 0
            self.progress_percent.emit(percent)

        result = ZipExtractor.extract(source_zip_to_extract, temp_extract_dir, unzip_progress)
        if not result['success']:
            self.finished.emit({'success': False, 'error': LanguageManager.get("msg_unzip_err", "Chyba pri rozbaľovaní: {0}").format(result['error'])})
            return

        try:
            with open(os.path.join(temp_extract_dir, "install.ini"), "w", encoding="utf-8") as f:
                f.write("[Status]\nstatus=success\n")
        except Exception as e:
            self.progress_log.emit(LanguageManager.get("msg_install_ini_err", "Upozornenie: Nepodarilo sa vytvoriť install.ini: {0}").format(e))

        needs_admin = WinAdmin.needs_admin_for_path(final_destination_dir)

        if needs_admin:
            self.progress_log.emit(LanguageManager.get("msg_uac_needed", "Vyžadujú sa práva Administrátora. Prosím, potvrďte systémové UAC okno..."))
            
            def on_state_changed(state_str):
                if state_str == "[STATUS] UAC_APPROVED":
                    self.progress_log.emit(LanguageManager.get("msg_uac_approved", "✅ UAC schválené. Spúšťam proces s administrátorskými právami..."))
                elif state_str == "[STATUS] PREPARING":
                    self.progress_log.emit(LanguageManager.get("msg_uac_preparing", "Pripravujem cieľový priečinok..."))
                elif state_str == "[STATUS] COPYING":
                    self.progress_log.emit(LanguageManager.get("msg_uac_copying", "Kopírujem súbory na systémový disk (môže to chvíľu trvať)..."))
                elif state_str == "[STATUS] CLEANING":
                    self.progress_log.emit(LanguageManager.get("msg_uac_cleaning", "Mažem dočasné inštalačné súbory..."))
                elif state_str == "[STATUS] ERROR_COPY":
                    self.progress_log.emit(LanguageManager.get("msg_uac_error_copy", "❌ Nastala chyba pri kopírovaní!"))
                elif state_str == "[STATUS] DONE":
                    self.progress_log.emit(LanguageManager.get("msg_uac_done", "✅ Operácia na systémovom disku dokončená."))
                
            success = WinAdmin.move_directory_with_uac(temp_extract_dir, final_destination_dir, state_callback=on_state_changed)
            
            if not success:
                self.finished.emit({'success': False, 'error': LanguageManager.get("msg_install_cancelled", "Inštalácia bola zrušená alebo zlyhala (súbory neboli prekopírované).")})
                return
        else:
            try:
                self.progress_log.emit(LanguageManager.get("msg_preparing_write", "Kopírujem súbory do cieľovej lokácie..."))
                os.makedirs(base_install_dir, exist_ok=True)
                if os.path.exists(final_destination_dir):
                    shutil.rmtree(final_destination_dir, ignore_errors=True)
                shutil.move(temp_extract_dir, final_destination_dir)
            except Exception as e:
                self.finished.emit({'success': False, 'error': LanguageManager.get("msg_move_dir_err", "Chyba pri presune zložky: {0}").format(e)})
                return

        if downloaded_zip_path and os.path.exists(downloaded_zip_path):
            try:
                os.remove(downloaded_zip_path)
            except Exception:
                pass

        final_python_exe = os.path.join(final_destination_dir, 'python.exe')
        if not os.path.exists(final_python_exe):
            for item in os.listdir(final_destination_dir):
                sub = os.path.join(final_destination_dir, item)
                if os.path.isdir(sub) and os.path.exists(os.path.join(sub, 'python.exe')):
                    final_python_exe = os.path.join(sub, 'python.exe')
                    break
        
        PythonDetector.add_local_python(folder_name, final_python_exe, pip_status="checking")
        
        self.progress_log.emit(LanguageManager.get("msg_install_success", "Inštalácia bola úspešne dokončená!"))
        self.progress_percent.emit(100)
        self.finished.emit({'success': True, 'path': final_python_exe})

    def cancel(self):
        self.is_cancelled = True


class PythonInstaller(QObject):
    installation_finished = pyqtSignal(dict)

    def __init__(self, log_widget, progress_bar, install_button):
        super().__init__()
        self.log_widget = log_widget
        self.progress_bar = progress_bar
        self.install_button = install_button
        self.install_thread = None
        self.worker = None

    def _handle_log(self, msg):
        self.log_widget.append(msg)

    def _handle_progress(self, val):
        self.progress_bar.setValue(val)

    def _handle_finished(self, result):
        self.on_installation_finished(result)

    def install(self, source_info: dict):
        if self.install_thread and self.install_thread.isRunning():
            self.log_widget.append(LanguageManager.get("msg_install_in_progress", "! Inštalácia už prebieha."))
            return

        self.install_button.setEnabled(False)
        self.install_button.setText(LanguageManager.get("btn_installing", "⏳ INŠTALUJEM..."))

        self.install_thread = QThread()
        self.worker = PythonInstallWorker(source_info)
        self.worker.moveToThread(self.install_thread)

        self.worker.progress_log.connect(self._handle_log, Qt.ConnectionType.QueuedConnection)
        self.worker.progress_percent.connect(self._handle_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._handle_finished, Qt.ConnectionType.QueuedConnection)

        self.install_thread.started.connect(self.worker.run)
        self.install_thread.start()

    def on_installation_finished(self, result: dict):
        if not result['success']:
            self.log_widget.append(f"CHYBA: {result['error']}")
        
        self.install_button.setEnabled(True)
        self.install_button.setText(LanguageManager.get("btn_install", "🛠 INŠTALOVAŤ"))
        
        self.installation_finished.emit(result)
        
        # --- ZMENA: Bezpečné ukončenie vlákna bez príkazu 'wait()', ktoré mrzlo okno ---
        if self.install_thread:
            self.install_thread.quit()
            self.worker.deleteLater()
            self.install_thread.deleteLater()
            self.install_thread = None
            self.worker = None