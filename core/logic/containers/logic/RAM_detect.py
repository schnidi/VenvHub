#----------------------------------------
# Súbor: core/logic/containers/logic/RAM_detect.py
#----------------------------------------

import psutil

class RAMDetector:
    """
    Služba pre zisťovanie spotreby operačnej pamäte (RAM) bežiacich procesov.
    """

    @staticmethod
    def get_memory_mb(pid: int) -> float:
        """
        Vráti celkové využitie pamäte (v MB) pre daný proces a všetky jeho podprocesy.
        Zahŕňa to rodičovský terminál (cmd.exe) aj v ňom bežiaci skript (python.exe).
        
        Args:
            pid (int): ID hlavného procesu.
            
        Returns:
            float: Využitie pamäte v Megabytoch (MB).
        """
        if not pid:
            return 0.0

        try:
            total_bytes = 0
            parent = psutil.Process(pid)
            
            # Prirátame pamäť samotného rodiča (napr. cmd alebo samotný python v silent režime)
            total_bytes += parent.memory_info().rss
            
            # Prirátame pamäť všetkých dcérskych procesov
            for child in parent.children(recursive=True):
                try:
                    total_bytes += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            # Prevod bajtov na megabyty
            return total_bytes / (1024 * 1024)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Proces už medzitým mohol skončiť
            return 0.0