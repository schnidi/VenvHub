from core.logic.pip_manager import PipManager

class WidgetPipHandler:
    @staticmethod
    def run_install(parent):
        """parent je ProjectMiniBar"""
        venv_path = parent.core.active_venv_path
        pkg = parent.settings_widget.edit_pkg.text().strip()
        log = parent.settings_widget.log_output

        if pkg:
            PipManager.install_package(venv_path, pkg, log)
            parent.settings_widget.edit_pkg.clear()