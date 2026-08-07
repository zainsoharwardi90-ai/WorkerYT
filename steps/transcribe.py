import os
import time
import tempfile
import subprocess
import requests

HF_ENDPOINT = os.environ.get(
    "HF_ENDPOINT",
    "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3",
)
MAX_ATTEMPTS = int(os.environ.get("HF_MAX_ATTEMPTS", "3"))
RETRY_WAIT_SECONDS = 20
CHUNK_THRESHOLD_SEC = 60
CHUNK_DURATION_SEC = 50
REQUEST_TIMEOUT = 300


def get_duration(audio_path):
    """Return audio duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed to get duration for {audio_path}: {result.stderr.strip()}"
        )
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Could not parse duration for {audio_path}: {result.stdout!r}")


def split_audio(audio_path, chunk_duration=CHUNK_DURATION_SEC):
    """Split audio into ~chunk_duration-second wav chunks using ffmpeg."""
    total = get_duration(audio_path)
    chunks = []
    start = 0.0
    idx = 0
    while start < total:
        chunk_path = os.path.join(
            tempfile.gettempdir(), f"tts_chunk_{os.getpid()}_{idx:04d}.wav"
        )
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-ss', f'{start:.3f}',
            '-t', f'{chunk_duration:.3f}',
            '-ac', '1',
            '-ar', '16000',
            chunk_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        chunks.append(chunk_path)
        start += chunk_duration
        idx += 1
    return chunks


def _transcribe_request(audio_bytes, token):
    """Send one chunk/request to the HF API with the existing retry logic."""
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
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code in (503, 504):
                last_error = f"Model loading / timeout ({resp.status_code}): {resp.text[:200]}"
                print(
                    f"[WARN] Whisper API returned {resp.status_code} on attempt "
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


def transcribe(audio_path, source_lang=None):
    token = os.environ.get("HF_API_TOKEN")
    if not token:
        raise RuntimeError("HF_API_TOKEN environment variable is not set")

    duration = get_duration(audio_path)

    if duration > CHUNK_THRESHOLD_SEC:
        print(
            f"[INFO] Audio duration {duration:.2f}s > {CHUNK_THRESHOLD_SEC}s. "
            f"Splitting into chunks..."
        )
        chunks = split_audio(audio_path)
        try:
            parts = []
            for i, chunk_path in enumerate(chunks, start=1):
                with open(chunk_path, "rb") as f:
                    audio_bytes = f.read()
                print(f"[INFO] Transcribing chunk {i}/{len(chunks)}: {chunk_path}")
                text = _transcribe_request(audio_bytes, token)
                parts.append(text)
            return " ".join(p for p in parts if p)
        finally:
            for chunk_path in chunks:
                try:
                    os.remove(chunk_path)
                    print(f"[INFO] Cleaned up {chunk_path}")
                except OSError as e:
                    print(f"[WARN] Failed to remove {chunk_path}: {e}")
    else:
        print(f"[INFO] Audio duration {duration:.2f}s <= {CHUNK_THRESHOLD_SEC}s. "
              f"Transcribing directly.")
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        return _transcribe_request(audio_bytes, token)
