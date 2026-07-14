#----------------------------------------
# Súbor: core/logic/resource_manager.py
#----------------------------------------

import os
import shutil
from PyQt6.QtWidgets import QFileDialog

class ResourceManager:
    """
    Univerzálna trieda pre prácu so zdrojmi (súbory a priečinky).
    """

    @staticmethod
    def find_resources(directory: str, extension: str) -> list[str]:
        """
        Nájde všetky súbory s danou príponou v adresári.
        Vracia zoznam názvov súborov bez prípony.
        """
        resources = []
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return resources

        try:
            for filename in os.listdir(directory):
                if filename.lower().endswith(extension.lower()):
                    # Odstránime príponu
                    resources.append(os.path.splitext(filename)[0])
        except OSError as e:
            print(f"CHYBA: Nepodarilo sa prečítať priečinok '{directory}': {e}")
            
        return sorted(resources)

    @staticmethod
    def read_resource_file(directory: str, name_without_ext: str, extension: str) -> str | None:
        """
        Načíta obsah súboru podľa jeho mena (bez prípony).
        """
        file_path = os.path.join(directory, f"{name_without_ext}{extension}")
        
        if not os.path.exists(file_path):
            # Tichá chyba, vráti None, ak súbor neexistuje
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"CHYBA: Nepodarilo sa načítať súbor '{file_path}': {e}")
            return None

    @staticmethod
    def import_resource(parent_widget, target_directory: str, dialog_title: str, file_filter: str) -> str | None:
        """
        Otvorí dialóg na import súboru, skopíruje ho a vráti jeho názov bez prípony.
        """
        file_path, _ = QFileDialog.getOpenFileName(parent_widget, dialog_title, "", file_filter)
        
        if not file_path:
            return None

        filename = os.path.basename(file_path)
        destination_path = os.path.join(target_directory, filename)

        try:
            shutil.copy2(file_path, destination_path)
            return os.path.splitext(filename)[0]
        except (shutil.Error, OSError) as e:
            print(f"CHYBA: Nepodarilo sa importovať súbor do '{destination_path}': {e}")
            return None

    @staticmethod
    def parse_qss_metadata(file_path: str) -> dict:
        """
        Prečíta prvých 15 riadkov .qss súboru a pokúsi sa z neho vyparsovať metadáta.
        Hľadá kľúče ako "Theme Name", "Version", "Author".
        """
        import re
        metadata = {}
        if not os.path.exists(file_path):
            return metadata
        
        pattern = re.compile(r"^\s*\*?\s*([\w\s]+):\s*(.+)$")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for _ in range(15):
                    line = f.readline()
                    if not line or '*/' in line:
                        break
                    
                    match = pattern.match(line)
                    if match:
                        key = match.group(1).strip()
                        value = match.group(2).strip()
                        metadata[key] = value
        except Exception:
            pass

        return metadata