import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

MODEL = "gemini-3.1-flash-live-preview"


async def main():
    print("Connecting to Gemini Live...")

    config = {
        "response_modalities": ["AUDIO"]
    }

    async with client.aio.live.connect(
        model=MODEL,
        config=config
    ) as session:

        print("Gemini Live connection successful!")


if __name__ == "__main__":
    asyncio.run(main())