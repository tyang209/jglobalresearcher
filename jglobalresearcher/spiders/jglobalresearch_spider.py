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
    	def scrapePapers(mainDict,innerHTML):
    		papers = []
    		soup = BeautifulSoup(innerHTML)

			#translation of unicode headers into english
			translationDict = {u'\u30da\u30fc\u30b8':'Page',
			                   u'\u53f7':'Issue',
			                    u'\u5dfb':'Volume',
			                    u'\u8cc7\u6599\u540d':'JournalName',
			                    u'\u8457\u8005':'Authors',
			                    u'\u767a\u884c\u5e74':'PubYear'}

			#re pattern for finding JGLOBALIDs
			jglobal_id_regex = re.compile(r'.*JGLOBAL_ID=(\d+)')

			linkArray=[]
			#only return divs that are direct decendents.
			#beautiful soup automatically adds a html,body fields

			for index,div in enumerate(soup.html.body.findAll('div',recursive=False)):

			    paperDict = {}
			    
			    link = div.find('a')['href']
			    
			    if link in linkArray:
			        continue
			        
			    linkArray.append(link)
			    paperDict['PaperLink'] = anchor['href']
			    match = jglobal_id_regex.match(link)
			    
			    if match:
			        paperDict['PaperinJGLOBAL'] = 'Yes'
			        paperDict['JGLOBALID'] = match.group(1)   
			        
			    for p in div.findAll('p'):
			        if p['class'] in (['light'],['txtR', 'light']):
			            paperDict['Title'] = p.text

			        elif p['class'] in [['light','mB10']]:
			            for span in p.findAll('span',{'class':'fwB'}):
			                translatedKey = translationDict[span.text.replace(u'\uff1a','').strip()]
			                paperDict[translatedKey]= span.next_sibling.strip()
			    papers.append(paperDict)
		   	return papers

    	def is_element_present(self, xpath):
		    try: 
		    	self.driver.find_element_by_xpath(xpath)
		    except NoSuchElementException: 
		    	return False
		    return True

		self.driver.get(response.url)
		self.driver.set_window_size(1920, 1000)
		time.sleep(5)
		items = []

		mainDict = {}
		mainDict['JGLOBALID'] = returnJGlobalID(response.url)
		nameXpath = "//h1[contains(@id,'JD_NMRJ')]"
		papersMoreButtonXP = "//td[contains(@id,'JD_PA')]//img[contains(@src,'/common/images/btn_more.png')]"
		miscMoreButtonXP = "//td[contains(@id,'JD_AR')]//img[contains(@src,'/common/images/btn_more.png')]"
		booksMoreButtonXP = "//td[contains(@id,'JD_BKNAM')]//img[contains(@src,'/common/images/btn_more.png')]"
		

		WebDriverWait(self.driver,60).until(
				lambda x: len(x.find_element(By.ID,'JD_NMRJ').text)>0
			)

		dept_affil_div = self.driver.find_element(By.ID,'JD_CS_2')
		jobTitle_div = self.driver.find_element(By.ID,'JD_CS_3')
		other_affil = self.driver.find_element(By.ID,'JD_CS_4')
		research_topics = self.driver.find_element(By.ID,'JD_RFD_J')

		if not is_element_present(self, papersMoreButtonXP):
			xpath = "//td[contains(@id,'JD_PA')]"
			elem = self.driver.find_element_by_xpath(xpath)
			elem.get_attribute('innerHTML')


		mainDict = parseDepartmentAffil(mainDict, dept_affil_div.get_attribute('innerHTML'))

		mainDict['JobTitle'] = jobTitle_div.text
		mainDict['Other_Affil'] = returnFreeText(mainDict, other_affil.text,'Other_Affil')
		mainDict['ResearchKeywords'] = returnResearchTopics(mainDict,returnResearchTopics)
		


		self.driver.close()
		return items
	