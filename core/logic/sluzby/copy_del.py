#----------------------------------------
# Súbor: core/logic/sluzby/copy_del.py
#----------------------------------------

import os
import shutil
import stat
from core.logic.sluzby.HDD_space import HDDSpaceLogic
from core.logic.language_manager import LanguageManager

class CopyDelService:
    """
    Univerzálna, vysoko odolná služba na kopírovanie a mazanie súborov.
    Podporuje sledovanie priebehu (v percentách) a okamžitý automatický 
    REVERZ (vymazanie nakopírovaného), ak používateľ operáciu zruší.
    """

    @staticmethod
    def safe_copy_with_rollback(
        src_path: str, 
        dst_path: str, 
        is_cancelled_func, 
        log_func=None, 
        progress_func=None, 
        delete_full_dst_on_rollback=False
    ) -> dict:
        """
        Inteligentné kopírovanie adresára.
        
        Args:
            src_path: Zdrojový priečinok.
            dst_path: Cieľový priečinok.
            is_cancelled_func: Funkcia, ktorá vráti True, ak užívateľ stlačil Zrušiť.
            log_func: Funkcia na prijímanie textových správ (napr. print alebo log.append).
            progress_func: Funkcia prijímajúca (int) od 0 do 100 pre Progress Bar.
            delete_full_dst_on_rollback: Ak je True, pri zrušení sa zmaže celá cieľová zložka.
                                         Ak je False, zmažú sa len reálne nakopírované súbory.
                                         
        Returns:
            dict: {'success': True/False, 'reason': 'OK', 'CANCELLED', 'INSUFFICIENT_SPACE', 'ERROR'}
        """
        def _log(msg):
            if log_func: log_func(msg)
            
        def _prog(val):
            if progress_func: progress_func(val)

        if not os.path.exists(src_path):
            msg = LanguageManager.get("copy_err_src_path", "❌ Zdrojová cesta neexistuje: {path}").format(path=src_path)
            _log(msg)
            err_reason = LanguageManager.get("copy_err_src_missing", "Zdroj neexistuje")
            return {"success": False, "reason": "ERROR", "error": err_reason}

        # 1. Analýza miesta
        _log(LanguageManager.get("copy_log_analyzing", "🔍 Analyzujem zdrojové dáta a voľné miesto..."))
        dir_info = HDDSpaceLogic.get_directory_info(src_path)
        total_items = len(dir_info["items"])
        needed_mb = dir_info["size_bytes"] / (1024 * 1024)
        free_mb = HDDSpaceLogic.get_free_space_mb(dst_path)

        if free_mb < (needed_mb + 50): # Rezerva 50MB
            msg = LanguageManager.get("copy_err_space", "❌ Málo miesta na disku! Vyžaduje sa {needed:.1f} MB, dostupné je len {free:.1f} MB.").format(needed=needed_mb, free=free_mb)
            _log(msg)
            return {"success": False, "reason": "INSUFFICIENT_SPACE"}

        # 2. Príprava na kopírovanie
        copied_paths = []
        current_item = [0] # Používame list, aby sme to mohli meniť vo vnútornej funkcii

        def _do_copy(s_dir, d_dir):
            if not os.path.exists(d_dir):
                os.makedirs(d_dir, exist_ok=True)
                copied_paths.append(d_dir)

            for item in os.listdir(s_dir):
                if is_cancelled_func():
                    raise InterruptedError(LanguageManager.get("copy_err_interrupted", "Kopírovanie zrušené"))

                s_item = os.path.join(s_dir, item)
                d_item = os.path.join(d_dir, item)

                if os.path.isdir(s_item):
                    _do_copy(s_item, d_item)
                else:
                    # Ochrana pred Read-Only pri prepisovaní
                    if os.path.exists(d_item):
                        try: os.chmod(d_item, stat.S_IWRITE)
                        except: pass
                    
                    shutil.copy2(s_item, d_item)
                    copied_paths.append(d_item)

                # Výpočet percent (smerom hore)
                current_item[0] += 1
                if total_items > 0 and current_item[0] % max(1, total_items // 100) == 0:
                    _prog(int((current_item[0] / total_items) * 100))

        # 3. Spustenie kopírovania
        try:
            _log(LanguageManager.get("copy_log_starting", "⏳ Spúšťam kopírovanie..."))
            _do_copy(src_path, dst_path)
            _prog(100)
            return {"success": True, "reason": "OK"}

        # 4. Spustenie REVERZU (Rollback) pri zrušení
        except InterruptedError:
            _log(LanguageManager.get("copy_log_rollback", "⚠️ Operácia prerušená používateľom. Začínam reverzný proces (mazanie)..."))
            
            if delete_full_dst_on_rollback:
                # Ak mažeme všetko, zistíme zoznam všetkých súborov v cieli
                rollback_items = HDDSpaceLogic.get_directory_info(dst_path)["items"]
            else:
                # Ak mažeme len to, čo sme vytvorili, ideme presne odzadu (od súborov k zložkám)
                rollback_items = list(reversed(copied_paths))

            total_rollback = len(rollback_items)
            
            for i, path in enumerate(rollback_items):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    if os.path.isdir(path): os.rmdir(path)
                    else: os.remove(path)
                except:
                    pass
                
                # Výpočet percent (smerom dole od % kde to seklo až po nulu)
                if total_rollback > 0 and i % max(1, total_rollback // 50) == 0:
                    remaining_percent = int(((total_rollback - i) / total_rollback) * 100)
                    _prog(remaining_percent)
            
            _prog(0)
            _log(LanguageManager.get("copy_log_rollback_ok", "✅ Nekompletné dáta boli úspešne vymazané."))
            return {"success": False, "reason": "CANCELLED"}

        except Exception as e:
            msg = LanguageManager.get("copy_err_unexpected", "❌ Neočakávaná chyba pri kopírovaní: {error}").format(error=e)
            _log(msg)
            return {"success": False, "reason": "ERROR", "error": str(e)}


    @staticmethod
    def safe_delete_with_progress(
        target_path: str, 
        log_func=None, 
        progress_func=None
    ) -> dict:
        """
        Bezpečne vymaže zložku s výpočtom percent (od 0 do 100%).
        
        Args:
            target_path: Priečinok alebo súbor na vymazanie.
            log_func: Callback pre textový log.
            progress_func: Callback pre percentá.
        """
        def _log(msg):
            if log_func: log_func(msg)
            
        def _prog(val):
            if progress_func: progress_func(val)

        if not os.path.exists(target_path):
            _prog(100)
            return {"success": True, "reason": "OK"}

        try:
            _log(LanguageManager.get("del_log_analyzing", "🔍 Analyzujem obsah na vymazanie..."))
            
            if os.path.isfile(target_path):
                try: os.chmod(target_path, stat.S_IWRITE)
                except: pass
                os.remove(target_path)
                _prog(100)
                return {"success": True, "reason": "OK"}

            dir_info = HDDSpaceLogic.get_directory_info(target_path)
            all_items = dir_info["items"]
            total_items = len(all_items)

            if total_items == 0:
                _prog(100)
                return {"success": True, "reason": "OK"}

            msg = LanguageManager.get("del_log_starting", "🗑️ Začínam mazať ({total} položiek)...").format(total=total_items)
            _log(msg)

            for i, path in enumerate(all_items):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    if os.path.isdir(path): os.rmdir(path)
                    else: os.remove(path)
                except:
                    pass
                
                if i % max(1, total_items // 100) == 0:
                    _prog(int((i / total_items) * 100))

            _prog(100)
            return {"success": True, "reason": "OK"}

        except Exception as e:
            msg = LanguageManager.get("del_err_unexpected", "❌ Chyba pri mazaní: {error}").format(error=e)
            _log(msg)
            return {"success": False, "reason": "ERROR", "error": str(e)}