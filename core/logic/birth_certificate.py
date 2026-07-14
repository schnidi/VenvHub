#----------------------------------------
# Súbor: core/logic/birth_certificate.py
#----------------------------------------

import os
import json
import datetime
import subprocess
from core._path import Paths

class BirthCertificateGenerator:
    """
    Centrálny manažér pre 'Rodné listy' (Birth Certificates).
    Sleduje a zaznamenáva stav virtuálneho prostredia (verziu Pythonu a balíčky).
    """

    @staticmethod
    def _get_python_version(python_exe: str) -> str:
        """Zistí presnú verziu Pythonu z daného exe súboru."""
        try:
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            result = subprocess.run(
                [python_exe, "--version"], 
                capture_output=True, 
                text=True, 
                creationflags=CREATE_NO_WINDOW
            )
            return result.stdout.strip() if result.returncode == 0 else "Neznáma"
        except Exception:
            return "Neznáma"

    @staticmethod
    def _get_installed_packages(python_exe: str) -> list:
        """
        Získa zoznam nainštalovaných balíčkov vo formáte JSON.
        POZNÁMKA: Aktuálne používa modul pip. Ak v budúcnosti prejdeš na čisté UV,
        stačí tento jeden príkaz zmeniť na ['uv', 'pip', 'list', '--format=json', '--python', python_exe].
        """
        try:
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            result = subprocess.run(
                [python_exe, "-m", "pip", "list", "--format=json"], 
                capture_output=True, 
                text=True, 
                creationflags=CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return []
        except Exception:
            return []

    @staticmethod
    def create_venv_certificate(project_name: str, venv_name: str, venv_path: str, python_exe: str, source_python_path: str = None) -> bool:
        """
        KROK 1: Vytvorí ZÁKLADNÝ rodný list pri 'narodení' prázdneho Venvu.
        Prijíma aj informáciu o zdrojovom Pythone (pre účely klonovania embed verzií).
        """
        cert_path = os.path.join(venv_path, "venv_birth_certificate.json")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data = {
            "document_type": "Venv Birth Certificate",
            "project_name": project_name,
            "venv_folder_name": venv_name,
            "created_at": now_str,
            "last_updated": now_str,
            "python_version": BirthCertificateGenerator._get_python_version(python_exe),
            "packages": [] # Na začiatku je prázdny
        }

        # Pridáme cestu k rodičovi, ak bola poskytnutá
        if source_python_path:
            data["source_python_path"] = source_python_path

        try:
            with open(cert_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Chyba pri generovaní rodného listu Venvu: {e}")
            return False

    @staticmethod
    def update_venv_certificate(venv_path: str) -> bool:
        """
        KROK 2: ŽIVÁ AKTUALIZÁCIA. 
        Zavolá sa vždy, keď sa do venvu niečo nainštaluje/odinštaluje/aktualizuje.
        Preskenuje aktuálny stav a zapíše ho do JSONu.
        """
        if not venv_path or not os.path.exists(venv_path):
            return False

        cert_path = os.path.join(venv_path, "venv_birth_certificate.json")
        python_exe = Paths.get_venv_python_exe_path(venv_path)

        # Načítanie existujúceho listu (alebo vytvorenie núdzového, ak ho niekto zmazal)
        data = {}
        if os.path.exists(cert_path):
            try:
                with open(cert_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass

        # Ak súbor neexistoval alebo bol poškodený, vytvoríme aspoň základnú štruktúru
        if not data:
            data = {
                "document_type": "Venv Birth Certificate",
                "project_name": "Neznámy (Obnovené)",
                "venv_folder_name": os.path.basename(venv_path),
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "python_version": BirthCertificateGenerator._get_python_version(python_exe)
            }

        # Aktualizujeme balíčky a čas. Ostatné dáta (vrátane source_python_path) zostávajú nedotknuté.
        data["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["packages"] = BirthCertificateGenerator._get_installed_packages(python_exe)

        try:
            with open(cert_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Chyba pri aktualizácii rodného listu: {e}")
            return False

    @staticmethod
    def create_app_certificate(project_name: str, venv_path: str, script_name: str, output_dir: str) -> str | None:
        """
        KROK 3: FINÁLNY RODNÝ LIST PRE APLIKÁCIU (.exe)
        Zoberie aktuálny stav venvu a vytvorí finálny JSON pre PyInstaller.
        """
        cert_name = f"{project_name}_birth_certificate.json"
        cert_path = os.path.join(output_dir, cert_name)
        
        python_exe = Paths.get_venv_python_exe_path(venv_path)
        
        data = {
            "document_type": "App Birth Certificate (PyInstaller Build)",
            "project_name": project_name,
            "entry_script": script_name,
            "build_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "python_environment": {
                "python_version": BirthCertificateGenerator._get_python_version(python_exe),
                "installed_packages": BirthCertificateGenerator._get_installed_packages(python_exe)
            }
        }

        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(cert_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return cert_path
        except Exception as e:
            print(f"Chyba pri generovaní rodného listu Aplikácie: {e}")
            return None