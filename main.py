"""
Súbor: main.pyw
Hlavný spúšťací modul aplikácie VenvHub Pro.
"""

import os
import sys

"""
Nastavenie kódovania UTF-8 pre Windows prostredie a pridanie
priečinka so spusteným skriptom do sys.path pre bezproblémový import modulov.
"""
os.environ["PYTHONUTF8"] = "1"

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


# =========================================================================
# NOVÉ: AKTIVÁCIA GLOBÁLNEHO ODCHYTÁVANIA TVRDÝCH PÁDOV (CRASH LOGGER)
# =========================================================================
try:
    from core.errors.crash_logger import CrashLogger
    CrashLogger.setup()
except Exception as e:
    print(f"Nepodarilo sa naštartovať CrashLogger: {e}")
# =========================================================================


"""
Most medzi PyQt6 a PySide6 (autodetekcia frameworku).
Zachytáva všetky importy Qt modulov a prekladá ich za chodu.
"""
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()


"""
Spustenie načúvacieho kódu na ochranu systémového venvu v prenosnom (portable) režime.
"""
from core.logic.system_listener import SystemListener
SystemListener.start_listening()


"""
Štandardné importy aplikácie prebiehajúce po inicializácii Qt prostredia.
"""
from PyQt6.QtWidgets import QApplication

from windows.widget import ProjectMiniBar
from windows.about_dialog import AboutDialog
from core.logic.project_manager import ProjectCore
from core.logic.skin_manager import SkinManager 
from core.single_instance import SingleInstance, SingleInstanceError
from core.logic.containers.logic.autostart_boot import AutostartBooter
from core.logic.sluzby.about_logic import AboutLogic


def main():
    """
    Hlavná vstupná funkcia aplikácie VenvHub Pro.
    Zabezpečuje inicializáciu Qt aplikácie, kontrolu jedinej inštancie (SingleInstance),
    registráciu okien a služieb, aplikáciu tém a spustenie hlavnej slučky udalosťami.
    """
    app = QApplication(sys.argv)

    """
    Registrácia triedy AboutDialog do centrálnej služby AboutLogic.
    Zamedzuje cyklickým závislostiam medzi titulkovou lištou a dialógom O programe.
    """
    AboutLogic.register_about_dialog(AboutDialog)

    """
    Logika jedinej inštancie aplikácie (SingleInstance).
    Zabraňuje viacnásobnému spusteniu a v prípade potreby prenesie bežiacu aplikáciu do popredia.
    """
    window_ref = [None]

    def bring_to_front():
        """
        Callback funkcia na obnovenie a aktiváciu okien pri pokuse o opätovné spustenie.
        """
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

    """
    Načítanie jadra správy projektov a spustenie neviditeľných služieb.
    """
    core = ProjectCore()

    """
    Štart neviditeľného mosta pre chytré mazanie balíčkov (APT autoremove).
    """
    from core.logic.sluzby.apt_listener import AptListener
    AptListener.start_listening(core)
    
    """
    Aplikovanie aktívnej vizuálnej témy z konfigurácie.
    """
    if core.active_theme and core.active_theme != "default":
        SkinManager.apply_skin(core.active_theme)
        
    widget = ProjectMiniBar(core)
    
    """
    Uloženie vytvoreného okna do kontajnera pre callback SingleInstance.
    """
    window_ref[0] = widget
    
    if core.last_pos:
        widget.move(core.last_pos[0], core.last_pos[1])
        
    widget.show()
    
    """
    Spustenie skupín nastavených pre automatický štart (Autostart).
    """
    AutostartBooter.run_autostart_groups(core)

       
    exit_code = app.exec()
    
    core.last_pos = widget.get_position()
    core.save_config()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()