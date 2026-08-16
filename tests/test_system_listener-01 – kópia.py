#----------------------------------------
# Súbor: tests/test_system_listener.py
# Komplexný jednotkový a integračný test pre core/logic/system_listener.py
# Podporuje PyQt6 aj PySide6 (cez most pyqt_to_pyside.py)
# 100% KÓDOVÉ POKRYTIE (COVERAGE)
#----------------------------------------

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# 1. AUTOMATICKÉ PRIDANIE KOREŇOVÉHO ADRESÁRA PROJEKTU DO sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. INICIALIZÁCIA QT MOSTA (Preklad PyQt6 -> PySide6 pre prostredie bez PyQt6)
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()

# 3. NASTAVENIE BEZHLAVÉHO REŽIMU PRE QT (Headless Mode)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# 4. IMPORT QT A SÚVISIACICH MODULOV (Po aktivácii Mosta)
from PyQt6.QtWidgets import QApplication, QMessageBox
from core._path import Paths
import core.logic.system_listener as sl
from core.logic.system_listener import (
    normalize_venv_name,
    get_machine_id,
    is_portable_mode,
    is_system_venv,
    get_embedinstall_config_path,
    _log_config_error,
    _load_config_cache,
    _save_config_cache,
    _preload_cache_async,
    verify_access,
    show_blocked_warning,
    SystemListener
)
from core.logic.sluzby.apt_listener import AptListener
from core.logic.sluzby.apt_logic import AptLogic

