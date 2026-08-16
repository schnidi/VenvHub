#----------------------------------------
# Súbor: tests/test_uninstall_guard_flow.py
#----------------------------------------
#
# Overuje novú "poistku" proti odinštalovaniu balíčkov, na ktorých
# závisia iné nainštalované balíčky (viď uninstall_apt.md).
#
# Keďže nemáme k dispozícii reálne core/pyqt prostredie, závislostný
# strom (AptLogic.get_dependency_graph) je pre účely testu nahradený
# (monkeypatched) jednoduchým fixture grafom.

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()

from core.logic.sluzby.apt_listener import AptListener
from core.logic.sluzby.apt_logic import AptLogic


# Fixture graf: "requests" vyžaduje "certifi" a "urllib3".
# "certifi" a "urllib3" nemajú žiadne ďalšie závislosti.
# "standalone-tool" nie je od nikoho vyžadovaný.
FAKE_GRAPH = {
    "requests": ["certifi", "urllib3", "idna"],
    "certifi": [],
    "urllib3": [],
    "idna": [],
    "standalone-tool": [],
}


class FakeCore:
    """Minimálna náhrada za reálny `core` objekt."""
    package_manager = "pip"


def print_step(step_number, title):
    print("\n" + "=" * 60)
    print(f"📌 KROK {step_number}: {title}")
    print("=" * 60)


