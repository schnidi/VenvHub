#----------------------------------------
# Súbor: core/logic/python_installer/box/python_ver_json.py
#----------------------------------------

import os
import json
import ctypes
from PyQt6.QtWidgets import QComboBox, QMessageBox
from PyQt6.QtCore import QObject, QFileSystemWatcher  # PRIDANÝ IMPORT
from core.logic.language_manager import LanguageManager

# Predpokladám, že cesty ťaháš odtiaľto, uprav import ak ho máš inde
from core._path import Paths 

class PythonVersionJsonManager(QObject):  # ZMENA: Pridané dedenie od QObject kvôli signálom
    def __init__(self, combo_urls: QComboBox):
        super().__init__()  # ZMENA: Nutná inicializácia QObject
        self.combo_urls = combo_urls
        self.jsonl_path = Paths.get_python_versions_jsonl_path()
        
        # --- NOVÉ: Sledovač zmien súboru ---
        self.watcher = QFileSystemWatcher()
        if os.path.exists(self.jsonl_path):
            self.watcher.addPath(self.jsonl_path)
            
        self.watcher.fileChanged.connect(self._on_file_saved)

    def _on_file_saved(self, path):
        """Táto metóda sa vystrelí okamžite, keď dáš v Notepade 'Uložiť'."""
        self.load_versions()
        
        # Ak by editor súbor na pozadí premazal a vytvoril nanovo, musíme ho znovu zachytiť
        if os.path.exists(self.jsonl_path) and self.jsonl_path not in self.watcher.files():
            self.watcher.addPath(self.jsonl_path)

    def load_versions(self):
        """
        Načíta dáta z .jsonl súboru a naplní rozbaľovacie menu.
        """
        self.combo_urls.clear()
        
        # Pridáme prázdnu/predvolenú možnosť
        self.combo_urls.addItem(LanguageManager.get("combo_select_version", "-- Vyberte verziu zo zoznamu --"), userData="")

        if not os.path.exists(self.jsonl_path):
            print(f"Upozornenie: Súbor {self.jsonl_path} nebol nájdený.")
            return

        try:
            with open(self.jsonl_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue # Preskočíme prázdne riadky
                    
                    try:
                        data = json.loads(line)
                        name = data.get("name", LanguageManager.get("txt_unknown_version", "Neznáma verzia"))
                        url = data.get("url", "")
                        
                        # Pridáme do comboboxu: Zobrazený text = name, Skryté dáta = url
                        self.combo_urls.addItem(name, userData=url)
                        
                    except json.JSONDecodeError:
                        print(f"Chyba pri čítaní riadku v JSONL: {line}")
                        
        except Exception as e:
            print(f"Chyba pri otváraní súboru {self.jsonl_path}: {e}")

    def get_selected_url(self) -> str:
        """
        Vráti URL vybranej položky z comboboxu.
        """
        return self.combo_urls.currentData()

    def edit_jsonl_file_as_admin(self, parent_widget=None):
        """
        Otvorí .jsonl súbor v poznámkovom bloku s administrátorskými právami (UAC).
        """
        if not os.path.exists(self.jsonl_path):
            # Ak súbor náhodou neexistuje v assets, vytvoríme aspoň prázdny s adresárom
            os.makedirs(os.path.dirname(self.jsonl_path), exist_ok=True)
            with open(self.jsonl_path, 'w', encoding='utf-8') as f:
                f.write('{"name": "Python 3.13.5 (64-bit)", "url": "https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip"}\n')
            
            # Kedže súbor práve vznikol, pridáme ho do nášho sledovača zmien
            if self.jsonl_path not in self.watcher.files():
                self.watcher.addPath(self.jsonl_path)

        try:
            # 1 = SW_SHOWNORMAL (otvorí okno normálne)
            # "runas" vyvolá Windows UAC štít (výzvu na práva admina)
            result = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                "notepad.exe", 
                self.jsonl_path, 
                None, 
                1
            )
            
            # Ak je result <= 32, znamená to chybu (napr. používateľ zamietol UAC okno)
            if result <= 32:
                if parent_widget:
                    QMessageBox.warning(
                        parent_widget,
                        LanguageManager.get("title_access_denied", "Prístup odmietnutý"),
                        LanguageManager.get("msg_admin_rights_required", "Pre úpravu tohto súboru sú potrebné administrátorské práva.\nÚprava bola zrušená.")
                    )
                else:
                    print("UAC zamietnuté alebo chyba pri spúšťaní Notepadu.")
                    
        except Exception as e:
            print(f"Nepodarilo sa otvoriť editor: {e}")