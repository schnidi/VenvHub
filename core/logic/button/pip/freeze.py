#----------------------------------------
# Súbor: core/logic/button/pip/freeze.py
#----------------------------------------

import subprocess
import os
from core._path import Paths
from core.logic.language_manager import LanguageManager
from core.logic.commands.command_factory import PackageManagerFactory

class FreezeHandler:
    @staticmethod
    def run(venv_path, project_root, manager_type="pip", log_callback=None):
        # Vyčistenie a zjednotenie lomiek pre aktuálny operačný systém
        req_path = os.path.normpath(Paths.get_requirements_txt_path(project_root))
        CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
        
        if log_callback: 
            msg = LanguageManager.get("freeze_generating", "Generujem requirements.txt do: {0}").format(req_path)
            log_callback(msg)

        try:
            dispatcher = PackageManagerFactory.get_dispatcher(manager_type, venv_path)
            cmd = dispatcher.get("freeze")

            with open(req_path, "w", encoding="utf-8") as f:
                process = subprocess.run(
                    cmd, 
                    stdout=f, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    creationflags=CREATE_NO_WINDOW
                )
            
            if process.returncode == 0:
                if log_callback: 
                    log_callback(LanguageManager.get("freeze_success", "--- SÚBOR requirements.txt BOL VYTVORENÝ ---"))
                return True
            else:
                if log_callback: 
                    log_callback(LanguageManager.get("freeze_error", "--- CHYBA PRI FREEZE ---"))
                    log_callback(process.stderr)
                return False

        except Exception as e:
            if log_callback:
                msg = LanguageManager.get("freeze_critical_error", "KRITICKÁ CHYBA: {0}").format(str(e))
                log_callback(msg)
            return False