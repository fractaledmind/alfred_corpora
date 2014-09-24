#!/usr/bin/python
# encoding: utf-8
#
# Copyright © 2014 stephen.margheim@gmail.com
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on September 16, 2014
#
import os.path
import urllib
import json
import sys

# Deps
import html2text
from workflow import Workflow, web
from bs4 import BeautifulSoup, SoupStrainer

"""
def scrape_loeb_volumes():
    all_loebs = scrape_loeb_index()
    for loeb in all_loebs:
        loeb_toc = scrape_loeb_volume(loeb)
        #scrape_loeb_pages(loeb_toc)
        loeb['loeb_toc'] = loeb_toc

    # Save array of dicts to Desktop as JSON file
    file_path = os.path.expanduser('~/Desktop/loeb_tocs.json')
    return all_loebs
    
def scrape_loeb_pages():
    #for section in loeb.values()[0]:
        #volume_url = self.base_url + section['entry_url']
    

    # Get HTML text of Perseus page
    html_text = urllib.urlopen(volume_url).read()

    # Process HTML with BeautifulSoup, straining on the parsing data
    page_content = SoupStrainer('div', {"id" : "contentRoot"})
    soup = BeautifulSoup(html_text, parse_only=page_content)
    page_html = unicode(soup).encode('ascii', 'xmlcharrefreplace')
    #print soup.prettify().encode('utf-8')
    return
"""

def _strip(string):
    # If already string
    try:
        return string.strip()
    except:
        return string

def _string(tag):
    # If BeautifulSoup class
    try:
        return tag.string.strip()
    except AttributeError:
        return tag

def _get_html(url):
    #html_text = urllib.urlopen(volume_url).read()
    html_text = web.get(url)
    try:
        return html_text.text
    except AttributeError:
        return None

def _soupify_html(html, strainer=None):
    if strainer:
        soup = BeautifulSoup(html, parse_only=strainer)
    else:
        soup = BeautifulSoup(html)
    return soup


class LoebLibrary(object):

    def __init__(self, wf):
        self.wf = wf
        self.base_url = 'http://www.loebclassics.com'
        self.index = self.index()     

    def index(self):
        loeb_index = self.wf.stored_data('loeb_index')
        if loeb_index == None:
            loeb_index = self.loeb_index()
            self.wf.store_data('loeb_index', loeb_index, serializer='json')
        return loeb_index

    @property
    def loeb_index(self):
        # Loeb index URL
        index_url = self.base_url + '/volumes'
        index_html = _get_html(index_url)
        strainer = SoupStrainer('div',
            {"class" : "contentItem tei-volume standardResult chunkResult"})
        index_soup = _soupify_html(index_html, strainer)
        # Get list of all parsing items
        index_items = index_soup.find_all('h1')
        # Generate list of dicts with parsing item info
        index_info = []
        for item in index_items:
            dct = {}
            dct['loeb_url'] = self._loeb_url(item)
            dct['loeb_number'] = self._loeb_number(item)
            dct['loeb_author'] = self._loeb_author(item)
            dct['loeb_title'] = self._loeb_title(item)
            index_info.append(dct)
        return index_info

    ## ------------------------------------------------------------------------

    @staticmethod
    def _loeb_url(item):
        tag = item.a
        return _strip(tag.get('href'))

    @staticmethod
    def _loeb_number(item):
        tag = item.find('span', {'class': 'loebNumber'})
        string = _string(tag)
        if string and 'LCL' in string:
            string = string.replace('LCL ', '').replace(':', '')
        return _strip(string)

    @staticmethod
    def _loeb_author(item):
        tag = item.find('span', {'class': 'authorName'})
        string = _string(tag)
        return _strip(string)

    @staticmethod
    def _loeb_title(item):
        tag = item.find('span', {'class': 'volumeTitle'})
        string = _string(tag)
        return _strip(string)


