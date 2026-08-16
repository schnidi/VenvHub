# VenvHub Pro - Konsolidované poznámky k vydaniu (Changelog)

**Verzia:** v2.5.25  
*Tento dokument sumarizuje všetky architektonické vylepšenia, optimalizácie výkonu, opravy chýb a vylepšenia stability zavedené vo verzii 2.5.25.*

---

## 🚀 Nové funkcie a vylepšenia stability

### 1. Plná kompatibilita správy závislostí so štandardom PEP 503 [v2.5.25]
- **Presná normalizácia balíčkov:** Mechanizmus správy balíčkov (APT logika) bol aktualizovaný na striktné dodržiavanie štandardu PEP 503. Názvy balíčkov s bodkami (`.`) alebo podčiarkovníkmi (`_`) (napr. `zope.interface`, `backports.zoneinfo`) sú v internom grafe správne normalizované.
- **Bezchybný manažment sirôt:** Vďaka zjednotenej normalizácii už nedochádza k nesprávnemu uzamykaniu uvoľnených závislostí a funkcia inteligentného čistenia (`autoremove`) pracuje s maximálnou presnosťou.

### 2. Zvýšená integrita a bezpečnosť pri analýze závislostí [v2.5.25]
- **Ochrana pred neúplnými dátami (Fail-Safe Dependency Graph):** Pri zisťovaní stavu nainštalovaných balíčkov bol zavedený atómový prístup. Ak proces načítania informácií zlyhá alebo je prerušený, systém operáciu bezpečne zastaví namiesto toho, aby pracoval s neúplným zoznamom.
- **Prevencia nechceného zmazania:** Týmto krokom je úplne vylúčené riziko, že by funkcia automatického odstraňovania nepoužívaných balíčkov (`autoremove`) omylom vyhodnotila potrebnú knižnicu ako osirelú kvôli dočasnej chybe čítania.
- **Fail-safe aj pri kontrole pred odinštalovaním:** Rovnaký princíp bol doplnený aj do kontroly reverzných závislostí, ktorá beží tesne pred samotným odinštalovaním balíčka. Ak sa v danom momente nepodarí spoľahlivo zistiť stav prostredia, operácia sa bezpečne zastaví a používateľ je o tom informovaný, namiesto toho, aby sa odinštalovanie ticho povolilo bez overenia.

### 3. Vylepšené čistenie starých knižníc pri aktualizácii balíčkov [v2.5.25]
- **Presné sledovanie životného cyklu:** Pri operáciách `pip install --upgrade` (alebo `-U`) si systém zaznamená strom závislostí pôvodnej verzie balíčka ešte pred začatím inštalácie novej verzie.
- **Okamžité uvoľnenie nepotrebných väzieb:** Ak nová verzia balíčka už nepotrebuje niektoré staršie podporné knižnice, systém ich správne identifikuje a umožní ich automatické prečistenie.

### 4. Spresnená indikácia výsledkov pri inštaláciách cez UV [v2.5.25]
- **Presnejšia spätná väzba:** Vylepšená komunikácia s ultra-rýchlym inštalátorom UV (Astral). Ak po úspešnej inštalácii balíčka následná kontrola závislostí odhalí konflikt, ktorý sa nepodarí automaticky vyriešiť, aplikácia presne ohlási stav a zabráni nesprávnemu zápisu stavu prostredia.

---

## 🐛 Opravy chýb a systémové záplaty

### Oprava nezrovnalostí v názvoch balíčkov pri čítaní závislostí 
- **Popis:** Odstránený nesúlad medzi surovým textovým výstupom správcu balíčkov a normalizovanými kľúčmi v grafe závislostí, čo spôsobovalo, že niektoré balíčky sa po odinštalovaní nadradenej knižnice neodstránili.
- **Riešenie:** Všetky extrahované závislosti prechádzajú dôslednou PEP 503 normalizáciou.

### Ošetrenie chybových stavov pri načítavaní zoznamu balíčkov 
- **Popis:** V prípade zlyhania systémového príkazu na výpis balíčkov aplikácia mylne považovala virtuálne prostredie za prázdne a hlásila úspešné dokončenie operácie.
- **Riešenie:** Chybové stavy sú teraz jednoznačne rozlíšené od prázdneho prostredia a používateľ je informovaný o skutočnej chybe.

