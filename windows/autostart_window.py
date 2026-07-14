#----------------------------------------
# Súbor: windows/autostart_window.py
#----------------------------------------

from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
import os

from core._path import Paths
from windows.autostart_group_item import AutostartGroupItem
from core.logic.containers.button.add_new_group import AddNewGroupHandler

# Nový import pre centrálnu komunikáciu s pozadím
from core.logic.containers.logic.autostart_boot import AutostartBooter
from core.logic.containers.box.json_projects import AutostartJsonManager

class AutostartWindow(QWidget):
    """
    Hlavný widget pre záložku "Container" / "Autostart".
    """
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core

        try:
            uic.loadUi(Paths.get_ui_file_path("autostart_window.ui"), self)
        except FileNotFoundError:
            print("CHYBA: Súbor ui/autostart_window.ui nebol nájdený.")
            return
            
        self.added_groups = {}
            
        self.btn_auto_add_group.clicked.connect(lambda: AddNewGroupHandler.run(self))

        # ZMENA: Napojenie sa na CENTRÁLNY ROUTER v jadre
        AutostartBooter.ui_callback = self.global_router_callback

        self.load_initial_groups()

    def load_initial_groups(self):
        for group_name, members in self.core.multi_groups.items():
            if AutostartJsonManager.has_saved_group(group_name):
                self.add_group(group_name, members)

    def global_router_callback(self, action_type, key_name=None, pid=None, status=None, message=None):
        """
        Prijíma požiadavky z bežiaceho jadra (AutostartBooter) a posiela ich správnym grafickým widgetom.
        """
        if action_type == "LOG":
            if key_name in self.added_groups:
                self.added_groups[key_name].auto_log_output.append(message)
                
        elif action_type == "REGISTRY":
            for group_widget in self.added_groups.values():
                group_widget.handle_registry_update(key_name, pid, status, message)

    def add_group(self, group_name, members):
        if group_name in self.added_groups:
            return

        group_item = AutostartGroupItem(parent_window=self)
        group_item.populate_data(group_name, members)
        self.group_container_layout.insertWidget(self.group_container_layout.count() - 1, group_item)
        self.added_groups[group_name] = group_item

    def remove_group(self, group_name, group_widget):
        if group_name in self.added_groups:
            del self.added_groups[group_name]
        group_widget.deleteLater()

    def sync_with_core(self):
        for group_name in list(self.added_groups.keys()):
            if group_name not in self.core.multi_groups:
                widget_to_remove = self.added_groups[group_name]
                self.remove_group(group_name, widget_to_remove)

        for group_name, widget in self.added_groups.items():
            members = self.core.multi_groups.get(group_name, [])
            widget.populate_data(group_name, members)

    def retranslate_ui(self):
        from core.logic.language_manager import LanguageManager
        LanguageManager.translate_ui(self)
        for group_widget in self.added_groups.values():
            group_widget.retranslate_ui()
