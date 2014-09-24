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
import re

# Deps
import html2text
from workflow import Workflow, web
from bs4 import BeautifulSoup, SoupStrainer, NavigableString

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

class PerseusLibrary(object):

    def __init__(self, wf):
        self.wf = wf
        self.url = 'http://www.perseus.tufts.edu/hopper/collection?collection=Perseus:collection:Greco-Roman'
        self.index = self.index()     

    def index(self):
        perseus_index = self.wf.stored_data('perseus_index')
        if perseus_index == None:
            perseus_index = self.perseus_index()
            #self.wf.store_data('perseus_index', perseus_index, serializer='json')
        return perseus_index

    @property
    def perseus_index(self):
        # Loeb index URL
        index_html = _get_html(self.url)
        strainer = SoupStrainer('table', {"class" : "tResults"})
        index_soup = _soupify_html(index_html, strainer)
        # Get list of all parsing items
        index_items = index_soup.find_all('tr', {"class" : "trResults"})
        print len(index_items)
        return
        # Generate list of dicts with parsing item info
        index_info = []
        for item in index_items:
            dct = {}
            
            index_info.append(dct)
        return index_info

class PerseusDoc(object):

    def __init__(self, wf):
        self.wf = wf
        self.to_visit = list()
        self.visited = set()
        self.base_url = 'http://www.perseus.tufts.edu/hopper/'

    def crawl(self, url):

        # Prepare full URL
        full_url = self.base_url + url
        # Get HTML content of URL
        html_text = _get_html(full_url)
        # Get BeautifulSoup parsing of HTML
        page_soup = _soupify_html(html_text)

        # Extract the page title
        page_title = page_soup.find('span', {'class': 'title'}).string
        # Get the main text content
        page_content = page_soup.find('div', {'class': re.compile('text_container')})
        # Remove any hyperlinks
        clean_content = self.strip_hyperlinks(page_content)
        content_html = unicode(clean_content).encode('ascii', 'xmlcharrefreplace')

        file_path = self.wf.datafile(page_title) + '.html'
        with open(file_path, 'a') as file:
            file.write(content_html)

        # Find the URL to the next page
        next_url = self.get_next_page(page_soup)
        if next_url:
            print next_url
            self.crawl(next_url)

    def get_next_page(self, soup):
        nav = soup.find('div', {'id': 'header_nav'})
        nav_choices = nav.find_all('a')
        for choice in nav_choices:
            if choice.img.get('alt') == 'next':
                return choice.get('href')

    def strip_hyperlinks(self, soup):
        for tag in soup.findAll('a'):
            s = ""
            for c in tag.contents:
                if not isinstance(c, NavigableString):
                    c = self.strip_hyperlinks(c)
                s += unicode(c)
            tag.replaceWith(s)
        return soup



# TODO: remove extra div stuff
    
def main(wf):
    PerseusLibrary(wf)
    #p = PerseusDoc(wf)
    #p.crawl('text?doc=Perseus%3atext%3a1999.02.0089')


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))  
