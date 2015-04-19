# -*- coding: utf8 -*-

import gevent

from bottle import route, abort, request, response, debug

from time import sleep
import pymongo
#import mmh3
from spooky import hash128
#import hashlib

import bson.json_util as json #can't use regular json module or else type error will occur for unknown types like ObjectID(...), use pymongo's bson module http://api.mongodb.org/python/current/api/bson/json_util.html
import sys, os

debug(True)

client=pymongo.MongoClient()
collection = client.test_database9 #collection
clips = collection.clips5 #database

users = collection.users
"""
>>> users = collection.users
>>> users.insert(name=Himel, client_minimum_id = None)
"""


#import pymongo; client=pymongo.MongoClient();collection = client.test_database;clips = collection.clips

def get_latest_clip_rows(): 
	"""
	if minimum_id:
		query = { '_id': { '$gt': minimum_id } }
	else: 
		query = None
	"""
	latest_clips = clips.find().sort('_id',pymongo.DESCENDING).limit( 50 ) #latest one on mongo #note find() returns a cursor object so nothing is really in memory yet, and sort is a not the in-memory built in sort that python uses
	return latest_clips

response.content_type = 'application/json'

#print globals()

@route('/test_async_long_polling')
def test_async_long_polling():
	#use boom or ab -c 20 -n 20 http://<host>:<port>
	#if you get average response time of 8 seconds,
	#that means the server is running asynchronously
	sleep(8)
	yield json.dumps(dict(test='ok'))
