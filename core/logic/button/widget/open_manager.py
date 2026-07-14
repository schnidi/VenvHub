#----------------------------------------
# Súbor: core/logic/button/widget/open_manager.py
#----------------------------------------

from windows.manager import MasterManager

class OpenManagerHandler:
    @staticmethod
    def run(parent):
        if parent.manager_window is None:
            parent.manager_window = MasterManager(parent.core)
            # ZMENA: Voláme on_config_changed namiesto obyčajného update_status
            parent.manager_window.config_changed.connect(parent.on_config_changed)
            parent.manager_window.theme_changed.connect(parent.on_skin_changed)
        
        parent.manager_window.show()
        parent.manager_window.raise_()
        parent.manager_window.activateWindow()