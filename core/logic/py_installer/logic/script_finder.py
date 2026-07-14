#----------------------------------------
# Súbor: core/logic/py_installer/logic/script_finder.py
#----------------------------------------

import os

class ScriptFinder:
    """
    Nástroj na vyhľadávanie spúšťacích Python skriptov.
    Hľadá IBA v koreňovom priečinku projektu, nelezier do podadresárov.
    """

    @staticmethod
    def get_python_scripts(project_path: str) -> list[str]:
        """
        Vráti zoznam .py súborov, ktoré sú PRIAMO v project_path.
        Ignoruje podadresáre.
        """
        if not project_path or not os.path.exists(project_path):
            return []

        found_scripts = []

        try:
            # Získame všetky položky v koreňovom priečinku
            items = os.listdir(project_path)

            for item in items:
                full_path = os.path.join(project_path, item)
                
                # Zaujímajú nás len SÚBORY (nie priečinky) s koncovkou .py
                if os.path.isfile(full_path) and item.endswith('.py'):
                    found_scripts.append(item)

        except Exception as e:
            print(f"Chyba pri hľadaní skriptov: {e}")
            return []

        # Zoradíme abecedne, pričom 'main.py' alebo 'app.py' by sme mohli zvýhodniť,
        # ale abecedné zoradenie zvyčajne stačí, keďže zoznam bude krátky.
        return sorted(found_scripts)