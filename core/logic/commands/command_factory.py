#----------------------------------------
# Súbor: core/logic/commands/command_factory.py
#----------------------------------------

from core.logic.commands.pip_commands import PipCommandDispatcher
from core.logic.commands.uv_commands import UvCommandDispatcher

class PackageManagerFactory:
    """
    Rozhodne, ktorú triedu dispečera má aplikácia použiť, 
    na základe zvoleného balíčkovacieho manažéra v nastaveniach.
    """
    
    @staticmethod
    def get_dispatcher(manager_type: str, venv_path: str):
        if manager_type == "uv":
            return UvCommandDispatcher(venv_path)
        else:
            return PipCommandDispatcher(venv_path)