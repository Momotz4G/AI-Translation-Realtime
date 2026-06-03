from deep_translator import GoogleTranslator

class DeepTranslatorEngine:
    def __init__(self, source='en', target='id'):
        self.translator = GoogleTranslator(source=source, target=target)
        
    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        try:
            return self.translator.translate(text)
        except Exception as e:
            print(f"Translation Error: {e}")
            return "Translation Error"
