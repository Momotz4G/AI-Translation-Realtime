import mss
from PIL import Image
import threading

class ScreenCapturer:
    def __init__(self):
        # mss.mss() creates thread-local handles on Windows, so we must instantiate it per-thread
        self._local = threading.local()
        
    @property
    def sct(self):
        if not hasattr(self._local, 'sct'):
            self._local.sct = mss.mss()
        return self._local.sct
        
    def capture_region(self, x, y, width, height) -> Image.Image:
        """
        Captures a specific region of the screen and returns a PIL Image.
        """
        monitor = {"top": y, "left": x, "width": width, "height": height}
        sct_img = self.sct.grab(monitor)
        # Convert to PIL Image
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
