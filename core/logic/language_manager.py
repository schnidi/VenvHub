#----------------------------------------
# Súbor: core/logic/language_manager.py
#----------------------------------------

import json
import locale
import threading
from PyQt6.QtWidgets import QWidget
from core._path import Paths
from core.logic.resource_manager import ResourceManager


class LanguageManager:
    _current_data = {}
    _current_lang_code = "en_US"
    _lock = threading.Lock()

    @classmethod
    def load_language(cls, lang_code="auto"):
        """Načíta JSON preklad pomocou ResourceManager-a (Thread-Safe)."""
        if lang_code == "auto":
            try:
                sys_lang = locale.getdefaultlocale()[0]
                lang_code = sys_lang if sys_lang else "en_US"
            except Exception:
                lang_code = "en_US"

        trans_dir = Paths.get_translations_dir()
        
        # Pokusy o načítanie: 1. Presný kód -> 2. Skrátený kód -> 3. Fallback en_US
        content = ResourceManager.read_resource_file(trans_dir, lang_code, ".json")
        if not content:
            short_code = lang_code.split('_')[0]
            content = ResourceManager.read_resource_file(trans_dir, short_code, ".json")
        if not content:
            content = ResourceManager.read_resource_file(trans_dir, "en_US", ".json")

        new_data = {}
        try:
            if content:
                new_data = json.loads(content)
        except Exception as e:
            print(f"[LanguageManager] CHYBA JAZYKA (Neplatný JSON): {e}")

        with cls._lock:
            cls._current_lang_code = lang_code
            cls._current_data = new_data

    @classmethod
    def get(cls, key: str, default: str = None) -> str:
        """Vráti preklad textu podľa kľúča (Thread-Safe)."""
        with cls._lock:
            val = cls._current_data.get(key)
        
        text = val if val is not None else (default if default is not None else key)
        
        # Globálna oprava zalomenia riadkov z JSON reťazcov
        if isinstance(text, str):
            text = text.replace("\\n", "\n")
            
        return text

    @classmethod
    def translate_ui(cls, window: QWidget):
        """Automaticky preloží widgety okna podľa ich objectName."""
        if not window:
            return

        with cls._lock:
            data_copy = dict(cls._current_data)

        for widget in window.findChildren(QWidget):
            name = getattr(widget, "objectName", lambda: "")()
            if not name or name.startswith("qt_"):
                continue
            
            text = data_copy.get(name)
            if text:
                text_clean = text.replace("\\n", "\n")
                if hasattr(widget, "setPlaceholderText"):
                    widget.setPlaceholderText(text_clean)
                elif hasattr(widget, "setText"):
                    widget.setText(text_clean)
                elif hasattr(widget, "setTitle"):
                    widget.setTitle(text_clean)
        
        win_name = window.objectName()
        if win_name in data_copy:
            window.setWindowTitle(data_copy[win_name].replace("\\n", "\n"))