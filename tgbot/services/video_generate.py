from typing import Union, Optional, Dict, Any

import aiohttp
import base64
import uuid
import os

from loguru import logger

from tgbot.services.gemeni_prompt import GeminiPromptService


class VideoGeneratorService:
    def __init__(self, prompt_file: str, prompt_api_key: str, video_api_token: str):
        self.prompt_service = GeminiPromptService(prompt_file, prompt_api_key)
        self.video_api_token = video_api_token
        self.generate_url = "https://api.kie.ai/api/v1/veo/generate"
        self.status_url = "https://api.kie.ai/api/v1/veo/record-info"
        self.upload_url = "https://kieai.redpandaai.co/api/file-base64-upload"

    async def upload_image(self, data: bytes, filename: Optional[str] = None) -> str:
        # Генерируем уникальное имя файла
        if not filename:
            filename = f"{uuid.uuid4().hex}.jpg"
        ext = os.path.splitext(filename)[1] or ".jpg"

        file_data = base64.b64encode(data).decode("utf-8")
        # Можно уточнить mime по расширению; по умолчанию jpeg
        mime = "image/jpeg"
        if ext.lower() in (".png",):
            mime = "image/png"
        base64_data = f"data:{mime};base64,{file_data}"
        payload = {
            "base64Data": base64_data,
            "uploadPath": "images",
            "fileName": filename
        }
        headers = {
            "Authorization": f"Bearer {self.video_api_token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.upload_url, json=payload, headers=headers) as response:
                data = await response.json()
                return data["data"]["downloadUrl"]

    async def generate_video(
            self,
            prompt_user: str,
            image_bytes: Optional[bytes] = None,
            image_filename: Optional[str] = None,
            model: str = "veo3",
            aspect_ratio: str = "16:9",
            enable_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Генерация видео (максимум одно изображение).
        """
        image_urls = []
        if image_bytes:
            uploaded_url = await self.upload_image(image_bytes, image_filename)
            image_urls.append(uploaded_url)

        prompt = await self.prompt_service.generate(prompt_user)
        logger.info(f'Prompt before adaptation: {prompt}')
        payload = {
            "prompt": prompt,
            "imageUrls": image_urls,
            "model": model,
            "aspectRatio": aspect_ratio,
            "enableFallback": enable_fallback
        }
        headers = {
            "Authorization": f"Bearer {self.video_api_token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.generate_url, json=payload, headers=headers) as response:
                resp_json = await response.json()
                if response.status != 200:
                    raise RuntimeError(f"Video generate error {response.status}: {resp_json}")
                return resp_json

    async def get_video_status(self, task_id: str):
        headers = {"Authorization": f"Bearer {self.video_api_token}"}
        params = {"taskId": task_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.status_url, headers=headers, params=params) as response:
                return await response.json()
