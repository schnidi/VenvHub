#----------------------------------------
# Súbor: core/logic/sluzby/unzip.py
#----------------------------------------

import os
import zipfile
from typing import Callable, Optional
from core.logic.language_manager import LanguageManager

class ZipExtractor:
    """
    Služba pre bezpečné a efektívne rozbaľovanie .zip archívov.
    Ponúka možnosť sledovania priebehu cez voliteľný callback.
    """

    @staticmethod
    def extract(source_zip: str, 
                destination_dir: str, 
                progress_callback: Optional[Callable[[int, int, str], None]] = None) -> dict:
        """
        Rozbalí obsah .zip archívu do cieľového priečinka.

        Args:
            source_zip (str): Cesta k zdrojovému .zip súboru.
            destination_dir (str): Cesta k cieľovému priečinku, kam sa má archív rozbaliť.
                                   Ak neexistuje, bude vytvorený.
            progress_callback (Optional[Callable]): Funkcia, ktorá sa volá počas extrakcie
                                                     pre každý súbor. Očakáva tri argumenty:
                                                     - current_file_num (int): Poradové číslo aktuálneho súboru.
                                                     - total_files (int): Celkový počet súborov v archíve.
                                                     - current_filename (str): Názov aktuálne rozbaľovaného súboru.

        Returns:
            dict: Slovník s výsledkom operácie.
                  - {'success': True} v prípade úspechu.
                  - {'success': False, 'error': 'Chybová správa'} v prípade zlyhania.
        """
        # 1. Validácia vstupov
        if not os.path.exists(source_zip):
            err_msg = LanguageManager.get("zip_err_src_missing", "Zdrojový súbor neexistuje: {file}").format(file=source_zip)
            return {'success': False, 'error': err_msg}
        
        if not zipfile.is_zipfile(source_zip):
            err_msg = LanguageManager.get("zip_err_invalid", "Súbor nie je platný .zip archív: {file}").format(file=source_zip)
            return {'success': False, 'error': err_msg}

        # 2. Príprava cieľového priečinka
        try:
            os.makedirs(destination_dir, exist_ok=True)
        except OSError as e:
            err_msg = LanguageManager.get("zip_err_mkdir", "Nepodarilo sa vytvoriť cieľový priečinok: {error}").format(error=e)
            return {'success': False, 'error': err_msg}

        # 3. Samotná extrakcia
        try:
            with zipfile.ZipFile(source_zip, 'r') as zip_ref:
                
                # Ak máme k dispozícii callback pre sledovanie priebehu
                if progress_callback:
                    file_list = zip_ref.infolist()
                    total_files = len(file_list)
                    
                    for i, member in enumerate(file_list):
                        # Zavoláme callback s aktuálnymi informáciami
                        progress_callback(i + 1, total_files, member.filename)
                        zip_ref.extract(member, destination_dir)
                
                # Ak callback nemáme, použijeme rýchlejšiu metódu extractall
                else:
                    zip_ref.extractall(destination_dir)

            return {'success': True}

        except zipfile.BadZipFile:
            err_msg = LanguageManager.get("zip_err_corrupt", "Archív je poškodený alebo má neplatný formát.")
            return {'success': False, 'error': err_msg}
        except PermissionError:
            err_msg = LanguageManager.get("zip_err_perms", "Nedostatok oprávnení na zápis do priečinku: {dir}").format(dir=destination_dir)
            return {'success': False, 'error': err_msg}
        except Exception as e:
            err_msg = LanguageManager.get("zip_err_unknown", "Neznáma chyba pri rozbaľovaní: {error}").format(error=e)
            return {'success': False, 'error': err_msg}

# --- Príklad použitia (tento kód by si mal v reálnej aplikácii preč) ---
if __name__ == '__main__':
    
    # Definovanie jednoduchej funkcie pre zobrazenie priebehu v konzole
    def my_progress_reporter(current, total, filename):
        percentage = (current / total) * 100
        msg = LanguageManager.get("zip_log_extracting", "Rozbaľujem: [{current}/{total}] {percent:.1f}% - {file}").format(
            current=current, total=total, percent=percentage, file=filename
        )
        print(msg)

    # Cesty (uprav si ich podľa potreby pre testovanie)
    test_zip_path = "C:/path/to/your/test_file.zip"
    test_dest_path = "C:/path/to/your/output_folder"

    msg_try = LanguageManager.get("zip_log_try", "Pokúšam sa rozbaliť '{src}' do '{dest}'...").format(src=test_zip_path, dest=test_dest_path)
    print(msg_try)
    
    # Volanie extrakcie s funkciou pre sledovanie priebehu
    result = ZipExtractor.extract(test_zip_path, test_dest_path, progress_callback=my_progress_reporter)

    if result['success']:
        print(LanguageManager.get("zip_log_success", "\nArchív bol úspešne rozbalený!"))
    else:
        err_msg = LanguageManager.get("zip_log_error", "\nCHYBA: {error}").format(error=result['error'])
        print(err_msg)