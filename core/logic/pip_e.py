#----------------------------------------
# Súbor: core/logic/pip_e.py
#----------------------------------------

import os
import json
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

from core._path import Paths
from core.logic.language_manager import LanguageManager
from core.logic.birth_certificate import BirthCertificateGenerator

CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

class PipEListWorker(QObject):
    """
    Asynchrónny Worker pre načítanie zoznamu editovateľných balíčkov.
    """
    log_msg = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(list) # Vracia zoznam slovníkov s dátami o balíčkoch

    def __init__(self, venv_path):
        super().__init__()
        self.venv_path = venv_path

    def run(self):
        try:
            python_exe = Paths.get_venv_python_exe_path(self.venv_path)
            if not os.path.exists(python_exe):
                err_msg = LanguageManager.get("pipe_err_no_python", "❌ Python executable nebol nájdený: {0}").format(python_exe)
                self.error.emit(err_msg)
                self.finished.emit([])
                return

            self.log_msg.emit(LanguageManager.get("pipe_log_loading", "🔄 Načítavam zoznam editovateľných balíčkov (pip list --editable)..."))
            
            cmd = [python_exe, "-m", "pip", "list", "--editable", "--format=json"]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding="utf-8", 
                errors="replace",
                creationflags=CREATE_NO_WINDOW
            )

            if result.returncode != 0:
                err_msg = LanguageManager.get("pipe_err_list_failed", "❌ Zlyhalo načítanie zoznamu: {0}").format(result.stderr)
                self.error.emit(err_msg)
                self.finished.emit([])
                return

            # Spracovanie JSON výstupu
            output = result.stdout.strip()
            if output:
                try:
                    packages = json.loads(output)
                    self.log_msg.emit(LanguageManager.get("pipe_log_loaded_count", "✅ Načítaných {0} editovateľných balíčkov.").format(len(packages)))
                    self.finished.emit(packages)
                except json.JSONDecodeError as e:
                    self.error.emit(LanguageManager.get("pipe_err_json_parse", "❌ Chyba pri spracovaní JSON výstupu: {0}").format(e))
                    self.finished.emit([])
            else:
                self.log_msg.emit(LanguageManager.get("pipe_log_no_packages", "ℹ️ V tomto prostredí nie sú nainštalované žiadne editovateľné balíčky."))
                self.finished.emit([])

        except Exception as e:
            self.error.emit(LanguageManager.get("pipe_err_critical", "❌ Kritická chyba: {0}").format(e))
            self.finished.emit([])


class PipEInstallWorker(QObject):
    """
    Asynchrónny Worker pre inštaláciu priečinka v režime vývoja (pip install -e).
    """
    log_msg = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(bool) # Vracia True ak úspech, inak False

    def __init__(self, venv_path, target_path):
        super().__init__()
        self.venv_path = venv_path
        self.target_path = target_path

    def run(self):
        try:
            python_exe = Paths.get_venv_python_exe_path(self.venv_path)
            if not os.path.exists(python_exe):
                self.error.emit(LanguageManager.get("pipe_err_no_python", "❌ Python executable nebol nájdený: {0}").format(python_exe))
                self.finished.emit(False)
                return

            # 1. Prísna validácia cieľového priečinka (pip -e vyžaduje setup.py alebo pyproject.toml)
            has_setup = os.path.exists(os.path.join(self.target_path, "setup.py"))
            has_toml = os.path.exists(os.path.join(self.target_path, "pyproject.toml"))
            
            if not has_setup and not has_toml:
                err_msg = LanguageManager.get("pipe_err_invalid_folder", "⚠️ Priečinok '{0}' neobsahuje súbor 'setup.py' ani 'pyproject.toml'. Inštalácia nie je možná.").format(os.path.basename(self.target_path))
                self.error.emit(err_msg)
                self.finished.emit(False)
                return

            # =====================================================================
            # FIX PRE EMBED PYTHON: Predinštalácia build nástrojov
            # =====================================================================
            self.log_msg.emit("🛠 Zabezpečujem build nástroje (setuptools, wheel)...")
            subprocess.run(
                [python_exe, "-m", "pip", "install", "setuptools", "wheel"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW
            )

            # =====================================================================
            # Spustenie inštalácie s VYPNNUTOU IZOLÁCIOU (--no-build-isolation)
            # =====================================================================
            cmd = [python_exe, "-m", "pip", "install", "-e", self.target_path, "--no-build-isolation"]
            
            self.log_msg.emit(LanguageManager.get("pipe_log_installing", "\n⚡ Spúšťam inštaláciu vývojového balíčka: pip install -e {0}").format(os.path.basename(self.target_path)))
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Smerujeme aj errory do štandardného výstupu
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=CREATE_NO_WINDOW
            )

            for line in iter(process.stdout.readline, ''):
                clean_line = line.strip()
                if clean_line:
                    self.log_msg.emit(f"  {clean_line}")

            process.wait()

            # Vyhodnotenie a aktualizácia rodného listu
            success = (process.returncode == 0)
            if success:
                self.log_msg.emit(LanguageManager.get("pipe_log_install_success", "✅ Balíček úspešne prelinkovaný (pip -e)."))
                # Aktualizujeme rodný list, keďže do venvu pribudol záznam
                BirthCertificateGenerator.update_venv_certificate(self.venv_path)
            else:
                self.error.emit(LanguageManager.get("pipe_err_install_failed", "❌ Inštalácia zlyhala s kódom {0}.").format(process.returncode))

            self.finished.emit(success)

        except Exception as e:
            self.error.emit(LanguageManager.get("pipe_err_critical", "❌ Kritická chyba: {0}").format(e))
            self.finished.emit(False)


class PipEUninstallWorker(QObject):
    """
    Asynchrónny Worker pre odinštalovanie editovateľného balíčka.
    """
    log_msg = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, venv_path, package_name):
        super().__init__()
        self.venv_path = venv_path
        self.package_name = package_name

    def run(self):
        try:
            python_exe = Paths.get_venv_python_exe_path(self.venv_path)
            if not os.path.exists(python_exe):
                self.error.emit(LanguageManager.get("pipe_err_no_python", "❌ Python executable nebol nájdený: {0}").format(python_exe))
                self.finished.emit(False)
                return

            cmd = [python_exe, "-m", "pip", "uninstall", "-y", self.package_name]
            
            self.log_msg.emit(LanguageManager.get("pipe_log_uninstalling", "\n🗑️ Odinštalujem balíček '{0}'...").format(self.package_name))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=CREATE_NO_WINDOW
            )

            for line in iter(process.stdout.readline, ''):
                clean_line = line.strip()
                if clean_line:
                    self.log_msg.emit(f"  {clean_line}")

            process.wait()

            success = (process.returncode == 0)
            if success:
                self.log_msg.emit(LanguageManager.get("pipe_log_uninstall_success", "✅ Balíček '{0}' bol úspešne odstránený.").format(self.package_name))
                BirthCertificateGenerator.update_venv_certificate(self.venv_path)
            else:
                self.error.emit(LanguageManager.get("pipe_err_uninstall_failed", "❌ Odinštalácia zlyhala s kódom {0}.").format(process.returncode))

            self.finished.emit(success)

        except Exception as e:
            self.error.emit(LanguageManager.get("pipe_err_critical", "❌ Kritická chyba: {0}").format(e))
            self.finished.emit(False)