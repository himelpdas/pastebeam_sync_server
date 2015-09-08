# -*- coding: utf8 -*-

import gevent

from bottle import route, abort, request, response, debug

from time import sleep
import pymongo
#import mmh3
from spooky import hash128
#import hashlib

import bson.json_util as json #can't use regular json module or else type error will occur for unknown types like ObjectID(...), use pymongo's bson module http://api.mongodb.org/python/current/api/bson/json_util.html
import sys, os, time, uuid

import validators

from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import HMAC,SHA512
import Crypto.Random

debug(True)

client=pymongo.MongoClient()
collection = client.test_database #collection
clips = collection.clips #database
contacts = collection.contacts
#accounts = collection.accounts #old way before web2py
accounts = collection.auth_user



"""
>>> users = collection.users
>>> users.insert(name=Himel, client_minimum_id = None)
"""

#import pymongo; client=pymongo.MongoClient();collection = client.test_database;clips = collection.clips; clips.remove()

def get_latest_row_and_clips(): 
	"""
	if minimum_id:
		query = { '_id': { '$gt': minimum_id } }
	else: 
		query = None
	"""
	latest_clips = clips.find().sort('_id',pymongo.DESCENDING).limit( 50 ) #latest one on mongo #note find() returns a cursor object so nothing is really in memory yet, and sort is a not the in-memory built in sort that python uses
	
	latest_row = None
	if latest_clips.count():
		latest_row  = latest_clips[0]
		
	latest_row_and_clips = dict(latest_row=latest_row, latest_clips=latest_clips)
		
	return latest_row_and_clips

"""
def login(email, password):
	print email
	found = accounts.find_one({"email":email})
	if not found:
		return dict(success=False, reason = "Account not found")
	key_derivation = PBKDF2(password, found["salt"]).encode("base64")
	if found["key_derivation"] != key_derivation:
		return dict(success=False, reason = "Incorrect password", found = found)
	else:
		return dict(success=True, reason= "Passwords matched", found = found)
"""	

def login(email, my_password):
	print email
	found = accounts.find_one({"email":email})
	if not found:
		return dict(success=False, reason = "Account not found")
	web2py_key = found["password"]
	if passwordMatchedWeb2pyKeyDerivation(my_password, web2py_key):
		return dict(success=False, reason = "Incorrect password", found = found)
	else:
		return dict(success=True, reason= "Passwords matched", found = found)
		
		
def passwordMatchedWeb2pyKeyDerivation(my_password, web2py_key):
	#generates a key that matches the key generated by web2py's CRYPT validator when user first signed up, under the condition that the password is the same
	method, salt, key = web2py_key.split("$") #web2py uses HMAC+SHA512 by default: u'pbkdf2(1000,20,sha512)$9b0873030107a7a9$81f5d44ca6e25da7eac8b78081380493ccde6a2d'
	my_key = PBKDF2(my_password, salt, dkLen=20, count=1000, prf=lambda p, s: HMAC.new(p, s, SHA512).digest()).encode("hex") #http://codereview.stackexchange.com/questions/10746/canonical-python-symmetric-cryptography-example
	return my_key == web2py_key

response.content_type = 'application/json' #for http

@route('/test_async_long_polling')
def test_async_long_polling():
	#use boom or ab -c 20 -n 20 http://<host>:<port>
	#if you get average response time of 8 seconds,
	#that means the server is running asynchronously
	sleep(8)
	yield json.dumps(dict(test='ok'))