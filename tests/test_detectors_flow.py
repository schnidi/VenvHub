#----------------------------------------
# Súbor: tests/test_detectors_flow.py
#----------------------------------------

import os
import sys
import json

# 1. Pridanie koreňového adresára projektu do Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. AKTIVÁCIA QT MOSTA (Musí sa spustiť PRED importom akýchkoľvek modulov)
from core.logic.pyqt_to_pyside import setup_qt_environment
setup_qt_environment()

# 3. Importy modulov aplikácie
from core.logic.python_detector import PythonDetector
from core.logic.uv_detector import UVDetector


def print_step(step_number, title):
    """Pomocná funkcia pre prehľadný výpis krokov do konzoly."""
    print("\n" + "=" * 60)
    print(f"📌 KROK {step_number}: {title}")
    print("=" * 60)


def simulate_sandbox_uv_check(active_python_path, uv_path):
    """
    Simulácia novej navrhovanej architektúry.
    Overuje, či uv patrí buď neutrálnemu systému, alebo aktívnemu Pythonu.
    Ak patrí cudzojazyčnej verzii Pythonu, zakáže ho použiť.
    """
    if not uv_path:
        return False, "UV nie je nainštalované nikde v systéme."

    uv_path_norm = os.path.normpath(uv_path).lower()
    active_py_dir = os.path.normpath(os.path.dirname(active_python_path)).lower()
    active_py_scripts = os.path.join(active_py_dir, "scripts").lower()

    # Prípad 1: UV leží priamo v aktívnom Pythone (Scripts)
    if uv_path_norm.startswith(active_py_scripts) or uv_path_norm.startswith(active_py_dir):
        return True, "Úspech: UV je súčasťou aktívneho Python prostredia."

    # Prípad 2: UV je nainštalované ako neutrálny systémový nástroj (napr. .local, cargo, standalone)
    # Zistíme, či cesta neobsahuje zmienku o iných lokálnych verziách Pythonu
    is_in_any_python_dir = "appdata\\local\\programs\\python" in uv_path_norm or "program files\\python" in uv_path_norm
    is_in_roaming_python = "appdata\\roaming\\python" in uv_path_norm

    if not is_in_any_python_dir and not is_in_roaming_python:
        return True, "Úspech: UV je nainštalované ako nezávislý neutrálny systémový nástroj."

    # Prípad 3: UV leží v inom Pythone (Cudzie prostredie)
    # Zistíme, či cesta obsahuje iný Python ako ten, s ktorým aktívne pracujeme
    if (is_in_any_python_dir or is_in_roaming_python) and not uv_path_norm.startswith(active_py_dir):
        # Ak obsahuje zložku Python, ale nezačína zložkou nášho aktívneho Pythonu
        return False, f"ZÁKAZ: UV patrí cudziemu Python prostrediu na ceste: {uv_path}"

    return True, "UV detekované v rámci povolených limitov."


def test_detectors_flow():
    # -------------------------------------------------------------------------
    # KROK 1: Skenovanie systémových a lokálnych verzií Pythonu
    # -------------------------------------------------------------------------
    print_step(1, "Skenovanie runtimov cez PythonDetector")
    
    # Spustíme detekciu s vynúteným prečítaním disku (force_refresh)
    pythons = PythonDetector.get_installed_pythons(force_refresh=True)
    
    print(f"📊 Počet detekovaných runtimov: {len(pythons)}")
    for idx, py in enumerate(pythons, start=1):
        status = py.get("pip_status", "Neznámy")
        local_flag = " [LOKÁLNY]" if py.get("is_local") else " [SYSTÉMOVÝ]"
        print(f"  {idx}. {py['display']}{local_flag} -> {py['path']} (PIP: {status})")

    assert len(pythons) > 0, "Chyba: V systéme nebol nájdený žiadny Python runtime!"

    # -------------------------------------------------------------------------
    # KROK 2: Detekcia UV v systéme cez UVDetector
    # -------------------------------------------------------------------------
    print_step(2, "Detekcia polohy UV cez UVDetector")
    
    # Vyčistíme starú cache, aby sme mali istotu reálneho testu
    UVDetector.reset_cache()
    uv_path = UVDetector.get_uv_path()
    
    print(f"⚙️ UV nainštalované?  {UVDetector.is_uv_installed()}")
    print(f"📂 Zistená cesta k UV: {uv_path}")

    # -------------------------------------------------------------------------
    # KROK 3: Simulácia prepojenia (Aktívny Python vs. UV)
    # -------------------------------------------------------------------------
    print_step(3, "Simulácia väzby: Aktívny Python vs. Poloha UV")

    # Ako testovací aktívny Python použijeme ten, pod ktorým beží tento test (sys.executable)
    active_python = sys.executable
    print(f"🐍 Aktuálne spustený Python (sys.executable): {active_python}")

    # Spustíme naše testovacie pravidlo sandboxu
    is_allowed, reason = simulate_sandbox_uv_check(active_python, uv_path)
    
    print(f"\n📢 Výsledok analýzy sandboxu:")
    print(f"  Povolené spustiť UV? -> {'ÁNO' if is_allowed else 'NIE (Pip fallback)'}")
    print(f"  Dôvod: {reason}")

    # -------------------------------------------------------------------------
    # KROK 4: Modelový test pre váš prípad (Python 3.13 aktívny, UV v Python 3.12)
    # -------------------------------------------------------------------------
    print_step(4, "Modelový test: Simulácia vášho prostredia (Pád vs. Záchrana)")

    # Simulujeme váš stav:
    # - Aktívne pracujete s Python 3.13
    # - UV máte schované v priečinku pre Python 3.12
    simulated_active_py = r"C:\Users\Viliam Schneider\AppData\Local\Programs\Python\Python313\python.exe"
    simulated_uv_path = r"C:\Users\Viliam Schneider\AppData\Roaming\Python\Python312\Scripts\uv.exe"

    print(f"🐍 Modelový aktívny Python: {simulated_active_py}")
    print(f"⚙️ Modelová poloha UV:      {simulated_uv_path}")

    is_allowed_sim, reason_sim = simulate_sandbox_uv_check(simulated_active_py, simulated_uv_path)

    print(f"\n📢 Výsledok modelovej analýzy:")
    print(f"  Povolené spustiť UV? -> {'ÁNO' if is_allowed_sim else 'NIE (Pip fallback)'}")
    print(f"  Dôvod: {reason_sim}")

    # Podľa našej novej stratégie sa nesmie povoliť UV z verzie 3.12, ak sme v prostredí 3.13!
    assert is_allowed_sim is False, "❌ Chyba: Nový ochranný filter nezablokoval cudzie UV prostredie!"
    print("\n✅ ÚSPECH: Ochranný filter úspešne zablokoval cudzie UV a predišiel by pádu systému.")


if __name__ == "__main__":
    test_detectors_flow()