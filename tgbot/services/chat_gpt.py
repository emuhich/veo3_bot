import aiohttp
import os
from typing import List, Dict, Optional, Any, Union
from io import BytesIO


class ChatGPTService:
    CHAT_URL = "https://api.openai.com/v1/chat/completions"
    TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"

    def __init__(
            self,
            api_key: str,
            chat_model: str = "gpt-4o-mini",
            whisper_model: str = "whisper-1",
            timeout: int = 120
    ):
        self.api_key = api_key
        self.chat_model = chat_model
        self.whisper_model = whisper_model
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}"
        }

    async def ask(
            self,
            messages: Optional[List[Dict[str, str]]] = None,
            question: Optional[str] = None,
            temperature: float = 0.7,
            top_p: float = 1.0
    ) -> str:
        if messages is None:
            messages = []
        if question:
            messages = messages + [{"role": "user", "content": question}]
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p
        }
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(self.CHAT_URL, json=payload,
                                        headers={**self._headers(), "Content-Type": "application/json"}) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Chat completion error {resp.status}: {await resp.text()}")
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"ask failed: {e}") from e

    async def transcribe(
            self,
            audio_path: str,
            language: Optional[str] = None,
            response_format: str = "json",
            temperature: float = 0.0
    ) -> str:
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"file not found: {audio_path}")
        form = aiohttp.FormData()
        form.add_field("model", self.whisper_model)
        form.add_field("response_format", response_format)
        form.add_field("temperature", str(temperature))
        if language:
            form.add_field("language", language)
        with open(audio_path, "rb") as f:
            form.add_field(
                "file",
                f,
                filename=os.path.basename(audio_path),
                content_type="application/octet-stream"
            )
            return await self._send_transcribe_form(form)

    async def transcribe_bytes(
            self,
            data: Union[bytes, BytesIO],
            filename: str = "voice.ogg",
            language: Optional[str] = None,
            response_format: str = "json",
            temperature: float = 0.0,
            content_type: str = "audio/ogg"
    ) -> str:
        """
        Транскрибация из памяти (без сохранения на диск).
        data: bytes или BytesIO
        """
        if isinstance(data, BytesIO):
            data.seek(0)
            raw = data.read()
        else:
            raw = data
        form = aiohttp.FormData()
        form.add_field("model", self.whisper_model)
        form.add_field("response_format", response_format)
        form.add_field("temperature", str(temperature))
        if language:
            form.add_field("language", language)
        form.add_field(
            "file",
            raw,
            filename=filename,
            content_type=content_type
        )
        return await self._send_transcribe_form(form)

    async def _send_transcribe_form(self, form: aiohttp.FormData) -> str:
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(self.TRANSCRIBE_URL, data=form, headers=self._headers()) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Transcription error {resp.status}: {await resp.text()}")
                    data: Any = await resp.json()
                    return data.get("text", "")
        except Exception as e:
            raise RuntimeError(f"transcribe failed: {e}") from e
