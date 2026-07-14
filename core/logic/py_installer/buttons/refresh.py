#----------------------------------------
# Súbor: core/logic/py_installer/buttons/refresh.py
#----------------------------------------

class TargetRefreshHandler:
    """
    Spravuje kliknutia na tlačidlá '🔄' (Refresh) v sekcii cieľov.
    Samotná logika načítania je delegovaná na metódy okna, 
    aby sme mali prístup k UI elementom a k jadru (ProjectCore).
    """

    @staticmethod
    def refresh_projects(window):
        """
        Reakcia na kliknutie tlačidla pre obnovu zoznamu projektov.
        """
        window.populate_projects()
        # window.populate_projects() sa postará aj o následné
        # načítanie venvov a skriptov pre vybraný projekt.

    @staticmethod
    def refresh_scripts(window):
        """
        Reakcia na kliknutie tlačidla pre obnovu zoznamu skriptov v aktuálnom projekte.
        """
        active_project = window.combo_project.currentText()
        if active_project:
            window.populate_scripts(active_project)