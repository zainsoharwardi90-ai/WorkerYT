from googletrans import Translator

_translator = None

def get_translator():
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

def translate(text, target_lang):
    translator = get_translator()
    result = translator.translate(text, dest=target_lang)
    return result.text
