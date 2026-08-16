# VenvHub Pro - Poznámky k vydaniu (Changelog)

**Verzia:** v2.5.24 (Prechod z verzie v2.5.23)  
*Tento dokument sumarizuje všetky zmeny, nové funkcie a opravy chýb uvedené vo verzii 2.5.24.*

---

## 🚀 Nové funkcie a vylepšenia

### Automatické vstrekovanie základných build nástrojov (`setuptools` & `wheel`)
- **Samoopravné vytváranie VENV:** Upravené súbory `create.py` a `pip_installer.py` automaticky inštalujú `setuptools` a `wheel` do každého novovytvoreného virtuálneho prostredia a opraveného Python runtime.
- **Podpora pre Embedded Python:** Zabezpečené, že Embedded a Portable Python prostredia sú hneď po vytvorení plne vybavené na zostavovanie a inštaláciu komplexných balíčkov bez potreby manuálneho zásahu.

### Viacúrovňová normalizácia ciest pre vnorené requirements súbory
- **Rekurzívne vyhľadávanie súborov:** Implementovaná metóda `PipManager._get_all_requirement_files()`, ktorá rekurzívne preskúma a nájde všetky vnorené requirements súbory (napr. `-r subfolder/requirements.txt`).
- **Kompletná sanitácia ciest:** Integrovaná služba `PathNormalizer.sanitize_requirements_file()` na všetky nájdené súbory ešte pred spustením inštalácie. To zaručuje cross-platform kompatibilitu lomítok v cestách (`/` vs `\`).

### Zachovanie natívnych špecifikácií balíčkov a markerov prostredia
- **Zachovanie plnej funkcionality Pip/UV:** Logika inštalácie z requirements bola upravená tak, aby zachovala presné verzie (`==`, `>=`), podmienky prostredia (`sys_platform`), extra indexy aj priame editable odkazy (`-e`), pričom eliminovala chyby v syntaxi ciest.

---

## 🐛 Opravy chýb a stabilita

### Oprava zlyhaní PEP 517 Build Backendu
- **Vyriešená chyba `BackendUnavailable`:** Opravený kritický problém, kedy inštalácia lokálnych editable balíčkov (`-e`) zlyhávala na chybe `Cannot import 'setuptools.build_meta'`. Predinštalovanie `setuptools` a `wheel` do prostredia zabezpečuje hladký priebeh PEP 517 buildov.

### Oprava nesúladu lomítok pre príkaz `-r` na Windowse a Linuxe
- **Oprava parsovania ciest:** Vyriešené chyby, kedy `pip install -r` zlyhal kvôli neosšetreným spätnejším lomítkam na Windowse alebo zlému formátu relatívnych ciest vo vnorených súboroch závislostí.

### Post-Processing Embedded Python prostredí
- **Vylepšenie služby `EmbedPythonCreated`:** Optimalizovaná verifikácia po vytvorení prostredia (`verify_pip_functional` a `fix_pth_file`), ktorá zabezpečuje odblokovanie `._pth` súborov a okamžitý prístup k `site-packages`.