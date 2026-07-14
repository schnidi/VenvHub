#----------------------------------------
# Súbor: core/logic/py_installer/worker.py
#----------------------------------------

import subprocess
import os
from PyQt6.QtCore import QThread, pyqtSignal
from core.logic.language_manager import LanguageManager

class PyInstallerWorker(QThread):
    log_signal = pyqtSignal(str)      # Posiela text do logu
    finished_signal = pyqtSignal(bool) # Posiela info o úspechu/zlyhaní

    # PRIDANÉ: project_path do parametrov
    def __init__(self, command_list, project_path):
        super().__init__()
        self.command_list = command_list
        self.project_path = project_path
        self.process = None

    def run(self):
        try:
            # Flag pre skrytie CMD okna na Windows (aby to bežalo len v našom logu)
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = 0x08000000  # CREATE_NO_WINDOW

            self.log_signal.emit(LanguageManager.get("msg_starting_command", "🚀 Spúšťam príkaz:\n{0}\n").format(' '.join(self.command_list)))
            self.log_signal.emit("-" * 50)

            # Spustenie procesu
            self.process = subprocess.Popen(
                self.command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Chyby presmerujeme do hlavného výstupu
                text=True,
                creationflags=creation_flags,
                encoding='utf-8',
                errors='replace',
                cwd=self.project_path  # PRIDANÉ: Pracovný adresár projektu
            )

            # Čítanie výstupu v reálnom čase
            for line in self.process.stdout:
                self.log_signal.emit(line.strip())

            self.process.wait()
            
            success = (self.process.returncode == 0)
            if success:
                self.log_signal.emit(LanguageManager.get("msg_build_success", "\n✅ BUILD DOKONČENÝ ÚSPEŠNE."))
            else:
                self.log_signal.emit(LanguageManager.get("msg_build_failed", "\n❌ BUILD ZLYHAL (Kód: {0})").format(self.process.returncode))

            self.finished_signal.emit(success)

        except Exception as e:
            self.log_signal.emit(LanguageManager.get("msg_critical_launch_err", "\nKRITICKÁ CHYBA PRI SPÚŠŤANÍ: {0}").format(str(e)))
            self.finished_signal.emit(False)

    def kill(self):
        if self.process:
            try:
                self.process.kill()
            except:
                pass