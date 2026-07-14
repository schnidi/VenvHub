#----------------------------------------
# Súbor: core/logic/button/pip/pip_command_worker.py
#----------------------------------------

import os
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal
from core.logic.birth_certificate import BirthCertificateGenerator
from core.logic.language_manager import LanguageManager

class PipCommandWorker(QObject):
    """
    Univerzálny worker, ktorý na pozadí spustí ľubovoľný príkaz
    (dostane ho už poskladaný z Factory) a priebežne posiela výstup.
    """
    started = pyqtSignal()
    output_line = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, venv_path, full_command):
        super().__init__()
        self.venv_path = venv_path
        # Očakáva komplet zoznam, napr. ['uv', 'pip', 'install', 'numpy', '--python', '...']
        self.full_command = full_command 

    def run(self):
        try:
            self.started.emit()
            
            process = subprocess.Popen(
                self.full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for line in process.stdout:
                self.output_line.emit(line.strip())

            process.wait()

            if process.returncode == 0:
                BirthCertificateGenerator.update_venv_certificate(self.venv_path)
            
            self.finished.emit(process.returncode)

        except Exception as e:
            err_msg = LanguageManager.get("pip_worker_err_critical", "Nastala kritická chyba pri spúšťaní príkazu: {error}").format(error=e)
            self.error.emit(err_msg)