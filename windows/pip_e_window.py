#----------------------------------------
# Súbor: windows/pip_e_window.py
#----------------------------------------

import os
from PyQt6.QtWidgets import (QDialog, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QFileDialog)
from PyQt6 import uic
from PyQt6.QtCore import Qt, QThread, pyqtSlot

from core._path import Paths
from core.logic.language_manager import LanguageManager
from windows.custom_title_bar import CustomTitleBar

# Import asynchrónnych workerov
from core.logic.pip_e import PipEListWorker, PipEInstallWorker, PipEUninstallWorker

class PipEWindow(QDialog):
    def __init__(self, parent, venv_path):
        super().__init__(parent)
        self.core = parent.core
        self.venv_path = venv_path
        
        self.active_thread = None
        self.active_worker = None
        
        # 1. Zrušenie štandardných okrajov Windows (Frameless)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("PipEWindow")
        
        # 2. Načítanie UI zo šablóny
        uic.loadUi(Paths.get_ui_file_path("pip_e_window.ui"), self)
        
        # 3. Vloženie našej custom lišty
        self.title_bar = CustomTitleBar(self)
        self.main_layout.insertWidget(0, self.title_bar)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        
        # 4. Inicializácia zobrazenia a eventov
        self.setup_ui()
        self.connect_signals()
        self.retranslate_ui()
        
        # 5. Okamžité načítanie balíčkov pri štarte okna
        self.refresh_list()

    def setup_ui(self):
        """Prispôsobenie šírok stĺpcov v tabuľke."""
        header = self.table_packages.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Názov balíčka
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Verzia
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Lokálna cesta (roztiahne sa)

    def retranslate_ui(self):
        """Aplikácia prekladov pre rôzne jazyky."""
        LanguageManager.translate_ui(self)
        
        self.table_packages.horizontalHeaderItem(0).setText(LanguageManager.get("col_pipe_name", "Názov balíčka"))
        self.table_packages.horizontalHeaderItem(1).setText(LanguageManager.get("col_pipe_version", "Verzia"))
        self.table_packages.horizontalHeaderItem(2).setText(LanguageManager.get("col_pipe_path", "Lokálna cesta"))
        
        if hasattr(self, 'title_bar'):
            self.title_bar.lbl_title.setText(LanguageManager.get("title_pip_e_manager", "Editovateľné balíčky (pip -e)"))
            
        venv_name = os.path.basename(self.venv_path)
        self.lbl_header.setText(LanguageManager.get("pip_e_header", "Inštalované cez pip -e pre: {name}").format(name=venv_name))

    def connect_signals(self):
        self.btn_refresh.clicked.connect(self.refresh_list)
        self.btn_add_package.clicked.connect(self.add_new_package)
        self.btn_remove_package.clicked.connect(self.remove_selected_package)

    @pyqtSlot(str)
    def log(self, message):
        """Zobrazí text v okne logu a posunie zobrazenie nadol."""
        self.log_output.append(message)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _set_ui_locked(self, locked: bool):
        """Zablokuje alebo odblokuje tlačidlá počas práce Workera na pozadí."""
        self.btn_refresh.setEnabled(not locked)
        self.btn_add_package.setEnabled(not locked)
        self.btn_remove_package.setEnabled(not locked)
        self.table_packages.setEnabled(not locked)

    def _cleanup_thread(self):
        """Bezpečné zmazanie vlákna z pamäte po jeho dokončení."""
        if self.active_thread:
            if self.active_thread.isRunning():
                self.active_thread.quit()
                self.active_thread.wait()
            self.active_thread.deleteLater()
            self.active_thread = None
        
        if self.active_worker:
            self.active_worker.deleteLater()
            self.active_worker = None

    # =========================================================================
    # --- AKCIA 1: NAČÍTANIE ZOZNAMU (Čisté, bez zápisu do VS Code) ---
    # =========================================================================
    def refresh_list(self):
        self._cleanup_thread()
        self._set_ui_locked(True)
        self.table_packages.setRowCount(0)

        self.active_thread = QThread()
        self.active_worker = PipEListWorker(self.venv_path)
        self.active_worker.moveToThread(self.active_thread)

        self.active_thread.started.connect(self.active_worker.run)
        self.active_worker.log_msg.connect(self.log)
        self.active_worker.error.connect(self._handle_error)
        
        # Po úspešnom dokončení spracujeme zoznam
        self.active_worker.finished.connect(self._on_list_loaded)
        
        # Upratovanie
        self.active_worker.finished.connect(self._cleanup_thread)
        self.active_thread.start()

    @pyqtSlot(list)
    def _on_list_loaded(self, packages):
        """Vloží načítané balíčky do tabuľky."""
        self.table_packages.setRowCount(0)
        
        for pkg in packages:
            row = self.table_packages.rowCount()
            self.table_packages.insertRow(row)
            
            name = pkg.get("name", "Neznámy")
            version = pkg.get("version", "")
            local_path = pkg.get("editable_project_location", "")
            
            item_name = QTableWidgetItem(name)
            item_ver = QTableWidgetItem(version)
            item_ver.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_path = QTableWidgetItem(local_path)
            
            self.table_packages.setItem(row, 0, item_name)
            self.table_packages.setItem(row, 1, item_ver)
            self.table_packages.setItem(row, 2, item_path)
            
        self._set_ui_locked(False)

    # =========================================================================
    # --- AKCIA 2: INŠTALÁCIA BALÍČKA (-e) ---
    # =========================================================================
    def add_new_package(self):
        """Otvorí dialóg a odošle cestu inštalačnému Workerovi."""
        initial_dir = getattr(self.core, 'pip_e_packages_root', os.path.expanduser("~"))
        if not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")
            
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            LanguageManager.get("title_select_pkg_dir", "Vybrať priečinok s balíčkom (setup.py / pyproject.toml)"),
            initial_dir
        )
        
        if not dir_path:
            return

        self._cleanup_thread()
        self._set_ui_locked(True)

        self.active_thread = QThread()
        self.active_worker = PipEInstallWorker(self.venv_path, dir_path)
        self.active_worker.moveToThread(self.active_thread)

        self.active_thread.started.connect(self.active_worker.run)
        self.active_worker.log_msg.connect(self.log)
        self.active_worker.error.connect(self._handle_error)
        
        self.active_worker.finished.connect(self._on_action_finished)
        self.active_worker.finished.connect(self._cleanup_thread)
        self.active_thread.start()

    # =========================================================================
    # --- AKCIA 3: ODINŠTALÁCIA BALÍČKA ---
    # =========================================================================
    def remove_selected_package(self):
        """Zistí, ktorý riadok je označený a pošle ho do Odinštalačného Workera."""
        selected_row = self.table_packages.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, LanguageManager.get("title_warning", "Upozornenie"), LanguageManager.get("pip_e_select_to_remove", "Najprv kliknite na balíček v tabuľke, ktorý chcete odinštalovať."))
            return
            
        pkg_name = self.table_packages.item(selected_row, 0).text()
        
        confirm = QMessageBox.question(
            self,
            LanguageManager.get("title_confirm", "Potvrdenie"),
            LanguageManager.get("pip_e_uninstall_confirm", "Naozaj chcete odinštalovať editovateľný balíček '{0}' z tohto venv?").format(pkg_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.No:
            return

        self._cleanup_thread()
        self._set_ui_locked(True)

        self.active_thread = QThread()
        self.active_worker = PipEUninstallWorker(self.venv_path, pkg_name)
        self.active_worker.moveToThread(self.active_thread)

        self.active_thread.started.connect(self.active_worker.run)
        self.active_worker.log_msg.connect(self.log)
        self.active_worker.error.connect(self._handle_error)
        
        self.active_worker.finished.connect(self._on_action_finished)
        self.active_worker.finished.connect(self._cleanup_thread)
        self.active_thread.start()

    # =========================================================================
    # --- OŠETRENIE CHÝB A DOKONČENIE ---
    # =========================================================================
    @pyqtSlot(str)
    def _handle_error(self, err_msg):
        """Prijíma chyby z akéhokoľvek Workera a zobrazí ich v dialógu."""
        self.log(err_msg)
        QMessageBox.critical(self, LanguageManager.get("title_error", "Chyba"), err_msg)

    @pyqtSlot(bool)
    def _on_action_finished(self, success):
        """Vyvolané po inštalácii alebo odinštalácii. V prípade úspechu aktualizuje zoznam."""
        if not success:
            self._set_ui_locked(False)
            return
            
        self.refresh_list()