#----------------------------------------
# Súbor: core/logic/containers/logic/check_multi_venv.py
#----------------------------------------

import os
from core.logic.process_registry import process_registry

class MultiVenvChecker:
    """
    Centrálna logika pre kontrolu konfliktov a evidenciu vlastníctva procesov
    spustených cez jednotlivé multiskupiny.
    """
    
    # Slovník (matrika) na uchovanie vlastníkov: { "cesta/k/venv": "nazov_skupiny" }
    _venv_owners = {}

    @staticmethod
    def get_running_conflicts(core, group_name: str) -> list:
        """
        Prejde všetky prostredia v skupine a vráti zoznam názvov projektov,
        ktorých prostredia (venv) už aktuálne bežia (nezáleží na vlastníkovi).
        Používa sa na predštartovú kontrolu.
        """
        conflicts = []
        members = core.multi_groups.get(group_name, [])
        
        for member in members:
            venv_path = member.get("venv_path")
            project_name = member.get("project", "Neznámy projekt")
            
            if venv_path and process_registry.is_running(venv_path):
                conflicts.append(project_name)
                
        return conflicts

    # --- SEKECIA LOGIKY: "MATRIKA VLASTNÍKOV" ---

    @staticmethod
    def set_owner(venv_path: str, group_name: str):
        """Zaznamená, ktorá skupina práve naštartovala a vlastní dané prostredie."""
        if venv_path and group_name:
            norm_path = os.path.normpath(venv_path).lower()
            MultiVenvChecker._venv_owners[norm_path] = group_name

    @staticmethod
    def is_owner(venv_path: str, group_name: str) -> bool:
        """Overí, či daná skupina je skutočným vlastníkom bežiaceho prostredia."""
        if not venv_path or not group_name:
            return False
        norm_path = os.path.normpath(venv_path).lower()
        return MultiVenvChecker._venv_owners.get(norm_path) == group_name

    @staticmethod
    def remove_owner(venv_path: str):
        """Vymaže vlastníka pre dané prostredie (napr. po úspešnom zastavení)."""
        if not venv_path:
            return
        norm_path = os.path.normpath(venv_path).lower()
        if norm_path in MultiVenvChecker._venv_owners:
            del MultiVenvChecker._venv_owners[norm_path]

    @staticmethod
    def clear_owners_for_group(core, group_name: str):
        """Prejde členov skupiny a vymaže všetkých vlastníkov, ktorí do nej patria."""
        members = core.multi_groups.get(group_name, [])
        for member in members:
            venv_path = member.get("venv_path")
            MultiVenvChecker.remove_owner(venv_path)