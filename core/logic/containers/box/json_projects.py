#----------------------------------------
# Súbor: core/logic/containers/box/json_projects.py
#----------------------------------------

import json
import os
from core._path import Paths

class AutostartJsonManager:
    """
    Manažér pre prácu s JSON konfiguráciou jednotlivých skupín v Autostarte.
    Zapisuje in-time dáta priamo do súborov v 'autostart_multi'.
    """

    @staticmethod
    def has_saved_group(group_name: str) -> bool:
        """
        NOVÉ: Zistí, či pre danú skupinu už fyzicky existuje uložený JSON súbor na disku.
        """
        if not group_name:
            return False
        file_path = Paths.get_autostart_file_path(group_name)
        return os.path.exists(file_path)

    @staticmethod
    def save_group(group_name: str, data_dict: dict):
        """Uloží (prepíše) nastavenia skupiny do JSON súboru."""
        if not group_name:
            return
            
        file_path = Paths.get_autostart_file_path(group_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"CHYBA: Nepodarilo sa uložiť autostart JSON pre '{group_name}': {e}")

    @staticmethod
    def load_group(group_name: str) -> dict:
        """Načíta nastavenia zo súboru. Ak neexistuje, vráti predvolenú štruktúru."""
        if not group_name:
            return {}

        file_path = Paths.get_autostart_file_path(group_name)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"CHYBA: Nepodarilo sa načítať autostart JSON pre '{group_name}': {e}")
                
        # Predvolená štruktúra, ak súbor ešte neexistuje
        return {
            "autostart": False,
            "respawn_global": False,
            "terminal": True,
            "silent": False,
            "projects": {}  # Bude obsahovať { "NazovProjektu": {"kotva": True, "wait": "5", "respawn": False} }
        }

    @staticmethod
    def delete_group(group_name: str):
        """Vymaže JSON súbor skupiny, ak existuje."""
        if not group_name:
            return
            
        file_path = Paths.get_autostart_file_path(group_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"CHYBA: Nepodarilo sa zmazať autostart JSON pre '{group_name}': {e}")