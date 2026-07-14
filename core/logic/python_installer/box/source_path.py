#----------------------------------------
# Súbor: core/logic/python_installer/box/source_path.py
#----------------------------------------

import os
from PyQt6.QtWidgets import QLineEdit, QPushButton, QFileDialog
from core.logic.language_manager import LanguageManager
from core._path import Paths  # PRIDANÝ IMPORT

class SourcePathManager:
    """
    Spravuje logiku pre vstupné pole (QLineEdit) a tlačidlo prehliadania (QPushButton),
    ktoré slúžia na zadanie zdroja pre inštaláciu Pythonu.
    Validuje, či ide o platnú URL alebo existujúci lokálny .zip súbor.
    """
    def __init__(self, edit_path: QLineEdit, btn_browse: QPushButton, parent_widget):
        """
        Inicializuje manažéra a napojí ho na UI prvky.
        
        Args:
            edit_path (QLineEdit): Textové pole pre zadanie cesty/URL.
            btn_browse (QPushButton): Tlačidlo na otvorenie dialógu pre výber súboru.
            parent_widget: Rodičovský widget (okno), potrebný pre zobrazenie QFileDialog.
        """
        self.edit_path = edit_path
        self.btn_browse = btn_browse
        self.parent = parent_widget
        
        # Prepojíme tlačidlo priamo tu, aby bola logika zapuzdrená
        self.btn_browse.clicked.connect(self.browse_for_zip_file)

    def browse_for_zip_file(self):
        """
        Otvorí systémový dialóg na výber .zip súboru a vloží cestu do QLineEdit.
        """
        # Otvorí dialóg v domovskom priečinku používateľa
        start_dir = os.path.expanduser("~")
        
        # Zobrazíme dialóg a filtrujeme len .zip súbory
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            LanguageManager.get("source_path_dialog_title", "Vyberte .zip archív s Pythonom"),
            start_dir,
            LanguageManager.get("source_path_dialog_filter", "Archívy ZIP (*.zip)")
        )
        
        # Ak používateľ vybral súbor (nestlačil Zrušiť)
        if file_path:
            self.edit_path.setText(file_path)

    def get_source_info(self) -> dict:
        """
        Analyzuje text v QLineEdit a vráti štruktúrované informácie.
        Toto je hlavná metóda, ktorú bude volať inštalátor.

        Returns:
            dict: Slovník s informáciami o zdroji.
                  Príklad úspechu: {'is_valid': True, 'type': 'url', 'path': 'http...'}
                  Príklad zlyhania: {'is_valid': False, 'error': 'Chybová správa'}
        """
        path = self.edit_path.text().strip()

        if not path:
            return {'is_valid': False, 'error': LanguageManager.get("source_path_err_empty", "Cesta k zdroju nesmie byť prázdna.")}
        
        # Prípad 1: Je to URL adresa?
        if path.lower().startswith(('http://', 'https://')):
            if not path.lower().endswith('.zip'):
                return {'is_valid': False, 'error': LanguageManager.get("source_path_err_url_zip", "URL adresa musí odkazovať na .zip súbor.")}
            
            return {
                'is_valid': True,
                'type': 'url',
                'path': path
            }
        
        # Prípad 2: Je to lokálna cesta?
        else:
            if not os.path.exists(path):
                return {'is_valid': False, 'error': LanguageManager.get("source_path_err_not_exist", "Zadaná lokálna cesta neexistuje.")}
            
            if not os.path.isfile(path):
                return {'is_valid': False, 'error': LanguageManager.get("source_path_err_not_file", "Cesta musí smerovať na súbor, nie na priečinok.")}

            if not path.lower().endswith('.zip'):
                return {'is_valid': False, 'error': LanguageManager.get("source_path_err_local_zip", "Súbor musí byť typu .zip archív.")}

            return {
                'is_valid': True,
                'type': 'local',
                'path': path
            }

    def get_expected_install_dir(self) -> str:
        """
        Zistí predpokladanú cieľovú zložku na základe zadanej cesty/URL v textovom poli.
        """
        path = self.edit_path.text().strip()
        if not path:
            return ""
            
        # Z URL 'https://.../python-3.13.5-embed-amd64.zip' vysekáme len 'python-3.13.5-embed-amd64'
        filename = os.path.basename(path)
        folder_name = os.path.splitext(filename)[0]
        
        if not folder_name:
            return ""
            
        return os.path.join(Paths.get_python_runtimes_install_dir(), folder_name)