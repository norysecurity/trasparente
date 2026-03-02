import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_api():
    api_key = os.getenv("QWEN_API_KEY")
    url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qwen-max",
        "messages": [
            {"role": "user", "content": "olá, responda apenas 'OK'"}
        ]
    }
    
    print(f"Testing with Key: {api_key[:5]}...{api_key[-5:]}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
