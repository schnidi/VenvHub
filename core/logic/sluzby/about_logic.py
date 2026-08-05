#----------------------------------------
# Súbor: core/logic/sluzby/about_logic.py
#----------------------------------------

import os
import json
from core._path import Paths
from core.logic.language_manager import LanguageManager


class AboutLogic:
    """Služba na prácu s dátami a načítavanie informácií pre okno 'O programe'."""

    _about_dialog_class = None

    @classmethod
    def register_about_dialog(cls, dialog_class):
        """Umožňuje zaregistrovať triedu AboutDialog pri štarte aplikácie."""
        cls._about_dialog_class = dialog_class

    @classmethod
    def show_about_dialog(cls, parent_window):
        """Získa HTML a otvorí okno 'O programe' bez priamej závislosti na UI."""
        if cls._about_dialog_class is None:
            print("[AboutLogic] CHYBA: Trieda AboutDialog nie je zaregistrovaná!")
            return

        html_content = cls.get_about_html()
        dialog = cls._about_dialog_class(parent_window, html_content)
        dialog.exec()

    @staticmethod
    def get_about_html() -> str:
        """Načíta súbor about.json a vráti HTML podľa jazyka."""
        json_path = os.path.join(Paths.get_base_path(), Paths.ASSETS_DIR_NAME, "about.json")
        html_content = LanguageManager.get("about_fallback_html", "<p>O programe</p>")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    current_lang = LanguageManager._current_lang_code
                    lang_key = f"about_html_{current_lang}"
                    
                    if lang_key in data:
                        html_content = data[lang_key]
                    elif "about_html_en_US" in data:
                        html_content = data["about_html_en_US"]
                    elif "about_html_sk_SK" in data:
                        html_content = data["about_html_sk_SK"]
                    elif "about_html" in data:
                        html_content = data["about_html"]
            except Exception as e:
                html_content = LanguageManager.get("about_err_load", "<p>Chyba: {0}</p>").format(e)
                
        return html_content