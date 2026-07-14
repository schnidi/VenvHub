#----------------------------------------
# Súbor: core/logic/button/manager/row_actions.py
#----------------------------------------

import subprocess
import os
from core.logic.button.manager.actions import ActionHandler # Volá centrálny motor
from core._path import Paths

class RowActionHandler:
    """
    Handler pre akcie v riadkoch tabuľky (Manager Window).
    Zabezpečuje, aby sa spúšťali konkrétne venvy nezávisle od globálneho nastavenia.
    """

    @staticmethod
    def run_venv(core, venv_path):
        """
        Zistí kontext z riadku a zavolá centrálnu funkciu na spustenie.
        """
        # Keďže táto akcia je viazaná na tabuľku, `core.active_project` je vždy správny
        project_path = Paths.get_project_path(core.projects_root, core.active_project)
        script_to_run = core.last_script or "main.py"
        
        ActionHandler.start_terminal_process(project_path, venv_path, script_to_run)

    @staticmethod
    def stop_venv(venv_path):
        """
        Zavolá centrálnu funkciu na zastavenie.
        """
        ActionHandler.stop_single(venv_path)