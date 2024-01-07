# Application to help me look for jobs, this has two functions:
1. Scrapes a linkedin search url for all its results, then shows the 10 most desired technologies/skills.
2. In a traditional linkedin search 80% of my time is wasted on junk postings. This parses those results into a jobclass file (database soon to be implemented) that removes spam and mislabeled jobs. This file makes it easy to filter or quickly browse multiple postings.

Features:
Asynchronous consumer/producer download model.
Custom Json dump that is 70% faster compared to default libraries.
IP address rotation service can be plugged in for instant scraping speed.
Linux and Windows friendly.
Still an overengineered mess.
