#----------------------------------------
# Súbor: tests/test_pip_e_flow.py
#----------------------------------------

import os
import sys
import json
import tempfile  # <-- Importovaný tempfile

# 1. Pridanie koreňového adresára projektu do Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. AKTIVÁCIA QT MOSTA (Musí sa spustiť PRED importom akýchkoľvek modulov)
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()

# 3. Importy modulov aplikácie
from core._path import Paths
from core.logic.sluzby.apt_listener import AptListener
from core.logic.sluzby.apt_logic import AptLogic
from core.logic.sluzby.requirements_parser import RequirementsParser


def print_step(step_number, title):
    """Pomocná funkcia pre prehľadný výpis krokov do konzoly."""
    print("\n" + "=" * 60)
    print(f"📌 KROK {step_number}: {title}")
    print("=" * 60)


def test_pip_e_flow():
    venv_path = sys.prefix
    
    # -------------------------------------------------------------------------
    # KROK 1: Získanie Python executable a kontrola ciest
    # -------------------------------------------------------------------------
    print_step(1, "Kontrola ciest venv a Python Executable")
    python_exe = Paths.get_venv_python_exe_path(venv_path)
    
    print(f"📂 Venv Path:       {venv_path}")
    print(f"⚙️ Python Exe Path: {python_exe}")
    print(f"🔍 Existuje Python? {os.path.exists(python_exe)}")
    
    assert os.path.exists(python_exe), f"Python spúšťací súbor nebol nájdený: {python_exe}"

    # -------------------------------------------------------------------------
    # KROK 2: Získanie zoznamu editable (-e) balíčkov cez AptListener
    # -------------------------------------------------------------------------
    print_step(2, "Volanie AptListener._get_editable_packages()")
    
    editable_packages = AptListener._get_editable_packages(venv_path)
    
    print(f"📊 Počet nájdených -e balíčkov: {len(editable_packages)}")
    print("📄 Surový JSON výstup z Listenera:")
    print(json.dumps(editable_packages, indent=4, ensure_ascii=False))

    # -------------------------------------------------------------------------
    # KROK 3: Analýza ciest a názvov -e balíčkov
    # -------------------------------------------------------------------------
    print_step(3, "Detailná analýza -e balíčkov")
    
    editable_names = set()
    if not editable_packages:
        print("ℹ️ V tomto venv nie sú momentálne nainštalované žiadne -e balíčky.")
    else:
        for idx, pkg in enumerate(editable_packages, start=1):
            name = AptLogic._normalize(pkg.get("name", ""))
            version = pkg.get("version")
            path = pkg.get("path") or pkg.get("editable_project_location", "Neznáma cesta")
            
            if name:
                editable_names.add(name)
            
            print(f"\n  [Balíček {idx}]")
            print(f"  🔹 Názov (normalizovaný): {name}")
            print(f"  🔹 Verzia:                {version}")
            print(f"  🔹 Cesta:                 {path}")
            print(f"  📂 Existuje na disku?     {os.path.exists(path)}")

    # -------------------------------------------------------------------------
    # KROK 4: Simulácia vyhodnotenia explicitných koreňov v AptLogic
    # -------------------------------------------------------------------------
    print_step(4, "Overenie prepojenia -e balíčkov s requirements.txt")

    with tempfile.TemporaryDirectory() as tmp_dir:
        req_file_path = os.path.join(tmp_dir, "requirements.txt")
        
        # Scenár A: Keď requirements.txt NEOCSAHUJE žiadny -e balíček
        with open(req_file_path, "w", encoding="utf-8") as f:
            f.write("requests>=2.25.0\n")
            
        parsed_reqs_a = RequirementsParser.parse(req_file_path)
        print(f"📄 Scenár A (Requirements bez -e): {parsed_reqs_a}")
        
        # Overíme, že žiadny -e balíček nie je v explicit_roots, ak chýba v requirements.txt
        for e_name in editable_names:
            if e_name != "requests":
                assert e_name not in parsed_reqs_a, f"❌ Chyba: {e_name} nesmie byť explicitný!"
        print("✅ Scenár A prešiel: -e balíčky NIE SÚ explicitné, lebo nie sú v requirements.txt.")

        # Scenár B: Ak sa pridá -e balíček do requirements.txt pomocou SKUTOČNEJ CESTY z JSONu
        if editable_packages:
            target_pkg = editable_packages[0]
            target_e_name = AptLogic._normalize(target_pkg.get("name", ""))
            # Získame SKUTOČNÚ CESTU z JSONu:
            target_e_path = target_pkg.get("editable_project_location") or target_pkg.get("path")
            
            # Zapíšeme do requirements.txt skutočnú cestu (-e C:/Cesta/K/Balicku)
            with open(req_file_path, "a", encoding="utf-8") as f:
                f.write(f"\n-e {target_e_path}\n")
                
            parsed_reqs_b = RequirementsParser.parse(req_file_path)
            print(f"📄 Scenár B (Requirements s -e {target_e_path}): {parsed_reqs_b}")
            
            # Simulácia logiky AptLogic
            explicit_roots_simulated = set(parsed_reqs_b)
            for e_pkg in editable_packages:
                e_norm = AptLogic._normalize(e_pkg.get("name", ""))
                if e_norm and e_norm in parsed_reqs_b:
                    explicit_roots_simulated.add(e_norm)
                    
            print(f"🎯 Výsledné explicit_roots pre AptLogic: {explicit_roots_simulated}")
            assert target_e_name in explicit_roots_simulated, f"❌ Chyba: {target_e_name} mal byť explicitný!"
            print(f"✅ Scenár B prešiel: Balíček '{target_e_name}' sa podľa skutočnej cesty stal explicitným!")
        else:
            print("ℹ️ Scenár B preskočený (vo venv nie je momentálne žiadny -e balíček).")


if __name__ == "__main__":
    test_pip_e_flow()