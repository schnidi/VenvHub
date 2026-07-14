#----------------------------------------
# Súbor: windows/builder_window.py
#----------------------------------------

import os
import json
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QHeaderView
from PyQt6 import uic
from PyQt6.QtCore import Qt

from core._path import Paths
from core.logic.language_manager import LanguageManager
from core.logic.py_installer.logic.script_finder import ScriptFinder
from core.logic.commands.pyinstaller_commands import PyInstallerCommandDispatcher

from core.logic.py_installer.buttons.browse import BrowseOutputHandler
from core.logic.py_installer.buttons.refresh import TargetRefreshHandler
from core.logic.py_installer.buttons.cancel_button import CancelButtonHandler
from core.logic.py_installer.buttons.agree_exe_button import AgreeExeButtonHandler
from core.logic.py_installer.buttons.icon_button import IconButtonHandler
from core.logic.py_installer.buttons.assets_buttons import AssetsButtonsHandler
from core.logic.py_installer.buttons.imports_buttons import ImportsButtonsHandler

try:
    from core.logic.box.uv_exe_install import UVExeInstaller
    UV_INSTALLER_AVAILABLE = True
except ImportError:
    UV_INSTALLER_AVAILABLE = False
try:
    from core.logic.box.metadata_exe import MetadataHandler
    METADATA_HANDLER_AVAILABLE = True
except ImportError:
    METADATA_HANDLER_AVAILABLE = False


