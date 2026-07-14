#----------------------------------------
# Súbor: core/logic/py_installer/logic/basic_setup.py
#----------------------------------------

class BasicSetupLogic:
    """
    Logika pre 1. záložku (Basic) v PyInstaller Builderi.
    Spracováva údaje z UI a vracia zoznam argumentov.
    """

    @staticmethod
    def get_args(app_name: str, icon_path: str, is_windowed: bool, is_onefile: bool) -> list[str]:
        """
        Vygeneruje argumenty pre základné nastavenia.
        
        Args:
            app_name (str): Názov aplikácie (--name).
            icon_path (str): Cesta k .ico súboru (--icon).
            is_windowed (bool): True ak chceme skryť konzolu (--noconsole).
            is_onefile (bool): True pre (--onefile), False pre (--onedir).
            
        Returns:
            list[str]: Zoznam argumentov, napr. ['--name', 'MojaApp', '--noconsole', '--onefile']
        """
        args = []

        # 1. Zabalenie (Onefile vs Onedir)
        if is_onefile:
            args.append("--onefile")
        else:
            args.append("--onedir")

        # 2. Konzola vs Skryté okno (GUI)
        if is_windowed:
            args.append("--noconsole")

        # 3. Názov aplikácie
        if app_name and app_name.strip():
            args.extend(["--name", app_name.strip()])

        # 4. Ikona
        if icon_path and icon_path.strip():
            # Úvodzovky tu zatiaľ nedávame, subprocess/shlex to zvládne. 
            # Dáme ich až pri zobrazení v Live Preview.
            args.extend(["--icon", icon_path.strip()])

        return args