import aiohttp
import asyncio


class GeminiPromptService:
    def __init__(self, prompt_file: str, api_key: str):
        self.prompt_file = prompt_file
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "google/gemini-2.5-pro"

    def _get_prompt(self, prompt_user: str) -> str:
        with open(self.prompt_file, 'r', encoding='utf-8') as file:
            prompt = file.read()
        return prompt.replace('{insert_here}', prompt_user)

    async def generate(self, prompt_user: str) -> str | None:
        result_prompt = self._get_prompt(prompt_user)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": result_prompt
                }
            ]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP error: {response.status}")
                    data = await response.json()
                    return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"Ошибка генерации промпта: {e}")
            return None
