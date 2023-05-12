from bs4 import BeautifulSoup
from dataclasses import dataclass, field
import requests
import re
import os
from datetime import timedelta, datetime
from typing import Union
from collections import Counter
from time import perf_counter
import pickle
import asyncio
import aiohttp

#this file is a list of common english words, with many technologies that use common words such as "python" or "rust" removed
#words that are not in this list are likely to be a piece of software, eg. SQL or Postgres
#source: https://github.com/dwyl/english-words
english_words = frozenset(map(str.rstrip, open(os.getcwd()+'/gApp/words_alpha.txt')))


@dataclass
class job():
    """Holds all relevant information about a job posting, and contains various functions to deal with lists of jobs.
    May be stored and read from a .jobfile
    
    Class Variables Information
    -    
    applicants: Only displays between 25 and 200. Any values outside that range are unknown."""
    #relevant_keywords MUST remain the last variable declared for making dumping easier
    title: str = '.'
    date_posted: str = '.'
    location: str = '.'
    seniority_level: str = '.'
    company_name: str = '.'
    employment_type: str = '.'
    industry: str = '.'
    job_function: str = '.'
    search_origin = '.'
    applicants: int = 0
    description: str = '.'
    search_origin: str = '.'
    URL: str = '.'
    #The following fields do not have a dedicated location and will take some testing to make consistent
    # salary: int = 0
    # years_of_experience: int = 0
    # education_level: str = ''
    # remote_type: str = ''
    
    #this must be the last variable declared, for making dumping easier
    relevant_keywords: dict = field(default_factory=dict)
    
    def dump(self):
        """Transform this object into a one line string and return it. Used to write human-readable .jobfiles.
        
        If there is a serialization error, this will return None.
        
        Delimiters: || for values and ^^ for dictionary contents"""
        # print(self.__dict__.keys())
        
        #grab dictionary of all variables in this class
        index = list(self.__dict__.values())
        #extract the relevant_keywords dictionary
        kwDict = index.pop(len(index)-1)
        #turn relevant_keywords dictionary into a string
        kw = '^^'.join([f'{key}^^{value}' for key,value in kwDict.items()])
        #turn the rest of vars into a string and combine them, terminating with a newline
        final = '||'.join([str(val) for val in index]) + f'||{kw}\n'
        ##Errorcheck the string before returning it
        if(final.count('||') == len(index)) and (final.count('^^') == len(kwDict)*2-1):
            return final
        return None
    
    def load(csv: str):
        """Loads a .jobfile and returns a list of the objects inside it.
        If the file is invalid, None will be returned."""
        #if not a .jobfile reject it
        if not (csv[-8:] == '.jobfile'):
            return None
        jobList = []
        with open(csv) as file:
            for i, line in enumerate(file):
                if not i == 0:
                    jobList.append(convert_from_jobfile(line))
        l = len(jobList)
        if l <= 0:
            assert('Jobfile is empty!')
            return None
        #success
        elif l > 0:
            return jobList
        raise Exception( 'unknown error in job.load()')
    
    def get_keywords(data: Union[str, list]):
        """Accepts a list of jobs or .jobfile and returns a Counter containing keyword counts, for importation into dataframes."""
        counter = Counter()
        jobs = []
        if type(data) == str:
            jobs = job.load(data)   
        for item in jobs:
            counter +=Counter(item.relevant_keywords)
        return counter
    
    async def get_linkedin(URL: str, session=None):
        """Downloads information from a linkedin posting into a job object.
        If there is a connection error, None will be returned."""
        #if no session is passed for async downloading, download the URL using requests
        if session == None:
            try:
                page = requests.get(URL).text
            except Exception:
                print(f"***\nerror connecting to {URL}\n***")
                return None
        #if a session is passed, LET 'ER RIP with async functions
        else:
            async with session.get(URL) as response:
                try:
                    page = await response.text()
                except Exception:
                    print(f"***\nerror connecting to {URL}\n***")
                    return None
             
        print(f'page: {clean_html(page)[:20]}')
                
        soup = BeautifulSoup(page, features="html.parser")
        #fill in all the information of the job class
        item = job()
        description = str(soup.find(class_="show-more-less-html__markup"))
        item.description = clean_html(description, special_chars=True)
        item.title = clean_html(str(soup.find(class_="top-card-layout__title")))
        print(f'title: {item.title}, soup: {clean_html(soup.text)[:20]}')
        #####
        ##figure out a  way to verify these before putting them in data
        #####
        #these fields are optional on postings
        # one, two, three, four = soup.findAll(class_="description__job-criteria-text")
        # if one: item.seniority_level = clean_html(str(one))
        # if two: item.employment_type = clean_html(str(two))
        # if three: item.job_function = clean_html(str(three))
        # if four: item.industry = clean_html(str(four))
        ######
        ##create a function to convert this into a specific date instead of "4 days ago"
        ######
        item.date_posted = clean_html(str(soup.find(class_="posted-time-ago__text")), special_chars=True)
        item.company_name = clean_html(str(soup.find(class_="topcard__org-name-link")))
        apps = clean_html(str(soup.find(class_="num-applicants__caption")), special_chars=True)
        apps = re.sub(r"[^\d]","", apps)
        #####
        ##applicants almost never works, try to fix it
        #####
        try:
            item.applicants = int(apps)
        except Exception:
            pass
            # print(f"Could not add applicants for {URL} ")
        item.location = clean_html(str(soup.find(class_="topcard__flavor--bullet")))
        item.URL = URL
        #The following fields do not have a dedicated location and will take some testing to make consistent
        # item.salary: int
        # item.years_of_experience: int
        # item.education_level: str
        # item.remote_type: str
        
        #process relevant_keywords last so that it can use all the other fields to determine which words are important
        item.relevant_keywords = count_relevant_words(item, english_words)
        if item.title == '.':
            print(f'***\nwtf its \'.\' \n*** {soup.text}')
        elif item.title == None:
            print(f'***\nwtf its None\n*** {soup.text}')
        elif item.title == 'None':
            print(f'***\nwhy the fuck is the text None on\n*** {soup.text}')
        else:
            print(f'Should be working: {item.title}')
        return item
    
