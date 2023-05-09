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

logging.basicConfig(filename="logfile.log", level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")

# @dataclass
# class SearchSettings:
#     pass

#search_results_to_analyze = https://www.linkedin.com/jobs/search/?currentJobId=3587714255&f_E=1%2C2%2C3&geoId=101174742&keywords=qa&location=Canada&refresh=true
search_results_to_analyze = "https://www.linkedin.com/jobs/search/?keywords=Qa&location=Canada&locationId=&geoId=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&position=1&pageNum=0"
# search_results_to_analyze = 'https://www.linkedin.com/jobs/search/?keywords=Qa&location=Canada&locationId=&geoId=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&f_JT=P&position=1&pageNum=0'
# search_results_to_analyze = "https://www.linkedin.com/jobs/search?keywords=Developer&location=Canada&locationId=&geoId=101174742&f_TPR=&f_E=3&position=1&pageNum=0"
def get_jobs_from_search(URL):
    jobList = []
    if "linkedin" in URL:
        urls = []
        urls = get_search_results_linkedin(URL)
        # with open('08-05-2023 22:09:24 keywords=Developer&location=Canada&locationId=&geoId=101174742&f_TPR=&f_E=3&position=1&pageNum=0.jobfile', "r") as file:
        #     for item in file:
        #         urls.append(item)
                
        writable_url = re.sub(r'.*?search/\?','',URL)
        label = f'URL_LIST - {datetime.now().strftime("%H:%M:%S %d-%m-%Y")} {writable_url}.jobfile'
        #write down urls in case they need to be reviewed later
        with open(label, "w") as file:
            for item in urls:
                file.write(f"{item}\n")
        #download all the URL pages into job objects which are nice and clean, store in file as we go
        with open(label[11:], "a") as file:
            for url in urls:
                print(f'downloading job from {url}')
                jobResult = job.get_linkedin(url)
                jobResult.search_origin = URL
                jobList.append(jobResult)
                file.write(jobResult.dump())
                    
            
        
            
#####
##implement a timeout to break the loop if it messes up so it doesnt go forever
#####
def get_search_results_linkedin(URL: str):
    opt = Options()
    opt.binary_location = "/usr/bin/google-chrome-stable"
    opt.add_argument("--incognito")
    driver = webdriver.Chrome(options=opt)
    driver.get(URL)
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
            print("looking for scroll button")
            button = driver.find_element(By.CLASS_NAME, "infinite-scroller__show-more-button--visible")
        except:
            print("found no scroll button")
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
        except:
            break
    print("done scrolling")
    #scape all job links from page
    cards = driver.find_elements(By.CLASS_NAME, "base-card__full-link")
    print(f'{len(cards)} found of {jobs_amount} total')
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
    except:
        print("***\nerror loading finish signal\n***")
    else:
        print("loaded finish signal")
        if signal.is_displayed():
            print('finish signal active')
            return False
        else:
            return None

# def check_for_end_of_results_linkedin(driver: webdriver, amount: int):
#     cards = driver.find_elements(By.CLASS_NAME, "base-card__full-link")
#     if len(cards) >= (amount-2):
#         print('all results downloaded')
#         print(f'{len(cards)} found of {amount-2} total')
#         return cards
#     print(f'{len(cards)} found of {amount-2} total, continuing...')
#     return None


get_jobs_from_search(search_results_to_analyze)




# def generate_URL_batch(settings: dict):
#     """Creates a URL list for the dates given at a select location.
    
#     Parameters
#     -
#     settings: The location and period of time you would like to search"""
#     date = datetime(settings['firstYear'], settings['firstMonth'], settings['firstDay'])
#     endDate = datetime(settings['lastYear'], settings['lastMonth'], settings['lastDay'])
#     total = (endDate - date)+ timedelta(days=1) 
#     url = ['']*total.days
#     testListt = ["https://python.org", "https://python.org", "https://python.org"]
#     for i in range(total.days):
#         #subNumber has a -1 due to the offset of lists
#         url[i] = (f"https://www.apahotel.com/monthly_search/?book-plan-category=11&book-no-night=30&prefsub={prefList[settings['subNumber']-1]}"
#         f"&areasub={idList[settings['subNumber']-1]}&book-checkin={date}&book-no-people={settings['numberPeople']}&book-no-room={settings['numberRooms']}&book-no-children1"
#         f"=&book-no-children2=&book-no-children3=&book-no-children4=&book-no-children5=&book-no-children6=&book-smoking={settings['smokingRoom']}&is_midnight=0")
#         date += timedelta(days=1)
#         with open(f'generatorlog.log', 'a') as f:
#                 f.write(f'{url[i]}\n\n')
#                 print(f'{url[i]}\n')
#     return url

# def SEARCH_EVERYTHING(settings: dict):
#     """Creates a URL list of all valid dates at all locations
    
#     Parameters
#     -
#     settings: Most settings will be overwritten by this function"""
#     settings["lastDay"] = 31
#     settings["lastMonth"] = 10
#     settings["lastYear"] = 2023
#     settings["firstDay"] = int(datetime.now().strftime("%d"))
#     settings["firstMonth"] = int(datetime.now().strftime("%m"))
#     settings["firstYear"] = int(datetime.now().strftime("%Y"))
#     urlList = generate_URL_batch(settings)
#     for i in range(len(idList)):
#         #subs start at one, not zero
#         settings["subNumber"] = i + 1
#         urlList = urlList + generate_URL_batch(settings)
#     return urlList
        

# async def get_and_check_HTML(session: aiohttp.ClientSession, url: str):
#     """Requests html from one url and waits. When the page arrives it is checked for vacancy
#     and if found, creates a file in the current directory containing its link
    
#     Parameters
#     -
#     session: the aiohttp session that is being used to send web requests.
#     url: website url that needs to be checked.
#     """
#     async with session.get(url) as response:
#         dump = await response.text()
#         logging.info(f"searched: {url}")
#         #when HTML is received, search it for availabilities and log the result
#         bookings = re.search((r'<span class="big-font">[^0]</span>'), dump)
#         if (bookings != None):
#             bookings = re.search(r'\d+', bookings.group())
#             print("FOUND ONE ON THIS DAY, NUMBER AVAIL: ", bookings.group())
#             logging.warning("match found")
#             #write the url with bookings to hard drive
#             with open(f'targetpage__{datetime.now()}.html', 'w') as f:
#                 f.write(url)
         
# async def main(mode: int):
#     """Creates a web session and uses asynchronous functions to download requested urls.
    
#     Parameters
#     -
#     mode: toggles the scope of the search.
    
#     0 - Search a single location, 1 - Search all locations during all dates
#     """
#     #use fake header because we arent a bot
#     async with aiohttp.ClientSession(headers=headers) as session:
#         #option for searching a single location or all of them
#         if mode == 0:
#             queryType = generate_URL_batch(querySettings)
#         if mode == 1:
#             queryType = SEARCH_EVERYTHING(querySettings)
#         await asyncio.gather(*[get_and_check_HTML(session, url) for url in queryType])
            
# # if __name__ == "__main__":
# #     idList, prefList, subList, engList = generate_location_lists()
# #     asyncio.run(main(1))