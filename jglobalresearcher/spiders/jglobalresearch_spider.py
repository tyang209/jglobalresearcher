# -*- coding: utf-8 -*-
import codecs
from urllib2 import unquote
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.spider import Spider
from scrapy.contrib.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy import Selector
from jglobalresearcher.items import JglobalresearcherItem
import re
from platform import system
from scrapy import log
from scrapy.log import ScrapyFileLogObserver
import json
from bs4 import BeautifulSoup

from selenium import webdriver
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time


class jglobalresearcher_spider(CrawlSpider):
	name = "jglobalresearcher_spider"

	def __init__(self,name=None,**kwargs):
		super(jglobalresearcher_spider, self).__init__(name, **kwargs)

		if system() == 'Darwin':
			self.driver = webdriver.Chrome("./chromedriver")
			# self.driver = webdriver.Firefox()
			print 'mac'
		elif system() =='Windows':
			self.driver = webdriver.Chrome("chromedriver.exe")
			# self.driver = webdriver.Firefox()
			print 'windows!'
		self.moreButtonXpath = "//img[contains(@src,'/common/images/btn_more.png')]"
		self.nextPagexpath = "//a[contains(@id,'JD_P_NEXT')]/img"
		allowed_domains = ["http://jglobal.jst.go.jp"]
		self.start_urls=["http://jglobal.jst.go.jp/detail.php?JGLOBAL_ID=200901040373420620&q=kyoto%20university&t=1"]
		self.JGLOBAL_DOMAIN = "http://jglobal.jst.go.jp"
		self.translationDict = {u'\u30da\u30fc\u30b8':'Page',
                   u'\u53f7':'Issue',
                    u'\u5dfb':'Volume',
                    u'\u8cc7\u6599\u540d':'JournalName',
                    u'\u8457\u8005':'Authors',
                    u'\u767a\u884c\u5e74':'PubYear',
					u'\u90e8\u7f72':'Department',
					u'\u4f4f\u6240':'Address',
					u'\u4e8b\u696d\u6982\u8981':'Department_Description',
					u'\u90e8\u7f72\u30fb\u8077\u540d':'Department_Job_Title',
					u'\u7814\u7a76\u8005\u30ea\u30be\u30eb\u30d0\u30fc':'Resolver',
					u'NDL\u30b5\u30fc\u30c1' : 'NDL',
					u'\u7814\u7a76\u8005HP(\u65e5)':'Personal_Home_Page'
						}		


	
	def returnJGlobalID(self,url):
		#return id after GLOBAL_ID
		return url.split('=')[1][0:-2]

	def parseDepartmentAffil(self,mainDict, innerHTML,other=False):
		other_flag = ''
		if other:
			other_flag='Other'
		soup = BeautifulSoup(innerHTML)
		if len(soup)==0:
			return mainDict
		#headers are in a span class so get the next text sibling
		#to key-value in department affiliation div 

		for span in soup.find('p',{'class':'light mB10'}).findAll('span'):
			cleanedHeader = span.text.strip().replace(u'\uff1a','')
			translated_key=self.translationDict[cleanedHeader]
			mainDict[other_flag+translated_key]=span.next_sibling.strip()
		#parse and find link to agency link
		try:
			mainDict[other_flag+'Institution'] = soup.find('a').text
			mainDict[other_flag+'Institution_link'] = soup.find('a')['href']
		except:
			pass
		return mainDict

	def returnFreeText(self,mainDict,innerHTML,key):
		# return div as a bunch of free text
		try:
			soup = BeautifulSoup(innerHTML)
			if len(soup.text)>0:
				mainDict[key] = soup.text

		except TypeError:
			mainDict[key] = ''
		return mainDict

	def nextButtonValid(self, driver2):
		nextButtonXpath = "//img[contains(@src,'/common/images/pager_arrow_next.png')]"
		nextButtonGreyXpath  ="//img[contains(@src,'/common/images/pager_arrow_next_no.png')]"
		print 'validating'
		try:
			elem = driver2.find_element_by_xpath("//div[contains(@id,'JD_PAGER')]")
			if self.is_element_present(elem,nextButtonXpath):
				return True
			elif self.is_element_present(elem,nextButtonGreyXpath):
				return False
			else:
				return False

		except NoSuchElementException:
			return False

	def scroll_element_into_view(self,driver, element):
   	 
	    y = element.location['y']
	    driver.execute_script('window.scrollTo(0, {0})'.format(y))

	def getAllPagesInnerHTML(self,link):

		nextButtonXpath = "//img[contains(@src,'/common/images/pager_arrow_next.png')]"		
		if system() == 'Darwin':
			driver2 = webdriver.Chrome("./chromedriver")
			# driver2 = webdriver.Firefox()
			print 'mac'
		elif system() =='Windows':
			driver2 = webdriver.Chrome("chromedriver.exe")
			# driver2 = webdriver.Firefox()
			print 'windows!'
		print link
		driver2.get(link)
		driver2.set_window_size(1920, 1000)
		masterSoup = BeautifulSoup('<html><body><body></html>')
		conditionFlag = True
		print 'entering while loop'
		while  conditionFlag:
			print 'waiting'
			WebDriverWait(driver2 , 60).until(
				EC.invisibility_of_element_located((By.ID, 'JD_MAIN_LD'))
				# lambda x: x.find_element(By.ID,'JD_MAIN_LD')
				)
			print 'not waiting'
			mainElem = driver2.find_element(By.ID,'JD_MAIN')
			mainElemHTML = mainElem.get_attribute('innerHTML')
			soup = BeautifulSoup(mainElemHTML)
			for div in soup.html.body.findAll('div',recursive=False):
				print div
				masterSoup.html.body.append(div)
			print len(masterSoup.findAll('div',recursive=False))
			if self.nextButtonValid(driver2):
				nextButton = driver2.find_element_by_xpath(nextButtonXpath)
				self.scroll_element_into_view(driver2,nextButton)
				nextButton.click()
			else:
				conditionFlag = False


		driver2.close()
		return masterSoup


	def scrapePapers(self,mainDict,miscElem):
		if self.is_element_present(miscElem,self.moreButtonXpath):
			html = miscElem.get_attribute('innerHTML')
			soup = BeautifulSoup(html)
			link = self.JGLOBAL_DOMAIN + soup.find('p',{'class':'txtAR'}).find('a')['href']
			soup = self.getAllPagesInnerHTML(link)
			for div in soup.findAll('div'):
				print div
		else:
			innerHTML = miscElem.get_attribute('innerHTML')
			soup = BeautifulSoup(innerHTML)
		papers = []
		

		#translation of unicode headers into english

		#re pattern for finding JGLOBALIDs
		jglobal_id_regex = re.compile(r'.*JGLOBAL_ID=(\d+)')

		linkArray=[]
		#only return divs that are direct decendents.
		#beautiful soup automatically adds a html,body fields


		for index,div in enumerate(soup.html.body.findAll('div',recursive=False)):
			print div
			paperDict = {}

			link = div.find('a')['href']

			if link in linkArray:
			    continue
			    
			linkArray.append(link)
			paperDict['PaperLink'] = link
			match = jglobal_id_regex.match(link)

			if match:
			    paperDict['PaperinJGLOBAL'] = 'Yes'
			    paperDict['JGLOBALID'] = match.group(1)   
			    
			for p in div.findAll('p'):
			    if p['class'] in (['light'],['txtR', 'light']):
			        paperDict['Title'] = p.text

			    elif p['class'] in [['light','mB10']]:
			        for span in p.findAll('span',{'class':'fwB'}):
			            translatedKey = self.translationDict[span.text.replace(u'\uff1a','').strip()]
			            paperDict[translatedKey]= span.next_sibling.strip()
			papers.append(paperDict)
		return papers

	def is_element_present(self,elem,xpath):
	    try: 
	    	elem.find_element_by_xpath(xpath)
	    except NoSuchElementException: 
	    	return False
	    return True
	def parseResearchGrants(self,innerHTML):
		soup = BeautifulSoup(innerHTML)
		grantArray = []
		for row in soup.findAll('tr'):
		    grantDict = {}
		    years = row.th.text.split(' - ')
		    if len(years[0])>0:
		        grantDict['StartYear']=years[0]
		    if len(years[1])>0:
		        grantDict['EndYear'] = years[1]
		    grantDict['Grant']  = row.td.text
		    grantArray.append(grantDict)
		return grantArray

	def parseOtherSourceLinks(self,webelements):
		array=[]
		resolver_regex = re.compile(r'.+id=(\d+)')
		researchmap_regex = re.compile(r'.+read(\d+)') 

		for elem in webelements:
			linkDict= {}
			soup = BeautifulSoup(elem.get_attribute('outerHTML'))
			title = soup.find('a')['title']
			link = unquote(soup.find('a')['href']).replace('http://jglobal.jst.go.jp/redir.php?url=','')
			if title =='researchmap':
				linkSource='researchmap'
				match = researchmap_regex.match(link)
				if match:
					linkDict['LinkID'] = match.group(1)				
			else:
				linkSource = self.translationDict.get(title,title)

			linkDict['Source'] = linkSource
			linkDict['Link'] = link
			if linkSource =='Resolver':
				match = resolver_regex.match(link)
				if match:
					linkDict['LinkID'] = match.group(1)
			array.append(linkDict)
		return array
	def parseResearchTags(self,innerHTML):
		soup = BeautifulSoup(innerHTML)
		array = []
		if len(soup)==0:
			return None
		for anchor in soup.findAll('a'):
			if len(anchor.findChildren())==0:
				array.append(anchor.text)
		return array


	def parse(self, response):
		print response.url
		self.driver.get(response.url)
		self.driver.set_window_size(1920, 1000)
		item = JglobalresearcherItem()

		mainDict = {}
		mainDict['JGLOBALID'] = self.returnJGlobalID(response.url)
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
		field_of_study = self.driver.find_element(By.ID,'JD_RFD_J')
		other_source_links = self.driver.find_elements_by_xpath("//a[contains(@class,'mR10')]")
		research_keywords = self.driver.find_element(By.ID,'JD_RFKW_2')
		grantResearch = self.driver.find_element(By.ID,'JD_THM')
		miscElem = self.driver.find_element(By.ID,'JD_AR')

		mainDict['Other_Source_Links'] = self.parseOtherSourceLinks(other_source_links)
		# if not self.is_element_present(papersMoreButtonXP):
		# 	xpath = "//td[contains(@id,'JD_PA')]"
		# 	elem = self.driver.find_element_by_xpath(xpath)
		# 	papersElem = elem.get_attribute('innerHTML')
		# if not self.is_element_present(miscMoreButtonXP): 


		mainDict = self.parseDepartmentAffil(mainDict, dept_affil_div.get_attribute('innerHTML'))

		mainDict['JobTitle'] = jobTitle_div.text
		mainDict = self.parseDepartmentAffil(mainDict, other_affil.get_attribute('innerHTML'),other=True)

		mainDict['Field_Of_Study'] = self.parseResearchTags(field_of_study.get_attribute('innerHTML'))
		mainDict['ResearchKeywords'] = self.parseResearchTags(research_keywords.get_attribute('innerHTML'))
		mainDict['ResearchGrants'] = self.parseResearchGrants(grantResearch.get_attribute('innerHTML'))		

		mainDict['Misc'] = self.scrapePapers(mainDict,miscElem)
		print 'done with papers'
		with codecs.open('export.json','w+','utf-8') as f:

		    json.dump(mainDict, f,indent=4)
			# for k,v in mainDict.iteritems():
			# 	if type(v) is dict:
			# 		for k2,v2 in v.iteritems():
			# 			f.write( '%s:%s\n' %(k2.decode('utf-8'),v2.decode('utf-8')))
			# 	else:
			# 		f.write( '%s:%s\n' %(k.decode('utf-8'),v.decode('utf-8')))
		# item['Dict'] = mainDict

		self.driver.close()
		return item