class BuilderWindow(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        uic.loadUi(Paths.get_ui_file_path("builder_window.ui"), self)
        
        self.text_preview_cmd.setReadOnly(True)
        
        header = self.table_data.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        
        self.init_connections()
        self.populate_projects()
        
        self.retranslate_ui()
        
        self.toggle_metadata_path_widgets(self.chk_add_birth_cert.isChecked())
        self.update_live_preview()

    def retranslate_ui(self):
        LanguageManager.translate_ui(self)
        if hasattr(self, 'lbl_birth_cert_path'):
            self.lbl_birth_cert_path.setText(LanguageManager.get("lbl_birth_cert_path", "Uložiť 'rodný list' do:"))
            self.edit_birth_cert_path.setPlaceholderText(LanguageManager.get("ph_birth_cert_path", "Relatívna cesta v projekte"))
        if hasattr(self, 'chk_pack_uv'):
            self.chk_pack_uv.setText(LanguageManager.get("chk_pack_uv", "Pribaliť k aplikácii inštalátor UV (uv.exe)"))
        if hasattr(self, 'tab_builder'):
            self.tab_builder.setTabText(0, LanguageManager.get("tab_builder_basic", "1. Základné (Basic)"))
            self.tab_builder.setTabText(1, LanguageManager.get("tab_builder_assets", "2. Súbory a Dáta (Assets)"))
            self.tab_builder.setTabText(2, LanguageManager.get("tab_builder_imports", "3. Importy (Imports)"))
            self.tab_builder.setTabText(3, LanguageManager.get("tab_builder_advanced", "4. Pokročilé (Advanced)"))
            
    def init_connections(self):
        self.btn_browse_output.clicked.connect(lambda: BrowseOutputHandler.run(self))
        self.btn_refresh_projects.clicked.connect(lambda: TargetRefreshHandler.refresh_projects(self))
        self.btn_refresh_scripts.clicked.connect(lambda: TargetRefreshHandler.refresh_scripts(self))
        self.btn_cancel.clicked.connect(lambda: CancelButtonHandler.run(self))
        self.btn_build.clicked.connect(lambda: AgreeExeButtonHandler.run(self))
        self.btn_browse_icon.clicked.connect(lambda: IconButtonHandler.run(self))
        self.btn_add_data_file.clicked.connect(lambda: AssetsButtonsHandler.add_file(self))
        self.btn_add_data_dir.clicked.connect(lambda: AssetsButtonsHandler.add_dir(self))
        self.btn_remove_data.clicked.connect(lambda: AssetsButtonsHandler.remove_selected(self))
        self.btn_add_hidden.clicked.connect(lambda: ImportsButtonsHandler.add_hidden(self))
        self.btn_rem_hidden.clicked.connect(lambda: ImportsButtonsHandler.remove_hidden(self))
        self.btn_add_exclude.clicked.connect(lambda: ImportsButtonsHandler.add_exclude(self))
        self.btn_rem_exclude.clicked.connect(lambda: ImportsButtonsHandler.remove_exclude(self))

        if METADATA_HANDLER_AVAILABLE:
            self.chk_add_birth_cert.toggled.connect(self.toggle_metadata_path_widgets)
            self.btn_browse_birth_cert_path.clicked.connect(lambda: MetadataHandler.browse_path(self))

        controls_to_connect = [
            self.combo_venv, self.combo_script, self.edit_output_path, self.edit_app_name,
            self.edit_icon, self.rb_onedir, self.rb_onefile, self.rb_console,
            self.rb_windowed, self.chk_clean, self.chk_admin, self.combo_log_level,
            self.edit_custom_args, self.chk_add_birth_cert
        ]
        if hasattr(self, 'chk_pack_uv'): controls_to_connect.append(self.chk_pack_uv)
        if hasattr(self, 'edit_birth_cert_path'): controls_to_connect.append(self.edit_birth_cert_path)

        for control in controls_to_connect:
            if hasattr(control, 'toggled'): control.toggled.connect(self.update_live_preview)
            elif hasattr(control, 'textChanged'): control.textChanged.connect(self.update_live_preview)
            elif hasattr(control, 'currentIndexChanged'): control.currentIndexChanged.connect(self.update_live_preview)

        self.combo_project.currentTextChanged.connect(self.on_project_changed)
        self.table_data.itemChanged.connect(self.update_live_preview)
        self.list_hidden_imports.model().rowsInserted.connect(self.update_live_preview)
        self.list_hidden_imports.model().rowsRemoved.connect(self.update_live_preview)
        self.list_exclude_modules.model().rowsInserted.connect(self.update_live_preview)
        self.list_exclude_modules.model().rowsRemoved.connect(self.update_live_preview)
        
    def toggle_metadata_path_widgets(self, checked):
        if hasattr(self, 'lbl_birth_cert_path'):
            self.lbl_birth_cert_path.setEnabled(checked)
            self.edit_birth_cert_path.setEnabled(checked)
            self.btn_browse_birth_cert_path.setEnabled(checked)
    
    def get_current_command_list(self) -> list[str]:
        venv_path = self.combo_venv.currentData()
        if not venv_path: return []
        
        project_name = self.combo_project.currentText()
        project_path = Paths.get_project_path(self.core.projects_root, project_name)

        birth_cert_path = ""
        if self.chk_add_birth_cert.isChecked() and hasattr(self, 'edit_birth_cert_path'):
            birth_cert_path = self.edit_birth_cert_path.text().strip()

        add_data_list = []
        for row in range(self.table_data.rowCount()):
            if self.table_data.item(row, 0) and self.table_data.item(row, 1):
                add_data_list.append((self.table_data.item(row, 0).text(), self.table_data.item(row, 1).text()))
        
        hidden_imports = [self.list_hidden_imports.item(i).text() for i in range(self.list_hidden_imports.count())]
        exclude_modules = [self.list_exclude_modules.item(i).text() for i in range(self.list_exclude_modules.count())]

        cmd_list = PyInstallerCommandDispatcher.get_build_command(
            project_path=project_path,
            venv_path=venv_path,
            script_path=self.combo_script.currentText(),
            output_dir=self.edit_output_path.text(),
            app_name=self.edit_app_name.text(),
            icon_path=self.edit_icon.text(),
            is_windowed=self.rb_windowed.isChecked(),
            is_onefile=self.rb_onefile.isChecked(),
            add_data_list=add_data_list,
            hidden_imports=hidden_imports,
            exclude_modules=exclude_modules,
            clean_build=self.chk_clean.isChecked(),
            uac_admin=self.chk_admin.isChecked(),
            log_level=self.combo_log_level.currentText(),
            custom_args=self.edit_custom_args.text(),
            birth_cert_relative_path=birth_cert_path
        )
        
        if not cmd_list:
            return []

        # Odstránime na chvíľu hlavný skript, aby sme mohli pridávať argumenty
        main_script = cmd_list.pop()

        # ==============================================================================
        # --- VENVHUB AUTO-INJEKTOR LOKÁLNYCH BALÍČKOV ---
        # ==============================================================================
        site_folder = "Lib" if os.name == 'nt' else "lib"
        json_file = os.path.join(venv_path, site_folder, "site-packages", "venvhub.json")
        
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    local_pkgs = json.load(f)
                
                sep = os.pathsep # ';' pre Windows, ':' pre Linux
                
                for pkg_name, pkg_path in local_pkgs.items():
                    if os.path.exists(pkg_path):
                        # 1. Pridáme --paths (PyInstaller vďaka tomuto nájde .py kód)
                        parent_dir = os.path.dirname(os.path.normpath(pkg_path))
                        cmd_list.extend(["--paths", parent_dir])
                        
                        # 2. Pridáme --add-data (Vďaka tomuto sa pribalia obrázky, UI, JSON, a všetky Assets z balíčka)
                        cmd_list.extend(["--add-data", f"{os.path.normpath(pkg_path)}{sep}{pkg_name}"])
            except Exception as e:
                print(f"[VenvHub Auto-Injektor] Chyba pri vkladaní lokálnych balíčkov: {e}")
        # ==============================================================================

        # UV EXE Pribalenie (Zostáva zachované)
        if UV_INSTALLER_AVAILABLE and hasattr(self, 'chk_pack_uv') and self.chk_pack_uv.isChecked():
            predicted_path = UVExeInstaller.get_uv_path_in_venv(venv_path)
            sep = os.pathsep
            cmd_list.extend(["--add-binary", f"{predicted_path}{sep}."])

        # Vrátime skript na koniec príkazu, kam patrí
        cmd_list.append(main_script)

        return cmd_list

    def update_live_preview(self, *args, **kwargs):
        cmd_list = self.get_current_command_list()
        html_preview = PyInstallerCommandDispatcher.get_preview_string(cmd_list)
        self.text_preview_cmd.setHtml(html_preview)

    def get_final_parsed_command(self) -> list[str]:
        return self.get_current_command_list()

    def populate_projects(self):
        self.combo_project.blockSignals(True)
        self.combo_project.clear()
        projects = self.core.get_projects()
        self.combo_project.addItems(projects)
        if self.core.active_project in projects:
            self.combo_project.setCurrentText(self.core.active_project)
        elif projects:
            self.combo_project.setCurrentText(projects[0])
        self.combo_project.blockSignals(False)
        self.on_project_changed(self.combo_project.currentText())

    def on_project_changed(self, project_name):
        if not project_name:
            self.combo_venv.clear()
            self.combo_script.clear()
            self.edit_output_path.clear()
            self.update_live_preview()
            return
        self.populate_venvs(project_name)
        self.populate_scripts(project_name)
        project_path = Paths.get_project_path(self.core.projects_root, project_name)
        default_dist = os.path.join(project_path, "dist")
        self.edit_output_path.setText(os.path.normpath(default_dist))
        self.update_live_preview()

    def populate_venvs(self, project_name):
        self.combo_venv.blockSignals(True)
        self.combo_venv.clear()
        venvs = self.core.get_venvs_for_project(project_name)
        for venv in venvs:
            display_text = f"{venv['name']} (Python {venv['version']})"
            self.combo_venv.addItem(display_text, venv['path'])
        current_path_index = self.combo_venv.findData(self.core.get_project_default_venv())
        if current_path_index != -1:
            self.combo_venv.setCurrentIndex(current_path_index)
        elif venvs:
            self.combo_venv.setCurrentIndex(0)
        self.combo_venv.blockSignals(False)

    def populate_scripts(self, project_name):
        self.combo_script.blockSignals(True)
        self.combo_script.clear()
        project_path = Paths.get_project_path(self.core.projects_root, project_name)
        if os.path.exists(project_path):
            scripts = ScriptFinder.get_python_scripts(project_path)
            self.combo_script.addItems(scripts)
            last_script = self.core.last_script if project_name == self.core.active_project else "main.py"
            if last_script in scripts:
                self.combo_script.setCurrentText(last_script)
            elif "main.py" in scripts:
                self.combo_script.setCurrentText("main.py")
            elif scripts:
                self.combo_script.setCurrentIndex(0)
        self.combo_script.blockSignals(False)