### Zamedzenie vzniku neúplného grafu závislostí 
- **Popis:** Pri zlyhaní čítania detailov jednej skupiny balíčkov mohol vzniknúť čiastočný graf, ktorý nezobrazoval všetky prepojenia.
- **Riešenie:** Akákoľvek chyba pri zbere informácií o balíčkoch okamžite a bezpečne preruší analýzu.

### Zjednotenie rozlišovania veľkosti písmen pri detekcii inštalovaných balíčkov 
- **Popis:** Pri spracovaní príkazu na inštaláciu/upgrade sa časť logiky (rozpoznanie, či ide o inštaláciu) vyhodnocovala necitlivo na veľkosť písmen, zatiaľ čo samotné vyťaženie zoznamu inštalovaných balíčkov z toho istého príkazu prebiehalo citlivo na veľkosť písmen. Pri nezvyčajnom tvare príkazu tak balíček mohol zostať neoznačený ako explicitný.
- **Riešenie:** Vyťaženie zoznamu inštalovaných balíčkov teraz používa rovnaké, na veľkosť písmen necitlivé vyhodnotenie ako zvyšok logiky rozpoznávania príkazu.

### Zachytenie uvoľnených závislostí pred samotnou aktualizáciou 
- **Popis:** Pri aktualizácii balíčka na novšiu verziu sa staré závislosti zisťovali až po prepísaní súborov na disku, kedy už pôvodné požiadavky nebolo možné dohľadať.
- **Riešenie:** Analýza pôvodných požiadaviek prebieha vopred.

### Korekcia stavového kódu pri zlyhaní UV kontroly závislostí 
- **Popis:** V určitých prípadoch UV inštalátor hlásil úspech aj vtedy, keď automatická oprava zistených konfliktov zlyhala.
- **Riešenie:** Výsledný stav inštalačnej úlohy teraz zohľadňuje aj výsledok opravnej fázy kompatibility.

### Fail-safe správanie pri kontrole reverzných závislostí pred odinštalovaním 
- **Popis:** Kontrola, či balíček pred odinštalovaním nevyžaduje niektorý iný nainštalovaný balíček, v prípade dočasného zlyhania zisťovania stavu prostredia tichο vyhodnotila situáciu rovnako, ako keby balíček naozaj nikto nevyžadoval — odinštalovanie tak mohlo prejsť bez skutočného overenia.
- **Riešenie:** Zlyhanie zisťovania stavu prostredia sa teraz jednoznačne odlišuje od potvrdeného "balíček nikto nevyžaduje". Pri neistote sa odinštalovanie zablokuje a používateľ je informovaný, že overenie zlyhalo a má to skúsiť znova.

### Bezpečné ukončovanie vlákna pri prekrývajúcich sa pip operáciách 
- **Popis:** Dokončenie pip operácie čítalo referenciu na bežiace vlákno až v momente svojho spustenia. Pri prípadnom prekrytí dvoch operácií nad tým istým panelom balíčka (napr. budúcim obídením existujúcich UI poistiek) tak hrozilo, že sa ukončí/počká na nesprávne, novšie a stále bežiace vlákno inej operácie namiesto vlákna tej, ktorá reálne skončila.
- **Riešenie:** Referencia na vlákno konkrétnej operácie sa teraz zachytáva priamo pri jej spustení a odovzdáva sa dokončovaciemu spracovaniu explicitne, takže vždy pracuje so správnym, "svojím" vláknom bez ohľadu na to, čo medzičasom ukazuje zdieľaný stav panela.

---

## 🌐 Lokalizácia

- Pridaný nový prekladový kľúč `apt_err_cannot_verify_deps` (EN aj SK) pre hlásenie z opravy (Bezpečné ukončovanie vlákna pri prekrývajúcich sa pip operáciách) — informuje používateľa, že overenie závislostí pred odinštalovaním zlyhalo a operácia bola z bezpečnostných dôvodov zastavená.

---

## 📁 Dotknuté súbory jadra aplikácie

- `core/logic/sluzby/apt_logic.py`
- `core/logic/sluzby/apt_listener.py`
- `core/logic/button/pip/pip_command_worker.py`
- `windows/pip_package_widget.py`