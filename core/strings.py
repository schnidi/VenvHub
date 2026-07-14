from enum import Enum

class T(Enum):
    """
    CENTRÁLNY KATALÓG TEXTOV A KĽÚČOV
    VS Code vám ukáže slovenský text pri napísaní 'T.'
    """

    # --- SYMBOLY A IKONY ---
    PLUS = "+"
    MINUS = "-"
    GEAR = "⚙"
    REFRESH_ICON = "🔄"
    FOLDER = "📁"
    PIN_ICON = "📌"
    TERMINAL_ICON = "🖥"
    CHECK = "✅"
    CROSS = "❌"
    PLAY = "▶"
    STOP = "■"
    DOT = "●"

    # --- TLAČIDLÁ A AKCIE ---
    BTN_CREATE = "+ VYTVORIŤ"
    BTN_INSTALL = "Inštalovať"
    BTN_UNINSTALL = "Uninstall"
    BTN_UPDATE = "Update"
    BTN_REFRESH = "🔄 Obnoviť zoznam"
    BTN_TERMINAL = "Otvorit terminál"
    BTN_UNINSTALL_RED = "❌ Odinštalovať"
    BTN_UPDATE_LATEST = "⬆️ Aktualizovať na najnovšiu"
    BTN_UPDATE_ALL = "⬆️ Aktualizovať všetky zastarané"
    BTN_FREEZE = "📜 Freeze > requirements.txt"
    BTN_SAVE_GROUP = "Uložiť zmeny v skupine"
    BTN_REMODE = "Prepnúť režim Single/Multi"

    # --- TOOLTIPY ---
    btn_pin_tooltip = "Stále navrchu"
    btn_toggle_mode_tooltip = "Prepnúť režim Single/Multi"
    btn_update_uptodate = "✅ Verzia je aktuálna"
    tip_newer_version = "Dostupná novšia verzia!"

    # --- HLAVNÉ NADPISY A TABY ---
    TAB_VENVS = "Správa Venvs"
    TAB_MULTI = "Hromadné Spúšťanie (Multi-run)"
    TITLE_PIP_MANAGER = "Pip Manažér (vyberte venv v tabuľke)"
    TITLE_QUICK_SETTINGS = "Quick Settings"
    STEP_1 = "1. Výber prostredia"
    STEP_2 = "2. Nastavenie spustenia"
    STEP_3 = "3. Akcie"

    # --- LABELI A TABUĽKY ---
    COL_PROJECT = "Projekt"
    COL_VENV = "Venv"
    COL_PROJECT_VENV = "Projekt / Venv"
    COL_SCRIPT = "Spúšťací skript"
    COL_PKG_NAME = "Názov balíčka"
    COL_INSTALLED_VER = "Nainštalovaná verzia"
    COL_LATEST_VER = "Najnovšia verzia"
    LBL_ROOT_PROJECTS = "Koreň projektov:"
    LBL_VENV_HUB = "Venv Hub:"
    LBL_CURRENT_PROJECT = "Aktuálny projekt:"
    LBL_LOADER = "Načítavam..."
    LBL_STATUS = "Stav"

    # --- FORMÁTOVANÉ TEXTY (s parametrami {0}, {1}) ---
    btn_update_fmt = "⬆️ Aktualizovať na {0}"
    fmt_selected_venv = "Zvolený: {0} (Python {1})"
    fmt_group_members = "Členovia skupiny: {0}"
    lbl_header_fmt = "Správca balíčkov pre: {0}"
    lbl_installed_fmt = "Nainštalovaná verzia: {0}"
    lbl_latest_fmt = "Najnovšia verzia: {0}"
    group_actions_fmt = "Akcie pre: {0}"

    # --- SPRÁVY (MESSAGES) ---
    msg_done = "--- HOTOVO ---"
    msg_please_wait = "Prosím, čakajte..."
    msg_loading_pkgs = "🔄 Načítavam zoznam balíčkov, prosím čakajte..."
    msg_busy = "!!! Už prebieha iná pip operácia, počkajte na jej dokončenie. !!!"
    
    msg_confirm_delete = "Naozaj chcete úplne vymazať venv:\n{0}?"
    """
    ⚠️ VAROVANIE: Kritická akcia.
    
    Zobrazí sa v potvrdzovacom dialógu pred zmazaním priečinka.
    {0} - Názov virtuálneho prostredia (venv).
    """
    msg_confirm_uninstall = "Naozaj chcete odinštalovať balíček "
    msg_all_updated = "--- Všetko aktualizované ---"
    msg_check_log = "Operácia zlyhala. Skontrolujte log pre viac detailov."
    msg_all_pkgs_ok = ">>> Zhrnutie: Všetky ostatné balíčky sú aktuálne. Niet čo robiť."

    # --- CHYBY (ERRORS) ---
    err_critical = "KRITICKÁ CHYBA: {0}"
    err_select_venv = "CHYBA: Najprv vyberte platné prostredie (venv)."
    err_list_failed = "CHYBA: Nepodarilo sa získať zoznam balíčkov."
    title_error = "Chyba"
    title_critical_error = "Kritická chyba"
    title_confirm = "Potvrdenie"

    # --- KLONOVANIE (CLONE) ---
    clone_dialog_title = "Klonovať / Zálohovať Venv"
    clone_preparing = "Pripravujem klonovanie..."
    clone_creating_venv = "Vytváram nové prostredie: {0}..."
    clone_installing_pkgs = "Inštalujem balíčky (môže trvať dlhšie)..."
    ctx_clone_venv = "🐑 Klonovať / Zálohovať Venv"

    # --- OSTATNÉ ---
    SELECTED_NONE = "Zvolený: ---"
    DEFAULT = "Predvolený"
    SYSTEM_DEFAULT = "System Default"
    VERSION = "Verzia"
    PROJECT = "Projekt"
    VENV = "Venv"