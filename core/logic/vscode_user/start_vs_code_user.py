#----------------------------------------
# Súbor: core/logic/vscode_user/start_vs_code_user.py
#----------------------------------------

import os
import subprocess
from core.logic.vs_code_json import VSCodeIntegration
from core.logic.language_manager import LanguageManager

class VSCodeLauncher:
    """
    Logika pre spustenie VS Code.
    Automaticky konfiguruje cesty k izolovaným profilom a prepína predvolený Venv.
    """

    @staticmethod
    def launch(core, project_path: str, venv_path: str) -> tuple[bool, str]:
        """
        Spustí VS Code pre zadaný projekt a prostredie.
        
        Args:
            core: Hlavný objekt aplikácie obsahujúci konfiguráciu.
            project_path (str): Cesta k priečinku projektu.
            venv_path (str): Cesta k vybranému virtuálnemu prostrediu.
            
        Returns:
            tuple: (Úspech - True/False, Chybová správa v prípade zlyhania)
        """
        if not project_path or not os.path.exists(project_path):
            return False, LanguageManager.get("err_project_path_not_exist", "Cesta k projektu neexistuje.")

        # 1. Zabezpečíme, že sa VS Code otvorí s týmto konkrétnym Venvom
        if venv_path and os.path.exists(venv_path):
            VSCodeIntegration.set_default_interpreter(project_path, venv_path)

        # 2. Základný príkaz pre spustenie VS Code
        # Na Windows je "code" zvyčajne odkaz na "code.cmd" v systémovej premennej PATH
        cmd = ["code"]

        # 3. Zistenie aktívneho používateľského profilu
        active_user_id = getattr(core, 'active_vscode_user', '')
        users_root = getattr(core, 'vscode_users_root', '')

        # Ak máme aktívny profil, pripojíme argumenty pre izoláciu dát a rozšírení
        if active_user_id and users_root and os.path.exists(users_root):
            profile_dir = os.path.join(users_root, active_user_id)
            
            if os.path.exists(profile_dir):
                # VS Code očakáva pre '--user-data-dir' zložku, v ktorej si následne sám hľadá/vytvára zložku 'User'.
                # Naša štruktúra je pripravená presne takto: profile_dir/data/User
                user_data_dir = os.path.join(profile_dir, "data")
                extensions_dir = os.path.join(profile_dir, "data", "extensions")
                
                cmd.extend(["--user-data-dir", user_data_dir])
                cmd.extend(["--extensions-dir", extensions_dir])

        # 4. Pridáme cieľový adresár projektu
        cmd.append(project_path)

        # 5. Samotné spustenie procesu
        try:
            # shell=True je dôležité na Windows, aby systém našiel 'code' v PATH (keďže je to .cmd a nie .exe)
            # CREATE_NO_WINDOW zabezpečí, že nám nepreblikne čierne cmd okno.
            is_windows = (os.name == 'nt')
            creation_flags = 0x08000000 if is_windows else 0
            
            subprocess.Popen(
                cmd, 
                shell=is_windows, 
                creationflags=creation_flags
            )
            return True, ""
            
        except Exception as e:
            return False, LanguageManager.get("err_launch_vscode", "Nepodarilo sa spustiť VS Code:\n{0}").format(str(e))
