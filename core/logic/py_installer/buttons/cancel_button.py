#----------------------------------------
# Súbor: core/logic/py_installer/buttons/cancel_button.py
#----------------------------------------

class CancelButtonHandler:
    """
    Spracováva kliknutie na tlačidlo 'Zrušiť'.
    Vyčistí všetky polia v záložkách a vráti UI do predvoleného stavu.
    """
    
    @staticmethod
    def run(window):
        # 1. Reset sekcie 'Ciele a prostredie' 
        # (Zavolaním on_project_changed sa znovu načítajú cesty a skripty pre aktuálny projekt)
        current_project = window.combo_project.currentText()
        if current_project:
            window.on_project_changed(current_project)

        # 2. Reset záložky 1 (Basic)
        window.edit_app_name.clear()
        window.edit_icon.clear()
        window.rb_onedir.setChecked(True)
        window.rb_console.setChecked(True)
        
        # --- DOPLNENÁ LOGIKA ---
        if hasattr(window, 'edit_birth_cert_path'):
            window.edit_birth_cert_path.clear()
        if hasattr(window, 'chk_add_birth_cert'):
            window.chk_add_birth_cert.setChecked(True)
        # --- KONIEC DOPLNENIA ---

        # 3. Reset záložky 2 (Assets)
        window.table_data.setRowCount(0)

        # 4. Reset záložky 3 (Imports)
        window.list_hidden_imports.clear()
        window.list_exclude_modules.clear()
        window.edit_hidden.clear()
        window.edit_exclude.clear()

        # 5. Reset záložky 4 (Advanced)
        window.chk_clean.setChecked(True)
        window.chk_admin.setChecked(False)
        window.combo_log_level.setCurrentText("INFO")

        # 6. Reset spodnej časti (Vlastné argumenty)
        window.edit_custom_args.clear()

        # 7. Okamžite aktualizujeme Live Preview, aby ukázal čistý príkaz
        if hasattr(window, 'update_live_preview'):
            window.update_live_preview()