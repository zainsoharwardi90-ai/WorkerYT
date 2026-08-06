import whisper

_model = None

def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model

def transcribe(audio_path, source_lang=None):
    model = get_model()
    options = {"task": "transcribe"}
    if source_lang:
        options["language"] = source_lang
    result = model.transcribe(audio_path, **options)
    return result["text"]
