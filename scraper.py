import os
from job_parse import job
import re
from datetime import timedelta, datetime
import logging
import asyncio
import aiohttp
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from dataclasses import dataclass
from time import perf_counter

logging.basicConfig(filename="scraper.log", level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")

# @dataclass
# class SearchSettings:
#     pass

#search_results_to_analyze = https://www.linkedin.com/jobs/search/?currentJobId=3587714255&f_E=1%2C2%2C3&geoId=101174742&keywords=qa&location=Canada&refresh=true
search_results_to_analyze = "https://www.linkedin.com/jobs/search/?keywords=Qa&location=Canada&locationId=&geoId=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&position=1&pageNum=0"
# search_results_to_analyze = 'https://www.linkedin.com/jobs/search/?keywords=Qa&location=Canada&locationId=&geoId=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&f_JT=P&position=1&pageNum=0'
# search_results_to_analyze = "https://www.linkedin.com/jobs/search?keywords=Developer&location=Canada&locationId=&geoId=101174742&f_TPR=&f_E=3&position=1&pageNum=0"

async def get_jobs_from_search(URL, connection_limit=3, jobList=[job]) -> list[job]:
    st = perf_counter()
    q = asyncio.Queue()
    spam_check = set()
    writable_search_origin = re.sub(r'.*?search/?\?','',URL)
    filename = f'{datetime.now().strftime("%H:%M:%S %d-%m-%Y")} {writable_search_origin}'
    
    #Create a web session and use a fake header because we arent a bot
    #limit connections to given value
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0"}
    connector = aiohttp.TCPConnector(limit_per_host=connection_limit)
    session = aiohttp.ClientSession(headers=headers, connector=connector)
    
    if "linkedin" in URL:
        producer = asyncio.create_task(_produce_urls_linkedin(URL, q, st))
    consumers = [asyncio.create_task(_consume_urls(session, q, filename, writable_search_origin, spam_check, jobList)) for i in range(connection_limit)]
        
    await asyncio.gather(producer)
    await q.join()
    await session.close()
        
    for c in consumers:
        c.cancel()
        
    #write down total time for this operation to complete
    with open('process_times.log', "a") as file:
        file.write(f'{len(jobList)} jobs took {perf_counter() - st} to download.\n')
        
    return jobList
    
    
        
            
async def _consume_urls(session, q: asyncio.Queue, filename: str, search_origin='.', spamcheck=set(), jobList=[]):
    """Downloads urls from a Queue and writes them to disk. If a list of jobs is provided, it will also add to that list.
    
    Optional Parameters:
    
    **spamcheck** Duplicate listings will be deleted, with multiple consumers this should be passed in so they all share one resource. Unfortunately there is no way to check for spam before downloading.
    
    **search_origin** Will add given URL to the downloaded job so it knows how it was originally found.
    """
    
    previously_bad_urls = [str]    
    while True:
        url = await q.get()
        newJob = await job.download(url, session, search_origin=search_origin)
        
        #Check that the received job was downloaded correctly, otherwise add it to queue one more time
        #If download fails a second time, log it and move on.
        #Then check if it's a spam posting by matching job title and company name, if it is we skip it,
        #Otherwise, add it to the list of jobs downloaded and write to file
        if newJob == None:
            if url in previously_bad_urls:
                print(f'unable to download job {url}')
                with open(f'MISSED - {filename}', "a") as file:
                        file.write(f"{url}\n")
            else:
                print(f'Did not receive job in consumer, adding back to download queue (one time)')
                previously_bad_urls.append(url)
                q.put_nowait(url)
            q.task_done
            continue
        
        id = newJob.title+newJob.company_name
        if id in spamcheck:
            q.task_done
            continue
        else:
            spamcheck.add(id)
        
        jobList.append(newJob)
        serialized_job = newJob.dump()
        if serialized_job == None:
            print(f'Downloaded job, but could not correctly serialize {url}')
            with open(f'MISSED - {filename}', "a") as file:
                file.write(f"{url}\n")
        else:
            with open(f'{filename}.jobfile', "a") as file:
                file.write(f'{serialized_job}')
        q.task_done
        print(f'Jobs downloaded: {len(jobList)}')

async def _produce_urls_linkedin(URL: str, q: asyncio.Queue, start_time=perf_counter(), filename=f'{datetime.now().strftime("%H:%M:%S %d-%m-%Y")}'):
    opt = Options()
    opt.binary_location = "/usr/bin/google-chrome-stable"
    opt.add_argument("--incognito")
    driver = webdriver.Chrome(options=opt)
    try:
        driver.get(URL)
    except Exception:
        logging.error('Selenium could not connect')
        
    #We will use a button to determine when we are finished
    #It only appears after a few pages and disappears when the list is fully loaded.
    #If all the results have been loaded before that button appears, the button variable will be set to false so we know.
    button = None
    urls = ['placeholder']
    jobs_amount = driver.find_element(By.CLASS_NAME, "results-context-header__job-count")
    jobs_amount = int(re.sub('[^\d]','',jobs_amount.text))
    button = __check_if_finished_without_button(driver)
    print(f'jobs found: {jobs_amount}')
    
    _add_urls_to_queue(driver, urls, q, filename)
    #urls[0] was a cheat so we don't have to check for an empty list every time later
    del urls[0]
    
    #scroll down until page transitions to button-based scrolling
    #------------------------------------------------------------
    #this will scroll to the bottom then to top of page repeatedly to make more results load
    #once a "more results" button appears, the  first section has done its work
    #then keep clicking the scroll button until it disappears, this may take awhile for lots of results
    #so links will be generated for downloading at the same time as scrolling
    while button == None:
        try:
            button = driver.find_element(By.CLASS_NAME, "infinite-scroller__show-more-button--visible")
        except Exception:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)
            driver.execute_script("window.scrollTo(0, 0)")
            button = __check_if_finished_without_button(driver)
            _add_urls_to_queue(driver, urls, q, filename)
    while button:
        _add_urls_to_queue(driver, urls, q, filename)
        try:
            button.click()
        except Exception:
            break
        await asyncio.sleep(.1)
    print("done scrolling")

    #report if there are missing results, log an error if the amount does not match
    print(f'{len(urls)} found of {jobs_amount} total')
    if not (len(urls) == jobs_amount):
        logging.error(f'{len(urls)} found of {jobs_amount} total. May have disconnected while searching.')
        
    #write down time that the initial url search took
    with open('process_times.log', "a") as file:
        file.write(f'{len(urls)} urls took {perf_counter() - start_time} to find.\n')

