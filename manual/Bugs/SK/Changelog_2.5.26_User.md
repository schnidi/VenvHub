# VenvHub Pro - Poznámky k vydaniu (Changelog)

**Verzia:** v2.5.26  
*Táto aktualizácia prináša automatické čistenie nepotrebných knižníc po hromadnej aktualizácii, ochranu pred nechceným odinštalovaním balíčkov z requirements.txt, plnú integráciu lokálnych balíčkov (pip -e) a zvýšenie stability na pozadí.*

---

## 🚀 Nové vylepšenia

### 🧹 Automatické upratanie po Hromadnej aktualizácii (Bulk Autoremove)
- **Čisté prostredie po každom update:** Keď kliknete na tlačidlo **Aktualizovať všetko** (či už v okne Pip Manažéra, v hlavnom okne Správcu alebo cez ikonu blesku v tabuľke), aplikácia po úspešnom zaktualizovaní balíčkov automaticky skontroluje celý systém.
- **Odstránenie starých pomocných knižníc:** Všetky staré a nepoužívané závislosti (siroty), ktoré novšie verzie programov už nepotrebujú, sú ihneď po hromadnom update automaticky a bezpečne odinštalované.
- **Jednotné fungovanie:** Všetky spôsoby hromadnej aktualizácie v celej aplikácii teraz zaručujú rovnaké a maximálne čisté správanie vášho virtuálneho prostredia.

### ⚠️ Ochrana a varovanie pred odinštalovaním kľúčových balíčkov (`requirements.txt`)
- **Inteligentné upozornenie:** Ak sa pokúsite odinštalovať balíček, ktorý je explicitne definovaný v súbore `requirements.txt` daného projektu, aplikácia zobrazí dôrazné varovné hlásenie s upozornením, že prostredie už nebude plne zodpovedať definícii projektu.
- **Trojstupňová ochrana:** Aplikácia bezpečne rozlišuje medzi bežnými balíčkami, chránenými podzávislosťami (ktoré nepovolí zmazať, kým ich iný balíček potrebuje) a hlavnými balíčkami projektu.
- **Plná lokalizácia:** Dialógové okná a hlásenia sú kompletne preložené do slovenčiny aj angličtiny.

### ✏️ Plná integrácia pre lokálne balíčky (`pip -e`)
- **Automatická správa závislostí:** Vývojové balíčky inštalované z lokálnych priečinkov v editovateľnom režime sú teraz plnohodnotne zapojené do inteligentného APT systému.
- **Čistenie po odinštalovaní:** Pri odinštalovaní balíčka (z okna *Lokálne balíčky* aj z bežného *Pip Manažéra*) sa automaticky spustí čistenie a bezpečne sa odstránia všetky osirelé knižnice, ktoré balíček využíval.

### 🛠️ Opravy chýb a vyššia stabilita
- **Spoľahlivejšie úlohy na pozadí:** Opravená chyba zachytávania signálov v pamäti (Garbage Collector bug), ktorá mohla v určitých prípadoch spôsobiť tiché vynechanie automatického upratovania po odinštalovaní.
- **Presnejšia evidencia balíčkov:** Aktualizácia balíčkov už umelo neoznačuje ich pomocné podknižnice ako „manuálne nainštalované“, vďaka čomu systém vždy presne vie, ktoré závislosti je bezpečné v budúcnosti upratať.

---

## 📁 Dotknuté súbory

- `core/logic/sluzby/apt_listener.py`
- `core/logic/sluzby/apt_logic.py`
- `windows/pip_package_widget.py`
- `translations/sk_SK.json`
- `translations/en_US.json`