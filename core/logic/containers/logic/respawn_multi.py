#----------------------------------------
# Súbor: core/logic/containers/logic/respawn_multi.py
#----------------------------------------

import os
import json
import time
import psutil
import subprocess
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

from core._path import Paths
from core.logic.process_registry import process_registry
from core.logic.containers.logic.check_multi_venv import MultiVenvChecker
from core.logic.language_manager import LanguageManager

class RespawnWorker(QThread):
    """
    Vlákno, ktoré bez sekania GUI počká 2 sekundy,
    zabije mŕtve okno terminálu a spustí projekt nanovo.
    """
    log_signal = pyqtSignal(str)

    def __init__(self, core, group_name, venv_path, project_name, script_to_run, is_terminal, failed_pid):
        super().__init__()
        self.core = core
        self.group_name = group_name
        self.venv_path = venv_path
        self.project_name = project_name
        self.script_to_run = script_to_run
        self.is_terminal = is_terminal
        self.failed_pid = failed_pid

    def run(self):
        # 1. Zabitie starého (mŕtveho) okna terminálu
        if self.failed_pid:
            try:
                if psutil.pid_exists(self.failed_pid):
                    parent = psutil.Process(self.failed_pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
            except Exception:
                pass

        # 2. Bezpečné oneskorenie, aby systém stihol uvoľniť porty/súbory
        time.sleep(2)

        # 3. Spustenie nanovo (Watchdog ho automaticky zachytí a vráti UI do stavu RUNNING)
        project_path = Paths.get_project_path(self.core.projects_root, self.project_name)
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_CONSOLE = 0x00000010

        # Preserve the hook environment variable if we are running with an active hook
        run_env = os.environ.copy()
        try:
            from core.logic.containers.logic.hook import HookManager
            hook_path = HookManager.get_active_hook(self.venv_path)
            if hook_path:
                run_env[HookManager.ENV_VAR_NAME] = hook_path
        except Exception:
            pass

        try:
            MultiVenvChecker.set_owner(self.venv_path, self.group_name)
            if self.is_terminal:
                activate_bat = Paths.get_venv_activate_bat_path(self.venv_path)
                cmd = f'cmd.exe /k "call "{activate_bat}" && python "{self.script_to_run}""'
                proc = subprocess.Popen(cmd, cwd=project_path, creationflags=CREATE_NEW_CONSOLE, env=run_env)
                process_registry.register(self.venv_path, pid=proc.pid, process_type='terminal')
            else:
                python_exe = Paths.get_venv_python_exe_path(self.venv_path)
                script_path = Paths.get_script_in_project_path(project_path, self.script_to_run)
                proc = subprocess.Popen([python_exe, script_path], cwd=project_path, creationflags=CREATE_NO_WINDOW, env=run_env)
                process_registry.register(self.venv_path, pid=proc.pid, process_type='silent')
        except Exception as e:
            err_msg = LanguageManager.get("respawn_err", "[{project}] Respawn CHYBA: {error}").format(project=self.project_name, error=e)
            self.log_signal.emit(err_msg)


class RespawnManager:
    """
    Logika pre počítanie pádov a rozhodovanie o reštarte.
    """
    _crash_counts = {}
    _active_workers = []

    @staticmethod
    def handle_crash(core, group_name, venv_path, project_name, script_to_run, is_terminal, failed_pid, log_callback):
        # 1. Zvýšenie počítadla
        count = RespawnManager._crash_counts.get(venv_path, 0) + 1
        RespawnManager._crash_counts[venv_path] = count

        # 2. Zápis do crash_log.jsonl v priečinku venvu
        log_file = os.path.join(venv_path, "crash_log.jsonl")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "project": project_name,
            "venv": os.path.basename(venv_path),
            "attempt": f"{count}/3",
            "status": "RESTARTING" if count <= 3 else "FATAL_STOP"
        }
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # 3. Vykonanie reštartu alebo definitívne zastavenie
        if count <= 3:
            log_msg = LanguageManager.get("respawn_log_restart", "[{project}] Pád detekovaný (Pokus {count}/3). Inicializujem reštart...").format(project=project_name, count=count)
            log_callback(log_msg)
            worker = RespawnWorker(core, group_name, venv_path, project_name, script_to_run, is_terminal, failed_pid)
            worker.log_signal.connect(log_callback)
            
            # Ochrana vlákna pred zmazaním z pamäte
            worker.finished.connect(worker.deleteLater)
            worker.finished.connect(lambda: RespawnManager._active_workers.remove(worker) if worker in RespawnManager._active_workers else None)
            RespawnManager._active_workers.append(worker)
            
            worker.start()
        else:
            log_msg = LanguageManager.get("respawn_log_fatal", "[{project}] Skript zlyhal 3x. Ďalšie reštarty sú zablokované. Okno terminálu ostáva otvorené.").format(project=project_name)
            log_callback(log_msg)

    @staticmethod
    def is_respawn_blocked(venv_path: str) -> bool:
        """True ak projekt už vyčerpal 3 pokusy o reštart."""
        return RespawnManager._crash_counts.get(venv_path, 0) >= 3

    @staticmethod
    def reset_counts(venv_paths: list):
        """Vynuluje počítadlá pre dané prostredia (Volá sa pri manuálnom STOP)."""
        for path in venv_paths:
            if path in RespawnManager._crash_counts:
                del RespawnManager._crash_counts[path]