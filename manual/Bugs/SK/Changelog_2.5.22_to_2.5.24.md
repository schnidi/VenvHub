# VenvHub Pro - Konsolidované poznámky k vydaniu (Changelog)

**Verzia:** v2.5.24 (Kumulatívne vydanie od v2.5.22 po v2.5.24)  
*Tento dokument sumarizuje všetky architektonické vylepšenia, nové funkcie, bezpečnostné opravy a opravy chýb zavedené vo verziách 2.5.23 a 2.5.24.*

---

## 🚀 Nové funkcie a vylepšenia

### Automatická injekcia základných nástrojov pre zostavenie (`setuptools` & `wheel`) [v2.5.24]
- **Samo-opravné vytváranie venv:** Aktualizované súbory `create.py` a `pip_installer.py` automaticky inštalujú `setuptools` a `wheel` do každého novovytvoreného virtuálneho prostredia aj opraveného Python runtime.
- **Podpora pre Embedded Python:** Zabezpečené, že embedded a prenosné Python prostredia sú ihneď po vytvorení plne vybavení na zostavovanie a inštaláciu zložitejších balíčkov bez potreby manuálneho zásahu.

### Viacúrovňová normalizácia ciest pre vnorené požiadavky [v2.5.24]
- **Rekurzívne vyhľadávanie súborov:** Implementovaná metóda `PipManager._get_all_requirement_files()` na rekurzívne skenovanie a rozlíšenie všetkých vnorených súborov s požiadavkami (napr. `-r subfolder/requirements.txt`).
- **Kompletná sanitácia ciest:** Integrovaná funkcia `PathNormalizer.sanitize_requirements_file()` naprieč všetkými nájdenými súbormi pred spustením inštalácie. To zaručuje kompatibilitu lomiek medzi platformami (`/` vs `\`).

### Zachovanie natívnych špecifikácií balíčkov a markerov prostredia [v2.5.24]
- **Plné zachovanie funkcií Pip/UV:** Refaktorovaná logika inštalácie požiadaviek tak, aby zachovávala verzie (`==`, `>=`), markery prostredia (`sys_platform`), extra index URL aj priame editable odkazy (`-e`), pričom sa eliminujú chyby v syntaxi ciest.

### Čistá architektúra a Princíp jednej zodpovednosti (APT systém) [v2.5.23]
- **Štrukturálna prerábka:** APT systém závislostí prešiel výrazným vyčistením architektúry. `AptListener` bol zbavený ťažkej logiky a teraz funguje striktne ako Interceptor (zachytávač akcií).
- **Migrácia logiky:** Všetky analytické metódy (napr. `_get_editable_packages`, `_is_package_required_by_others`, `_get_requires_for_package`) boli presunuté do jadra `AptLogic`. Logika vyhodnocuje dáta, zatiaľ čo listener spravuje iba tok UI.

### Injekcia závislostí a prevrátenie riadenia (Container Logic) [v2.5.23]
- **Moderný návrhový vzor:** Implementovaná Injekcia závislostí (Dependency Injection) v `HookManager` (`hook.py`).
- **Dynamická registrácia:** Namiesto natvrdo napísaných závislostí teraz `HookManager` umožňuje externým modulom (ako `RespawnManager`) dynamicky registrovať ich funkcie kontroly pádov (`register_respawn_checker`). Správa životného cyklu je vďaka tomu modulárna a ľahko testovateľná.

---

## 🐛 Opravy chýb a stabilita

### Bezpečnostná oprava zraniteľností Path Traversal a Symlinkov v `RequirementsParser` [v2.5.24]
- **Vymáhanie hraníc pre vstupný súbor:** Opravená kritická bezpečnostná diera v `RequirementsParser.parse()`, pri ktorej vstupné súbory (vrátane symlinkov ukazujúcich mimo adresár projektu) obchádzali kontrolu Path Traversal. Kontrola hraníc adresára sa teraz striktne vykonáva na začiatku pre hlavný súbor ako aj pre vnorené súbory (`-r`).

### Oprava zlyhaní PEP 517 Build Backendov [v2.5.24]
- **Vyriešená chyba `BackendUnavailable`:** Opravená chyba, pri ktorej inštalácia lokálnych editable balíčkov (`-e`) zlyhávala na chybovej hláške `Cannot import 'setuptools.build_meta'`. Predinštalovanie `setuptools` a `wheel` zabezpečuje hladký priebeh PEP 517 buildov.

### Oprava nekompatibility lomiek (Windows/Linux) pri príznaku `-r` [v2.5.24]
- **Oprava parsovania ciest:** Vyriešené chyby, pri ktorých `pip install -r` zlyhával kvôli neosetreným spätným lomkám vo Windows alebo nesprávnym relatívnym cestám vo vnútri vnorených súborov.

### Post-processing Embedded Python prostredia [v2.5.24]
- **Vylepšenie služby `EmbedPythonCreated`:** Optimalizované overenie po vytvorení (`verify_pip_functional` & `fix_pth_file`), ktoré zabezpečuje odblokovanie `._pth` súborov a okamžitý prístup k `site-packages`.

### Odstránenie cyklickej závislosti v APT systéme [v2.5.23]
- **Oprava:** Úplne odstránená kritická cyklická závislosť (Circular Import Loop) medzi `apt_listener.py` a `apt_logic.py`.
- **Dopad:** Zabraňuje skrytým pádom typu `ImportError` pri štarte aplikácie alebo pri operáciách na pozadí.

### Odstránenie cyklickej závislosti v Container Hook [v2.5.23]
- **Oprava:** Prerušená architektonická slučka medzi `hook.py` a `respawn_multi.py` v zložke logiky kontajnerov.
- **Dopad:** `hook.py` už nemusí priamo importovať Respawn Manager na kontrolu počtu zlyhaní, čo zaručuje plynulú správu terminálov na pozadí.

---

## 🧹 Refaktorizácia kódu a údržba projektu

### Oddelenie okna "O aplikácii" (Služba `AboutLogic`) [v2.5.24]
- **Eliminácia cyklických závislostí:** Vyňatá viacjazyčná HTML logika a inicializácia dialógu z `CustomTitleBar` do samostatnej služby `AboutLogic` (`core/logic/sluzby/about_logic.py`).
- **Dynamická registrácia:** Dialóg `AboutDialog` sa teraz registruje pri štarte v `main.py`, čo čistí architektúru a eliminuje riziko cyklických importov pri otváraní okna.

### 100% Validácia čistej architektúry [v2.5.23 - v2.5.24]
- Vďaka odstráneniu cyklických importov naprieč APT logikou, Container hookmi a UI službami projekt úspešne prechádza prísnymi architektonickými testami s **nulovým** výskytom cyklických závislostí.

---

## 📁 Modifikované a dotknuté súbory

- `core/logic/sluzby/requirements_parser.py`
- `core/logic/sluzby/apt_listener.py`
- `core/logic/sluzby/apt_logic.py`
- `core/logic/sluzby/about_logic.py`
- `core/logic/sluzby/pip_installer.py`
- `core/logic/sluzby/create.py`
- `core/logic/containers/logic/hook.py`
- `core/logic/containers/logic/respawn_multi.py`
- `main.py`