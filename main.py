#----------------------------------------
# Súbor: main.pyw
#----------------------------------------

import os
import sys

# =====================================================================
# --- DOČASNÁ DIAGNOSTIKA ZAMRZNUTIA (odstrániť po vyriešení problému) ---
# Každých 8 sekúnd vypíše do konzoly presný zásobník (stack trace)
# VŠETKÝCH bežiacich vlákien - aj keby bolo hlavné vlákno zaseknuté
# v natívnom (C++/Windows API) volaní, kde Ctrl+C nezaberá.
# =====================================================================
#import faulthandler
#faulthandler.enable()
#faulthandler.dump_traceback_later(8, repeat=True)

# =====================================================================
# --- NASTAVENIE SYS.PATH A VYNÚTENIE UTF-8 PRE WINDOWS ---
# =====================================================================
os.environ["PYTHONUTF8"] = "1"

# Zabezpečíme, že priečinok so spusteným skriptom bude v sys.path,
# čo vyrieši problémy s importovaním modulov (ModuleNotFoundError: No module named 'windows')
# bez ohľadu na to, z akého pracovného adresára je skript spustený.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


# =====================================================================
# --- MOST MEDZI PyQt6 A PySide6 (AUTODETEKCIA FRAMEWORKU) ---
# TOTO ZACHYTÍ VŠETKY IMPORTY A PRELOŽÍ ICH DO PYSIDE6 ZA CHODU
# =====================================================================
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()


# =====================================================================
# SPUSTENIE NAČÚVACIEHO KÓDU NA OCHRANU SYSTEM VENV V PORTABLE REŽIME
# =====================================================================
from core.logic.system_listener import SystemListener
SystemListener.start_listening()
# ---------------------


# =====================================================================
# --- ŠTANDARDNÉ IMPORTY APLIKÁCIE ---
# Tieto už pôjdu cez prekladač, ak si systém vybral PySide6
# =====================================================================
from PyQt6.QtWidgets import QApplication

from windows.widget import ProjectMiniBar
from core.logic.project_manager import ProjectCore
from core.logic.skin_manager import SkinManager 
from core.single_instance import SingleInstance, SingleInstanceError
from core.logic.containers.logic.autostart_boot import AutostartBooter

def main():
    app = QApplication(sys.argv)

    # --- SINGLE INSTANCE LOGIKA (ZAČIATOK) ---
    window_ref = [None]

    def bring_to_front():
        if window_ref[0]:
            win = window_ref[0]
            win.show()
            win.raise_()
            win.activateWindow()
            if hasattr(win, 'manager_window') and win.manager_window:
                win.manager_window.show()
                win.manager_window.raise_()
                win.manager_window.activateWindow()

    APP_ID = "VenvHubPro_Single_Instance_Lock"
    checker = SingleInstance(APP_ID, bring_to_front)
    
    try:
        if checker.is_running():
            sys.exit(0)
    except SingleInstanceError as e:
        print(f"CHYBA: {e}")
        sys.exit(1)

    app._single_instance = checker
    # --- SINGLE INSTANCE LOGIKA (KONIEC) ---
    
    # Pokračujeme v štarte aplikácie, lebo sme prví
    core = ProjectCore()
    
    if core.active_theme and core.active_theme != "default":
        SkinManager.apply_skin(core.active_theme)
        
    widget = ProjectMiniBar(core)
    
    # --- DÔLEŽITÉ: Uložíme vytvorené okno do kontajnera pre callback ---
    window_ref[0] = widget
    
    if core.last_pos:
        widget.move(core.last_pos[0], core.last_pos[1])
        
    widget.show()
    
    # =================================================================
    # --- SPUSTENIE AUTOSTARTU ---
    # =================================================================
    AutostartBooter.run_autostart_groups(core)
    
    exit_code = app.exec()
    
    core.last_pos = widget.get_position()
    core.save_config()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()