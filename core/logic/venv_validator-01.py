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
        self.local_found_version = None # Verzia, ktorú sme našli na tomto PC
        self.target_python_path = None # Cesta k tomu Pythonu, ktorým to opravíme

    def validate(self, available_pythons: list[dict]):
        # 1. Načítame pyvenv.cfg
        if not self._parse_pyvenv_cfg(): return

        # 2. Ak pôvodná cesta existuje, neriešime
        if os.path.exists(self.original_home):
            self.status = VenvStatus.VALID
            return

        # 3. Pôvodná cesta neexistuje - porovnávame verzie do hĺbky
        orig_v_str = self.original_version # napr. "3.11.3"
        orig_parts = [int(x) for x in orig_v_str.split('.')] # [3, 11, 3]

        best_py = None
        current_status = VenvStatus.BROKEN_INCOMPATIBLE

        for py in available_pythons:
            # Vytiahneme verziu z display name "Python 3.11.6"
            v_match = re.search(r'(\d+\.\d+\.\d+)', py.get("display", ""))
            if not v_match: continue
            
            found_v_str = v_match.group(1) # "3.11.6"
            found_parts = [int(x) for x in found_v_str.split('.')] # [3, 11, 6]

            # KONTROLA VETVY (Major.Minor musí sedieť)
            if found_parts[0] == orig_parts[0] and found_parts[1] == orig_parts[1]:
                # Sme v správnej vetve (3.11), teraz pozrieme na ten "Drift" (tretie číslo)
                self.local_found_version = found_v_str
                self.target_python_path = py['path']

                if found_parts[2] == orig_parts[2]:
                    current_status = VenvStatus.BROKEN_FIXABLE_PERFECT
                    break # Našli sme 100% zhodu, končíme hľadanie
                elif found_parts[2] > orig_parts[2]:
                    current_status = VenvStatus.BROKEN_FIXABLE_UPGRADE
                else:
                    current_status = VenvStatus.BROKEN_FIXABLE_DOWNGRADE
        
        self.status = current_status