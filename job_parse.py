from bs4 import BeautifulSoup
import jsonpickle
from dataclasses import dataclass, field
import requests
import re
import os
import json
from datetime import timedelta, datetime
import logging
import time

#this file is a list of common english words, with many technologies that use common words such as "python" or "rust" removed
#words that are not in this list are likely to be a piece of software, eg. SQL or Postgres
#source: https://github.com/dwyl/english-words
english_words = frozenset(map(str.rstrip, open(os.getcwd()+'/gApp/words_alpha.txt')))


@dataclass
class job():
    """Holds all relevant information about a single job posting.
    May be stored and read from csv.
    
    ::job.applicants:: Only displays between 25 and 200. Any values outside that range are unknown."""
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
        """Transform this object into a one line string and return it.
        
        Delimiters: | for values and ^ for dictionary contents"""
        
        #grab dictionary of all variables in this class
        index = list(self.__dict__.values())
        #extract the relevant_keywords dictionary
        kwDict = index.pop(len(index)-1)
        #turn relevant_keywords dictionary into a string
        kw = '^'.join([f'{key}^{value}' for key,value in kwDict.items()])
        #turn the rest of vars into a string and combine them, terminating with a newline
        final = '|'.join([str(val) for val in index]) + f'|{kw}\n'
        return final
        
    def load(string: str):
        """Create job object from a line of csv. String must be in a format created by this class using dump_csv()
        
        Returns the initialized job object."""
        #delete newline char
        string = string[:-1]
        vars = string.split('|')
        #remove the final string containing dictionary entries
        kw = vars.pop(len(vars)-1).split('^')
        kwDict = {}
        #load dictionary items into a real dictionary
        for i in range(0,len(kw)-1,2):
            kwDict[kw[i]] = int(kw[i+1])
        return job(*vars,kwDict)
    
    def get_linkedin(URL: str):
        return download_job_linkedin(URL)
    
        
    

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

def count_relevant_words(text: str, languageSet: frozenset):
    """Counts the words of a string, but only if they are not in the provided set.
    The string can be an html block, this is a very sexy function."""
    wordCounts = {}
    text = clean_html(text, clean_spaces=False)
    wordList = text.casefold().split()
    #ignore english words in text
    for word in wordList:
        if word in languageSet:
            pass
        #count the occurances of relevant words
        else:
            if word in wordCounts:
                wordCounts[word] += 1
            else:
                wordCounts[word] = 1
    return wordCounts

url = 'https://ca.linkedin.com/jobs/view/qa-engineer-at-ecapital-corp-3590139610?refId=ij2nQ8iQfvY6hlOQjBBghg%3D%3D&trackingId=VY7qvBilt8RnMmCfRbVTJw%3D%3D&position=6&pageNum=0&trk=public_jobs_jserp-result_search-card'
url = 'https://ca.linkedin.com/jobs/view/full-stack-developer-at-talentlab-3586545566?refId=5%2BlKr7zQOyEMHEUAMH1wSg%3D%3D&trackingId=8LkkuWqCvQWB4z1t1VH%2Big%3D%3D&trk=public_jobs_topcard-title'

def download_job_linkedin(URL: str):
    # header that pretends to be a browser
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0"}
    try:
        page = requests.get(URL, headers=headers, allow_redirects=False)
    except:
        print("***\nerror connecting to website\n***")
    soup = BeautifulSoup(page.text, features="html.parser")
    
    #fill in all the information of the job class
    item = job()
    description = str(soup.find(class_="show-more-less-html__markup"))
    item.description = clean_html(description, special_chars=True)
    item.relevant_keywords = count_relevant_words(description, english_words)
    item.title = clean_html(str(soup.find(class_="top-card-layout__title")))
    #####
    ##figure out a  way to verify these before putting them in data
    #####
    #these fields are optional on postings
    # criteria = soup.findAll(class_="description__job-criteria-text")
    # len(criteria)
    # print(criteria)
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
    try:
        item.applicants = int(apps)
    except:
        print("applicants had no value")
    item.location = clean_html(str(soup.find(class_="topcard__flavor--bullet")))
    item.URL = URL
    #The following fields do not have a dedicated location and will take some testing to make consistent
    # item.salary: int
    # item.years_of_experience: int
    # item.education_level: str
    # item.remote_type: str
    return item

go = job.get_linkedin('https://ca.linkedin.com/jobs/view/int-business-analyst-at-apex-systems-3563272817?refId=rLpEFZ2ozzMldV4n1LIQIw%3D%3D&trackingId=wGAETr0qkqp0qa%2BlTv4qzQ%3D%3D&position=12&pageNum=7&trk=public_jobs_jserp-result_search-card')
print(go.applicants)