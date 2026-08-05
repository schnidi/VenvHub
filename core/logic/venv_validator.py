import os
import re
from enum import Enum, auto

class VenvStatus(Enum):
    VALID = auto()
    BROKEN_FIXABLE_PERFECT = auto()   # 100% zhoda (3.11.3 == 3.11.3)
    BROKEN_FIXABLE_UPGRADE = auto()   # Vyšší patch (3.11.3 -> 3.11.6)
    BROKEN_FIXABLE_DOWNGRADE = auto() # Nižší patch (3.11.3 -> 3.11.1)
    BROKEN_INCOMPATIBLE = auto()      # Iná vetva (3.11 -> 3.12)
    MISSING_CONFIG = auto()

class VenvValidator:
    def __init__(self, venv_path: str):
        self.venv_path = venv_path
        self.status = None
        self.original_version = None 
        self.original_home = None
        self.local_found_version = None # Verzia, ktorú sme našli na tomto PC
        self.target_python_path = None  # Cesta k tomu Pythonu, ktorým to opravíme

    def validate(self, available_pythons: list[dict]):
        # 1. Načítame pyvenv.cfg (ak zlyhá, nastavia sa stavy v pomocnej metóde)
        if not self._parse_pyvenv_cfg():
            self.status = VenvStatus.MISSING_CONFIG
            return

        # 2. Ak pôvodná cesta existuje, venv je plne validný
        if self.original_home and os.path.exists(self.original_home):
            self.status = VenvStatus.VALID
            return

        if not self.original_version:
            self.status = VenvStatus.BROKEN_INCOMPATIBLE
            return

        # 3. Pôvodná cesta neexistuje - hľadáme NAJBLIŽŠIEHO kandidáta
        orig_parts = [int(x) for x in self.original_version.split('.')] # [3, 11, 3]

        best_candidate = None
        min_distance = float('inf')

        for py in available_pythons:
            # Vytiahneme verziu z display name (napr. "Python 3.11.6")
            v_match = re.search(r'(\d+\.\d+\.\d+)', py.get("display", ""))
            if not v_match:
                continue
            
            found_v_str = v_match.group(1) # "3.11.6"
            found_parts = [int(x) for x in found_v_str.split('.')] # [3, 11, 6]

            # KONTROLA VETVY (Major.Minor musí presne sedieť, napr. 3.11)
            if found_parts[0] == orig_parts[0] and found_parts[1] == orig_parts[1]:
                # Vypočítame absolútny rozdiel v patch verzii
                distance = abs(found_parts[2] - orig_parts[2])

                # AK JE TO PRESNÁ ZHODA (3.11.3 == 3.11.3) -> Okamžite končíme hľadanie
                if distance == 0:
                    best_candidate = {
                        "version": found_v_str,
                        "path": py['path'],
                        "status": VenvStatus.BROKEN_FIXABLE_PERFECT
                    }
                    break

                # AK HĽADÁME NAJBLIŽŠIU VERZIU (menšia vzdialenosť vyhráva)
                if distance < min_distance:
                    min_distance = distance
                    status = (VenvStatus.BROKEN_FIXABLE_UPGRADE 
                              if found_parts[2] > orig_parts[2] 
                              else VenvStatus.BROKEN_FIXABLE_DOWNGRADE)
                    
                    best_candidate = {
                        "version": found_v_str,
                        "path": py['path'],
                        "status": status
                    }

        # 4. Zapíšeme najlepší nájdený výsledok
        if best_candidate:
            self.local_found_version = best_candidate["version"]
            self.target_python_path = best_candidate["path"]
            self.status = best_candidate["status"]
        else:
            self.status = VenvStatus.BROKEN_INCOMPATIBLE