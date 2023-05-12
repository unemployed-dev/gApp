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
def get_jobs_from_search(URL):
    st = perf_counter()
    if "linkedin" in URL:
        urls = []
        urls = get_search_results_linkedin(URL)
        #Check that the search results have been generated properly
        if urls == None:
            logging.error('Unable to access linkedin search results. Likely a connection issue.')
            return
        #create a filename
        writable_url = re.sub(r'.*?search/?\?','',URL)
        filename = f'URL_LIST - {datetime.now().strftime("%H:%M:%S %d-%m-%Y")} {writable_url}.jobfile'
        #write down urls in case they need to be reviewed later
        with open(filename, "w") as file:
            for item in urls:
                file.write(f"{item}\n")
        #write down time that this scrape took
        with open('process_times.log', "a") as file:
            file.write(f'{len(urls)} URLs took {perf_counter() - st} to scrape.')
                    
        #download all the URL pages into job objects which are nice and clean, store in a file as we go
        asyncio.run(download_jobs(urls, filename[11:], URL))
        
        #write down total time for this operation to complete
        with open('process_times.log', "a") as file:
            file.write(f'{len(urls)} jobs took {perf_counter() - st} to download.')
            
async def download_jobs(urls: list, filename: str, query: str):
    """Creates a web session and uses asynchronous functions to download requested urls.
    """
    #use fake header because we arent a bot
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0"}
    #download all urls into a list of jobs asynchronously
    async with aiohttp.ClientSession(headers=headers) as session:
        jobList = await asyncio.gather(*[job.get_linkedin(url, session) for url in urls])
    
    finalList = jobList
    spam_check = set()
    
    #write jobs to a file
    with open(filename, "a") as file:
        for i,item in enumerate(jobList):            
            #check that it was downloaded cworrectly
            if item.title == '.':
                # logging.error(f'Was not able to download {urls[i]}')
                print(f'Empty job: {item.dump()}')
                del finalList[i]
                continue
            #check for spam and filter out jobs with the same posting title and company name, O(n) time
            id = item.title+item.company_name
            if id in spam_check:
                # print(f'{id} is spam')
                # print(f'this is whats in the spam: {item.title}')
                del finalList[i]
                continue
            else:
                spam_check.add(id)
            
            #add the search origin to the job
            item.search_origin = query
            serialized_item = item.dump()
            #check that it was serialized correctly
            if serialized_item == None:
                logging.error(f'Could not correctly serialize {urls[i]}')
                print(f'Could not correctly serialize {urls[i]}')
            else:
                file.write(serialized_item)
    print(f'completed {filename}')
    return finalList
                    
            
        
            
#####
##implement a timeout to break the loop if it messes up so it doesnt go forever
#####
def get_search_results_linkedin(URL: str):
    opt = Options()
    opt.binary_location = "/usr/bin/google-chrome-stable"
    opt.add_argument("--incognito")
    driver = webdriver.Chrome(options=opt)
    #attempt connection
    try:
        driver.get(URL)
    except Exception:
        logging.error('Selenium could not connect')
    #we will use the button to determine when all results are loaded.
    #it only appears after a few pages, and disappears when the list is fully loaded
    #it will be set to false if all results are loaded before it appears
    button = None
    urls = []
    #determine how many jobs will need to be loaded
    jobs_amount = driver.find_element(By.CLASS_NAME, "results-context-header__job-count")
    jobs_amount = int(re.sub('[^\d]','',jobs_amount.text))
    #look for signal that all results have been returned
    button = buttonless_check_for_more_results_linkedin(driver)
    ###
    #implement timer and log how long searches take by size. pass the jobs amount to user and the time they may have to wait
    ###
    print(f'jobs found: {jobs_amount}')
    
    #scroll down until page transitions to button-based scrolling
    while button == None:
        try:
            button = driver.find_element(By.CLASS_NAME, "infinite-scroller__show-more-button--visible")
        except Exception:
            #scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
            #scroll to top
            driver.execute_script("window.scrollTo(0, 0)")
            button = buttonless_check_for_more_results_linkedin(driver)
    #keep clicking scroll down button when it appears
    while button:  
        try:
            button.click()
        except Exception:
            break
    print("done scrolling")
    #scape all job links from page
    cards = driver.find_elements(By.CLASS_NAME, "base-card__full-link")
    #report if there are missing results
    print(f'{len(cards)} found of {jobs_amount} total')
    if not (len(cards) == jobs_amount):
        logging.error(f'{len(cards)} found of {jobs_amount} total. May have disconnected while searching.')
        
    for item in cards:
            urls.append(item.get_attribute('href'))
    return urls

def buttonless_check_for_more_results_linkedin(driver: webdriver):
    """If all results are displayed on the first few pages of a linkedin search, this will return false.
    This should only be used before a button is spawned, and not after."""
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

get_jobs_from_search(search_results_to_analyze)