def convert_from_jobfile(string: str):
    """Create job object from a line of custom csv created by job class. String must be in the .jobfile format()

    Returns the initialized job object."""
    #delete final newline char
    string = string[:-1]
    vars = string.split('||')
    #remove the string containing dictionary entries
    kw = vars.pop(len(vars)-1).split('^^')
    kwDict = {}
    #load dictionary items into a real dictionary
    for i in range(0,len(kw)-1,2):
        kwDict[kw[i]] = int(kw[i+1])
    return job(*vars,kwDict)

def clean_html(text: str, clean_spaces=True, special_chars=False):
    """Returns given string without tags.
    Strings can be returned containing special characters, or with a-z only.
    Can skip cleaning spaces for a small optimization."""
    #remove html tags
    text = re.sub(r"<.*?>", " ", text)
    
    if special_chars:
        #put spaces after phrase terminating characters
        re.sub(r"([\.\,\:\;])", r"\1 ", text)
    else:
        #remove special characters
        text = re.sub(r"[\W+0-9]"," ", text)
        
    if clean_spaces:
        #extra spaces were inserted to prevent words from conjoining, remove them
        text = " ".join(text.split())
    return text

def count_relevant_words(theJob: job, languageSet: frozenset):
    """Counts the words of a string, but only if they are not in the provided set.
    The string can be an html block, this is a very sexy function."""
    wordCounts = {}
    text = clean_html(theJob.description, clean_spaces=False)
    wordList = text.casefold().split()
    ignore = (f'{theJob.title} {theJob.company_name} {theJob.job_function} {theJob.location} {theJob.industry}'
            f'{theJob.location} {theJob.seniority_level} {theJob.job_function}'.casefold().split())

    posting_name = theJob.company_name.casefold().split()
    for word in wordList:
        #ignore english words
        if word in languageSet:
            continue
        #ignore words that are just descriptors for the job
        if word in ignore:
            continue
        #track the occurances of relevant words
        if word in wordCounts:
            wordCounts[word] += 1
        else:
            wordCounts[word] = 1
    return wordCounts


url = 'https://ca.linkedin.com/jobs/view/qa-engineer-at-ecapital-corp-3590139610?refId=ij2nQ8iQfvY6hlOQjBBghg%3D%3D&trackingId=VY7qvBilt8RnMmCfRbVTJw%3D%3D&position=6&pageNum=0&trk=public_jobs_jserp-result_search-card'
url = 'https://ca.linkedin.com/jobs/view/full-stack-developer-at-talentlab-3586545566?refId=5%2BlKr7zQOyEMHEUAMH1wSg%3D%3D&trackingId=8LkkuWqCvQWB4z1t1VH%2Big%3D%3D&trk=public_jobs_topcard-title'


# go = asyncio.run(job.get_linkedin('https://ca.linkedin.com/jobs/view/int-business-analyst-at-apex-systems-3563272817?refId=rLpEFZ2ozzMldV4n1LIQIw%3D%3D&trackingId=wGAETr0qkqp0qa%2BlTv4qzQ%3D%3D&position=12&pageNum=7&trk=public_jobs_jserp-result_search-card'))
# print(go.dump())

# testlist =job.load('17:19:39 10-05-2023 keywords=Qa&location=Canada&locationId=&geoId=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&position=1&pageNum=0.jobfile')
# st = perf_counter()
# with open('pickletest', 'wb') as file:
#     pickle.dump(testlist, file)
# with open('pickletest', 'rb') as file:
#     print(pickle.load(file))
# tt = perf_counter()
# print(f'pickle: {tt - st}')
# tt = perf_counter()
# with open('dumptest', 'w') as file:
#     for line in testlist:
#         file.write(line.dump())
# loaded = job.load('dumptest')
# et = perf_counter()
# print (f"jbfunc: {et - tt}")
#####
#write then read test results:
#####
# pickle: 0.6444128079892835
# jbfunc: 0.003757433994906023
# thats a 72%% increase in performance over pickling
# print(go.applicants)
