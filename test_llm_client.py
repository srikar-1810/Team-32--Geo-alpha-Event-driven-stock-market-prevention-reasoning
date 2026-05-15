import asyncio
import os
from openai import AsyncOpenAI

async def test_llm():
    try:
        with open(".env", "r") as f:
            env = f.read()
        
        api_key = None
        base_url = None
        model = None
        
        for line in env.splitlines():
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
            elif line.startswith("OPENAI_BASE_URL="):
                base_url = line.split("=", 1)[1].strip()
            elif line.startswith("OPENAI_MODEL="):
                model = line.split("=", 1)[1].strip()
        
        print(f"Testing with Model: {model}, URL: {base_url}")
        
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello!"}],
            max_tokens=10
        )
        print("SUCCESS!")
        print(response)
        
    except Exception as e:
        print("FAILED!")
        print(type(e).__name__, str(e))

if __name__ == "__main__":
    asyncio.run(test_llm())
