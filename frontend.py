import streamlit as st
from job_parse import job
import scraper
import matplotlib.pyplot as plt
from collections import Counter


st.title('My site')
st.text('This is written stuff')

#numer of results you would like to be displayed in the bar graph
amount = 20

# jobList = job.get_keywords('17:19:39 10-05-2023 keywords=Qa&location=Canada&locationId=&geoId'
#                             '=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&position=1&pageNum=0.jobfile')
jobList = scraper.get_jobs_from_search('https://www.linkedin.com/jobs/search/?currentJobId=3284295341&f_E=3&geoId=106234700&keywords=Developer&location=Ottawa%2C%20Ontario%2C%20Canada&refresh=true')
# jobList = job.load('00:15:34 14-05-2023 keywords=Qa&location=Canada&locationId=&geoId=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&position=1&pageNum=0.jobfile')
kws = job.keywords(jobList)
#extract the most common keywords
results = kws.most_common(amount)
#convert Count dictionary to two lists
keywords = [i[0] for i in results]
values = [i[1] for i in results]
#reverse for visual clarity
keywords.reverse()
values.reverse()
# creating the bar plot
fig = plt.figure(figsize = (10, 5))
plt.barh(keywords, values, color ='teal',
        height = 0.4)
#labels
plt.xlabel("No. of times mentioned")
plt.ylabel("Key words")
plt.title("Most important words in this search.")
#ship it
st.pyplot(fig)