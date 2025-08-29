import asyncio
import base64

import requests

from gemeni_prompt import GeminiPromptService


def generate_video():
    url = "https://api.kie.ai/api/v1/veo/generate"
    token = "f2944ae73e6cadd3dc440b11d3d18c3d"
    image_path = 'images/2025-08-27 17.03.50.jpg'
    image_url = updload_image(image_path)

    service = GeminiPromptService('prompt.txt',
                                  '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')
    result = asyncio.run(service.generate("Возьми человка с фото (не меняй его, оставь таким как есть) и сделай так что он вдувает в себя воздушные шарики, рядом стоит балон с газом, при этом после каждого шара он становится веселее."))

    payload = {
        "prompt": result,
        "imageUrls": [image_url],
        "model": "veo3",
        "aspectRatio": "16:9",
        "seeds": 12345,
        "enableFallback": False
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    print(response.json())


def updload_image(image_path):
    token = "f2944ae73e6cadd3dc440b11d3d18c3d"

    # Read file and convert to base64
    with open(image_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
        base64_data = f'data:image/jpeg;base64,{file_data}'

    url = "https://kieai.redpandaai.co/api/file-base64-upload"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "base64Data": base64_data,
        "uploadPath": "images",
        "fileName": "base64-image_4.jpg"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()['data']['downloadUrl']


def get_video_status(task_id):
    token = "f2944ae73e6cadd3dc440b11d3d18c3d"
    url = "https://api.kie.ai/api/v1/veo/record-info"

    params = {
        "taskId": task_id
    }

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers, params=params)

    print(response.json())


if __name__ == "__main__":
    # generate_video()
    get_video_status("2a3513d6c13768b03d9de1e3b44186ab")
