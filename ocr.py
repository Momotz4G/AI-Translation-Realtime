import asyncio
import os
import tempfile
from PIL import Image

from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage import StorageFile

class WindowsOCR:
    def __init__(self):
        # Initializes the OCR engine with the default system language.
        self.engine = OcrEngine.try_create_from_user_profile_languages()
        
    async def _extract_text_async(self, image_path: str) -> str:
        try:
            storage_file = await StorageFile.get_file_from_path_async(image_path)
            stream = await storage_file.open_read_async()
            decoder = await BitmapDecoder.create_async(stream)
            bitmap = await decoder.get_software_bitmap_async()
            result = await self.engine.recognize_async(bitmap)
            return result.text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def extract_text(self, image: Image.Image) -> str:
        if not self.engine:
            return ""
            
        # Preprocess image to improve OCR accuracy on game/dark backgrounds
        from PIL import ImageOps, ImageEnhance
        
        # 1. Convert to Grayscale
        processed = ImageOps.grayscale(image)
        # 2. Increase Contrast
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(2.0)
        # 3. Upscale to make small text clearer for the engine
        processed = processed.resize((processed.width * 2, processed.height * 2), Image.Resampling.LANCZOS)
            
        # Write to a temporary file since Windows SDK requires a storage file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(temp_fd)
        
        try:
            processed.save(temp_path, format="PNG")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            text = loop.run_until_complete(self._extract_text_async(temp_path))
            loop.close()
            return text
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
