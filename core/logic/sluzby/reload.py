#----------------------------------------
# Súbor: core/logic/sluzby/reload.py
#----------------------------------------

import os

class DirectoryReloader:
    """
    Univerzálna služba na čítanie a filtrovanie obsahu adresárov.
    """

    @staticmethod
    def get_subdirectories(target_dir: str, required_file: str = None) -> list:
        """
        Vráti zoznam podadresárov v zadanej ceste.
        
        Args:
            target_dir (str): Cesta k hlavnému adresáru, ktorý sa má prehľadať.
            required_file (str, voliteľné): Ak je zadaný názov súboru (napr. 'install.ini'), 
                                            vrátia sa IBO tie podadresáre, ktoré tento súbor obsahujú.
        
        Returns:
            list[dict]: Zoznam slovníkov s kľúčmi 'name' a 'path'.
        """
        directories = []

        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            return directories

        for item_name in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item_name)
            
            # Zaujímajú nás len zložky, nie voľne pohodené súbory
            if os.path.isdir(item_path):
                
                # Ak vyžadujeme konkrétny súbor vnútri zložky, skontrolujeme ho
                if required_file:
                    marker_path = os.path.join(item_path, required_file)
                    if not os.path.exists(marker_path):
                        continue # Preskočí túto zložku a ide na ďalšiu
                
                # Ak sme prešli filtrami, pridáme do výsledku
                directories.append({
                    'name': item_name,
                    'path': item_path
                })
                
        return directories