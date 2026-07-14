#----------------------------------------
# Súbor: core/logic/containers/logic/sekvence_start.py
#----------------------------------------

import os
import time
import subprocess
import psutil
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from core.logic.language_manager import LanguageManager
from core._path import Paths
from core.logic.process_registry import process_registry
from core.logic.containers.logic.check_multi_venv import MultiVenvChecker
from core.logic.containers.logic.hook import HookManager
from core.logic.containers.logic.respawn_multi import RespawnManager

class SekvenceStart(QObject):
    """
    Trieda zodpovedná za novú, zjednotenú logiku spúšťania programov v rámci kontajnerov.
    Implementuje presne 8 variačných konfigurácií na základe kombinácie troch nastavení:
    1. Wait (Čakanie) - oneskorenie pred štartom
    2. Kotva (Hook) - čakanie na úspešnú inicializáciu
    3. Respawn (Reštart) - automatická obnova pri páde
    """
    log_signal = pyqtSignal(str)

    def __init__(self, core, group_name):
        super().__init__()
        self.core = core
        self.group_name = group_name
        self.is_cancelled = False
        
        # Evidencia predchodcov: Pamäť už spustených projektov v aktuálnej sekvencii pre reťazovú kontrolu
        self.predchadzajuce_projekty = []

    def cancel(self):
        """Prerušenie spúšťania sekvencie."""
        self.is_cancelled = True

    def spusti_projekt(self, member, json_data):
        """
        Spustí konkrétny projekt zo skupiny na základe 1 z 8 variačných konfigurácií.
        """
        project_name = member.get("project")
        venv_path = member.get("venv_path")
        script_to_run = member.get("script_to_run")

        if not all([project_name, venv_path, script_to_run]):
            self.log_signal.emit(LanguageManager.get("msg_incomplete_project_data", "❌ Neúplné údaje pre projekt v skupine."))
            return False

        # Načítanie nastavení projektu
        project_settings = json_data.get("projects", {})
        proj_conf = project_settings.get(project_name, {})
        has_kotva = bool(proj_conf.get("kotva", False))
        respawn_enabled = bool(proj_conf.get("respawn", False))
        
        try:
            wait_time = int(proj_conf.get("wait", "0"))
        except ValueError:
            wait_time = 0

        has_wait = wait_time > 0

        # Výpis zvolenej konfigurácie (1 až 8)
        self._log_konfiguraciu(project_name, has_wait, wait_time, has_kotva, respawn_enabled)

        # Spustenie podľa jednej z 8 kombinácií
        uspech = self._vykonaj_spustenie(
            project_name=project_name,
            venv_path=venv_path,
            script_to_run=script_to_run,
            has_wait=has_wait,
            wait_time=wait_time,
            has_kotva=has_kotva,
            respawn_enabled=respawn_enabled,
            json_data=json_data
        )

        # Zápis úspešného projektu medzi predchodcov
        if uspech:
            self.predchadzajuce_projekty.append({
                "project_name": project_name,
                "venv_path": venv_path,
                "has_kotva": has_kotva
            })

        return uspech

    def _log_konfiguraciu(self, project_name, has_wait, wait_time, has_kotva, respawn_enabled):
        """Vypíše do logu, ktorá z 8 konfigurácií bola zvolená."""
        if not has_wait and not has_kotva and not respawn_enabled:
            msg = LanguageManager.get("msg_config_1", "[{0}] Volba 1: Bez čakania, Bez kotvy, Bez reštartu").format(project_name)
            self.log_signal.emit(msg)
        elif has_wait and not has_kotva and not respawn_enabled:
            msg = LanguageManager.get("msg_config_2", "[{0}] Volba 2: Len s Čakaním (Wait = {1}s)").format(project_name, wait_time)
            self.log_signal.emit(msg)
        elif not has_wait and has_kotva and not respawn_enabled:
            msg = LanguageManager.get("msg_config_3", "[{0}] Volba 3: Len s Kotvou").format(project_name)
            self.log_signal.emit(msg)
        elif has_wait and has_kotva and not respawn_enabled:
            msg = LanguageManager.get("msg_config_4", "[{0}] Volba 4: S Čakaním (Wait = {1}s) a Kotvou").format(project_name, wait_time)
            self.log_signal.emit(msg)
        elif not has_wait and not has_kotva and respawn_enabled:
            msg = LanguageManager.get("msg_config_5", "[{0}] Volba 5: Len s Reštartom (Respawn)").format(project_name)
            self.log_signal.emit(msg)
        elif has_wait and not has_kotva and respawn_enabled:
            msg = LanguageManager.get("msg_config_6", "[{0}] Volba 6: S Čakaním (Wait = {1}s) a Reštartom (Respawn)").format(project_name, wait_time)
            self.log_signal.emit(msg)
        elif not has_wait and has_kotva and respawn_enabled:
            msg = LanguageManager.get("msg_config_7", "[{0}] Volba 7: S Kotvou a Reštartom (Respawn)").format(project_name)
            self.log_signal.emit(msg)
        elif has_wait and has_kotva and respawn_enabled:
            msg = LanguageManager.get("msg_config_8", "[{0}] Volba 8: Všetky tri zapnuté (Čakanie {1}s + Kotva + Reštart)").format(project_name, wait_time)
            self.log_signal.emit(msg)

    def _vykonaj_spustenie(self, project_name, venv_path, script_to_run, has_wait, wait_time, has_kotva, respawn_enabled, json_data):
        """
        Vykoná samotnú spúšťaciu logiku a ošetrí prípadné pády/reštarty.
        """
        pokus = 0
        max_pokusov = 3 if respawn_enabled else 1

        while pokus < max_pokusov:
            if self.is_cancelled:
                self.log_signal.emit(LanguageManager.get("msg_launch_cancelled", "[{0}] ⏹️ Spúšťanie bolo zrušené.").format(project_name))
                return False

            # --- KROK 1: Čakanie (Wait) ak je zapnuté (Konfigurácie 2, 4, 6, 8) ---
            # Pri opätovnom reštarte (Respawn) sa čaká znova iba ak je povolený reštart s wait-om (Konfigurácie 6, 8)
            if has_wait:
                if pokus == 0 or (pokus > 0 and respawn_enabled):
                    self.log_signal.emit(LanguageManager.get("msg_countdown_wait", "[{0}] ⏱️ Odpočítavam Wait {1}s...").format(project_name, wait_time))
                    
                    if not self._pockaj_sekundy(wait_time, project_name):
                        return False

            # --- KROK 2: Príprava a čistenie predošlých procesov ---
            process_registry.cleanup_dead_processes(venv_path)
            if pokus == 0 and process_registry.is_running(venv_path):
                self.log_signal.emit(LanguageManager.get("msg_skipping_already_running", "[{0}] ⏩ Preskakujem, projekt už beží.").format(project_name))
                return True

            project_path = Paths.get_project_path(self.core.projects_root, project_name)
            run_env = os.environ.copy()
            hook_path = None

            # --- KROK 3: Príprava kotvy (Konfigurácie 3, 4, 7, 8) ---
            if has_kotva:
                run_env, hook_path = HookManager.prepare_hook_env(venv_path)

            # --- KROK 4: Spustenie procesu ---
            self.log_signal.emit(LanguageManager.get("msg_launching_process", "[{0}] Spúšťam proces (pokus {1}/{2})...").format(project_name, pokus + 1, max_pokusov))
            try:
                # Zistenie typu okna
                is_terminal = json_data.get("terminal", True)
                CREATE_NO_WINDOW = 0x08000000
                CREATE_NEW_CONSOLE = 0x00000010

                if is_terminal:
                    activate_bat = Paths.get_venv_activate_bat_path(venv_path)
                    # Obalíme volanie do 'call' a použijeme priamo cwd parameter
                    cmd = f'cmd.exe /k "call "{activate_bat}" && python "{script_to_run}""'
                    proc = subprocess.Popen(cmd, cwd=project_path, creationflags=CREATE_NEW_CONSOLE, env=run_env)
                else:
                    python_exe = Paths.get_venv_python_exe_path(venv_path)
                    script_path = Paths.get_script_in_project_path(project_path, script_to_run)
                    proc = subprocess.Popen([python_exe, script_path], cwd=project_path, creationflags=CREATE_NO_WINDOW, env=run_env)

                MultiVenvChecker.set_owner(venv_path, self.group_name)
                process_registry.register(venv_path, pid=proc.pid, process_type='terminal' if is_terminal else 'silent')

            except Exception as e:
                self.log_signal.emit(LanguageManager.get("msg_launch_process_err", "[{0}] ❌ Chyba pri spustení procesu: {1}").format(project_name, e))
                if respawn_enabled:
                    pokus += 1
                    if pokus < max_pokusov:
                        self.log_signal.emit(LanguageManager.get("msg_wait_before_restart", "[{0}] 🔄 Čakám 2 sekundy pred novým pokusom o reštart...").format(project_name))
                        
                        if not self._pockaj_sekundy(2, project_name):
                            return False
                        continue
                return False

            # --- KROK 5: Čakanie na Kotvu ak je zapnutá (Konfigurácie 3, 4, 7, 8) ---
            if has_kotva and hook_path:
                self.log_signal.emit(LanguageManager.get("msg_waiting_for_hook", "[{0}] ⚓ Zmrazujem sekvenciu a čakám na signál kotvy...").format(project_name))
                hook_success = HookManager.wait_for_hook(
                    venv_path=venv_path,
                    hook_path=hook_path,
                    log_callback=self.log_signal.emit,
                    respawn_enabled=respawn_enabled,
                    is_cancelled_func=lambda: self.is_cancelled
                )

                if self.is_cancelled:
                    return False

                if not hook_success:
                    # Program buď spadol pred poslaním kotvy, alebo uplynul limit
                    if respawn_enabled:
                        pokus += 1
                        if pokus < max_pokusov:
                            self.log_signal.emit(LanguageManager.get("msg_program_crashed_before_hook", "[{0}] ❌ Program spadol pred odoslaním kotvy. Čakám 2 sekundy pred reštartom...").format(project_name))
                            # Zabijeme starý proces
                            self._zabi_proces_podla_pid(proc.pid)
                            
                            if not self._pockaj_sekundy(2, project_name):
                                return False
                            continue
                    
                    self.log_signal.emit(LanguageManager.get("msg_hook_error_abort", "❌ CHYBA KOTVY! Prerušujem štartovanie celej skupiny '{0}'.").format(self.group_name))
                    return False

            # Ak sme sa dostali sem, proces úspešne naštartoval (a prípadne prešiel kotvou)
            return True

        self.log_signal.emit(LanguageManager.get("msg_failed_after_attempts", "❌ [{0}] Nepodarilo sa úspešne naštartovať ani po {1} pokusoch.").format(project_name, max_pokusov))
        return False

    def _pockaj_sekundy(self, sekundy, aktualny_projekt="Neznámy"):
        """
        Prerušiteľné čakanie po malých krokoch. 
        Počas odpočtu aktívne kontroluje, či niektorý zo starších (predchádzajúcich) 
        programov v sekvencii nespadol. Ak áno, zablokuje a po oprave resetuje svoj odpočet.
        """
        prebehnute = 0.0
        while prebehnute < sekundy:
            if self.is_cancelled:
                return False

            # KONTROLA PREDCHODCOV (či niekto nespadol kým my čakáme)
            for predchodca in self.predchadzajuce_projekty:
                p_venv = predchodca["venv_path"]
                p_name = predchodca["project_name"]
                p_kotva = predchodca["has_kotva"]

                if not process_registry.is_running(p_venv):
                    # ZÁPIS Č. 1 - Pád predchodcu
                    msg_crash = LanguageManager.get(
                        "msg_wait_predchodca_crash", 
                        "[{0}] ⚠️ POZOR! Predchodca '{1}' spadol počas odpočtu! Prerušujem odpočet a čakám na jeho stav..."
                    ).format(aktualny_projekt, p_name)
                    self.log_signal.emit(msg_crash)
                    
                    # Čakáme, kým ho RespawnWorker na pozadí nepostaví na nohy (alebo nezablokuje)
                    while not process_registry.is_running(p_venv):
                        if self.is_cancelled:
                            return False
                        
                        # Dominový efekt - ak predchodca vyčerpá pokusy, sekvencia končí
                        if RespawnManager.is_respawn_blocked(p_venv):
                            # ZÁPIS Č. 2 - Definitívny koniec (Fatal)
                            msg_fatal = LanguageManager.get(
                                "msg_wait_predchodca_fatal", 
                                "[{0}] 🛑 FATAL ERROR: Predchodca '{1}' definitívne zlyhal. Štart sekvencie '{2}' sa trvalo blokuje!"
                            ).format(aktualny_projekt, p_name, self.group_name)
                            self.log_signal.emit(msg_fatal)
                            return False
                            
                        time.sleep(0.5)

                    # ZÁPIS Č. 3 - Predchodca sa reštartoval
                    msg_restarted = LanguageManager.get(
                        "msg_wait_predchodca_restarted", 
                        "[{0}] 🔄 Predchodca '{1}' bol reštartovaný systémom."
                    ).format(aktualny_projekt, p_name)
                    self.log_signal.emit(msg_restarted)

                    # Ak mal predchodca Kotvu, musíme znova počkať na signál od jeho zreštartovanej verzie
                    if p_kotva:
                        # ZÁPIS Č. 4 - Čakanie na novú kotvu
                        msg_new_hook = LanguageManager.get(
                            "msg_wait_predchodca_new_hook", 
                            "[{0}] ⚓ Čakám na NOVÚ kotvu od reštartovaného '{1}'..."
                        ).format(aktualny_projekt, p_name)
                        self.log_signal.emit(msg_new_hook)
                        
                        hook_path = HookManager.get_active_hook(p_venv)
                        
                        hook_success = HookManager.wait_for_hook(
                            venv_path=p_venv,
                            hook_path=hook_path,
                            log_callback=self.log_signal.emit,
                            respawn_enabled=True,
                            is_cancelled_func=lambda: self.is_cancelled
                        )
                        if not hook_success:
                            # ZÁPIS Č. 5 - Reštartovaný padol na kotve
                            msg_hook_failed = LanguageManager.get(
                                "msg_wait_predchodca_hook_failed", 
                                "[{0}] 🛑 FATAL ERROR: Reštartovaný '{1}' zlyhal pri kotve. Sekvencia končí."
                            ).format(aktualny_projekt, p_name)
                            self.log_signal.emit(msg_hook_failed)
                            return False
                    
                    # Predchodca je zachránený. Plný čas pre stabilitu: RESETUJEME NASTAVENIA ČAKANIA NA NULU!
                    prebehnute = 0.0
                    
                    # ZÁPIS Č. 6 - Stabilizácia a reset odpočtu
                    msg_stabilized = LanguageManager.get(
                        "msg_wait_predchodca_stabilized", 
                        "[{0}] ✅ Predchodca stabilizovaný. Odpočet {1}s začína ÚPLNE ODZNOVA."
                    ).format(aktualny_projekt, sekundy)
                    self.log_signal.emit(msg_stabilized)
                    
                    break # Preruší for cyklus (aby sme nezvyšovali čas) a vráti sa na začiatok while cyklu
                    
            else:
                # Tento 'else' patrí k 'for' cyklu. Spustí sa len ak žiadny predchodca nespadol (nevykonal sa break).
                time.sleep(0.5)
                prebehnute += 0.5
                
        return True

    def _zabi_proces_podla_pid(self, pid):
        """Bezpečne ukončí visiaci proces a všetky jeho podprocesy."""
        if pid:
            try:
                if psutil.pid_exists(pid):
                    parent = psutil.Process(pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
            except Exception:
                pass