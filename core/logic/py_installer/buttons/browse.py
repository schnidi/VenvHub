#----------------------------------------
# Súbor: core/logic/py_installer/buttons/browse.py
#----------------------------------------

import os
from PyQt6.QtWidgets import QFileDialog
from core._path import Paths
from core.logic.language_manager import LanguageManager

class BrowseOutputHandler:
    @staticmethod
    def run(window):
        """
        Otvorí dialóg na výber výstupného priečinka (--distpath)
        a zapíše ho do QLineEdit (edit_output_path).
        """
        # Zistíme, aká cesta je momentálne v texte
        current_path = window.edit_output_path.text().strip()
        
        # Ak tam nič nie je, alebo cesta neexistuje, predvolíme koreň aktuálneho projektu
        if not current_path or not os.path.exists(current_path):
            active_project = window.combo_project.currentText()
            if active_project and window.core.projects_root:
                current_path = Paths.get_project_path(window.core.projects_root, active_project)
            else:
                current_path = ""

        # Preklad titulku pre dialóg
        dialog_title = LanguageManager.get("dialog_select_output", "Vyberte výstupný priečinok pre .exe")
        
        # Otvoríme dialóg pre výber priečinka
        selected_dir = QFileDialog.getExistingDirectory(
            window, 
            dialog_title, 
            current_path
        )

        # Ak používateľ niečo vybral (nezrušil dialóg), zapíšeme to do okna
        if selected_dir:
            # Normalizujeme lomené čiary pre Windows
            normalized_path = os.path.normpath(selected_dir)
            window.edit_output_path.setText(normalized_path)