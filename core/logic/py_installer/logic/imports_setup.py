#----------------------------------------
# Súbor: core/logic/py_installer/logic/imports_setup.py
#----------------------------------------

class ImportsSetupLogic:
    """
    Logika pre 3. záložku (Imports) v PyInstaller Builderi.
    Spracováva zoznamy (QListWidget) pre skryté importy a vylúčené moduly.
    """

    @staticmethod
    def get_args(hidden_imports: list[str], exclude_modules: list[str]) -> list[str]:
        """
        Vygeneruje argumenty pre importy.
        
        Args:
            hidden_imports: Zoznam názvov modulov z list_hidden_imports.
            exclude_modules: Zoznam názvov modulov z list_exclude_modules.
            
        Returns:
            list[str]: Zoznam argumentov, napr. ['--hidden-import', 'sqlite3', '--exclude-module', 'tkinter']
        """
        args = []

        # 1. Skryté importy (moduly, ktoré PyInstaller automaticky nenašiel)
        if hidden_imports:
            for module_name in hidden_imports:
                clean_name = module_name.strip()
                if clean_name:
                    args.extend(["--hidden-import", clean_name])

        # 2. Vylúčené moduly (moduly, ktoré chceme zámerne odstrániť z buildu pre šetrenie miesta)
        if exclude_modules:
            for module_name in exclude_modules:
                clean_name = module_name.strip()
                if clean_name:
                    args.extend(["--exclude-module", clean_name])

        return args