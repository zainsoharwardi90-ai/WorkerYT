import os
import time
import requests

HF_ENDPOINT = os.environ.get(
    "HF_ENDPOINT",
    "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3",
)
MAX_ATTEMPTS = int(os.environ.get("HF_MAX_ATTEMPTS", "3"))
RETRY_WAIT_SECONDS = 20


def transcribe(audio_path, source_lang=None):
    token = os.environ.get("HF_API_TOKEN")
    if not token:
        raise RuntimeError("HF_API_TOKEN environment variable is not set")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(
                HF_ENDPOINT,
                data=audio_bytes,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "audio/wav",
                },
                timeout=120,
            )

            if resp.status_code == 503:
                last_error = f"Model is loading (503): {resp.text[:200]}"
                print(
                    f"[WARN] Whisper model is loading (503) on attempt "
                    f"{attempt}/{MAX_ATTEMPTS}. Waiting {RETRY_WAIT_SECONDS}s..."
                )
                time.sleep(RETRY_WAIT_SECONDS)
                continue

            if resp.status_code != 200:
                raise RuntimeError(
                    f"HF API returned HTTP {resp.status_code}: {resp.text[:500]}"
                )

            data = resp.json()
            text = data.get("text")
            if not text:
                raise RuntimeError(f"HF API returned no transcription: {resp.text[:500]}")
            return text

        except requests.RequestException as e:
            last_error = f"Request failed: {e}"
            print(f"[WARN] Transcription attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_WAIT_SECONDS)

    raise RuntimeError(f"Transcription failed after {MAX_ATTEMPTS} attempts: {last_error}")
