#----------------------------------------
# Súbor: core/logic/language_manager.py
#----------------------------------------

import json
import locale
from PyQt6.QtWidgets import QWidget
from core._path import Paths
from core.logic.resource_manager import ResourceManager  # <--- PRIDANÝ IMPORT

class LanguageManager:
    _current_data = {}
    _current_lang_code = "en_US"

    @staticmethod
    def load_language(lang_code="auto"):
        """Načíta JSON preklad pomocou spoločného ResourceManager-a."""
        if lang_code == "auto":
            try:
                sys_lang = locale.getdefaultlocale()[0]
                lang_code = sys_lang if sys_lang else "en_US"
            except Exception:
                lang_code = "en_US"

        LanguageManager._current_lang_code = lang_code
        trans_dir = Paths.get_translations_dir()
        
        # 1. Pokus: Načítanie presného kódu (napr. sk_SK)
        content = ResourceManager.read_resource_file(trans_dir, lang_code, ".json")
        
        # 2. Pokus: Ak sa nenašiel, skúsime skrátený kód (napr. sk)
        if not content:
            short_code = lang_code.split('_')[0]
            content = ResourceManager.read_resource_file(trans_dir, short_code, ".json")
            
        # 3. Pokus: Fallback na angličtinu
        if not content:
            content = ResourceManager.read_resource_file(trans_dir, "en_US", ".json")

        # Spracovanie JSON obsahu
        try:
            if content:
                LanguageManager._current_data = json.loads(content)
            else:
                LanguageManager._current_data = {}
        except Exception as e:
            print(f"CHYBA JAZYKA (Neplatný JSON): {e}")
            LanguageManager._current_data = {}

    @staticmethod
    def get(key, default=None):
        """Vráti preklad textu."""
        val = LanguageManager._current_data.get(key)
        
        # Získa text buď zo slovníka, alebo použije predvolený
        text = val if val is not None else (default if default is not None else key)
        
        # --- GLOBÁLNA OPRAVA ZALOMENIA RIADKOV ---
        # Ak je výsledok text (string), nahradí doslovné znaky '\' a 'n' 
        # za skutočný neviditeľný znak pre nový riadok.
        if isinstance(text, str):
            text = text.replace("\\n", "\n")
            
        return text

    @staticmethod
    def translate_ui(window: QWidget):
        """Automaticky preloží widgety podľa objectName."""
        for widget in window.findChildren(QWidget):
            if not hasattr(widget, "objectName"): continue
            name = widget.objectName()
            if not name or name.startswith("qt_"): continue
            
            text = LanguageManager._current_data.get(name)
            if text:
                if hasattr(widget, "setPlaceholderText"):
                    widget.setPlaceholderText(text)
                elif hasattr(widget, "setText"):
                    widget.setText(text)
                elif hasattr(widget, "setTitle"):
                    widget.setTitle(text)
                
                if hasattr(widget, "setToolTip"):
                    pass 
        
        win_name = window.objectName()
        if win_name in LanguageManager._current_data:
            window.setWindowTitle(LanguageManager._current_data[win_name])