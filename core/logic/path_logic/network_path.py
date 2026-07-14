#----------------------------------------
# Súbor: core/logic/path_logic/network_path.py
#----------------------------------------

import os

class NetworkPathLogic:
    """
    Logika pre detekciu sieťových ciest a dostupnosti diskov.
    """

    @staticmethod
    def is_unc_path(path: str) -> bool:
        # Pridané 'r' pred úvodzovky (riadok 14)
        r"""Detekuje \\Server\Share cesty."""
        if not path: return False
        norm = os.path.normpath(path)
        return norm.startswith(r"\\")

    @staticmethod
    def is_drive_root_available(path: str) -> bool:
        # PRIDANÉ 'r' TU (riadok 24) - toto vyrieši SyntaxWarning: invalid escape sequence '\P'
        r"""
        Zistí, či je pripojený disk, na ktorom sa cesta nachádza.
        Napr. pre 'Z:\Projekty\App' skontroluje, či existuje 'Z:\'.
        """
        if not path: return False
        
        drive, _ = os.path.splitdrive(path)
        if not drive: 
            return True # Relatívna cesta, považujeme za dostupnú
            
        # Pridáme lomítko, aby sme skontrolovali root (napr. C:\)
        drive_root = drive + os.sep 
        return os.path.exists(drive_root) 