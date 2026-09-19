import os
import tempfile
from openai import OpenAI


class STTService:

    def __init__(self):
        self.provider = os.getenv("STT_PROVIDER", "whisper")
        self.use_mock = os.getenv("USE_MOCK_AI", "true").lower() == "true"
        api_key = os.getenv("OPENAI_API_KEY", "mock-key")
        self.client = OpenAI(api_key=api_key) if not self.use_mock else None

    def transcribe(self, audio_bytes: bytes = None, text_override: str = None) -> str:
        if text_override and text_override.strip():
            return text_override.strip()

        if self.use_mock or not audio_bytes:
            return "Anna 5 kilo biyyam add cheyyi"

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as audio_file:
                res = self.client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )
            os.remove(tmp_path)
            return res.text.strip()
        except Exception as e:
            return f"Error transcribing audio: {str(e)}"