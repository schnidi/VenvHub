# ----------------------------------------
# Súbor: core/logic/button/manager/create.py (OPRAVENÁ VERZIA)
# ----------------------------------------

import os
import subprocess
import re
import json
from datetime import datetime
from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from core.logic.language_manager import LanguageManager
from windows.progress_dialog import ProgressDialog
from core._path import Paths
from core.logic.vs_code_json import VSCodeIntegration
from core.logic.birth_certificate import BirthCertificateGenerator
from core.logic.sluzby.sanitize_venv_name import sanitize_venv_name

LOGGING_ENABLED = False


def write_to_debug_file(message):
    if not LOGGING_ENABLED:
        return
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        log_file = os.path.join(desktop, "VENV_DEBUG_LOG.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')}] {message}\n")
    except Exception:
        pass


class VenvCreatorWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress_log = pyqtSignal(str)

    def __init__(
        self,
        python_exe,
        venv_path,
        is_local=False,
        is_portable=True,
        project_name="",
        parent_py_path="",
    ):
        super().__init__()
        self.python_exe = os.path.normpath(python_exe)
        self.venv_path = os.path.normpath(venv_path)
        self.is_local = is_local
        self.is_portable = is_portable
        self.project_name = project_name
        self.parent_py_path = parent_py_path
        self.is_running = True

    def _get_python_version_short(self):
        try:
            res = subprocess.run(
                [self.python_exe, "--version"],
                capture_output=True,
                text=True,
                creationflags=0x08000000,
            )
            version_str = res.stdout.strip() or res.stderr.strip()
            match = re.search(r"Python (\d+)\.(\d+)", version_str)
            if match:
                return f"{match.group(1)}{match.group(2)}"
        except Exception as e:
            write_to_debug_file(f"Nepodarilo sa zistiť verziu Pythonu: {e}")
        return "312"

    def _fix_pth_file(self):
        ver_short = self._get_python_version_short()
        pth_filename = f"python{ver_short}._pth"
        scripts_dir = os.path.join(self.venv_path, "Scripts")
        pth_path = os.path.join(scripts_dir, pth_filename)

        if not os.path.exists(pth_path):
            try:
                content = (
                    f"python{ver_short}.zip\n.\n..\n..\\Lib\\site-packages\nimport"
                    " site\n"
                )
                with open(pth_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                write_to_debug_file(f"CHYBA pri vytváraní ._pth: {e}")

    def _verify_pip_functional(self):
        pip_exe = os.path.join(self.venv_path, "Scripts", "pip.exe")
        if not os.path.exists(pip_exe):
            return False
        try:
            res = subprocess.run(
                [pip_exe, "--version"],
                capture_output=True,
                text=True,
                creationflags=0x08000000,
            )
            return res.returncode == 0
        except Exception:
            return False

    def run(self):
        CREATE_NO_WINDOW = 0x08000000
        write_to_debug_file(
            f"\nŠTART PROCESU: {self.python_exe} -> {self.venv_path}"
        )

        # OPRAVA č.2: Namiesto sterilného slovníka zoberieme kópiu systému
        # a iba prebijeme premenné, ktoré by mohli venvu podstrčiť cudzí PYTHONPATH
        clean_env = os.environ.copy()
        clean_env.pop("PYTHONPATH", None)
        clean_env.pop("PYTHONHOME", None)
        clean_env["PATH"] = ";".join([
            os.path.join(
                os.environ.get("SystemRoot", "C:\\Windows"), "System32"
            ),
            os.path.dirname(self.python_exe),
            clean_env.get("PATH", ""),
        ])

        try:
            if self.is_local:
                self.progress_log.emit(
                    LanguageManager.get(
                        "msg_create_step1_virtualenv",
                        "Krok 1: Spúšťam virtualenv...",
                    )
                )
                command = [
                    self.python_exe,
                    "-I",
                    "-B",
                    "-m",
                    "virtualenv",
                    "--no-download",
                    self.venv_path,
                ]

                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                    env=clean_env,
                    cwd=os.path.dirname(self.python_exe),
                )

                if result.returncode != 0:
                    raise RuntimeError(
                        f"virtualenv zlyhal s kódom {result.returncode}:\n"
                        f"{result.stderr}"
                    )

                self.progress_log.emit(
                    LanguageManager.get(
                        "msg_create_step2_pth",
                        "Krok 2: Opravujem konfiguráciu (._pth)...",
                    )
                )
                self._fix_pth_file()

                self.progress_log.emit(
                    LanguageManager.get(
                        "msg_create_step3_pip",
                        "Krok 3: Overujem funkčnosť PIP...",
                    )
                )
                if not self._verify_pip_functional():
                    raise RuntimeError(
                        "PIP bol vytvorený, ale nefunguje (Access Violation)."
                    )

            else:
                self.progress_log.emit(
                    LanguageManager.get(
                        "msg_create_standard_venv", "Metóda: Štandardný venv..."
                    )
                )
                command = [self.python_exe, "-m", "venv", self.venv_path]

                # OPRAVA č.1: Pridané capture_output=True proti zamrznutiu v --noconsole
                res = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                    env=clean_env,
                )
                if res.returncode != 0:
                    raise RuntimeError(
                        f"venv zlyhal s kódom {res.returncode}:\n{res.stderr}"
                    )

            # OPRAVA č.4: Rodný list generujeme priamo tu na pozadí!
            # Keď Windows Defender zasekne pip list na 5 sekúnd, GUI zostane plynulé.
            self.progress_log.emit(
                LanguageManager.get(
                    "msg_create_cert", "Zapisujem rodný list prostredia..."
                )
            )
            new_venv_python = Paths.get_venv_python_exe_path(self.venv_path)
            folder_name = os.path.basename(self.venv_path)

            BirthCertificateGenerator.create_venv_certificate(
                project_name=self.project_name,
                venv_name=folder_name,
                venv_path=self.venv_path,
                python_exe=new_venv_python,
                source_python_path=self.parent_py_path,
            )
            BirthCertificateGenerator.update_venv_certificate(self.venv_path)

            self.progress_log.emit(
                LanguageManager.get(
                    "msg_create_ok", "Všetko v poriadku, prostredie je aktívne."
                )
            )
            self.finished.emit()

        except Exception as e:
            write_to_debug_file(f"KRITICKÁ CHYBA: {str(e)}")
            self.error.emit(str(e))
        finally:
            self.is_running = False