def _add_urls_to_queue(driver: webdriver.Chrome, urls: list[str], q: asyncio.Queue, filename):
    """Identify all job links on the page. Skip the ones we have already seen and put the rest in queue.
    Log the new links to a file"""
    cards = driver.find_elements(By.CLASS_NAME, "base-card__full-link")
    for item in cards:
        url = item.get_attribute('href')
        if url not in urls:
            q.put_nowait(url)
            urls.append(url)
            with open(f'URLS_FOUND - {filename}', "a") as file:
                file.write(f"{url}\n")
    print('Producing links')

def __check_if_finished_without_button(driver: webdriver):
    """If the final results are displayed on the first few pages of a linkedin search, this will return false.
    False is used to avoid strange behaviours because the button variable that calls this should normally be initialized or None.
    This should only be used before a button is spawned (aka when it's set to none), and not after."""
    signal = None
    #if the signal object can't be found there is a major issue and we will crash
    try: 
        signal = driver.find_element(By.CLASS_NAME, "inline-notification__text")
    except Exception:
        print("***\nerror loading finish signal\n***")
        logging.error('error loading finish signal on initial search')
    else:
        if signal.is_displayed():
            print('finish signal active')
            return False
        else:
            return None

asyncio.run(get_jobs_from_search(search_results_to_analyze))