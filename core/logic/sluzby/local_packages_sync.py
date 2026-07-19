#----------------------------------------
# Súbor: core/logic/sluzby/local_packages_sync.py
#----------------------------------------

import os
import json
from core._path import Paths
from core.logic.vs_code_json import VSCodeIntegration

class LocalPackagesSyncService:
    """
    Centrálna služba, ktorá zistí, aké lokálne balíčky sú pripojené
    do aktuálneho Venvu (čítaním venvhub.json) a následne
    tieto cesty synchronizuje s VS Code (settings.json).
    """

    @staticmethod
    def sync_venv_to_vscode(core, venv_path: str):
        if not core.active_project or not venv_path:
            return

        project_path = Paths.get_project_path(core.projects_root, core.active_project)

        # 1. Hľadáme venvhub.json v danom Venve
        site_folder = "Lib" if os.name == 'nt' else "lib"
        site_packages_dir = os.path.join(venv_path, site_folder, "site-packages")
        json_file = os.path.join(site_packages_dir, "venvhub.json")

        target_paths = []

        # 2. Ak existuje, prečítame prepojené cesty
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Zoberieme len reálne cesty k balíčkom
                    target_paths = list(data.values())
            except Exception as e:
                print(f"[LocalPackagesSync] Chyba pri čítaní {json_file}: {e}")

        # 3. Bezpečné získanie koreňa lokálnych balíčkov (OPRAVENÝ FILTER!)
        local_root = getattr(core, 'local_packages_root', '')

        # 4. Synchronizácia s VS Code
        try:
            # Synchronizácia Python ciest (settings.json)
            VSCodeIntegration.sync_local_packages(
                project_path=project_path,
                selected_paths=target_paths,
                local_packages_root=local_root
            )
            
            # --- OPRAVA: TOTO SME ZABUDLI ZAVOLAŤ PRI PREPÍNANÍ VENVU! ---
            # Synchronizácia úloh a skratiek (tasks.json a keybindings.json) cez Brutal Check
            VSCodeIntegration.sync_vscode_tasks_and_keybindings(
                project_path=project_path,
                selected_paths=target_paths,
                local_packages_root=local_root,
                log_callback=print # Vypíše logy do systémovej konzoly
            )
            
        except Exception as e:
            print(f"[LocalPackagesSync] Chyba pri synchronizácii s VS Code: {e}")