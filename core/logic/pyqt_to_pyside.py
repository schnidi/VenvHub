#----------------------------------------
# Súbor: core/logic/pyqt_to_pyside.py
#----------------------------------------
import os
import sys
import importlib.util
from importlib.abc import MetaPathFinder, Loader

def _pyside_load_ui_mimic(uifile, baseinstance=None):
    """
    Napodobňuje správanie PyQt6.uic.loadUi pre PySide6.
    Rozbalí XML a "nalepí" jeho prvky na už existujúce okno (self).
    """
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import QFile, QMetaObject, QDir
    from PySide6.QtWidgets import QWidget

    loader = QUiLoader()
    
    # -------------------------------------------------------------------
    # OPRAVA: Nastavenie pracovného adresára pre QUiLoader.
    # Zabezpečí, že relatívne cesty vnútri .ui súborov (napr. ../core/..) 
    # sa budú vyhodnocovať voči zložke, v ktorej sa daný .ui súbor nachádza.
    # -------------------------------------------------------------------
    ui_dir = os.path.dirname(os.path.abspath(uifile))
    loader.setWorkingDirectory(QDir(ui_dir))

    ui_file = QFile(uifile)
    if not ui_file.open(QFile.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Nepodarilo sa otvoriť UI súbor: {uifile}")

    # PySide6 QUiLoader vytvorí nové samostatné okno v pamäti
    loaded_widget = loader.load(ui_file, baseinstance)
    ui_file.close()

    if baseinstance:
        # 1. Skopírujeme všetky nájdené objekty na baseinstance (self)
        for child in loaded_widget.findChildren(object):
            name = child.objectName()
            if name:
                setattr(baseinstance, name, child)

        # 2. Presunieme hlavný layout na baseinstance
        if isinstance(baseinstance, QWidget) and hasattr(loaded_widget, 'layout'):
            layout = loaded_widget.layout()
            if layout:
                baseinstance.setLayout(layout)

        # 3. Napojíme sloty pre signály (napr. tlačidlá)
        QMetaObject.connectSlotsByName(baseinstance)
        return baseinstance
    
    return loaded_widget

class PyQtToPySideFinder(MetaPathFinder, Loader):
    """
    Kľúčový zachytávač (Interceptor) importov.
    Kedykoľvek Python uvidí v kóde 'import PyQt6.XXX', táto trieda zasiahne
    a vráti mu 'PySide6.XXX'.
    """
    def find_spec(self, fullname, path, target=None):
        if fullname == 'PyQt6' or fullname.startswith('PyQt6.'):
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        pyside_name = spec.name.replace('PyQt6', 'PySide6')

        # Špeciálny preklad pre 'uic' modul
        if pyside_name == 'PySide6.uic':
            import types
            fake_uic = types.ModuleType("uic")
            fake_uic.loadUi = _pyside_load_ui_mimic
            return fake_uic

        # Načítanie skutočného PySide modulu
        try:
            mod = importlib.import_module(pyside_name)
        except ImportError:
            raise ImportError(f"Nepodarilo sa preložiť '{spec.name}', ekvivalent '{pyside_name}' chýba v PySide6.")

        # Mapovanie PyQt špecifík na PySide6 ekvivalenty
        if pyside_name == 'PySide6.QtCore':
            mod.pyqtSignal = mod.Signal
            mod.pyqtSlot = mod.Slot

        # -------------------------------------------------------------------
        # OPRAVA: top-level "PyQt6" NESMIE byť priamo vrátený reálny PySide6
        # modul. Ten by mal __name__ == "PySide6", a Python by pri
        # "from PyQt6 import uic" (fromlist-import) potom hľadal "PySide6.uic"
        # namiesto "PyQt6.uic" (lebo fromlist-mechanizmus interne používa
        # module.__name__, nie pôvodne požadovaný názov). Vytvoríme preto
        # samostatný proxy modul s __name__ == "PyQt6" a explicitne mu
        # nastavíme atribút 'uic', aby sa fromlist-fallback import vôbec
        # nemusel spúšťať.
        # -------------------------------------------------------------------
        if spec.name == 'PyQt6':
            import types
            proxy = types.ModuleType('PyQt6')
            proxy.__dict__.update(mod.__dict__)
            proxy.__name__ = 'PyQt6'

            fake_uic = types.ModuleType("uic")
            fake_uic.loadUi = _pyside_load_ui_mimic
            proxy.uic = fake_uic
            sys.modules['PyQt6.uic'] = fake_uic

            return proxy

        return mod

    def exec_module(self, module):
        pass


def _module_fully_available(dotted_name: str) -> bool:
    """
    Bezpečná náhrada za importlib.util.find_spec() pre dotované názvy
    (napr. "PyQt6.QtWidgets").

    DÔVOD OPRAVY:
    Ak rodičovský balík (napr. "PyQt6") na sys.path neexistuje VÔBEC
    (žiadny priečinok, žiadny zvyšok, žiadny namespace package), tak
    importlib.util.find_spec("PyQt6.QtWidgets") nevráti None, ale priamo
    vyhodí ModuleNotFoundError. Presne to sa stáva v zabalenej PyInstaller
    aplikácii, kde po PyQt6 nie je ani stopa.

    Táto funkcia danú výnimku korektne odchytí a v takom prípade vráti
    False – takže sa kód správa rovnako, nech je vo venv (alebo .exe)
    čokoľvek: PyQt6 plne nainštalovaný, úplne chýbajúci, alebo len zvyšok
    po starej (od)instalácii.
    """
    try:
        return importlib.util.find_spec(dotted_name) is not None
    except ModuleNotFoundError:
        return False


def setup_qt_environment():
    # OPRAVA: Obe kontroly idú cez _module_fully_available(), ktorá
    # bezpečne odchytí ModuleNotFoundError, keď balík úplne chýba
    # (typicky v PyInstaller .exe bez akejkoľvek stopy po PyQt6).
    has_pyqt6 = _module_fully_available("PyQt6.QtWidgets")
    has_pyside6 = _module_fully_available("PySide6.QtWidgets")

    if has_pyqt6:
        print("[Qt Framework] Detekovaný plný PyQt6. Aplikácia beží natívne.")
        return

    if has_pyside6:
        print("[Qt Framework] PyQt6 nenájdený. Aktivovaný PySide6 Most (Compatibility Bridge).")
        # Nasadíme zachytávač na 1. miesto, aby prebil prípadné zvyšky zmazaného PyQt6
        sys.meta_path.insert(0, PyQtToPySideFinder())
    else:
        print("\n" + "="*60)
        print("[KRITICKÁ CHYBA] Nebol nájdený žiadny grafický framework!")
        print("Musíš nainštalovať buď PyQt6 alebo PySide6 vo svojom Venv.")
        print("Príkaz: pip install PySide6")
        print("="*60 + "\n")
        sys.exit(1)
