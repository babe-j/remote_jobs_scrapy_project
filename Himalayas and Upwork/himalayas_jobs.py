import csv
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin

def save_to_csv(data:list, first_time:bool):
    mode = 'w' if first_time else 'a'
    with open("himalayas_jobs.csv", mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        if first_time: 
            writer.writeheader()
        writer.writerows(data)

async def scrape_himalayas(max_pages = 5):
    # Creates an async context manager for Playwright — ensures browser is launched and closed cleanly
    async with async_playwright() as p:
        try:
            # Launches Chromium browser in non-headless mode (headless=False shows browser window)
            browser = await p.chromium.launch(headless=False) 
            context = await browser.new_context() 
            
            # Sets default wait timeout for all actions in this context (milliseconds)
            context.set_default_timeout(60000)

            # Opens a new browser tab/page
            page =  await context.new_page()
            print("going to preferred site")

            try:
                # Navigates to the jobs listing page with a longer-than-default timeout
                response = await page.goto('https://himalayas.app/jobs/worldwide', timeout=100000)
                # Basic HTTP response validation
                if not response or not response.ok:
                    print(f"Non-200 response: {response.status if response else 'No response'}")
                    return
            except Exception as e:
                print(f"GOTO failed: {e}")
            
            # Waits until the DOM is loaded before proceeding (scripts/images may still load after this)
            await page.wait_for_load_state('domcontentloaded')

            # Ensures at least one job listing element is attached before scraping
            await page.wait_for_selector('article.flex.flex-shrink-0.cursor-pointer', state='attached', timeout=60000)

            first_time = True
            page_number = 1 
            while page_number <= max_pages:
                print(f"scraping page {page_number}")

                # Wait for the page content to load after navigation
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_selector('article.flex', state='attached')

                # Selects all job container elements on the page
                product_elements = await page.query_selector_all('article.flex')

                for product in product_elements:
                    try:
                        # Query selectors for job-specific details — these CSS selectors are tightly bound to site structure
                        job_title_el = await product.query_selector('a.text-xl')
                        company_name_el = await product.query_selector('a.inline-flex')
                        date_posted_el = await  product.query_selector('time.hidden.flex-shrink-0')
                        job_info_el = await product.query_selector_all('div.inline-flex')
                        url_el = await product.query_selector('a.text-xl')

                        # Extracts text/attributes only if element exists to avoid NoneType errors
                        title = await job_title_el.inner_text() if job_title_el else None 
                        company_name = await company_name_el.inner_text() if company_name_el else None 
                        date_posted = await date_posted_el.inner_text() if date_posted_el else None 
                        
                        # Joins multiple job info tags (e.g., "Full-time, Remote") into a single string
                        job_type = ",".join([ await el.inner_text() for el in job_info_el]) if job_info_el else None 
                        
                        link = await url_el.get_attribute('href') if url_el else None 
             
                        base_url = 'https://himalayas.app/'
                        himalayas_jobs = [{
                            'Title': title,
                            'CompanyName': company_name,  
                            'DatePosted': date_posted, 
                            'JobType' : job_type,
                            # Converts relative job URL to full absolute URL
                            'JobLink': urljoin(base_url, link)  
                        }]

                        save_to_csv(himalayas_jobs, first_time)
                        first_time = False

                    except Exception as e:
                        print(f"Error extracting product: {e}")
                        continue 
               
                # Pagination: locates "Next page" link and navigates if available
                next_page = page.locator('a.flex.flex-row-reverse')
                if await next_page.count() == 0:
                    print("You have reached the end of the page!")
                    break
                await next_page.click()
                await page.wait_for_selector('article.flex', state='attached')
                page_number += 1

            await browser.close()
            await context.close()
        
        except Exception as e:
           print(f"Error: {e}")
            
# Kicks off the scraping coroutine max_pages can be any number  
asyncio.run(scrape_himalayas(max_pages=99))
