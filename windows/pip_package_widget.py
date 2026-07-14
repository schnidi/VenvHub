#----------------------------------------
# Súbor: windows/pip_package_widget.py
#----------------------------------------

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6 import uic
from PyQt6.QtCore import QThread
from core._path import Paths
from core.logic.language_manager import LanguageManager
from core.logic.button.pip.pip_command_worker import PipCommandWorker
from core.logic.commands.command_factory import PackageManagerFactory # NOVÉ

class PipPackageWidget(QWidget):
    def __init__(self, parent_window, venv_path):
        super().__init__()
        self.parent_window = parent_window
        self.venv_path = venv_path
        self.package_data = None
        
        self.thread = None
        self.worker = None
        
        uic.loadUi(Paths.get_ui_file_path("pip_package_actions_widget.ui"), self)
        
        self.connect_signals()
        self.clear_data()

    def connect_signals(self):
        self.btn_update.clicked.connect(self.on_update)
        self.btn_uninstall.clicked.connect(self.on_uninstall)
        self.btn_install_specific.clicked.connect(self.on_install_specific)

    def retranslate_ui(self):
        LanguageManager.translate_ui(self)
        if self.package_data:
            self.set_package_data(self.package_data)
        else:
            self.clear_data()

    def clear_data(self):
        self.package_data = None
        msg_select = LanguageManager.get("group_package_actions_default", "Vyberte balíček v tabuľke")
        self.group_actions.setTitle(msg_select)
        
        fmt_inst = LanguageManager.get("lbl_installed_fmt", "Nainštalovaná verzia: {0}")
        self.lbl_installed_version.setText(fmt_inst.format("-"))
        
        fmt_lat = LanguageManager.get("lbl_latest_fmt", "Najnovšia verzia: {0}")
        self.lbl_latest_version.setText(fmt_lat.format("-"))
        
        fmt_update = LanguageManager.get("btn_update_fmt", "⬆️ Aktualizovať na {0}")
        word_latest = LanguageManager.get("word_latest", "najnovšiu") 
        self.btn_update.setText(fmt_update.format(word_latest))
        
        self.edit_specific_version.clear()
        self.set_buttons_enabled(False)

    def set_package_data(self, package_data):
        self.package_data = package_data
        if not self.package_data:
            self.clear_data()
            return
            
        pkg_name = self.package_data['name']
        current_ver = self.package_data['version']
        latest_ver = self.package_data['latest']

        fmt_title = LanguageManager.get("group_actions_fmt", "Akcie pre: {0}")
        self.group_actions.setTitle(fmt_title.format(pkg_name))
        
        fmt_inst = LanguageManager.get("lbl_installed_fmt", "Nainštalovaná verzia: {0}")
        self.lbl_installed_version.setText(fmt_inst.format(current_ver))
        
        fmt_lat = LanguageManager.get("lbl_latest_fmt", "Najnovšia verzia: {0}")
        self.lbl_latest_version.setText(fmt_lat.format(latest_ver))
        
        self.set_buttons_enabled(True)
        
        if current_ver == latest_ver:
            self.btn_update.setEnabled(False)
            txt_uptodate = LanguageManager.get("btn_update_uptodate", "✅ Verzia je aktuálna")
            self.btn_update.setText(txt_uptodate)
        else:
            self.btn_update.setEnabled(True)
            fmt_update = LanguageManager.get("btn_update_fmt", "⬆️ Aktualizovať na {0}")
            self.btn_update.setText(fmt_update.format(latest_ver))

    def set_buttons_enabled(self, enabled):
        if enabled and not self.package_data: return
        self.btn_update.setEnabled(enabled)
        self.btn_uninstall.setEnabled(enabled)
        self.btn_install_specific.setEnabled(enabled)
        self.edit_specific_version.setEnabled(enabled)
        
        if enabled and self.package_data:
            if self.package_data['version'] == self.package_data['latest']:
                self.btn_update.setEnabled(False)

    def log(self, message):
        if hasattr(self.parent_window, "log_output"):
            self.parent_window.log_output.append(message)

    # --- ZMENA: command je teraz už hotové pole [uv, pip, install...] ---
    def run_pip_command(self, full_command, start_message):
        self.log(start_message)
        self.set_buttons_enabled(False)

        self.thread = QThread()
        self.worker = PipCommandWorker(self.venv_path, full_command)
        self.worker.moveToThread(self.thread)

        self.worker.output_line.connect(self.log) 
        self.worker.finished.connect(self.on_command_finished)
        self.worker.error.connect(self.on_command_error)
        self.thread.started.connect(self.worker.run)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_command_finished(self, exit_code):
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(5000)
        
        if exit_code == 0:
            msg_success = LanguageManager.get("msg_op_success", "--- Operácia úspešne dokončená ---")
            self.log(msg_success)
            self.parent_window.refresh_list() 
        else:
            msg_fail = LanguageManager.get("msg_op_failed_code", "--- Operácia zlyhala s kódom {0} ---").format(exit_code)
            self.log(msg_fail)
            title_err = LanguageManager.get("title_error", "Chyba")
            msg_err = LanguageManager.get("msg_check_log", "Operácia zlyhala. Skontrolujte log pre viac detailov.")
            QMessageBox.warning(self, title_err, msg_err)
        
        self.set_buttons_enabled(True)

    def on_command_error(self, error_message):
        self.log(f"CHYBA: {error_message}")
        title_crit = LanguageManager.get("title_critical_error", "Kritická chyba")
        QMessageBox.critical(self, title_crit, error_message)
        self.set_buttons_enabled(True)

    def _get_manager_type(self):
        """Pomocná metóda pre získanie aktuálneho manažéra z hlavného jadra."""
        return self.parent_window.parent().core.package_manager

    def on_update(self):
        if not self.package_data: return
        pkg_name = self.package_data['name']
        
        dispatcher = PackageManagerFactory.get_dispatcher(self._get_manager_type(), self.venv_path)
        full_cmd = dispatcher.get("upgrade", package_name=pkg_name)
        
        msg = LanguageManager.get("msg_starting_update", "\n--- Spúšťam update pre {0} ---").format(pkg_name)
        self.run_pip_command(full_cmd, msg)

    def on_uninstall(self):
        if not self.package_data: return
        pkg_name = self.package_data['name']
        title = LanguageManager.get("title_confirm", "Potvrdenie")
        msg = LanguageManager.get("msg_confirm_uninstall", "Naozaj chcete odinštalovať balíček '{0}'?").format(pkg_name)
        
        confirm = QMessageBox.question(self, title, msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            dispatcher = PackageManagerFactory.get_dispatcher(self._get_manager_type(), self.venv_path)
            full_cmd = dispatcher.get("uninstall", package_name=pkg_name)
            
            msg_start = LanguageManager.get("msg_starting_uninstall", "\n--- Spúšťam odinštaláciu {0} ---").format(pkg_name)
            self.run_pip_command(full_cmd, msg_start)

    def on_install_specific(self):
        if not self.package_data: return
        pkg_name = self.package_data['name']
        version = self.edit_specific_version.text().strip()
        
        if not version:
            title = LanguageManager.get("title_error", "Chyba")
            msg = LanguageManager.get("msg_enter_version", "Zadajte verziu (napr. 1.2.3)")
            QMessageBox.warning(self, title, msg)
            return
            
        dispatcher = PackageManagerFactory.get_dispatcher(self._get_manager_type(), self.venv_path)
        full_cmd = dispatcher.get("install_specific", package_name=pkg_name, version=version)
        
        package_spec = f"{pkg_name}=={version}"
        msg_start = LanguageManager.get("msg_installing_spec", "\n--- Inštalujem {0} ---").format(package_spec)
        self.run_pip_command(full_cmd, msg_start)
        self.edit_specific_version.clear()