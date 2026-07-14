#----------------------------------------
# Súbor: core/logic/containers/logic/autostart_boot.py
#----------------------------------------

import os
from core.logic.containers.box.json_projects import AutostartJsonManager
from core.logic.containers.button.autostart_actions import AutostartActionHandler
from core.logic.containers.logic.check_multi_venv import MultiVenvChecker
from core.logic.process_registry import process_registry
from core.logic.language_manager import LanguageManager

class AutostartBooter:
    core_ref = None
    ui_callback = None
    group_logs = {}

    @staticmethod
    def run_autostart_groups(core):
        """Spustí sa pri štarte aplikácie z main.py."""
        AutostartBooter.core_ref = core
        
        # 1. Nasadíme centrálneho sledovača na pozadí, ktorý žije nezávisle od GUI
        process_registry.set_callback(AutostartBooter.central_watchdog_callback)

        # 2. Skontrolujeme všetky skupiny a zapneme tie s Autostartom
        for group_name in core.multi_groups.keys():
            if AutostartJsonManager.has_saved_group(group_name):
                data = AutostartJsonManager.load_group(group_name)
                
                if data.get("autostart", False):
                    conflicts = MultiVenvChecker.get_running_conflicts(core, group_name)
                    if conflicts:
                        log_msg = LanguageManager.get("autostart_log_skip", "[BOOT] Preskakujem Autostart, bežia: {conflicts}").format(conflicts=', '.join(conflicts))
                        AutostartBooter.log_to_group(group_name, log_msg)
                        continue

                    log_msg = LanguageManager.get("autostart_log_start", "[BOOT] Spúšťam Autostart pre skupinu: {group}").format(group=group_name)
                    AutostartBooter.log_to_group(group_name, log_msg)
                    
                    # Odovzdávame LAMBDU, ktorá zapíše logy do pamäte, odkiaľ si ich UI môže hocikedy vytiahnuť
                    AutostartActionHandler.start_group(
                        core, 
                        group_name, 
                        log_callback=lambda msg, g=group_name: AutostartBooter.log_to_group(g, msg)
                    )

    @staticmethod
    def log_to_group(group_name, message):
        """Ukladá logy do pamäte a posúva ich do UI, ak je otvorené."""
        if group_name not in AutostartBooter.group_logs:
            AutostartBooter.group_logs[group_name] = []
        
        AutostartBooter.group_logs[group_name].append(message)
        
        # Ak je UI aktívne a nalinkované, pošleme mu to priamo, inak to ostáva len v pamäti
        if AutostartBooter.ui_callback:
            AutostartBooter.ui_callback("LOG", key_name=group_name, message=message)

    @staticmethod
    def central_watchdog_callback(pid, key_name, status, message):
        """Zachytáva VŠETKY pády a zmeny stavu bez ohľadu na to, či je grafické okno otvorené."""
        
        # 1. Pošleme signál do GUI, aby si preplo LEDky a text v tabuľke (ak je otvorené)
        if AutostartBooter.ui_callback:
            AutostartBooter.ui_callback("REGISTRY", key_name=key_name, pid=pid, status=status, message=message)

        # 2. Ak proces SPADOL (ERROR), vyriešime RESPAWN rovno tu na pozadí!
        if status.startswith('ERROR'):
            core = AutostartBooter.core_ref
            if not core: return

            owner_group = None
            matched_member = None
            
            # Zistíme, komu patrí tento spadnutý proces
            for g_name, members in core.multi_groups.items():
                for m in members:
                    v_path = m.get("venv_path")
                    if v_path and os.path.normpath(v_path).lower() == key_name:
                        if MultiVenvChecker.is_owner(v_path, g_name):
                            owner_group = g_name
                            matched_member = m
                            break
                if owner_group: break

            if owner_group and matched_member:
                log_msg = LanguageManager.get("autostart_log_watchdog", "[WATCHDOG] {msg}").format(msg=message)
                AutostartBooter.log_to_group(owner_group, log_msg)
                
                venv_path = matched_member["venv_path"]
                project_name = matched_member["project"]
                script_to_run = matched_member.get("script_to_run", "main.py")
                
                data = AutostartJsonManager.load_group(owner_group)
                is_terminal = data.get("terminal", True)
                proj_settings = data.get("projects", {}).get(project_name, {})
                respawn_enabled = proj_settings.get("respawn", False)

                if respawn_enabled:
                    try:
                        from core.logic.containers.logic.respawn_multi import RespawnManager
                        RespawnManager.handle_crash(
                            core=core,
                            group_name=owner_group,
                            venv_path=venv_path,
                            project_name=project_name,
                            script_to_run=script_to_run,
                            is_terminal=is_terminal,
                            failed_pid=pid,
                            log_callback=lambda msg: AutostartBooter.log_to_group(owner_group, msg)
                        )
                    except Exception as e:
                        err_msg = LanguageManager.get("autostart_err_respawn", "Chyba Respawnu na pozadí: {error}").format(error=e)
                        AutostartBooter.log_to_group(owner_group, err_msg)
                else:
                    MultiVenvChecker.remove_owner(venv_path)