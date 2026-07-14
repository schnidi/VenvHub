#----------------------------------------
# Súbor: core/logic/py_installer/buttons/imports_buttons.py
#----------------------------------------

from PyQt6.QtCore import Qt

class ImportsButtonsHandler:
    
    # --- SKRYTÉ IMPORTY (Hidden) ---
    @staticmethod
    def add_hidden(window):
        text = window.edit_hidden.text().strip()
        if text:
            # Skontrolujeme, či tam už taký nie je
            existing = window.list_hidden_imports.findItems(text, Qt.MatchFlag.MatchExactly)
            if not existing:
                window.list_hidden_imports.addItem(text)
            window.edit_hidden.clear()
            if hasattr(window, 'update_live_preview'):
                window.update_live_preview()

    @staticmethod
    def remove_hidden(window):
        selected_items = window.list_hidden_imports.selectedItems()
        for item in selected_items:
            window.list_hidden_imports.takeItem(window.list_hidden_imports.row(item))
        if selected_items and hasattr(window, 'update_live_preview'):
            window.update_live_preview()

    # --- VYLÚČENÉ MODULY (Exclude) ---
    @staticmethod
    def add_exclude(window):
        text = window.edit_exclude.text().strip()
        if text:
            existing = window.list_exclude_modules.findItems(text, Qt.MatchFlag.MatchExactly)
            if not existing:
                window.list_exclude_modules.addItem(text)
            window.edit_exclude.clear()
            if hasattr(window, 'update_live_preview'):
                window.update_live_preview()

    @staticmethod
    def remove_exclude(window):
        selected_items = window.list_exclude_modules.selectedItems()
        for item in selected_items:
            window.list_exclude_modules.takeItem(window.list_exclude_modules.row(item))
        if selected_items and hasattr(window, 'update_live_preview'):
            window.update_live_preview()