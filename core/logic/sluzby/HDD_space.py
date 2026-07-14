#----------------------------------------
# Súbor: core/logic/sluzby/HDD_space.py
#----------------------------------------

import os
import shutil

class HDDSpaceLogic:
    """
    Služba pre analýzu diskového priestoru a obsahu priečinkov.
    """

    @staticmethod
    def get_free_space_mb(target_path: str) -> float:
        """Vráti voľné miesto na disku (kde leží target_path) v MB."""
        try:
            # Ak cesta ešte neexistuje, zistíme disk z rodičovskej cesty
            while not os.path.exists(target_path) and target_path != "":
                target_path = os.path.dirname(target_path)
                
            total, used, free = shutil.disk_usage(target_path)
            return free / (1024 * 1024)
        except Exception:
            return 0.0

    @staticmethod
    def get_directory_info(dir_path: str) -> dict:
        """
        Prehľadá adresár od najhlbších vrstiev (bottom-up).
        Vráti celkovú veľkosť v bajtoch a zoznam VŠETKÝCH súborov a zložiek.
        Tento zoznam je ideálny na mazanie, lebo zložky sú na konci.
        """
        total_size = 0
        all_items = []
        
        if not os.path.exists(dir_path):
            return {"size_bytes": 0, "items": []}

        try:
            for root, dirs, files in os.walk(dir_path, topdown=False):
                for f in files:
                    filepath = os.path.join(root, f)
                    all_items.append(filepath)
                    try:
                        total_size += os.path.getsize(filepath)
                    except: pass
                for d in dirs:
                    all_items.append(os.path.join(root, d))
                    
            all_items.append(dir_path) # Samotný hlavný priečinok na záver
        except Exception:
            pass

        return {"size_bytes": total_size, "items": all_items}

    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """Prevedie bajty na čitateľný text (MB, GB)."""
        mb = size_bytes / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GB"
        return f"{mb:.2f} MB"