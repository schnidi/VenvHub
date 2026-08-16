#----------------------------------------
# Súbor: tests/test_apt_listener.py
# Komplexný test pre core/logic/sluzby/apt_listener.py
# 100% KÓDOVÉ POKRYTIE
#----------------------------------------

import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# 1. AUTOMATICKÉ PRIDANIE KOREŇOVÉHO ADRESÁRA PROJEKTU DO sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. INICIALIZÁCIA QT MOSTA
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()

# 3. NASTAVENIE BEZHLAVÉHO REŽIMU PRE QT
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# 4. IMPORTY
from core.logic.sluzby.apt_listener import AptListener
from core.logic.sluzby.apt_logic import AptLogic


class TestAptListenerReverseDependencies(unittest.TestCase):
    """Testy pre AptListener a kontrolu reverzných závislostí vrátane Linkeru."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.venv_path = os.path.join(self.temp_dir, "test_venv")
        
        site_folder = "Lib" if os.name == 'nt' else "lib"
        self.site_packages = os.path.join(self.venv_path, site_folder, "site-packages")
        os.makedirs(self.site_packages, exist_ok=True)
        
        self.mock_core = MagicMock()
        self.mock_core.package_manager = "pip"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_packages_from_install_and_uninstall_cmd(self):
        """Test vytiahnutia názvov balíčkov z install/uninstall príkazov."""
        cmd_install = ["python", "-m", "pip", "install", "requests", "colorama>=0.4.6", "--upgrade"]
        extracted_ins = AptListener._extract_packages_from_install_cmd(cmd_install)
        self.assertIn("requests", extracted_ins)
        self.assertIn("colorama", extracted_ins)

        cmd_uninstall = ["python", "-m", "pip", "uninstall", "-y", "pytest", "colorama"]
        extracted_un = AptListener._extract_packages_from_uninstall_cmd(cmd_uninstall)
        self.assertIn("pytest", extracted_un)
        self.assertIn("colorama", extracted_un)

    @patch.object(AptLogic, "get_dependency_graph")
    def test_is_package_required_by_pip_and_linker_combined(self, mock_get_graph):
        """Test detekcie kombinovaných závislostí: PIP (pytest) + Linker (My Logger)."""
        mock_get_graph.return_value = {
            "pytest": ["colorama"],
            "colorama": []
        }

        linker_pkg_path = os.path.join(self.temp_dir, "my_logger_pkg")
        os.makedirs(linker_pkg_path, exist_ok=True)
        meta_content = {"name": "My Logger", "requires_pip": ["colorama"]}
        with open(os.path.join(linker_pkg_path, "local_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta_content, f)

        venvhub_data = {"my_logger": linker_pkg_path}
        with open(os.path.join(self.site_packages, "venvhub.json"), "w", encoding="utf-8") as f:
            json.dump(venvhub_data, f)

        deps = AptListener._is_package_required_by_others(self.venv_path, self.mock_core, "colorama")
        
        self.assertIn("pytest", deps)
        self.assertIn("My Logger (Linker)", deps)
        self.assertEqual(len(deps), 2)


class TestAptListenerFullCoverage(unittest.TestCase):
    """Komplexný test pre všetky metódy a patchovanie v AptListener."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.venv_path = os.path.join(self.temp_dir, "test_venv")
        
        site_folder = "Lib" if os.name == 'nt' else "lib"
        self.site_packages = os.path.join(self.venv_path, site_folder, "site-packages")
        os.makedirs(self.site_packages, exist_ok=True)
        
        self.mock_core = MagicMock()
        self.mock_core.package_manager = "pip"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_packages_from_commands(self):
        """Test extrakcie názvov balíčkov z príkazu na inštaláciu a odinštaláciu."""
        cmd_in = ["python", "-m", "pip", "install", "requests>=2.0", "colorama"]
        extracted_in = AptListener._extract_packages_from_install_cmd(cmd_in)
        self.assertEqual(extracted_in, ["requests", "colorama"])

        cmd_un = ["python", "-m", "pip", "uninstall", "-y", "pytest", "flask"]
        extracted_un = AptListener._extract_packages_from_uninstall_cmd(cmd_un)
        self.assertEqual(extracted_un, ["pytest", "flask"])

    @patch("subprocess.run")
    @patch("core._path.Paths.get_venv_python_exe_path")
    def test_get_editable_packages(self, mock_exe, mock_run):
        """Test načítania editable balíčkov pomocou mockovania subprocess."""
        mock_exe.return_value = os.path.join(self.temp_dir, "python.exe")
        
        with open(mock_exe.return_value, "w") as f:
            f.write("")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps([{"name": "my-editable-pkg", "version": "0.1.0"}])
        mock_run.return_value = mock_process

        res = AptListener._get_editable_packages(self.venv_path)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "my-editable-pkg")

    @patch("core.logic.commands.command_factory.PackageManagerFactory.get_dispatcher")
    @patch("subprocess.run")
    def test_get_requires_for_package(self, mock_run, mock_get_dispatcher):
        """Test vyčítania 'Requires:' z pip show príkazu."""
        mock_dispatcher = MagicMock()
        mock_dispatcher.get.return_value = ["python", "-m", "pip", "show", "pytest"]
        mock_get_dispatcher.return_value = mock_dispatcher

        mock_process = MagicMock()
        mock_process.stdout = "Name: pytest\nVersion: 8.0\nRequires: colorama, iniconfig, pluggy\n"
        mock_run.return_value = mock_process

        reqs = AptListener._get_requires_for_package(self.venv_path, "pytest", "pip")
        self.assertEqual(reqs, ["colorama", "iniconfig", "pluggy"])

    @patch.object(AptLogic, "get_dependency_graph")
    def test_is_package_required_by_pip_and_linker_combined(self, mock_get_graph):
        """Druhý test detekcie blokovania (pôvodný duplikát z FullCoverage)."""
        mock_get_graph.return_value = {
            "pytest": ["colorama"],
            "colorama": []
        }

        linker_pkg_path = os.path.join(self.temp_dir, "my_logger_pkg")
        os.makedirs(linker_pkg_path, exist_ok=True)
        meta_content = {"name": "My Logger", "requires_pip": ["colorama"]}
        with open(os.path.join(linker_pkg_path, "local_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta_content, f)

        venvhub_data = {"my_logger": linker_pkg_path}
        with open(os.path.join(self.site_packages, "venvhub.json"), "w", encoding="utf-8") as f:
            json.dump(venvhub_data, f)

        deps = AptListener._is_package_required_by_others(self.venv_path, self.mock_core, "colorama")
        
        self.assertIn("pytest", deps)
        self.assertIn("My Logger (Linker)", deps)
        self.assertEqual(len(deps), 2)

    def test_start_listening_and_pip_e_uninstall_blocked(self):
        """Test zapnutia načúvania a zablokovania odinštalácie v PipEUninstallWorker."""
        AptListener.start_listening(self.mock_core)
        
        from core.logic.pip_e import PipEUninstallWorker

        worker = PipEUninstallWorker.__new__(PipEUninstallWorker)
        worker.venv_path = self.venv_path
        worker.package_name = "colorama"
        worker.log_msg = MagicMock()
        worker.finished = MagicMock()

        with patch.object(AptListener, "_is_package_required_by_others", return_value=["pytest"]):
            worker.run()
            worker.log_msg.emit.assert_called_once()
            worker.finished.emit.assert_called_with(False)

    @patch("core.logic.sluzby.apt_logic.AptLogic.mark_as_explicit")
    @patch("core.logic.sluzby.apt_logic.AptLogic.autoremove")
    def test_pip_manager_patch_callbacks(self, mock_autoremove, mock_mark):
        """Test, či PipManager po dokončení inštalácie správne updatuje APT logiku."""
        from core.logic.pip_manager import PipManager
        AptListener.start_listening(self.mock_core)

        mock_worker = MagicMock()
        mock_worker.cmd = ["python", "-m", "pip", "install", "requests"]
        mock_worker.venv_path = self.venv_path
        mock_worker.success = True
        mock_log = MagicMock()

        PipManager._run_pip_task(mock_worker, mock_log)
        mock_worker.signals.finished.connect.call_args[0][0]()

        mock_mark.assert_called_with(self.venv_path, "requests")
        mock_autoremove.assert_not_called()

    @patch("PyQt6.QtWidgets.QMessageBox.warning")
    @patch("core.logic.sluzby.apt_listener.AptListener._is_package_required_by_others")
    def test_pip_package_widget_blocked_uninstall(self, mock_is_required, mock_warning):
        """Test zablokovania odinštalácie v GUI (PipPackageWidget)."""
        from windows.pip_package_widget import PipPackageWidget
        AptListener.start_listening(self.mock_core)

        mock_is_required.return_value = ["dependent-package"]

        mock_widget = MagicMock()
        mock_widget.venv_path = self.venv_path

        PipPackageWidget.run_pip_command(
            mock_widget, 
            ["python", "-m", "pip", "uninstall", "-y", "requests"], 
            "Start"
        )

        mock_warning.assert_called_once()
        self.assertIn("Nemožno odinštalovať", mock_warning.call_args[0][2])

    @patch("core.logic.sluzby.apt_logic.AptLogic.install_sync")
    def test_pipe_install_sync_callback(self, mock_sync):
        """Test, či Pip-E inštalácia po úspechu synchronizuje APT."""
        from core.logic.pip_e import PipEInstallWorker
        AptListener.start_listening(self.mock_core)

        worker = PipEInstallWorker.__new__(PipEInstallWorker)
        worker.finished = MagicMock()
        worker.__init__(self.venv_path, "target/path")

        worker.finished.connect.call_args[0][0](True)
        mock_sync.assert_called_once_with(self.mock_core, self.venv_path, worker.log_msg.emit)

    @patch("core.logic.sluzby.apt_logic.AptLogic.autoremove")
    def test_local_linker_patch_autoremove(self, mock_autoremove):
        """Test, či zrušenie linkovania lokálneho balíčka spustí autoremove sirokov."""
        from core.logic.button.manager.local_packages_linker import LocalPackagesLinker
        
        mock_linker_ui = MagicMock()
        mock_linker_ui.core = self.mock_core
        mock_linker_ui.venv_path = self.venv_path
        mock_linker_ui.parent._get_linked_packages.return_value = ["old_pkg"]

        pkg_dir = os.path.join(self.temp_dir, "old_pkg")
        os.makedirs(pkg_dir)
        self.mock_core.local_packages_root = self.temp_dir
        with open(os.path.join(pkg_dir, "local_meta.json"), "w") as f:
            json.dump({"requires_pip": ["colorama"]}, f)

        selected_items_data = [{"name": "new_pkg"}]

        with patch.object(LocalPackagesLinker, 'apply_changes', return_value=True):
            AptListener.start_listening(self.mock_core)
            LocalPackagesLinker.apply_changes(mock_linker_ui, selected_items_data)

        mock_autoremove.assert_called_once()
        self.assertEqual(mock_autoremove.call_args[1]['released_packages'], ["colorama"])


if __name__ == "__main__":
    unittest.main(verbosity=2)