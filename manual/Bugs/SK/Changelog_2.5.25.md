# VenvHub Pro - Poznámky k vydaniu (Changelog)

**Verzia:** v2.5.25  
*Tento dokument sumarizuje všetky bezpečnostné opravy, architektonické spevnenia APT systému, vylepšenia správy vlákien a lokalizácie zavedené vo verzii 2.5.25.*

---

## 🚀 Nové funkcie a vylepšenia

### Inteligentný Autoremove pri aktualizácii balíčkov (Upgrade Lifecycle) [v2.5.25]
- **Predbežné zachytávanie uvoľnených závislostí:** Implementované zachytávanie pôvodných požiadaviek balíčkov (`Requires:`) v `AptListener` ešte pred spustením príkazu `--upgrade`.
- **Automatické čistenie sirôt po update:** Ak novšia verzia balíčka zahodí alebo zníži svoje závislosti (napr. prechod na modernejšie knižnice bez pomocných balíčkov), systém ich po upgrade automaticky identifikuje a bezpečne odstráni pomocou `autoremove`.

### Robustná ochrana integrity venvu pri UV správe balíčkov [v2.5.25]
- **Presné sledovanie stavu opráv:** `PipCommandWorker` teraz striktne vyhodnocuje výsledok automatickej opravy konfliktov (`uv pip check` a auto-downgrade).
- **Zamedzenie falošnému úspechu:** Ak inštalácia prebehne, ale riešenie závislostí zlyhá, worker odošle chybový návratový kód (`exit_code = 1`). Tým zabráni predčasnému vygenerovaniu rodného listu venvu (`BirthCertificateGenerator`) a neoprávnenému zápisu do APT stavu.

### Defenzívna správa Qt vlákien a pamäte vo widgetoch [v2.5.25]
- **Zamedzenie súbehu vlákien (Concurrency Guard):** Vo `windows/pip_package_widget.py` bola implementovaná poistka blokujúca opakované alebo programatické volanie `run_pip_command`, kým predchádzajúce vlákno beží.
- **Automatické čistenie referencií:** Po dokončení operácie sa referencie `self.thread` a `self.worker` okamžite nulujú (`None`), čo eliminuje riziko zavesených objektov v pamäti.

---

## 🐛 Opravy chýb a stabilita

### PEP 503 normalizácia v `get_requires_for_package` (Oprava zabetónovania sirôt) [v2.5.25]
- **Kritická oprava:** Zjednotená normalizácia názvov balíčkov podľa štandardu PEP 503 (konverzia bodiek `.` a podčiarkovníkov `_` na pomlčky `-`).
- **Dopad:** Odstránená chyba, pri ktorej uvoľnené závislosti (napr. `zope.interface` vs `zope-interface`) neboli rozpoznané v strome uvoľnených balíčkov, čo spôsobovalo ich nesprávne zaradenie do `"explicit"` zoznamu cez Self-Healing mechanizmus.

### Bezpečné spracovanie dávok balíčkov (Chunking) v `get_dependency_graph` [v2.5.25]
- **Odstránenie deštruktívneho `continue`:** Opravené spracovanie balíčkov v dávkach po 30 (`SHOW_MULTIPLE_CHUNK_SIZE`).
- **Dopad:** Ak zlyhá alebo timeoutne načítanie informácií pre ľubovoľnú dávku, systém okamžite preruší proces a vráti chybový stav (`None`). Zamedzilo sa tým vytvoreniu neúplného stromu závislostí, ktorý by viedol k mylnému zmazaniu stále potrebných balíčkov.

### Rozlíšenie technických chýb od prázdneho virtuálneho prostredia [v2.5.25]
- **Oprava maskovania chýb:** `get_dependency_graph()` teraz striktne vracia `None` pri akejkoľvek technickej chybe (napr. nedostupný `python.exe`, poškodený `pip`, chýbajúce práva) a prázdny slovník `{}` vracia výhradne pre skutočne prázdny venv.
- **Dopad na `autoremove` a `install_sync`:** Pri zlyhaní príkazu `pip list` sa operácia okamžite preruší s chybovým hlásením, namiesto tichého úspechu alebo zbytočného nanovo inštalovania všetkých requirements.

### Case-insensitive zachytávanie inštalačných príkazov [v2.5.25]
- **Oprava konzistencie:** V `apt_listener.py` bola opravená kontrola príkazov na `cmd_lower`, čo zaručuje spoľahlivú detekciu manuálne inštalovaných balíčkov bez ohľadu na veľkosť písmen.

---

## 🌐 Lokalizácia a preklady (LanguageManager)

### 100% integrácia textov cez `LanguageManager` [v2.5.25]
- Všetky chybové stavy, varovania zlyhania dávok, pády získavania zoznamu balíčkov a UV diagnostika boli prepojené na `LanguageManager.get()`.
- Doplnené nové lokalizačné kľúče do **`sk_SK.json`** aj **`en_US.json`**:
  - `apt_err_pkg_details_code`, `apt_err_pkg_details_fail`
  - `apt_err_pkg_list_code`, `apt_err_graph_failed`, `apt_err_graph`
  - `uv_fix_error_manual` (s parametrickým výpisom konfliktných balíčkov).

---

## 📁 Modifikované a dotknuté súbory

- `core/logic/sluzby/apt_logic.py`
- `core/logic/sluzby/apt_listener.py`
- `core/logic/button/pip/pip_command_worker.py`
- `windows/pip_package_widget.py`
- `/translations/sk_SK.json`
- `/translations/en_US.json`