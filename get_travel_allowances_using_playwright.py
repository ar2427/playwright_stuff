import asyncio
from playwright.async_api import async_playwright
 
async def create_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='./user_session', headless=False
        )
        page = await browser.new_page()
        await page.goto("https://concur.cornell.edu")

        # Ask the user to log in manually
        input("Please log in manually, then press Enter here to save your session...")
        
        # Save cookies and LocalStorage into a storage state file
        await page.context.storage_state(path="storage_state.json")
        
        await browser.close()
 
async def reuse_session():
    async with async_playwright() as p:
        # Load the previously saved storage state
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="storage_state.json")  # Load cookies and LocalStorage
        
        page = await context.new_page()
        await page.goto("https://concur.cornell.edu")  # This should be logged in automatically
        # await page.goto("https://us2.concursolutions.com/nui/expense/report/6B3FFE88DC74445E8C82")
        
        input("Press enter when done!")
        
        await browser.close()

if __name__ == "__main__":
    # Step 1: Save the session
    # asyncio.run(create_session())
    
    # Step 2: Reuse the session later
    asyncio.run(reuse_session())