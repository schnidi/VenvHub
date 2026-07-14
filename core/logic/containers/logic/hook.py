#----------------------------------------
# Súbor: core/logic/containers/logic/hook.py
#----------------------------------------

import os
import time
from core.logic.process_registry import process_registry
from core.logic.language_manager import LanguageManager

class HookManager:
    """
    Služba pre riadenie 'Kotvy' (Synchronizačného bodu).
    Prepája VenvHub a bežiaci Python skript pomocou súborového markera.
    """
    
    ENV_VAR_NAME = "VENVHUB_KOTVA"
    _active_hooks = {}

    @staticmethod
    def prepare_hook_env(venv_path: str) -> tuple[dict, str]:
        """
        Vygeneruje absolútne unikátny názov signálneho súboru pre toto spustenie
        a zapíše ho do systémových premenných.
        """
        unique_id = int(time.time() * 1000)
        hook_path = os.path.join(venv_path, f"ready_signal_{unique_id}.hook")
        
        env = os.environ.copy()
        env[HookManager.ENV_VAR_NAME] = hook_path
        
        # Store active hook
        norm_venv = os.path.normpath(venv_path).lower()
        HookManager._active_hooks[norm_venv] = hook_path
        
        return env, hook_path

    @staticmethod
    def get_active_hook(venv_path: str) -> str | None:
        if not venv_path:
            return None
        norm_venv = os.path.normpath(venv_path).lower()
        return HookManager._active_hooks.get(norm_venv)

    @staticmethod
    def wait_for_hook(venv_path: str, hook_path: str, log_callback=None, respawn_enabled: bool = False, is_cancelled_func=None) -> bool:
        """
        Zastaví vlákno a čaká donekonečna, kým skript nevytvorí marker súbor.
        Aktívne sleduje, či proces nespadol, s ohľadom na pomalý štart CMD okna.
        Zároveň okamžite reaguje na kliknutie tlačidla STOP (cez is_cancelled_func).
        """
        start_time = time.time()
        was_dead = False
        
        while True:
            # 0. AK NÁM Z POZADIA PRIŠIEL SIGNÁL, ŽE SME TO ZRUŠILI (Tlačidlo STOP)
            if is_cancelled_func and is_cancelled_func():
                return False

            # 1. SKRIPT POSLAL SIGNÁL (vytvoril súbor)
            if os.path.exists(hook_path):
                try: 
                    os.remove(hook_path) # Upraceme po sebe
                except: 
                    pass
                if log_callback: 
                    log_callback(LanguageManager.get("hook_log_success", "✅ ⚓ Signál KOTVA prijatý! Program beží, pokračujem v sekvencii."))
                return True
                
            # 2. INTELIGENTNÁ OCHRANA: Čo ak skript spadol predtým, než stihol poslať Kotvu?
            is_running = process_registry.is_running(venv_path)
            
            if not is_running:
                if not was_dead:
                    was_dead = True
                    if log_callback:
                        log_callback(LanguageManager.get("hook_log_wait_restart", "⚠️ Proces nie je spustený, čakám na prípadný reštart..."))
                
                if respawn_enabled:
                    from core.logic.containers.logic.respawn_multi import RespawnManager
                    if RespawnManager.is_respawn_blocked(venv_path):
                        if log_callback:
                            log_callback(LanguageManager.get("hook_err_fatal_respawn", "🛑 FATAL ERROR: Proces definitívne zlyhal po 3 pokusoch o reštart!"))
                        return False
                else:
                    elapsed = time.time() - start_time
                    if elapsed > 6.0:
                        if log_callback:
                            log_callback(LanguageManager.get("hook_err_fatal_crash", "🛑 FATAL ERROR: Proces spadol alebo sa vypol skôr, než stihol odoslať signál Kotvy!"))
                        return False
            else:
                if was_dead:
                    # It was dead, but now it is running again! Reset grace period.
                    was_dead = False
                    start_time = time.time()
                    if log_callback:
                        log_callback(LanguageManager.get("hook_log_restart_detect", "🔄 Detekované opätovné spustenie procesu. Resetujem čakaciu lehotu pre Kotvu."))
                        
            # Uspatie slučky
            time.sleep(0.5)