class VenvCreationBridge(QObject):
    success_signal = pyqtSignal()
    error_signal = pyqtSignal(str)


class CreateVenvHandler:
    _thread = None
    _worker = None

    @staticmethod
    def run(parent, core, py_list):
        if not core.active_project:
            QMessageBox.warning(
                parent,
                LanguageManager.get("title_error", "Chyba"),
                LanguageManager.get("err_select_project", "Vyberte projekt."),
            )
            return

        venv_name, ok = QInputDialog.getText(
            parent,
            LanguageManager.get("title_new_venv", "Nové prostredie"),
            LanguageManager.get("msg_venv_name_for", "Meno pre '{0}':").format(
                core.active_project
            ),
        )

        raw_venv_name = venv_name.strip()
        if not ok or not raw_venv_name:
            return

        safe_venv_name = sanitize_venv_name(raw_venv_name)
        folder_name = f"{core.active_project}_{safe_venv_name}"
        full_path = Paths.get_venv_path(core.venv_hub_root, folder_name)

        if os.path.exists(full_path):
            QMessageBox.warning(
                parent,
                LanguageManager.get("title_error", "Chyba"),
                LanguageManager.get(
                    "msg_venv_exists_simple", "Venv už existuje."
                ),
            )
            return

        selected_idx = parent.combo_py.currentIndex()
        python_exe = py_list[selected_idx]["path"]
        is_local = "[Local]" in py_list[selected_idx]["display"]

        parent_py_path = python_exe
        if is_local:
            app_root = Paths.get_app_root_path()
            try:
                rel_path = os.path.relpath(python_exe, app_root)
                parent_py_path = f"[REL_TO_APP]/{rel_path}".replace("\\", "/")
            except ValueError:
                pass

        progress_dialog = ProgressDialog(parent)
        progress_dialog.set_message(
            LanguageManager.get(
                "msg_creating_venv", "Vytváram venv: {0}..."
            ).format(safe_venv_name)
        )

        CreateVenvHandler._thread = QThread()
        CreateVenvHandler._worker = VenvCreatorWorker(
            python_exe,
            full_path,
            is_local,
            core.is_portable,
            project_name=core.active_project,
            parent_py_path=parent_py_path,
        )
        CreateVenvHandler._worker.moveToThread(CreateVenvHandler._thread)

        CreateVenvHandler._thread.started.connect(CreateVenvHandler._worker.run)
        CreateVenvHandler._worker.progress_log.connect(
            progress_dialog.add_log_message
        )

        # OPRAVA č.3: Korektné upratanie vlákna pri úspechu AJ pri chybe
        CreateVenvHandler._worker.finished.connect(
            CreateVenvHandler._thread.quit
        )
        CreateVenvHandler._worker.finished.connect(
            CreateVenvHandler._worker.deleteLater
        )
        CreateVenvHandler._worker.error.connect(CreateVenvHandler._thread.quit)
        CreateVenvHandler._worker.error.connect(
            CreateVenvHandler._worker.deleteLater
        )
        CreateVenvHandler._thread.finished.connect(
            CreateVenvHandler._thread.deleteLater
        )

        def on_success():
            progress_dialog.accept()
            try:
                project_path = Paths.get_project_path(
                    getattr(core, "projects_root", ""), core.active_project
                )
                VSCodeIntegration.initialize_project_settings(
                    project_path, full_path
                )
            except Exception as e:
                QMessageBox.critical(
                    parent,
                    LanguageManager.get("title_vscode_error", "Chyba VS Code"),
                    LanguageManager.get(
                        "msg_vscode_config_failed",
                        "Zápis konfigurácie pre VS Code zlyhal:\n{0}",
                    ).format(str(e)),
                )

            parent.refresh_table()

        def on_error(msg):
            progress_dialog.reject()
            QMessageBox.critical(
                parent,
                LanguageManager.get("title_error", "Chyba"),
                LanguageManager.get(
                    "msg_create_failed_log_desktop",
                    "Zlyhanie pri tvorbe prostredia:\n\n{0}",
                ).format(msg),
            )

        bridge = VenvCreationBridge(parent)
        bridge.success_signal.connect(on_success)
        bridge.error_signal.connect(on_error)

        CreateVenvHandler._worker.finished.connect(bridge.success_signal)
        CreateVenvHandler._worker.error.connect(bridge.error_signal)

        CreateVenvHandler._thread.start()
        progress_dialog.exec()