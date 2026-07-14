#----------------------------------------
# Súbor: core/logic/py_installer/logic/assets_setup.py
#----------------------------------------

import os

class AssetsSetupLogic:
    """
    Logika pre 2. záložku (Assets) v PyInstaller Builderi.
    Spracováva pridané súbory a priečinky z QTableWidget a prevádza ich na --add-data argumenty.
    """

    @staticmethod
    def get_args(data_items: list[tuple[str, str]]) -> list[str]:
        """
        Vygeneruje argumenty pre pridané dátové súbory a priečinky.
        
        Args:
            data_items: Zoznam n-tíc (tuples) vo formáte [(zdrojova_cesta, cielovy_priecinok), ...]
                        Získané z tabuľky table_data v UI.
            
        Returns:
            list[str]: Zoznam argumentov, napr. ['--add-data', 'config.json;.', '--add-data', 'ui;ui']
        """
        args = []
        
        if not data_items:
            return args

        # os.pathsep vloží bodkočiarku ';' na Windows a dvojbodku ':' na Unix/Linux/Mac
        separator = os.pathsep 
        
        for source_path, dest_folder in data_items:
            # Odstránime prípadné biele znaky
            src = source_path.strip()
            dst = dest_folder.strip()
            
            # Ak je cieľový priečinok prázdny, PyInstaller by to mal skopírovať do koreňa aplikácie (označuje sa ako '.')
            if not dst:
                dst = "."
                
            if src:
                # Pridáme argument do zoznamu
                args.extend(["--add-data", f"{src}{separator}{dst}"])

        return args