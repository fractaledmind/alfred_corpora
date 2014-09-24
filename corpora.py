#!/usr/bin/python
# encoding: utf-8
#
# Copyright © 2014 stephen.margheim@gmail.com
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on September 23, 2014
#
from HTMLParser import HTMLParser
from collections import OrderedDict
import os.path
import urllib
import json
import sys
import re

# Deps
import html2text
from workflow import Workflow, web
from bs4 import BeautifulSoup, SoupStrainer, NavigableString

CORPORA = {
    'loeb': 'http://www.loebclassics.com',
    'perseus': 'http://www.perseus.tufts.edu/hopper',
    'phi': 'http://latin.packhum.org'
}

class Corpus(object):

    def __init__(self, wf, corpus):
        self.wf = wf
        self.corpus = corpus
        self.index = self.index_json()

    @property
    def index_url(self):
        """Generate proper URL to index page for specified `corpus`

        """
        base_url = CORPORA.get(self.corpus)
        if self.corpus == 'phi':
            index_url = base_url + '/canon'
        elif self.corpus == 'perseus':
            temp_url = base_url + '/collection'
            index_url = temp_url + '?collection=Perseus:collection:Greco-Roman'
        elif self.corpus == 'loeb':
            index_url = base_url + '/volumes'
        return index_url

    def index_html(self):
        """Return HTML of index page for specified `corpus`. 

        """
        cache_file = self.wf.datafile(self.corpus + '_index.html')
        if not os.path.exists(cache_file):
            html_text = web.get(self.index_url).text
            encoded_html = html_text.encode('ascii', 'xmlcharrefreplace')
            with open(cache_file, 'w') as file:
                file.write(encoded_html)
            return html_text
        else:
            parser = HTMLParser()
            with open(cache_file, 'r') as file:
                encoded_html = file.read()
            return parser.unescape(encoded_html)

    def index_json(self):
        """Return JSON array of dictionary for `corpus` index.

        """
        index_file = self.corpus + '_index'
        index_json = self.wf.stored_data(index_file)
        if index_json == None:
            index_html = self.index_html()
            if self.corpus == 'phi':
                index_json = self.phi_index_json(index_html)
            elif self.corpus == 'perseus':
                index_json = self.perseus_index_json(index_html)
            elif self.corpus == 'loeb':
                index_json = self.loeb_index_json(index_html)
            self.wf.store_data(index_file, index_json, serializer='json')
        return index_json

    def phi_index_json(self, index_html):
        strainer = SoupStrainer('div', {"class" : "canon"})
        soup = BeautifulSoup(index_html, parse_only=strainer)
        items = soup.find_all('li', {'class': 'auth'})
        info = OrderedDict()
        for item in items:
            author = self._string(item.a.find('span', {'class': 'anam'}))
            d = info[author] = dict()

            d['phi_author_url'] = self._strip(item.a.get('href'))
            d['phi_author_name'] = self._string(item.a.find('span', {'class': 'anam'}))
            d['phi_author_num'] = self._string(item.a.find('span', {'class': 'anum'}))
            d['phi_author_abrv'] = self._string(item.a.find('span', {'class': 'abrv'}))
            d['phi_author_works'] = list()
            works = item.ul.find_all('li', {'class': 'work'})
            for work in works:
                wd = dict()
                wd['phi_work_url'] = self._strip(work.a.get('href'))
                wd['phi_work_name'] = self._string(work.a.find('span', {'class': 'wnam'}))
                wd['phi_work_bib'] = self._string(work.a.find('span', {'class': 'bib'}))
                wd['phi_work_num'] = self._string(work.a.find('span', {'class': 'wnum'}))
                wd['phi_work_abrv'] = self._string(work.a.find('span', {'class': 'wabv'}))
                d['phi_author_works'].append(wd)
            info.update(d)
        return info

    def loeb_index_json(self, index_html):
        strainer = SoupStrainer('div',
            {"class" : "contentItem tei-volume standardResult chunkResult"})
        soup = BeautifulSoup(index_html, parse_only=strainer)
        items = soup.find_all('h1')
        info = OrderedDict()
        for item in items:
            author = self._string(item.find('span', {'class': 'authorName'}))
            try:
                data = info[author]
            except KeyError:
                data = info[author] = list()
            d = dict()
            d['loeb_url'] = self._strip(item.a.get('href'))
            loeb_number = item.find('span', {'class': 'loebNumber'})
            loeb_number = self._string(loeb_number).replace('LCL ', '')\
                                                   .replace(':', '')
            d['loeb_number'] = self._strip(loeb_number)
            loeb_author = item.find('span', {'class': 'authorName'})
            d['loeb_author'] = self._string(loeb_author)
            loeb_title = item.find('span', {'class': 'volumeTitle'})
            d['loeb_title'] = self._string(loeb_title)
            data.append(d)
        return info

    def perseus_index_json(self, index_html):
        """
        {author : [
            {wtitle,
             wurl,
             weditor,
             wlang,
             wabrv,
             wsubs: [
                stitle,
                surl,
                sabrv
             ]}
        ]}
        """
        strainer = SoupStrainer('table', {'class' : 'tResults'})
        soup = BeautifulSoup(index_html, parse_only=strainer)
        items = soup.find_all('tr', {'class' : 'trResults'})
        
        info = OrderedDict()
        for item in items:
            author = item.get('id').split(',')[0]
            author_tag = item.find('td', {'class': 'tdAuthor'})
            d = list()
            # Only 1 work
            if author_tag.text.startswith('\n\t\t\t\t'):
                # Extract document information
                wd = self._perseus_doc_dict(author_tag)
                # Try to get URL to document
                doc_url = self._perseus_cleanup_link(author_tag.a.get('href'))
                if doc_url:
                    wd['perseus_work_url'] = doc_url
                wd['perseus_work_subs'] = self._perseus_subdocs(author_tag)
                d.append(wd)
            
            # More than 1 work
            elif author_tag.text.startswith('\n\t\t\t'):
                data = item.get('id').split(',')
                works = soup.find_all('tr', {'class': 'trHiddenResults',
                                      'id': re.compile(data[0])})
                for work in works:
                    wd = self._perseus_work_dict(work)
                    # Try to get URL to document
                    doc_url = self._perseus_cleanup_link(work.a.get('href'))
                    if doc_url:
                        wd['perseus_url'] = doc_url                    
                    wd['perseus_sub_docs'] = self._perseus_subdocs(work)
                    d.append(wd)
            info[author] = d
        return info


    @staticmethod
    def _perseus_cleanup_link(link):
        clean = re.sub(r";jsessionid=.*?\?", "?", link)
        if clean.startswith('text'):
            return clean

    @staticmethod
    def _perseus_cleanup_info(info):
        idx = info.find('search this work')
        doc = info[:idx]
        return [x.strip() for x in doc.split('\n') if x.strip()]

    def _perseus_doc_dict(self, doc):
        d = dict()
        array = self._perseus_cleanup_info(doc.text)
        d['perseus_work_author'] = array[0]
        d['perseus_work_title'] = array[1]
        for part in array[2:]:
            if part in ('(Greek)', '(Latin)', '(English)'):
                d['perseus_work_lang'] = part
            elif re.match(r'\[.*?\]', part):
                d['perseus_work_abrv'] = part
            else:
                d['perseus_work_editor'] = part
        return d

    def _perseus_work_dict(self, work):
        d = dict()
        array = self._perseus_cleanup_info(work.text)
        d['perseus_work_title'] = array[0]
        for part in array[1:]:
            if part in ('(Greek)', '(Latin)', '(English)'):
                d['perseus_work_lang'] = part
            elif re.match(r'\[.*?\]', part):
                d['perseus_work_abrv'] = part
            else:
                d['perseus_work_editor'] = part
        return d

    def _perseus_subdocs(self, tag):
        array = list()
        subs = tag.find('ul', {'class': 'subdoc'})
        if subs:
            for item in subs.find_all('li'):
                link = self._perseus_cleanup_link(item.a.get('href'))
                if link:
                    d = self._perseus_work_dict(item)
                    d['perseus_work_url'] = link
                    array.append(d)
        return array


    ## ------------------------------------------------------------------------

    @staticmethod
    def _strip(string):
        try:
            return string.strip()
        except:
            return string

    def _string(self, tag):
        # If BeautifulSoup class
        try:
            return self._strip(tag.text)
        except AttributeError:
            return tag



def main(wf):
    loeb_authors = Corpus(wf, 'loeb').index.keys()
    phi_authors = Corpus(wf, 'phi').index.keys()
    perseus_authors = Corpus(wf, 'perseus').index.keys()

    all_authors = [loeb_authors, phi_authors, perseus_authors]
    print len(loeb_authors), len(phi_authors), len(perseus_authors)
    print set(all_authors[0]).intersection(*all_authors)


if __name__ == '__main__':
    wf = Workflow()
    sys.exit(wf.run(main))  
