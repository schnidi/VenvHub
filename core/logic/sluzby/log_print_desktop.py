import os
from datetime import datetime

class DesktopLogger:
    """
    Nezávislý logger na plochu. Každý modul (súbor) si môže vytvoriť vlastnú inštanciu
    s vlastným názvom súboru a vlastným nezávislým prepínačom zapnutia/vypnutia.
    """
    def __init__(self, is_enabled: bool, filename: str):
        self.is_enabled = is_enabled
        self.filename = filename

    def write(self, message: str):
        """Zapíše log, iba ak je táto konkrétna inštancia povolená."""
        if not self.is_enabled:
            return
            
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            log_file = os.path.join(desktop, self.filename)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')}] {message}\n")
        except Exception:
            pass