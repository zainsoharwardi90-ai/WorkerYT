from googletrans import Translator

_translator = None

def get_translator():
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

def translate(text, target_lang):
    translator = get_translator()
    last_error = None

    for attempt in range(1, 3):
        try:
            result = translator.translate(text, dest=target_lang)
            if result is None or not result.text:
                last_error = f"Translation returned an empty or None result for target_lang '{target_lang}'"
                raise RuntimeError(last_error)
            return result.text
        except RuntimeError:
            if attempt < 2:
                print(f"[WARN] Translation attempt {attempt}/2 failed: {last_error}. Retrying...")
                continue
            raise
        except Exception as e:
            last_error = f"Translation request failed: {e}"
            print(f"[WARN] Translation attempt {attempt}/2 failed: {e}")
            if attempt < 2:
                continue
            break

    raise RuntimeError(f"Translation failed for target_lang '{target_lang}': {last_error}")
