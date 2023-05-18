from bs4 import BeautifulSoup
from dataclasses import dataclass, field
import requests
import re
import os
from typing import Union
from collections import Counter
import asyncio

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
        #grab dictionary of all variables in this class
        index = list(self.__dict__.values())
        #extract the relevant_keywords dictionary from that dict
        kwDict = index.pop(len(index)-1)
        #turn the relevant_keywords dictionary into a string
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
        if not (csv[-8:] == '.jobfile'):
            return None
        
        jobList = []
        with open(csv) as file:
            for i, line in enumerate(file):
                    jobList.append(_convert_from_jobfile(line))
        l = len(jobList)
        if l <= 0:
            assert('Jobfile is empty!')
            return None
        if l > 0:
            return jobList
        raise Exception( 'unknown error in job.load()')
    
    def keywords(data: Union[str, list]):
        """Accepts a list of jobs or a .jobfile and returns a Counter containing keyword counts, for importation into dataframes."""
        counter = Counter()
        jobs = []
        if type(data) == str:
            jobs = job.load(data)
        else:
            jobs = data
            
        for item in jobs:
            try:
                counter +=Counter(item.relevant_keywords)
            except Exception:
                print('There was an empty item in the job list when getting keywords. This should not happen.')
        return counter
    
    async def download(URL: str, session=None, timeout_duration=10, attempt_limit=1, search_origin='.'):
        """Downloads information from a linkedin posting into a job object.
        If there is a connection error, None will be returned.
        
        ::attempt_limit:: Maximum number of attempts to try and download the url.
        Each attempt will wait twice as long as the last before trying again. Default at 10 seconds."""
        #if no session is passed for async downloading, download the URL using request
        if session == None:
            try:
                page = requests.get(URL).text
            except Exception:
                print(f"***\nerror connecting to {URL}\n***")
                return None
            
        #if a session is passed, LET 'ER RIP with async function
        async with session.get(URL) as response:
            timeout = timeout_duration
            page = await response.text()
            #if we get denied because of too many requests, retry after waiting a second.
            while not (response.status == 200):
                print(f'Response code is: {response.status}. Probably too many requests. Waiting {timeout_duration} seconds')
                timeout *= 2
                await asyncio.sleep(timeout)
                page = await response.text()
                if timeout >= timeout_duration*pow(2,attempt_limit):
                    # print(f'Timed out while getting {URL}')
                    # print(f'response code is: {response.status}')
                    return None
                
        if "linkedin" in URL:
            item = _create_job_from_linkedin(page, URL, search_origin)
        else:
            print("non-linkedin sites are not yet supported")
            return None
                
        #Errorcheck, return None if there is an issue.
        if (item == None) or item.title == ('.' or 'None' or None):
            print(f'***\nUnknown Error for {URL}\n***')
            print(f'title: {item.title}')
            return None   
        print(f'Downloaded: {item.title}')
        return item
    
def _create_job_from_linkedin(page: str, URL: str, search_origin='.'):
    """Create a job object and fill in its information from a linkedin html page"""
    
    soup = BeautifulSoup(page, features="html.parser")
    item = job()
    description = str(soup.find(class_="show-more-less-html__markup"))
    item.description = _clean_html(description, special_chars=True)
    item.title = _clean_html(str(soup.find(class_="top-card-layout__title")))
    #####
    ##figure out a  way to verify these before putting them in data
    #####
    #these fields are optional on postings
    # one, two, three, four = soup.findAll(class_="description__job-criteria-text")
    # if one: item.seniority_level = _clean_html(str(one))
    # if two: item.employment_type = _clean_html(str(two))
    # if three: item.job_function = _clean_html(str(three))
    # if four: item.industry = _clean_html(str(four))
    ######
    ##create a function to convert this into a specific date instead of "4 days ago"
    ######
    item.date_posted = _clean_html(str(soup.find(class_="posted-time-ago__text")), special_chars=True)
    item.company_name = _clean_html(str(soup.find(class_="topcard__org-name-link")))
    apps = _clean_html(str(soup.find(class_="num-applicants__caption")), special_chars=True)
    apps = re.sub(r"[^\d]","", apps)
    #####
    ##applicants almost never works, try to fix it
    #####
    try:
        item.applicants = int(apps)
    except Exception:
        pass
    item.location = _clean_html(str(soup.find(class_="topcard__flavor--bullet")))
    item.search_origin = search_origin
    item.URL = URL
    #The following fields do not have a dedicated location and will take some testing to make consistent
    # item.salary: int
    # item.years_of_experience: int
    # item.education_level: str
    # item.remote_type: str
    
    #process relevant_keywords last so that it can use all the other fields to determine which words are important
    item.relevant_keywords = _count_relevant_words(item, english_words)
    return item
        
    
def _convert_from_jobfile(string: str):
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

def _clean_html(text: str, clean_spaces=True, special_chars=False):
    """Returns given string without tags.
    Strings can be returned containing special characters, or with a-z only.
    Can skip cleaning spaces for a small optimization."""
    #remove html tags
    text = re.sub(r"<.*?>", " ", text)
    
    if special_chars:
        #put spaces after characters that terminate phrases or sentences
        re.sub(r"([\.\,\:\;])", r"\1 ", text)
    else:
        #remove special characters
        text = re.sub(r"[\W+0-9]"," ", text)
        
    if clean_spaces:
        #extra spaces were inserted to prevent words from conjoining, remove them
        text = " ".join(text.split())
    return text

def _count_relevant_words(theJob: job, languageSet: frozenset):
    """Counts the words of a string, but only if they are not in the provided set.
    The string can be an html block, this is a very sexy function."""
    wordCounts = {}
    text = _clean_html(theJob.description, clean_spaces=False)
    wordList = text.casefold().split()
    #we do not want to track words involving any of the following fields
    ignore = (f'{theJob.title} {theJob.company_name} {theJob.job_function} {theJob.location} {theJob.industry}'
            f'{theJob.location} {theJob.seniority_level} {theJob.job_function}'.casefold().split())

    for word in wordList:
        #ignore english words
        if word in languageSet:
            continue
        #ignore words that are descriptors for the job
        if word in ignore:
            continue
        #track the occurances of relevant words
        if word in wordCounts:
            wordCounts[word] += 1
        else:
            wordCounts[word] = 1
    return wordCounts

#####
#write then read test results:
#####
# pickle: 0.6444128079892835
# jbfunc: 0.003757433994906023
# thats a 72%% increase in performance over pickling
# print(go.applicants)
