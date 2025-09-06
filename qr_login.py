import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 👈 headless=False ताकि QR दिखे
        context = await browser.new_context()

        page = await context.new_page()
        await page.goto("https://web.whatsapp.com")

        print("📲 कृपया अपने फोन से WhatsApp QR Code स्कैन करें...")
        # QR scan का इंतज़ार करो
        await page.wait_for_selector("div[title='Search input textbox']", timeout=0)
        print("✅ Login successful!")

        # Login state save कर लो
        await context.storage_state(path="session.json")
        print("💾 session.json saved successfully!")

        await browser.close()

asyncio.run(main())
