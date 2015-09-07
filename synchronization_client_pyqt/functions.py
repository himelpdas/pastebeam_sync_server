#--coding: utf-8 --

import urlparse
import os

import bson.json_util as json 
from bson.binary import Binary

import hashlib, uuid, time, sys, cgi, tempfile

import validators

from spooky import hash128

from collections import deque


def string_is_url(url):
	split_url = url.split()
	if len(url) < 2048 and len(split_url) == 1: #make sure text is under 2048 (for performance), and make sure the text is continuous like a url should be
		if bool(urlparse.urlparse(split_url[0]).scheme in ['http', 'https', 'ftp', 'ftps', 'bitcoin', 'magnet'] ): #http://stackoverflow.com/questions/25259134/how-can-i-check-whether-a-url-is-valid-using-urlparse
			return True
	return False

def getFolderSize(folder, max=None): #http://stackoverflow.com/questions/1392413/calculating-a-directory-size-using-python
	#recursively check folder size
	total_size = os.path.getsize(folder)
	for item in os.listdir(folder):
		itempath = os.path.join(folder, item)
		if os.path.isfile(itempath):
			total_size += os.path.getsize(itempath)
		elif os.path.isdir(itempath):
			total_size += getFolderSize(itempath)
		if max and total_size >= max:
			return float("inf") #1024*1024*1024*1024 #http://stackoverflow.com/questions/7781260/how-can-i-represent-an-infinite-number-in-python
	return total_size
	
	
#See: http://daringfireball.net/2010/07/improved_regex_for_matching_urls
import re, urllib
 
GRUBER_URLINTEXT_PAT = re.compile(ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')

def PRINT(label, data):
	print "\n%s: %s"%(label.capitalize(), data)
	
def URL(scheme, addr, port, *_args, **_vars): 
	url = "{scheme}://{addr}:{port}/".format(scheme=scheme, addr=addr, port=port)
	if _args:
		args = "/".join(_args)
		url+=args
	if _vars:
		url+="?"
		for key, value in _vars.items():
			url+="{key}={value}&".format(key=key, value=value)
		url=url[:-1]
	return url