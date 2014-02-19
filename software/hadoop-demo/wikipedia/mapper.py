#!/usr/bin/env python

import bz2
import os
import sys
import xml.sax

class WikipediaTitleHandler(xml.sax.ContentHandler):
    def startElement(self, name, attrs):
        self.chars = []
        self.tag = name

    def characters(self, content):
        if self.tag == 'title':
            self.chars.append(content)

    def endElement(self, name):
        if self.tag == 'title':
            title = ''.join(self.chars)
            if title.startswith('Talk:'):
                return
            if title.startswith('User talk:'):
                return
            if title.startswith('Wikipedia:'):
                return
            if title.startswith('Wikipedia talk:'):
                return
            if title.startswith('User:'):
                return
            print title.encode('utf8')





def process_xml(input):
    
    parser = xml.sax.make_parser()
    parser.setContentHandler(WikipediaTitleHandler())
    parser.parse(input)


if __name__ == '__main__':
  input = bz2.BZ2File('/dev/fd/0')
  process_xml(input)