# Inicializácia QApplication pre testy s GUI (QMessageBox)
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestSystemListenerHelperFunctions(unittest.TestCase):
    """Testy pre samostatné pomocné funkcie v system_listener.py."""

    def setUp(self):
        sl._MACHINE_ID_CACHE = None
        sl._CONFIG_CACHE = None

    def test_normalize_venv_name(self):
        """Testovanie robustného čistenia a normalizácie názvov venvov."""
        self.assertEqual(normalize_venv_name(None), "")
        self.assertEqual(normalize_venv_name(""), "")
        self.assertEqual(normalize_venv_name("   "), ".")
        
        self.assertEqual(normalize_venv_name(r"C:\Users\Test\My Venv\ "), "my venv")
        self.assertEqual(normalize_venv_name("/home/user/Project/VENV/"), "venv")
        
        nfd_name = "Ve\u0301nv_S\u030cku\u0301s\u030cka"
        nfc_name = "vénv_škúška"
        self.assertEqual(normalize_venv_name(nfd_name), nfc_name)

    def test_get_machine_id_and_caching(self):
        """Test generovania SHA-256 podpisu a pamäťovej cache."""
        machine_id1 = get_machine_id()
        self.assertIsInstance(machine_id1, str)
        self.assertEqual(len(machine_id1), 64)

        machine_id2 = get_machine_id()
        self.assertEqual(machine_id1, machine_id2)

    @patch("os.name", "nt")
    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_get_machine_id_windows_registry(self, mock_query, mock_open_key):
        """Test čítania Windows registrov pre machine_id."""
        mock_query.return_value = ("TEST-GUID-12345", 1)
        machine_id = get_machine_id()
        self.assertIsInstance(machine_id, str)

    def test_is_portable_mode(self):
        """Test detekcie portable režimu pomocou súborového markera."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(Paths, 'get_app_root_path', return_value=temp_dir):
                self.assertFalse(is_portable_mode())
                
                marker_path = os.path.join(temp_dir, Paths.PORTABLE_MARKER_FILENAME)
                with open(marker_path, "w") as f:
                    f.write("1")
                
                self.assertTrue(is_portable_mode())

    def test_is_system_venv(self):
        """Test identifikácie Systémového vs. Virtualenv/Embed Venvu."""
        self.assertFalse(is_system_venv(""))
        self.assertFalse(is_system_venv("/non/existent/path"))

        with tempfile.TemporaryDirectory() as temp_dir:
            cfg_path = os.path.join(temp_dir, "pyvenv.cfg")
            
            # 1. Systémový venv (neobsahuje slovo 'virtualenv')
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("home = C:\\Python310\ninclude-system-site-packages = false\n")
            self.assertTrue(is_system_venv(temp_dir))

            # 2. Virtualenv / Embed venv (obsahuje slovo 'virtualenv')
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("home = C:\\Python310\nvirtualenv = 20.4.0\n")
            self.assertFalse(is_system_venv(temp_dir))

    def test_get_embedinstall_config_path(self):
        """Test správneho zostavenia cesty k portable_system_py.json."""
        with patch.object(Paths, 'get_config_file_path', return_value=os.path.join("C:", "app", "config.json")):
            path = get_embedinstall_config_path()
            self.assertTrue(path.endswith("portable_system_py.json"))


class TestConfigCacheAndAtomicWrite(unittest.TestCase):
    """Testy pre atomický zápis, čítanie a chybové logovanie portable_system_py.json."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "portable_system_py.json")
        sl._CONFIG_CACHE = None

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_config_error(self):
        """Test bezpečného logovania bez zhodenia aplikácie."""
        with patch("core.logic.system_listener.get_embedinstall_config_path", return_value=self.config_path):
            _log_config_error("test_action", Exception("Test Error"))
            log_file = os.path.join(self.temp_dir, "system_listener_errors.log")
            self.assertTrue(os.path.exists(log_file))
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("test_action", content)
                self.assertIn("Test Error", content)

    def test_log_config_error_resilience(self):
        """DOPLNENÉ: Test, že chyba v samotnom logovaní nespôsobí pád aplikácie."""
        with patch("core.logic.system_listener.get_embedinstall_config_path", side_effect=Exception("Fatal Error")):
            try:
                _log_config_error("test_action", Exception("Test Error"))
            except Exception as e:
                self.fail(f"_log_config_error vyhodil výnimku, hoci mal zlyhať potichu: {e}")

    def test_load_and_save_config_cache(self):
        """Test načítania, atomického zápisu a pamäťovej cache."""
        with patch("core.logic.system_listener.get_embedinstall_config_path", return_value=self.config_path):
            data = _load_config_cache()
            self.assertEqual(data, {})

            new_data = {"test_venv": "1234567890abcdef"}
            _save_config_cache(new_data)
            
            self.assertTrue(os.path.exists(self.config_path))
            with open(self.config_path, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            self.assertEqual(disk_data, new_data)
            self.assertEqual(_load_config_cache(), new_data)

    def test_load_corrupted_config(self):
        """Test správania pri poškodenom JSON súbore (Fail-Open)."""
        with patch("core.logic.system_listener.get_embedinstall_config_path", return_value=self.config_path):
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write("{ invalid json content ...")
            
            data = _load_config_cache()
            self.assertEqual(data, {})

    def test_save_config_write_failure_cleanup(self):
        """Test zlyhania zápisu a upratania .tmp súboru."""
        with patch("core.logic.system_listener.get_embedinstall_config_path", return_value=self.config_path):
            with patch("builtins.open", side_effect=IOError("Write blocked")):
                _save_config_cache({"key": "val"})
                tmp_file = self.config_path + ".tmp"
                self.assertFalse(os.path.exists(tmp_file))

    def test_preload_cache_async(self):
        """Test asynchrónneho predhriatia cache na pozadí."""
        with patch("core.logic.system_listener.is_portable_mode", return_value=True), \
             patch("core.logic.system_listener._load_config_cache") as mock_load, \
             patch("core.logic.system_listener.get_machine_id") as mock_mac:
            
            _preload_cache_async()
            time.sleep(0.1)
            mock_load.assert_called_once()
            mock_mac.assert_called_once()


class TestVerifyAccessAndUI(unittest.TestCase):
    """Testovanie verifikačnej logiky prístupu a výstražných okien."""

    def setUp(self):
        sl._CONFIG_CACHE = None
        sl._MACHINE_ID_CACHE = "CURRENT_PC_SHA256"

    def test_verify_access_conditions(self):
        """Test všetkých podmienok v verify_access."""
        self.assertTrue(verify_access(""))

        with patch("core.logic.system_listener.is_portable_mode", return_value=False):
            self.assertTrue(verify_access("/path/to/venv"))

        with patch("core.logic.system_listener.is_portable_mode", return_value=True), \
             patch("core.logic.system_listener.is_system_venv", return_value=False):
            self.assertTrue(verify_access("/path/to/venv"))

        # Ak venv nie je zatiaľ zapísaný v configu -> Povoliť prístup
        with patch("core.logic.system_listener.is_portable_mode", return_value=True), \
             patch("core.logic.system_listener.is_system_venv", return_value=True), \
             patch("core.logic.system_listener._load_config_cache", return_value={}):
            self.assertTrue(verify_access("/path/to/unknown_venv"))

        # Rovnaké PC -> Povoliť prístup
        with patch("core.logic.system_listener.is_portable_mode", return_value=True), \
             patch("core.logic.system_listener.is_system_venv", return_value=True), \
             patch("core.logic.system_listener._load_config_cache", return_value={"my_venv": "CURRENT_PC_SHA256"}):
            self.assertTrue(verify_access("/path/to/my_venv"))

        # Cudzie PC -> Zablokovať prístup
        with patch("core.logic.system_listener.is_portable_mode", return_value=True), \
             patch("core.logic.system_listener.is_system_venv", return_value=True), \
             patch("core.logic.system_listener._load_config_cache", return_value={"my_venv": "OTHER_PC_SHA256"}):
            self.assertFalse(verify_access("/path/to/my_venv"))

    @patch.object(QMessageBox, 'exec')
    def test_show_blocked_warning(self, mock_exec):
        """Test zobrazenia varovného okna blokovania bez pádu GUI."""
        show_blocked_warning("TestVenv")
        mock_exec.assert_called_once()


class TestSystemListenerPatches(unittest.TestCase):
    """Kompletný test všetkých opatchovaných funkcií v SystemListener.start_listening()."""

    @classmethod
    def setUpClass(cls):
        SystemListener.start_listening()

    @patch("core.logic.system_listener.show_blocked_warning")
    @patch("core.logic.system_listener.verify_access")
    def test_single_play_patches(self, mock_verify, mock_warning):
        """Test 1. NAČÚVANIE SINGLE PLAY (Terminal, Silent, Open Terminal)."""
        from core.logic.button.manager.actions import ActionHandler

        # Blocked scenár
        mock_verify.return_value = False
        ActionHandler.start_terminal_process("proj", "/venv/path", "script.py")
        mock_warning.assert_called_with("path")

        ActionHandler.start_silent_process("proj", "/venv/path", "script.py")
        self.assertEqual(mock_warning.call_count, 2)

        ActionHandler.open_terminal_only("proj", "/venv/path")
        self.assertEqual(mock_warning.call_count, 3)

    @patch("core.logic.system_listener.show_blocked_warning")
    @patch("core.logic.system_listener.verify_access")
    def test_multi_play_patch(self, mock_verify, mock_warning):
        """Test 2. NAČÚVANIE MULTI PLAY (Autostart Groups)."""
        from core.logic.containers.button.autostart_actions import AutostartActionHandler

        mock_core = MagicMock()
        mock_core.multi_groups = {
            "Group1": [{"venv_path": "/venv/bad_venv"}]
        }

        mock_verify.return_value = False
        log_mock = MagicMock()

        AutostartActionHandler.start_group(mock_core, "Group1", log_callback=log_mock)
        mock_warning.assert_called_once()
        log_mock.assert_called_once()

    @patch("core.logic.system_listener.show_blocked_warning")
    @patch("core.logic.system_listener.verify_access")
    def test_clone_patch(self, mock_verify, mock_warning):
        """Test 3. NAČÚVANIE KLONOVANIA."""
        from core.logic.button.manager.clone import CloneHandler

        mock_verify.return_value = False
        CloneHandler.run(MagicMock(), MagicMock(), "/venv/blocked")
        mock_warning.assert_called_once()

    @patch("core.logic.system_listener.show_blocked_warning")
    @patch("core.logic.system_listener.verify_access")
    def test_vscode_patch(self, mock_verify, mock_warning):
        """Test 4. NAČÚVANIE VS CODE."""
        from core.logic.vscode_user.start_vs_code_user import VSCodeLauncher

        mock_verify.return_value = False
        success, msg = VSCodeLauncher.launch(MagicMock(), "proj", "/venv/blocked")
        self.assertFalse(success)
        mock_warning.assert_called_once()

    @patch("core.logic.system_listener.show_blocked_warning")
    @patch("core.logic.system_listener.verify_access")
    def test_master_manager_patches(self, mock_verify, mock_warning):
        """Test 5. NAČÚVANIE PIP MANAŽÉROV (Pip, Local, Pip-E)."""
        from windows.manager import MasterManager

        mock_verify.return_value = False
        
        manager_inst = MasterManager.__new__(MasterManager)
        manager_inst.selected_venv_path = "/venv/blocked"

        manager_inst.open_pip_manager()
        manager_inst.open_local_packages_window()
        manager_inst.open_pip_e_window()

        self.assertEqual(mock_warning.call_count, 3)

    @patch("core.logic.system_listener.is_portable_mode", return_value=True)
    @patch("core.logic.system_listener._save_config_cache")
    def test_birth_certificate_patch(self, mock_save, mock_portable):
        """Test 6. ZÁPIS RODNÉHO LISTU (Vytvorenie Venvu)."""
        from core.logic.birth_certificate import BirthCertificateGenerator

        BirthCertificateGenerator.create_venv_certificate(
            "Proj", "MyVenv", "/path/to/MyVenv", "python.exe", source_python_path="C:\\Python\\python.exe"
        )
        time.sleep(0.2)
        mock_save.assert_called()

    def test_portable_path_logic_repair_patch(self):
        """DOPLNENÉ A OPRAVENÉ: Test zamedzenia opravy ciest pre Systémový Venv v Portable režime."""
        from core.logic.path_logic.portable import PortablePathLogic

        # Vytvoríme mock na ORIGINÁLNU opravenú metódu
        with patch("core.logic.system_listener.is_portable_mode", return_value=True), \
             patch("core.logic.system_listener.is_system_venv", return_value=True):
            
            # Zavoláme opatchovanú funkciu
            # Kedže je to Systémový Venv v Portable, funkcia MUSÍ okamžite skončiť (return)
            # a nedotknúť sa ničom vnútri.
            try:
                PortablePathLogic.check_and_repair_venv_if_needed("/venv/system")
            except Exception as e:
                self.fail(f"check_and_repair_venv_if_needed zlyhal: {e}")

    @patch("core.logic.system_listener.show_blocked_warning")
    @patch("core.logic.system_listener.verify_access")
    def test_pip_manager_and_freeze_patches(self, mock_verify, mock_warning):
        """Test 8. PIP OPERÁCIE, FREEZE A MAZANIE."""
        from core.logic.pip_manager import PipManager
        from core.logic.button.pip.freeze import FreezeHandler

        mock_verify.return_value = False
        mock_log = MagicMock()

        PipManager.install_package("/venv/blocked", "requests", mock_log)
        PipManager.uninstall_package("/venv/blocked", "requests", mock_log)
        PipManager.install_requirements("/venv/blocked", "/proj", mock_log)
        PipManager.update_all_packages("/venv/blocked", mock_log)
        result = FreezeHandler.run("/venv/blocked", "/proj", log_callback=mock_log)

        self.assertFalse(result)
        self.assertEqual(mock_warning.call_count, 5)
        self.assertEqual(mock_log.append.call_count, 4)


# =========================================================================
# NOVÁ PRIDANÁ TRIEDA PRE TESTOVANIE REVERZNÝCH ZÁVISLOSTÍ (PIP, EDITABLE, LINKER)
# =========================================================================
class TestAptListenerReverseDependencies(unittest.TestCase):
    """Nové testy pre AptListener a kontrolu reverzných závislostí vrátane Linkeru."""

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

        # Vytvorenie Linker balíčka (venvhub.json + local_meta.json)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)