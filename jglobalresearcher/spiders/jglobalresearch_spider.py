# -*- coding: utf-8 -*-
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.spider import Spider
from scrapy.contrib.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy import Selector
from jglobalresearcher.items import JglobalresearcherItem
import re
from platform import system
from scrapy import log
from scrapy.log import ScrapyFileLogObserver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import time


class jglobalresearcher_spider(CrawlSpider):
	name = "jglobalresearcher_spider"
	def __init__(self,name=None,**kwargs):
		super(jglobalresearcher_spider, self).__init__(name, **kwargs)

		if system() == 'Darwin':
			self.driver = webdriver.Chrome("./chromedriver")
			print 'mac'
		elif system() =='Windows':
			self.driver = webdriver.Chrome("chromedriver.exe")
			print 'windows!'
		allowed_domains = ["jglobal.jst.go.jp"]
		self.start_urls=["http://jglobal.jst.go.jp/detail.php?JGLOBAL_ID=200901040373420620&q=kyoto%20university&t=1"]



	def parse(self, response):

		def returnJGlobalID(url):
			#return id after GLOBAL_ID
			return url.split('=')[1][0:-2]

		def parseDepartmentAffil(mainDict, innerHTML):
			soup = BeautifulSoup(innerHTML)
			#headers are in a span class so get the next text sibling
			#to key-value in department affiliation div 
			for span in soup.find('p',{'class':'light mB10'}).findAll('span'):
    			mainDict[span.text.strip()]=span.next_sibling.strip()
    		#parse and find link to agency link
    		try:
    			mainDict['機関'] = soup.find('a').text
    			mainDict['機関_link'] = soup.find('a')['href']
	    		
	    		return mainDict
	    	except:
	    		return mainDict
    	def returnFreeText(mainDict,innerHTML,key):
    		# return div as a bunch of free text
    		try:
    			soup = BeautifulSoup(innerHTML)
    			if len(soup.text)>0:
    				mainDict[key] = soup.text

    		except TypeError:
    			
    		return mainDict
    	def returnResearchTopics(mainDict,innerHTML):
    		textArray=[]
    		try:
				soup =BeautifulSoup(doc)
				for anchor in soup.findAll('a'):
					if len(anchor.findChildren())==0:
				        textArray.append(anchor.text)
				        mainDict['ResearchTopics'] = textArray
    		except TypeError:
    			
    		return mainDict


		self.driver.get(response.url)
		self.driver.set_window_size(1920, 1000)
		time.sleep(5)
		items = []

		mainDict = {}
		mainDict['JGLOBALID'] = returnJGlobalID(response.url)
		nameXpath = "//h1[contains(@id,'JD_NMRJ')]"
		WebDriverWait(self.driver,60).until(
				lambda x: len(x.find_element(By.ID,'JD_NMRJ').text)>0
			)

		dept_affil_div = self.driver.find_element(By.ID,'JD_CS_2')
		jobTitle_div = self.driver.find_element(By.ID,'JD_CS_3')
		other_affil = self.driver.find_element(By.ID,'JD_CS_4')
		research_topics = self.driver.find_element(By.ID,'JD_RFD_J')


		mainDict = parseDepartmentAffil(mainDict, dept_affil_div.get_attribute('innerHTML'))

		mainDict['JobTitle'] = jobTitle_div.text
		mainDict['Other_Affil'] = returnFreeText(mainDict, other_affil.text,'Other_Affil')
		mainDict['ResearchKeywords'] = returnResearchTopics(mainDict,returnResearchTopics)
		


		self.driver.close()
		return items
	