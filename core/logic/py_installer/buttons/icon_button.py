#----------------------------------------
# Súbor: core/logic/py_installer/buttons/icon_button.py
#----------------------------------------

import os
from PyQt6.QtWidgets import QFileDialog
from core.logic.language_manager import LanguageManager

class IconButtonHandler:
    @staticmethod
    def run(window):
        # Preklad pre titulok a filter
        title = LanguageManager.get("dialog_select_icon", "Vyberte ikonu pre aplikáciu")
        # Filter pre ikony (Windows .ico, Mac .icns)
        file_filter = "Icons (*.ico *.icns);;All Files (*.*)"
        
        # Zistíme aktuálnu cestu projektu, aby sa dialóg otvoril tam
        current_dir = ""
        active_project = window.combo_project.currentText()
        if active_project and window.core.projects_root:
            from core._path import Paths
            current_dir = Paths.get_project_path(window.core.projects_root, active_project)

        # Otvoríme dialóg
        file_path, _ = QFileDialog.getOpenFileName(window, title, current_dir, file_filter)

        # Ak používateľ vybral súbor, vložíme ho do riadku a aktualizujeme náhľad
        if file_path:
            window.edit_icon.setText(os.path.normpath(file_path))
            if hasattr(window, 'update_live_preview'):
                window.update_live_preview()