class LoebVolume(object):

    def __init__(self, wf, title):
        self.wf = wf
        self.title = title
        self.library = LoebLibrary(self.wf).index
        self.base_url = 'http://www.loebclassics.com'
        self.volume = self.volume()

    def volume(self):
        loeb_volume = self.wf.stored_data(self.title)
        if loeb_volume == None:
            loeb_volume = self.loeb_volume()
            self.wf.store_data(self.title, loeb_volume, serializer='json')
        return loeb_volume    

    def loeb_volume(self):
        gen = (x['loeb_url'] for x in self.library
                if x['loeb_title'] == self.title)
        volume_url = self.base_url + next(gen, None)

        # Get HTML text of Perseus page
        volume_html = _get_html(volume_url)

        # Process HTML with BeautifulSoup
        volume_soup = _soupify_html(volume_html)

        vol_title = self._volume_title(volume_soup)
        vol_abstract = self._volume_abstract(volume_soup)

        vol_toc = volume_soup.find('div', {"class" : "toc tocContent"})
        # Get list of all parsing items
        toc_items = vol_toc.find_all('a')
        toc = {vol_title: []}
        for entry in toc_items:
            dct = {}
            dct['entry_url'] = self._entry_url(entry)
            dct['entry_title'] = self._entry_title(entry)
            dct['entry_page'] = self._entry_page(entry)
            toc[vol_title].append(dct)
        return toc

    @property
    def volume_first_page(self):
        first_dict = self.volume.values()[0][0]
        return first_dict['entry_url']

    def scrape_all_pages(self):
        first_page_url = self.volume_first_page['entry_url']
        next_page_url = self.scrape_volume_page(first_page_url)

    def scrape_volume(self, url=None):
        if url:
            section_url = self.base_url + url
        else:
            section_url = self.base_url + self.volume_first_page
        section_html = _get_html(section_url)
        if section_html:
            section_soup = _soupify_html(section_html)
            section_content = section_soup.find('div', {"id" : "contentRoot"})
            section_xml = unicode(section_content).encode('ascii', 'xmlcharrefreplace')
            with open(self.wf.datafile(self.title + '.xml'), 'a') as file:
                file.write(section_xml)
                file.write('\n\n') 

            # Find the URL to the next page
            next_page = self.get_next_page(section_soup)
            if next_page:
                print next_page
                self.scrape_volume(next_page)

    def get_next_page(self, soup):
        nav = soup.find('nav', {"class" : "pageNav"}).ul
        nav_choices = nav.find_all('li')
        for choice in nav_choices:
            if choice.get('class') == ['next']:
                return choice.a.get('href')
        




    ## ------------------------------------------------------------------------

    @staticmethod
    def _volume_title(soup):
        vol_title = _string(soup.title)
        vol_clean =  vol_title.replace(' | Loeb Classical Library', '')
        return _strip(vol_clean)

    @staticmethod
    def _volume_abstract(soup):
        abstract_tag = soup.find('div', {'id': 'lclAbstract'})
        abstract_html = unicode(abstract_tag.p).encode('ascii', 'xmlcharrefreplace')
        abstract_clean = abstract_html.replace('<p>', '').replace('</p>', '')
        return _strip(abstract_clean)

    @staticmethod
    def _entry_url(entry):
        return _strip(entry['href'])

    @staticmethod
    def _entry_title(entry):
        array = entry.contents
        if array != []:
            return _strip(array[0])
        else:
            return None

    @staticmethod
    def _entry_page(entry):
        return _string(entry.span)

    
def main(wf):
    #data = LoebLibrary(wf).index
    print LoebVolume(wf, 'Brutus. Orator').scrape_volume('/view/marcus_tullius_cicero-brutus/1939/pb_LCL342.1.xml')

    """Clean up for HTML:
    + <header>.*?</header>
    + <span class="pageNumber">.*?</span>

    prince '/Users/smargheim/Library/Application Support/Alfred 2/Workflow Data/com.hackademic.loebs/Theaetetus. Sophist.xml' -s '/Users/smargheim/Library/Application Support/Alfred 2/Workflow Data/com.hackademic.loebs/normalize.css' -s '/Users/smargheim/Library/Application Support/Alfred 2/Workflow Data/com.hackademic.loebs/override.css' -s '/Users/smargheim/Library/Application Support/Alfred 2/Workflow Data/com.hackademic.loebs/print.css' -o '/Users/smargheim/Library/Application Support/Alfred 2/Workflow Data/com.hackademic.loebs/theaetetus.pdf'
    """

if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))  
