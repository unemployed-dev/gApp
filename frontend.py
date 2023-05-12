import streamlit as st
from job_parse import job
import matplotlib.pyplot as plt
from collections import Counter


st.title('My site')
st.text('This is written stuff')

#numer of results you would like to be displayed in the bar graph
amount = 20

jobList = job.get_keywords('17:19:39 10-05-2023 keywords=Qa&location=Canada&locationId=&geoId'
                            '=101174742&f_TPR=&f_PP=101788145&f_E=1%2C2%2C3%2C4&position=1&pageNum=0.jobfile')
results = jobList.most_common(amount)
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