#----------------------------------------
# Súbor: windows/local_packages_window.py
#----------------------------------------

import os
import json
from PyQt6.QtWidgets import (QDialog, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QWidget, QHBoxLayout)
from PyQt6 import uic
from PyQt6.QtCore import Qt

from core._path import Paths
from core.logic.language_manager import LanguageManager
from windows.custom_title_bar import CustomTitleBar

from core.logic.button.manager.local_packages_linker import LocalPackagesLinker

class LocalPackagesWindow(QDialog):
    def __init__(self, parent, venv_path):
        super().__init__(parent)
        self.core = parent.core
        self.venv_path = venv_path
        
        # Frameless okno
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("LocalPackagesWindow")
        
        # Načítanie UI
        uic.loadUi(Paths.get_ui_file_path("local_packages_window.ui"), self)
        
        # Vloženie Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        self.main_layout.insertWidget(0, self.title_bar)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        
        self.setup_ui()
        self.connect_signals()
        self.retranslate_ui()
        
        self.refresh_list()

    def setup_ui(self):
        """Nastaví správanie a šírku stĺpcov v tabuľke."""
        header = self.table_packages.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Názov balíčka
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Verzia
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Stav
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Stručný popis (roztiahne sa na zvyšok)

    def retranslate_ui(self):
        LanguageManager.translate_ui(self)
        
        # Nastaví názvy stĺpcov manuálne, pretože QT Designer nevie použiť LanguageManager
        self.table_packages.horizontalHeaderItem(0).setText(LanguageManager.get("col_local_pkg_name", "Názov balíčka"))
        self.table_packages.horizontalHeaderItem(1).setText(LanguageManager.get("col_local_pkg_version", "Verzia"))
        self.table_packages.horizontalHeaderItem(2).setText(LanguageManager.get("col_local_pkg_status", "Stav"))
        self.table_packages.horizontalHeaderItem(3).setText(LanguageManager.get("col_local_pkg_description", "Stručný popis"))
        if hasattr(self, 'title_bar'):
            self.title_bar.lbl_title.setText(self.windowTitle())
            
        venv_name = os.path.basename(self.venv_path)
        self.lbl_header.setText(LanguageManager.get("local_pkg_header", "Lokálne balíčky pre: {name}").format(name=venv_name))

    def connect_signals(self):
        self.btn_refresh.clicked.connect(self.refresh_list)
        self.btn_apply.clicked.connect(self.apply_changes)

    def log(self, message):
        self.log_output.append(message)

    def _get_state_file_path(self):
        if os.name == 'nt':
            site_packages_dir = os.path.join(self.venv_path, "Lib", "site-packages")
        else:
            site_packages_dir = os.path.join(self.venv_path, "lib", "site-packages")
            
        os.makedirs(site_packages_dir, exist_ok=True)
        # --- ZMENA: Čítame už nový JSON súbor namiesto .venvhub_linked ---
        return os.path.join(site_packages_dir, "venvhub.json")

    def _get_linked_packages(self):
        state_path = self._get_state_file_path()
        linked_pkgs = set()
        
        if os.path.exists(state_path):
            try:
                # --- ZMENA: Súbor sa teraz parsuje ako JSON a berú sa z neho len kľúče ---
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    linked_pkgs = set(data.keys())
            except Exception as e:
                self.log(LanguageManager.get("local_pkg_err_read", "Chyba pri čítaní stavového súboru: {error}").format(error=e))
                
        return linked_pkgs

    def refresh_list(self):
        self.table_packages.setRowCount(0)
        
        local_root = getattr(self.core, 'local_packages_root', "")
        
        if not local_root or not os.path.exists(local_root):
            self.log(LanguageManager.get("local_pkg_err_no_root", "⚠️ Upozornenie: Cesta k lokálnym balíčkom nie je nastavená alebo neexistuje."))
            return
            
        linked_packages = self._get_linked_packages()
        self.log(LanguageManager.get("local_pkg_log_loading", "\n🔄 Načítavam dostupné lokálne balíčky..."))
        
        loaded_count = 0
        
        for item in os.listdir(local_root):
            pkg_path = os.path.join(local_root, item)
            
            if os.path.isdir(pkg_path):
                meta_path = os.path.join(pkg_path, "local_meta.json")
                
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            
                        folder_name = item
                        display_name = meta.get("name", folder_name)
                        pkg_version = meta.get("version", "1.0.0")
                        pkg_desc = str(meta.get("short_description", ""))
                        
                        is_linked = folder_name in linked_packages
                        
                        self._add_row_to_table(display_name, pkg_version, pkg_path, is_linked, pkg_desc)
                        loaded_count += 1
                        
                    except Exception as e:
                        self.log(LanguageManager.get("local_pkg_err_meta", "⚠️ Chyba pri čítaní {path}: {error}").format(path=meta_path, error=e))

        self.log(LanguageManager.get("local_pkg_log_loaded", "✅ Boli úspešne načítané {count} lokálne balíčky.").format(count=loaded_count))

    def _add_row_to_table(self, display_name, version, full_path, is_linked, description):
        row = self.table_packages.rowCount()
        self.table_packages.insertRow(row)
        
        item_name = QTableWidgetItem(display_name)
        item_name.setFlags(item_name.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item_name.setCheckState(Qt.CheckState.Checked if is_linked else Qt.CheckState.Unchecked)
        item_name.setData(Qt.ItemDataRole.UserRole, os.path.normpath(full_path))
        self.table_packages.setItem(row, 0, item_name)
        
        item_ver = QTableWidgetItem(version)
        item_ver.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_packages.setItem(row, 1, item_ver)
        
        status_text = LanguageManager.get("local_pkg_status_linked", "✅ Prelinkované") if is_linked else "-"
        item_status = QTableWidgetItem(status_text)
        item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_packages.setItem(row, 2, item_status)
        
        item_desc = QTableWidgetItem(description)
        self.table_packages.setItem(row, 3, item_desc)

    def apply_changes(self):
        selected_items_data = []
        for row in range(self.table_packages.rowCount()):
            item_name = self.table_packages.item(row, 0)
            
            if item_name.checkState() == Qt.CheckState.Checked:
                selected_items_data.append({
                    'name': item_name.text(), 
                    'path': item_name.data(Qt.ItemDataRole.UserRole)
                })

        linker = LocalPackagesLinker(self)
        success = linker.apply_changes(selected_items_data)
        
        if success:
            self.refresh_list()