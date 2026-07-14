#----------------------------------------
# Súbor: core/single_instance.py
#----------------------------------------

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtCore import QObject

class SingleInstanceError(Exception):
    """Raised when the single-instance lock server cannot be started."""
    pass

class SingleInstance(QObject):
    def __init__(self, app_id, main_window_callback=None):
        super().__init__()
        self.app_id = app_id
        self.main_window_callback = main_window_callback
        self.server = QLocalServer()
        self.socket = QLocalSocket()

    def is_running(self):
        """
        Vráti True, ak inštancia už beží.
        Zároveň pošle správu bežiacej inštancii, aby sa zobrazila.
        """
        self.socket.connectToServer(self.app_id)
        
        # Dáme rozumný timeout 2000ms. Komunikácia bežne trvá < 5ms. 
        # Ak to trvá dlhšie ako 2s, niečo je buď extrémne preťažené, alebo appka zamrzla.
        if self.socket.waitForConnected(2000):
            self.socket.write(b"WAKE_UP")
            self.socket.waitForBytesWritten(1000)
            self.socket.disconnectFromServer()
            return True
            
        # --- ROBUSTNÁ KONTROLA CHYBY ---
        # Ak sme sa nepripojili, zistíme PREČO namiesto slepého mazania servera.
        err = self.socket.error()
        
        if err in (QLocalSocket.LocalSocketError.ServerNotFoundError, 
                   QLocalSocket.LocalSocketError.ConnectionRefusedError):
            # Tieto chyby znamenajú, že tam naozaj nikto nepočúva 
            # (napr. predchádzajúca inštancia natvrdo spadla a nechala po sebe "odpad").
            # AŽ TERAZ je bezpečné premazať starý "mŕtvy" server.
            self.server.removeServer(self.app_id)
        else:
            # Ak nastala iná chyba (napr. SocketTimeoutError), znamená to, že kanál EXISTUJE, 
            # ale prvá inštancia bola tak brutálne vyťažená, že nám nestihla odpovedať do 2 sekúnd.
            # V takom prípade ju budeme považovať za bežiacu a NEKRADNEME jej server.
            return True
            
        # Pokračujeme vytvorením nášho servera
        self.server.newConnection.connect(self._on_new_connection)
        
        if not self.server.listen(self.app_id):
            raise SingleInstanceError(
                f"Nepodarilo sa spustiť SingleInstance server: {self.server.errorString()}"
            )
            
        return False

    def _on_new_connection(self):
        """Volá sa v BEŽIACEJ aplikácii, keď sa niekto pokúsi spustiť novú."""
        new_socket = self.server.nextPendingConnection()
        if not new_socket: return
        
        if new_socket.waitForReadyRead(1000):
            data = new_socket.readAll().data()
            if data == b"WAKE_UP":
                if self.main_window_callback:
                    self.main_window_callback()
                    
        new_socket.disconnectFromServer()