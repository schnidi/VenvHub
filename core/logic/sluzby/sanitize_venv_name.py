#----------------------------------------
# Súbor: core/logic/sluzby/sanitize_venv_name.py
#----------------------------------------

import re

def sanitize_venv_name(name: str) -> str:
    """
    Pripraví bezpečný názov pre zložku vo Windowse.
    Zámerne zachováva diakritiku a iné jazyky (Azbuka, Čínština),
    aby aplikácia zostala user-friendly pre celý svet.
    
    Čo funkcia robí:
    1. Nahradí medzery podtržníkmi (CMD nezvláda medzery v cestách).
    2. Odstráni zakázané znaky Windowsu pre tvorbu priečinkov: < > : " / \\ | ? *
    """
    if not name:
        return "unnamed_venv"
        
    # 1. Nahradíme medzery (veľmi dôležité)
    safe_name = name.replace(" ", "_")
    
    # 2. Odstránime znaky, ktoré by zhodili File System Windowsu
    # V regulárnom výraze je \\ správne pre zápas jednej lomky
    safe_name = re.sub(r'[<>:"/\\|?*]', '', safe_name)
    
    return safe_name