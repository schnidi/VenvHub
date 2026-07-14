#----------------------------------------
# Súbor: core/logic/sluzby/downloader.py
#----------------------------------------
import requests
from typing import Callable, Optional

class Downloader:
    @staticmethod
    def download_file(url: str, dest_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> dict:
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded_size, total_size)
            return {'success': True, 'path': dest_path}
        except Exception as e:
            return {'success': False, 'error': str(e)}