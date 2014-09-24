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

class PHI_Latin_Library(object):

    def __init__(self, wf):
        self.wf = wf
        self.url = 'http://latin.packhum.org'
        self.index = self.index()

    def index(self):
        phi_index = self.wf.stored_data('phi_index')
        if phi_index == None:
            phi_index = self.phi_index()
            self.wf.store_data('phi_index', phi_index, serializer='json')
        return phi_index

    def phi_index(self):
        # Loeb index URL
        #index_html = _get_html(self.url + '/canon')
        index_html = self.wf.workflowfile('phi_canon.html')
        with open(index_html, 'r') as file:
            index_html = file.read()

        strainer = SoupStrainer('div', {"class" : "canon"})
        index_soup = _soupify_html(index_html, strainer)
        # Get list of all parsing items
        index_items = index_soup.find_all('li', {'class': 'auth'})
        # Generate list of dicts with parsing item info
        index_info = []
        for item in index_items[1:3]:
            print item.a.get('href')
            print item.a.find('span', {'class': 'anam'}).text
            print item.a.find('span', {'class': 'anum'}).text
            print item.a.find('span', {'class': 'abrv'}).text
            print '- - -'
            works = item.ul.find_all('li', {'class': 'work'})
            for work in works:
                print work.a.get('href')
                print work.a.find('span', {'class': 'wnam'}).text
                print work.a.find('span', {'class': 'bib'})
                print work.a.find('span', {'class': 'anum'}).text
                print work.a.find('span', {'class': 'wnum'}).text
                print work.a.find('span', {'class': 'wabv'}).text

            #dct = {}
            #dct['id'] = item.get('id')
            #dct['url'] = item.a.get('href')
            #dct['name'] = item.a.span.text
            #index_info.append(dct)
        return index_info



def main(wf):
    PHI_Latin_Library(wf).phi_index()
    #p = PerseusDoc(wf)
    #p.crawl('text?doc=Perseus%3atext%3a1999.02.0089')


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))  
