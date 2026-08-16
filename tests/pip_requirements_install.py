#----------------------------------------
# Súbor: tests/pip_requirements_install.py
#----------------------------------------
#
# KOMPLETNÝ, KROK-ZA-KROKOM test celej logiky "Inštalujem z requirements.txt":
#
#   ČASŤ A - izolované moduly (PathNormalizer, RequirementsParser, dispatcher)
#   ČASŤ B - PRIAME zavolanie SKUTOČNEJ, nezmenenej funkcie
#            core.logic.pip_manager.PipManager.install_requirements()
#            (presne tá istá funkcia, ktorú spúšťa tvoje GUI tlačidlo),
#            so zachyteným subprocess volaním (nič sa reálne neinštaluje).
#
# Spusti s -s aby si videl VŠETKY print() výpisy (pytest ich inak potlačí):
#
#     python -m pytest tests/pip_requirements_install.py -v -s
#
# alebo priamo ako skript:
#
#     python tests/pip_requirements_install.py

import os
import sys
import tempfile
import subprocess

# 1. Pridanie koreňového adresára projektu do Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. AKTIVÁCIA QT MOSTA (musí bežať PRED importom modulov aplikácie)
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()

# 3. Importy - PRESNE tá istá logika, akú používa reálna appka
from core._path import Paths
from core.logic.sluzby.path_normalizer import PathNormalizer
from core.logic.sluzby.requirements_parser import RequirementsParser
from core.logic.commands.command_factory import PackageManagerFactory
from core.logic.pip_manager import PipManager  # <-- SKUTOČNÁ produkčná trieda


def print_step(step_number, title):
    print("\n" + "=" * 70)
    print(f"📌 KROK {step_number}: {title}")
    print("=" * 70)


class FakeLogWidget:
    """Nahrádza QTextEdit/log_widget z GUI - len vypisuje na konzolu."""
    def append(self, msg):
        print(f"    [LOG] {msg}")


def _write_broken_requirements(req_path, fake_pkg_dir):
    """Zapíše requirements.txt so ZÁMERNE rozbitým (spätné lomítka) -e riadkom."""
    broken_path = fake_pkg_dir.replace("/", "\\")
    with open(req_path, "w", encoding="utf-8") as f:
        f.write("requests>=2.25.0\n")
        f.write(f"-e {broken_path}\n")
    return broken_path


