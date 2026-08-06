from deep_translator import GoogleTranslator

_translators = {}

def get_translator(target_lang):
    if target_lang not in _translators:
        _translators[target_lang] = GoogleTranslator(source="auto", target=target_lang)
    return _translators[target_lang]

def translate(text, target_lang):
    translator = get_translator(target_lang)
    last_error = None

    for attempt in range(1, 3):
        try:
            result = translator.translate(text)
            if not result:
                last_error = f"Translation returned an empty or None result for target_lang '{target_lang}'"
                raise RuntimeError(last_error)
            return result
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
