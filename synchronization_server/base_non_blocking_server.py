# -*- coding: utf8 -*-

import gevent

from bottle import route, abort, request, response, debug

from time import sleep
import pymongo
#import mmh3
from spooky import hash128
#import hashlib

import bson.json_util as json #can't use regular json module or else type error will occur for unknown types like ObjectID(...), use pymongo's bson module http://api.mongodb.org/python/current/api/bson/json_util.html
import sys, os, time

import validators

from Crypto.Protocol.KDF import PBKDF2
import Crypto.Random

debug(True)

client=pymongo.MongoClient()
collection = client.test_database #collection
clips = collection.clips #database
accounts = collection.accounts

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
	
def login(email, password):
	found = accounts.find_one({"email":email})
	if not found:
		return dict(success=False, reason = "Account not found!")
	key_derivation = PBKDF2(password, found["salt"]).encode("base64")
	if found["key_derivation"] != key_derivation:
		return dict(success=False, reason = "Incorrect password!")
	else:
		return dict(success=True, reason= "Passwords matched!")
		

response.content_type = 'application/json'

#print globals()

@route('/test_async_long_polling')
def test_async_long_polling():
	#use boom or ab -c 20 -n 20 http://<host>:<port>
	#if you get average response time of 8 seconds,
	#that means the server is running asynchronously
	sleep(8)
	yield json.dumps(dict(test='ok'))