def test_pip_requirements_install():
    with tempfile.TemporaryDirectory() as tmp_root:
        # -----------------------------------------------------------------
        # PRÍPRAVA: falošný "editable" balíček
        # -----------------------------------------------------------------
        fake_pkg_dir = os.path.join(tmp_root, "pip-e", "pip1")
        os.makedirs(fake_pkg_dir, exist_ok=True)
        with open(os.path.join(fake_pkg_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(
                "[build-system]\n"
                "requires = [\"setuptools\"]\n"
                "build-backend = \"setuptools.build_meta\"\n\n"
                "[project]\n"
                "name = \"pip1\"\n"
                "version = \"0.0.1\"\n"
            )

        project_root = os.path.join(tmp_root, "moj_projekt")
        os.makedirs(project_root, exist_ok=True)
        req_path = Paths.get_requirements_txt_path(project_root)

        # ===================================================================
        # ČASŤ A - IZOLOVANÉ MODULY (rovnaké ako v predchádzajúcom teste)
        # ===================================================================
        print_step("A1", "Zápis requirements.txt so SPÄTNÝMI lomítkami")
        broken_path = _write_broken_requirements(req_path, fake_pkg_dir)
        with open(req_path, "r", encoding="utf-8") as f:
            print(f.read())

        print_step("A2", "RequirementsParser.parse() - PRED sanitizáciou")
        parsed_before = RequirementsParser.parse(req_path)
        print(f"Parsované balíčky: {parsed_before}")

        print_step("A3", "PRIAME volanie PathNormalizer.sanitize_requirements_file() (izolovane)")
        PathNormalizer.sanitize_requirements_file(req_path)
        with open(req_path, "r", encoding="utf-8") as f:
            raw_after = f.read()
        print(raw_after)
        assert "\\" not in raw_after, "❌ Samotný PathNormalizer modul má bug - toto by NEMALO zlyhať."
        print("✅ ČASŤ A prešla: izolovaný modul PathNormalizer funguje správne.")

        # ===================================================================
        # ČASŤ B - SKUTOČNÁ PRODUKČNÁ FUNKCIA PipManager.install_requirements
        # ===================================================================
        print_step("B1", "Znovu ROZBÍJAM requirements.txt (spätné lomítka), aby sme testovali od nuly")
        broken_path = _write_broken_requirements(req_path, fake_pkg_dir)
        with open(req_path, "r", encoding="utf-8") as f:
            print(f.read())

        print_step("B2", "Zachytávam subprocess.Popen v pip_manager.py (aby sa NIČ reálne neinštalovalo)")
        import core.logic.pip_manager as pip_manager_module

        captured = {}

        class FakeProcess:
            """Simuluje ukončený proces bez skutočného spustenia pip."""
            def __init__(self):
                self.stdout = iter(["(simulované - subprocess nebol reálne spustený)"])
                self.returncode = 0
            def wait(self):
                return self.returncode

        def fake_popen(cmd, *args, **kwargs):
            print(f"    [ZACHYTENÉ] subprocess.Popen by spustil: {cmd}")
            captured["cmd"] = cmd
            return FakeProcess()

        original_popen = pip_manager_module.subprocess.Popen
        pip_manager_module.subprocess.Popen = fake_popen

        try:
            print_step("B3", "VOLÁM SKUTOČNÚ PipManager.install_requirements() - žiadne úpravy, žiadne mocky logiky")
            fake_log = FakeLogWidget()
            PipManager.install_requirements(
                venv_path=os.path.dirname(os.path.dirname(sys.executable)),
                project_root=project_root,
                log_widget=fake_log,
                manager_type="pip",
            )

            # install_requirements spúšťa worker vo vlákne (threading.Thread) -
            # počkáme, kým dobehne, nech je "cmd" isto zachytené.
            if PipManager._current_thread:
                PipManager._current_thread.join(timeout=10)

        finally:
            pip_manager_module.subprocess.Popen = original_popen

        print_step("B4", "OBSAH requirements.txt HNEĎ PO volaní install_requirements()")
        with open(req_path, "r", encoding="utf-8") as f:
            raw_after_prod = f.read()
        print(raw_after_prod)

        print_step("B5", "Zachytený príkaz, ktorý by sa reálne poslal do pip")
        print(f"cmd = {captured.get('cmd')}")

        # -------------------------------------------------------------
        # TOTO JE KĽÚČOVÁ KONTROLA - overuje SKUTOČNÝ produkčný kód,
        # nie izolovaný modul.
        # -------------------------------------------------------------
        if "\\" in raw_after_prod:
            print("\n❌❌❌ ZISTENÉ: PipManager.install_requirements() V PRODUKCII")
            print("    NEVOLÁ PathNormalizer.sanitize_requirements_file()!")
            print("    Súbor na disku ostal rozbitý so spätnými lomítkami.")
            print("    -> Over si import a volanie v core/logic/pip_manager.py")
        else:
            print("\n✅ Produkčná funkcia install_requirements() súbor správne sanitizovala.")

        assert "\\" not in raw_after_prod, (
            "❌ CHYBA: Skutočná PipManager.install_requirements() nesanitizovala "
            "requirements.txt pred zostavením pip príkazu. Skontroluj, či v "
            "core/logic/pip_manager.py naozaj existuje volanie "
            "PathNormalizer.sanitize_requirements_file(req_path) PRED "
            "riadkom 'cmd = dispatcher.get(\"install_requirements\", ...)'."
        )


if __name__ == "__main__":
    test_pip_requirements_install()
    print("\n🎉 VŠETKY KROKY (A aj B) PREŠLI ÚSPEŠNE.")