def test_uninstall_guard_flow():
    core = FakeCore()
    venv_path = sys.prefix

    # Monkeypatch: get_dependency_graph vráti pripravený fixture graf
    # namiesto reálneho volania subprocessov.
    original_get_dependency_graph = AptLogic.get_dependency_graph
    AptLogic.get_dependency_graph = staticmethod(lambda venv_path, core: FAKE_GRAPH)

    try:
        # ---------------------------------------------------------------
        # KROK 1: Balíček, na ktorom závisia iné balíčky, sa NESMIE dať
        #         odinštalovať -> _is_package_required_by_others musí
        #         vrátiť neprázdny zoznam.
        # ---------------------------------------------------------------
        print_step(1, "Kontrola blokovaného balíčka ('certifi' je vyžadovaný 'requests')")

        dependents = AptListener._is_package_required_by_others(venv_path, core, "certifi")
        print(f"🔗 Balíčky závislé na 'certifi': {dependents}")

        assert "requests" in dependents, "❌ Chyba: 'requests' malo byť nájdené ako závislé na 'certifi'!"
        print("✅ KROK 1 prešiel: 'certifi' je správne označený ako potrebný pre iné balíčky.")

        # ---------------------------------------------------------------
        # KROK 2: Balíček bez závislých (leaf / standalone) sa MUSÍ dať
        #         odinštalovať bez prekážok.
        # ---------------------------------------------------------------
        print_step(2, "Kontrola voľne odinštalovateľného balíčka ('standalone-tool')")

        dependents = AptListener._is_package_required_by_others(venv_path, core, "standalone-tool")
        print(f"🔗 Balíčky závislé na 'standalone-tool': {dependents}")

        assert dependents == [], "❌ Chyba: 'standalone-tool' nemal mať žiadne závislé balíčky!"
        print("✅ KROK 2 prešiel: 'standalone-tool' je voľne odinštalovateľný.")

        # ---------------------------------------------------------------
        # KROK 3: Samotný root balíček ('requests') nemá závislé balíčky,
        #         hoci je sám o sebe rodičom v grafe -> nesmie sa
        #         "vidieť" sám na sebe (self != dependent).
        # ---------------------------------------------------------------
        print_step(3, "Kontrola, že koreňový balíček nezávisí sám na sebe")

        dependents = AptListener._is_package_required_by_others(venv_path, core, "requests")
        print(f"🔗 Balíčky závislé na 'requests': {dependents}")

        assert dependents == [], "❌ Chyba: 'requests' nemal byť vyžadovaný žiadnym iným balíčkom vo fixture grafe!"
        print("✅ KROK 3 prešiel: koreňový balíček je správne vyhodnotený ako odinštalovateľný.")

        # ---------------------------------------------------------------
        # KROK 4: Normalizácia názvov (napr. veľké písmená / podčiarkovníky)
        #         musí fungovať rovnako ako v AptLogic._normalize.
        # ---------------------------------------------------------------
        print_step(4, "Kontrola normalizácie názvu balíčka pri zisťovaní závislostí")

        dependents = AptListener._is_package_required_by_others(venv_path, core, "Certifi")
        print(f"🔗 Balíčky závislé na 'Certifi' (rôzne veľké písmená): {dependents}")

        assert "requests" in dependents, "❌ Chyba: normalizácia názvu zlyhala pri kontrole veľkých písmen!"
        print("✅ KROK 4 prešiel: normalizácia názvu balíčka funguje správne.")

        # ---------------------------------------------------------------
        # KROK 5: Guard v PipEUninstallWorker.run() musí zablokovať
        #         odinštalovanie balíčka, na ktorom niečo závisí,
        #         a NESMIE zavolať pôvodný (skutočný) subprocess kód.
        # ---------------------------------------------------------------
        print_step(5, "Kontrola poistky v PipEUninstallWorker.run() (blokovaný prípad)")

        from core.logic.pip_e import PipEUninstallWorker
        AptListener._patch_pipe_uninstall(core)

        worker_blocked = PipEUninstallWorker(venv_path, "certifi")

        captured = {"logs": [], "finished_with": None}
        worker_blocked.log_msg.connect(lambda m: captured["logs"].append(m))
        worker_blocked.finished.connect(lambda ok: captured.__setitem__("finished_with", ok))

        worker_blocked.run()

        print(f"📝 Zachytené logy: {captured['logs']}")
        print(f"🏁 finished emitované s hodnotou: {captured['finished_with']}")

        assert captured["finished_with"] is False, "❌ Chyba: worker mal skončiť s finished(False)!"
        assert any("certifi" in m for m in captured["logs"]), "❌ Chyba: chýba varovná správa o zablokovanom balíčku!"
        print("✅ KROK 5 prešiel: PipEUninstallWorker správne odmietol odinštalovať vyžadovaný balíček.")

        # ---------------------------------------------------------------
        # KROK 6: Guard nesmie brániť odinštalovaniu balíčka bez
        #         závislých -> orig_run() sa musí zavolať (over pomocou
        #         monkeypatchu na subprocess.Popen, aby test nič reálne
        #         nemenil vo venve).
        # ---------------------------------------------------------------
        print_step(6, "Kontrola poistky v PipEUninstallWorker.run() (povolený prípad)")

        import core.logic.pip_e as pip_e_module

        class FakeStdout:
            def __init__(self, lines):
                self._lines = iter(lines)

            def readline(self):
                return next(self._lines, '')

        class FakeProcess:
            returncode = 0
            stdout = FakeStdout(["Successfully uninstalled standalone-tool\n"])

            def wait(self):
                pass

        original_popen = pip_e_module.subprocess.Popen
        original_update_cert = pip_e_module.BirthCertificateGenerator.update_venv_certificate
        pip_e_module.subprocess.Popen = lambda *a, **kw: FakeProcess()
        pip_e_module.BirthCertificateGenerator.update_venv_certificate = staticmethod(lambda venv_path: None)

        try:
            worker_allowed = PipEUninstallWorker(venv_path, "standalone-tool")

            captured_allowed = {"finished_with": None}
            worker_allowed.finished.connect(lambda ok: captured_allowed.__setitem__("finished_with", ok))

            worker_allowed.run()

            print(f"🏁 finished emitované s hodnotou: {captured_allowed['finished_with']}")
            assert captured_allowed["finished_with"] is True, "❌ Chyba: 'standalone-tool' mal byť úspešne odinštalovaný!"
            print("✅ KROK 6 prešiel: balíček bez závislých bol správne odinštalovaný (orig_run sa vykonal).")
        finally:
            pip_e_module.subprocess.Popen = original_popen
            pip_e_module.BirthCertificateGenerator.update_venv_certificate = original_update_cert

    finally:
        # Vrátime pôvodnú (nezmenenú) implementáciu
        AptLogic.get_dependency_graph = original_get_dependency_graph


if __name__ == "__main__":
    test_uninstall_guard_flow()
    print("\n🎉 Všetky testy prešli úspešne.")
