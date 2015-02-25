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


		self.moreButtonXpath = "//img[contains(@src,'/common/images/btn_more.png')]"
		self.nextPagexpath = "//a[contains(@id,'JD_P_NEXT')]/img"
		allowed_domains = ["http://jglobal.jst.go.jp"]
		self.start_urls=["http://jglobal.jst.go.jp/detail.php?JGLOBAL_ID=200901079241931254&q=%E4%BA%AC%E9%83%BD%E5%A4%A7%E5%AD%A6&t=1",
						"http://jglobal.jst.go.jp/detail.php?JGLOBAL_ID=200901069127676630&q=%E4%BA%AC%E9%83%BD%E5%A4%A7%E5%AD%A6&t=1",
						"http://jglobal.jst.go.jp/detail.php?JGLOBAL_ID=200901064753496323&q=%E4%BA%AC%E9%83%BD%E5%A4%A7%E5%AD%A6&t=1"]
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
					u'\u7814\u7a76\u8005HP(\u65e5)':'Personal_Home_Page',
					u'\u66f8\u7c4d':'Books',
					u'\u767a\u660e\u8005':'Inventor',
					u'\u51fa\u9858\u4eba/\u7279\u8a31\u6a29\u8005':'Patentee',
					u'\u516c\u5831\u7a2e\u5225':'Patent_Type',
					u'\u51fa\u9858\u756a\u53f7':'Patent_Number',
					u'\u51fa\u9858\u65e5':'Filing_Date',
					u'\u6982\u8981(\u8acb\u6c42\u98051)':'Patent_Summary'
						}		

	def initDriver(self,browser='Chrome'):
		if system() == 'Darwin':
			driver = webdriver.Chrome("./chromedriver")
			# self.driver = webdriver.Firefox()

		elif system() =='Windows':
			driver = webdriver.Chrome("chromedriver.exe")
			# self.driver = webdriver.Firefox()
	
		return driver
	
	def returnJGlobalID(self,url):
		#return id after GLOBAL_ID
		return url.split('=')[1][0:-2]

	def parseDepartmentAffil(self, elem,other=False):
		other_flag = ''
		if other:
			other_flag='Other'

		soup = self.returnProperSoup(elem)

		returnDict = {}
		if len(soup)==0:
			return returnDict
		#headers are in a span class so get the next text sibling
		#to key-value in department affiliation div 

		for span in soup.find('p',{'class':'light mB10'}).findAll('span'):
			cleanedHeader = span.text.strip().replace(u'\uff1a','')
			translated_key=self.translationDict[cleanedHeader]
			returnDict[other_flag+translated_key]=span.next_sibling.strip()
		#parse and find link to agency link
		try:
			returnDict[other_flag+'Institution'] = soup.find('a').text
			returnDict[other_flag+'Institution_link'] = soup.find('a')['href']
		except:
			pass
		return returnDict

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
		driver2=self.initDriver()
		driver2.get(link)
		driver2.set_window_size(1920, 1000)
		masterSoup = BeautifulSoup('<html><body><body></html>')
		conditionFlag = True
	
		while  conditionFlag:
	
			WebDriverWait(driver2 , 60).until(
				EC.invisibility_of_element_located((By.ID, 'JD_MAIN_LD'))
				# lambda x: x.find_element(By.ID,'JD_MAIN_LD')
				)
		
			mainElem = driver2.find_element(By.ID,'JD_MAIN')
			mainElemHTML = mainElem.get_attribute('innerHTML')
			soup = BeautifulSoup(mainElemHTML)
			for element in soup.html.body:
		
				masterSoup.html.body.append(element)
		
			if self.nextButtonValid(driver2):
				nextButton = driver2.find_element_by_xpath(nextButtonXpath)
				self.scroll_element_into_view(driver2,nextButton)
				nextButton.click()
			else:
				conditionFlag = False


		driver2.close()
		return masterSoup

	def isMoreButtonPresent(self,soup):
		a = soup.find('img',{'src':'/common/images/btn_more.png'})
		if a is None:
			return False
		else:
			return True

	def returnProperSoup(self,elem):
		innerHTML = elem.get_attribute('innerHTML')
		soup = BeautifulSoup(innerHTML)

		flag = self.isMoreButtonPresent(soup)

		if flag:
			html = elem.get_attribute('innerHTML')
			soup = BeautifulSoup(html)
			link = self.JGLOBAL_DOMAIN + soup.find('p',{'class':'txtAR'}).find('a')['href']
			soup = self.getAllPagesInnerHTML(link)
			return soup
		else:
			return soup
	def parseCitedPapersPatent(self,elem):
		papers = []
		soup = self.returnProperSoup(elem)

		if len(soup)==0:
			return papers


		#translation of unicode headers into english

		#re pattern for finding JGLOBALIDs
		for index,div in enumerate(soup.html.body.td.findAll('div',recursive=False)):

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
		        if p['class'] ==['txtR', 'light']:
		            paperDict['Title'] = p.text

		        
		    for span in div.next_sibling.findAll('span',{'class':'fwB'}):
		        translatedKey = translationDict[span.text.replace(u'\uff1a','').strip()]
		        if translatedKey=='Authors':
		            paperDict[translatedKey] = [author.strip() for author in span.next_sibling.split(u'\u3001')]
		        else:
		            paperDict[translatedKey]= span.next_sibling.strip()
		    papers.append(paperDict)
    
	def scrapePapers(self,elem):
		papers = []
		soup = self.returnProperSoup(elem)

		if len(soup)==0:
			return papers


		#translation of unicode headers into english

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
			newElem = elem.find_element_by_xpath(xpath)
		except NoSuchElementException: 
			return False
		return True

	def parseBooksPresentations(self,elem):
		array = []
		soup = self.returnProperSoup(elem)

		if len(soup) == 0:
			return bookArray
		for div in soup.body.findAll('div',recursive=False):
			d = {}
			textArray = div.findAll('p')
			d['Title'] = textArray[0].text
			d['Info'] = textArray[1].text
			array.append(bookDict)
		return array


	def parseCareerTimeline(self,elem,CareerGrantEducation):
		
		soup = self.returnProperSoup(elem)
		array = []
		if len(soup) == 0:
			return array
		if len(soup.findAll('tr'))==0:
		    array.append(array.soup.text)
		else:
			for row in soup.findAll('tr'):
			    d = {}
			    if len(row.th.text)>0:
				    years = row.th.text.split(' - ')
				    if len(years[0])>0:
				        d['StartYear']=years[0]
				    if len(years[1])>0:
				        d['EndYear'] = years[1]
			    d[CareerGrantEducation]  = row.td.text
			    array.append(d)
		return array

	def parseWorks(self,elem):
		array = []
		soup = self.returnProperSoup(elem)

		if len(soup) == 0:
			return array

		for div in soup.td.findAll('div',recursive=False):
		    textArray = div.find('p')
		    textArray.text

		    array.append(div.find('p').text)
		return array

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
	def parseDegree(self,elem):
		soup = self.returnProperSoup(elem)
		array = []
		if len(soup)==0:
			return None
		for line in soup.findAll('br'):
			
			array.append(line.previous_sibling)
		return array

	def parseAffiliationTags(self,elem):
		soup = self.returnProperSoup(elem)
		array = []
		if len(soup)==0:
			return None
		for anchor in soup.findAll('a'):
			if len(anchor.findChildren())==0:
				array.append(anchor.text)
		return array

	def parsePatents(self,elem):
		soup = self.returnProperSoup(elem)
		array = []
		if len(soup)==0:
			return None

		for div in soup.findAll('div'):
		    patent = {}
		    for p in div.findAll('p'):
		        if p['class'] in (['light'],['txtR', 'light']):
		            patent['Title'] = p.text
		            patent['Link'] = p.find('a')['href']
		        
		        elif p['class'] in [['light','mB10']]:
		            for span in p.findAll('span',{'class':'fwB'}):
		            	header=span.text 
		            	header = header.replace(u'\uff1a','')           
		                patent[self.translation[header]]=[inventor.strip() for inventor in span.next_sibling.split(',')]
			Array.append(patent)
		return array



	def parse(self, response):
		print response.url
		driver = self.initDriver()
		driver.get(response.url)
		driver.set_window_size(1920, 1000)
		item = JglobalresearcherItem()

		mainDict = {}
		mainDict['JGLOBALID'] = self.returnJGlobalID(response.url)
		nameXpath = "//h1[contains(@id,'JD_NMRJ')]"
		papersMoreButtonXP = "//td[contains(@id,'JD_PA')]//img[contains(@src,'/common/images/btn_more.png')]"
		miscMoreButtonXP = "//td[contains(@id,'JD_AR')]//img[contains(@src,'/common/images/btn_more.png')]"
		booksMoreButtonXP = "//td[contains(@id,'JD_BKNAM')]//img[contains(@src,'/common/images/btn_more.png')]"


		WebDriverWait(driver,60).until(
				lambda x: len(x.find_element(By.ID,'JD_NMRJ').text)>0
			)

		dept_affil_div = driver.find_element(By.ID,'JD_CS_2')

		japanese_name_elem = driver.find_element(By.ID,'JD_NMRJ')
		doubleName_elem = driver.find_element(By.ID,'JD_NM')
		jobTitle_div = driver.find_element(By.ID,'JD_CS_3')
		other_affil = driver.find_element(By.ID,'JD_CS_4')
		field_of_study = driver.find_element(By.ID,'JD_RFD_J')
		other_source_links = driver.find_elements_by_xpath("//a[contains(@class,'mR10')]")
		research_keywords = driver.find_element(By.ID,'JD_RFKW_2')
		grantResearch = driver.find_element(By.ID,'JD_THM')
		miscElem = driver.find_element(By.ID,'JD_AR')
		papersElem = driver.find_element(By.ID,'JD_PA')
		booksElem = driver.find_element(By.ID,'JD_BKNAM')
		patentsElem = driver.find_element(By.ID,'JD_PT')		
		presentationsElem = driver.find_element(By.ID,'JD_PR')		
		workElem = driver.find_element(By.ID,'JD_OA')	
		educationElem = driver.find_element(By.ID,'JD_GS')	
		degreeElem = driver.find_element(By.ID,'JD_AC')	
		careerElem = driver.find_element(By.ID,'JD_RC')	
		committeeElem = driver.find_element(By.ID,'JD_BJH')	
		societiesElem = driver.find_element(By.ID,'JD_SO')	
		citedPapersElem = driver.find_element(By.ID,'JD_EA')
		citedPatentsElem = driver.find_element(By.ID,'JD_EP')

		mainDict['Name_Japanese'] = japanese_name_elem.get_attribute('textContent')

		names = doubleName_elem.get_attribute('textContent').split('|')
		mainDict['Name_Katakana'] = names[0]
		mainDict['Name_English'] = names[1]


		mainDict['Other_Source_Links'] = self.parseOtherSourceLinks(other_source_links)

		mainDict['Department_Affiliation'] = self.parseDepartmentAffil(dept_affil_div)
		otherAffilDict = self.parseDepartmentAffil(other_affil,other=True)
		if len(otherAffilDict)>0:
			mainDict['Department_Affiliation'] = (mainDict['Department_Affiliation'].items() +
													otherAffilDict.items())
		mainDict['JobTitle'] = jobTitle_div.text
		

		mainDict['Field_Of_Study'] = self.parseAffiliationTags(field_of_study)
		mainDict['ResearchKeywords'] = self.parseAffiliationTags(research_keywords)
		mainDict['ResearchGrants'] = self.parseCareerTimeline(grantResearch,'Grants')		
		mainDict['Papers'] = self.scrapePapers(papersElem)
		mainDict['Misc'] = self.scrapePapers(miscElem)
		mainDict['Books'] = self.parseBooksPresentations(booksElem)
		mainDict['Patents'] = self.parsePatents(patentsElem)
		mainDict['Presentations'] = self.parseBooksPresentations(presentationsElem)
		mainDict['Works'] = self.parseWorks(workElem)
		mainDict['ResearchGrants'] = self.parseCareerTimeline(educationElem,'Institution_Name')	
		mainDict['Degrees'] = self.parseDegree(degreeElem)
		mainDict['Career'] = self.parseCareerTimeline(careerElem,'Career_Title')	
		mainDict['Committees'] = self.parseCareerTimeline(committeeElem,'Committee_Title')	
		mainDict['Societies_Affiliaitons'] = self.parseAffiliationTags(societiesElem)
		mainDict['Cited_Papers'] = self.parseCitedPapersPatent(citedPapersElem)
		mainDict['Cited_Patents'] = self.parseCitedPapersPatent(citedPatentsElem)

		with codecs.open('export2.json','a+','utf-8') as f:

		    json.dump(mainDict, f,indent=4)

		driver.close()
		return item
