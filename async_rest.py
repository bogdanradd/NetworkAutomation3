import asyncio
import aiohttp
import json

async def fetch(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        return await response.text()

async def main():
    urls = {
        "https://httpbin.org/delay/2",
        "https://httpbin.org/delay/3",
        "https://httpbin.org/delay/1"
    }
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(fetch(session, url) for url in urls))
        for i, result in enumerate(results, 1):
            print(f"Response {i}: origin: {json.loads(result)['origin']}")
            print(result)

asyncio.run(main())