#----------------------------------------
# Súbor: core/logic/button/pip/load_list.py
#----------------------------------------

import json
import subprocess
import os
from core.logic.commands.command_factory import PackageManagerFactory

class LoadListHandler:
    @staticmethod
    def get_packages(venv_path, manager_type="pip"):
        """
        Univerzálny načítavač balíčkov.
        """
        CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
        dispatcher = PackageManagerFactory.get_dispatcher(manager_type, venv_path)
        packages = []
        
        # 1. Načítanie nainštalovaných balíčkov
        try:
            cmd_list = dispatcher.get("list_json")
            result = subprocess.run(cmd_list, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                installed_map = {item['name']: item['version'] for item in data}
            else:
                return [] 
        except Exception:
            return []

        # 2. Načítanie zastaraných balíčkov
        outdated_map = {}
        try:
            cmd_outdated = dispatcher.get("list_outdated_json")
            result_out = subprocess.run(cmd_outdated, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if result_out.returncode == 0:
                out_data = json.loads(result_out.stdout)
                outdated_map = {item['name']: item['latest_version'] for item in out_data}
        except Exception:
            pass

        # 3. Spojenie dát pre tabuľku
        for name, version in installed_map.items():
            latest = outdated_map.get(name, version) 
            packages.append({
                'name': name,
                'version': version,
                'latest': latest
            })
            
        return sorted(packages, key=lambda x: x['name'].lower())