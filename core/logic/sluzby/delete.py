#----------------------------------------
# Súbor: core/logic/sluzby/delete.py
#----------------------------------------

import os
import shutil
import ctypes
import time
from core.logic.sluzby.win_admin import WinAdmin
from core.logic.language_manager import LanguageManager

class UniversalDeleter:
    """
    Univerzálna služba pre bezpečné odstraňovanie súborov a adresárov.
    """

    @staticmethod
    def delete(target_path: str) -> dict:
        """
        Odstráni zadanú cestu (súbor alebo priečinok).
        Automaticky rieši administrátorské práva cez UAC, ak sú potrebné.
        
        Args:
            target_path (str): Cesta k súboru alebo adresáru na vymazanie.
            
        Returns:
            dict: {'success': True/False, 'error': 'Prípadná chybová hláška'}
        """
        if not os.path.exists(target_path):
            err_msg = LanguageManager.get("del_err_path", "Cesta neexistuje: {path}").format(path=target_path)
            return {'success': False, 'error': err_msg}

        # 1. Zistíme, či na túto cestu potrebujeme UAC práva
        if WinAdmin.needs_admin_for_path(target_path):
            
            # Príkaz sa líši pre súbor a pre zložku
            if os.path.isdir(target_path):
                cmd_params = f'/c rmdir /S /Q "{target_path}"'
            else:
                cmd_params = f'/c del /F /Q "{target_path}"'
            
            # Vyvoláme UAC okno
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", cmd_params, None, 0)
            
            if ret <= 32:
                err_msg = LanguageManager.get("del_err_uac", "Vymazanie zrušené používateľom (UAC odmietnuté).")
                return {'success': False, 'error': err_msg}
            
            # Počkáme na asynchrónne vymazanie systémom
            for _ in range(15):
                if not os.path.exists(target_path):
                    return {'success': True}
                time.sleep(0.5)
                
            err_msg = LanguageManager.get("del_err_timeout", "Časový limit vypršal. Súbor možno nebol vymazaný.")
            return {'success': False, 'error': err_msg}
            
        # 2. Ak nepotrebujeme UAC práva, mažeme priamo v aktuálnom vlákne
        else:
            try:
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
                return {'success': True}
                
            except PermissionError:
                err_msg = LanguageManager.get("del_err_in_use", "Súbor je otvorený iným programom alebo nemáte práva.")
                return {'success': False, 'error': err_msg}
            except Exception as e:
                err_msg = LanguageManager.get("del_err_unexpected_noicon", "Chyba pri mazaní: {error}").format(error=e)
                return {'success': False, 'error': err_msg}