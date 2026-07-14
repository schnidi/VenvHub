#----------------------------------------
# Súbor: core/logic/py_installer/logic/advanced_setup.py
#----------------------------------------

class AdvancedSetupLogic:
    """
    Logika pre 4. záložku (Advanced) v PyInstaller Builderi.
    Spracováva CheckBoxy a ComboBoxy pre technické nastavenia buildu.
    """

    @staticmethod
    def get_args(clean_build: bool, uac_admin: bool, log_level: str) -> list[str]:
        """
        Vygeneruje argumenty pre pokročilé nastavenia.
        
        Args:
            clean_build (bool): Z chk_clean (True = vyčistí PyInstaller cache pred buildom).
            uac_admin (bool): Z chk_admin (True = vyžiada admin práva na Windows pri štarte app).
            log_level (str): Z combo_log_level (INFO, DEBUG, WARN, ERROR, FATAL).
            
        Returns:
            list[str]: Zoznam argumentov, napr. ['--clean', '--uac-admin', '--log-level', 'DEBUG']
        """
        args = []

        # 1. Vyčistiť cache (odporúča sa vždy mať zapnuté)
        if clean_build:
            args.append("--clean")

        # 2. Vyžiadanie Administrátorských práv (funguje hlavne na Windows)
        if uac_admin:
            args.append("--uac-admin")

        # 3. Úroveň logovania výstupu z PyInstalleru
        if log_level and log_level.strip():
            # Typické hodnoty: TRACE, DEBUG, INFO, WARN, ERROR, FATAL
            args.extend(["--log-level", log_level.strip().upper()])

        return args