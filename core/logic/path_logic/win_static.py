#----------------------------------------
# Súbor: core/logic/path_logic/win_static.py
#----------------------------------------

import os

class WinStaticPathLogic:
    """
    Logika pre statickú (inštalovanú) verziu.
    Cesty sú pevné. Ak neexistujú, považujú sa za zmazané/chybné.
    """

    @staticmethod
    def validate_project_path(path: str) -> bool:
        """
        Jednoducho overí, či priečinok projektu existuje.
        """
        if not path:
            return False
        return os.path.exists(path) and os.path.isdir(path)

    @staticmethod
    def validate_venv_path(path: str) -> bool:
        """
        Overí, či existuje priečinok venvu a či vyzerá validne
        (či obsahuje skripty na spustenie).
        """
        if not path or not os.path.exists(path):
            return False
            
        # Rýchla kontrola integrity
        if os.name == 'nt':
            activate_script = os.path.join(path, 'Scripts', 'activate.bat')
        else:
            activate_script = os.path.join(path, 'bin', 'activate')
            
        return os.path.exists(activate_script)

    @staticmethod
    def should_cleanup(project_name: str, path: str) -> bool:
        """
        Rozhodovacia logika: Máme tento projekt navrhnúť na vymazanie?
        Vráti True, ak cesta neexistuje.
        (Samotné okno s otázkou 'Zmazať?' bude riešiť GUI, nie táto logika).
        """
        return not WinStaticPathLogic.validate_project_path(path)