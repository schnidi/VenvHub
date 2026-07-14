#----------------------------------------
# Súbor: core/logic/button/manager/activate.py
#----------------------------------------

from core._path import Paths
from core.logic.vs_code_json import VSCodeIntegration
from core.logic.sluzby.local_packages_sync import LocalPackagesSyncService

class ActivateHandler:
    @staticmethod
    def set_default(core, venv_path, parent_window):
        # 1. Nastavíme ako predvolený v našom VenvHub Pro
        core.active_venv_path = venv_path
        core.save_config()

        # 2. Zosynchronizujeme to s VS Code (prepíše python.exe)
        project_path = Paths.get_project_path(core.projects_root, core.active_project)
        VSCodeIntegration.set_default_interpreter(project_path, venv_path)

        # 3. Zosynchronizujeme lokálne balíčky cez centrálnu službu
        LocalPackagesSyncService.sync_venv_to_vscode(core, venv_path)

        # 4. Aktualizujeme GUI
        parent_window.refresh_table()
        parent_window.config_changed.emit()