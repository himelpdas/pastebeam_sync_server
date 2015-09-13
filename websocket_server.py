from gevent import monkey; monkey.patch_all() #declare BEFORE all imports

from functions import *

from gevent.event import AsyncResult
#from gevent.queue import Queue
from collections import deque

import uuid, time

from bottle import Bottle, static_file
app = Bottle()

if os.name=="nt":
	UPLOAD_DIR="C:\\Users\\Himel\\Desktop\\test\\uploads"
else:
	UPLOAD_DIR="/home/das/Projects/junk"
	
def PRINT(label, data):
	print "\n%s: %s"%(label.capitalize(), data)

@app.route('/echo')
def test_async_websocket():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')

	while True:
		try:	
			message = wsock.receive()
			#sleep(8)
			wsock.send(message)
		except WebSocketError:
			break
			
def incommingGreenlet(wsock, timeout, USER_ID, OUTGOING_QUEUE): #these seem to run in another namespace, you must pass them global or inner variables

	#client_previous_clip = get_latest_row_and_clips()['latest_row'] or {} #SHOULD CHECK SERVER TO AVOID RACE CONDITIONS? #too much bandwidth if receiving row itself, only text and hash are fine (data)
	
	for second in xrange(timeout): #Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem

		received = wsock.receive()
		
		if not received:
			raise WebSocketError
			
		delivered = json.loads(received)
		
		question  = delivered['question']
		
		data = delivered['data']
		
		print delivered
		
		response = {"echo":delivered["echo"]}

		if question == "Contacts?":
			#IN PROGRESS
			emails_in = sorted(data["list"])
			data_out = None
			reason = None
			success = False
			
			print emails_in
			
			try:
				for each_email in emails_in:
					assert validators.email(each_email) #this is a setter, so make sure it passes validation
				else: #empty list, then this is a getter
					found = contacts.find_one({"owner_id":USER_ID})
					if found:
						data_out = sorted(found["list"])
						success = True
			except AssertionError:
				reason = "An email failed validation."
			else:
				if not data_out:
					data_out=emails_in
					result = contacts.update_one({"owner_id":USER_ID}, {"$set":{"owner_id":USER_ID, "list" : emails_in}}, upsert=True) #upsert True will update (with arg2 )if filter (arg1) not found
					success = True
			
			response.update(dict(
				answer="Contacts!",
				data = {
					"success":success,
					"data":data_out,
					"reason":reason
				}
			))
		
		if question == "Star?":
						
			#success = bool(clips.find_one_and_update({"_id":data["_id"]},{"bookmarked":True}) )
			
			exists = bool(clips.find_one({
				"hash":data["hash"],"starred":True, #it may be multiple hashes exists across different users
				"owner_id":USER_ID, #so enforce with user_id
			})) #find_one returns None if none found
			if not exists:
				#create star
				data["owner_id"]=USER_ID
				data["starred"]=True
				data['timestamp_server'] = time.time()
				reason = clips.insert_one(data).inserted_id
				success = True

				#find old crap
				tmp_free_user_limit = 5
				old = clips.find({
					"starred":True,
					"owner_id":USER_ID,
				}).sort('_id',pymongo.DESCENDING)[tmp_free_user_limit:]
				
				#delete old crap
				clips.delete_many({"_id":{'$in': map(lambda each: each["_id"], old) }  }   )
				
			else:
				reason = "already starred"
				success = False

			response.update(dict(
				answer="Star!",
				data = {
					"reason" : reason,
					"success" : success
				}
					
			))
							
		if question == "Delete?":
			
			remove_id = data["remove_id"]
			remove_row = data["remove_row"]
			list_widget_name = data["list_widget_name"]
					
			location = list_widget_name, remove_row

			result  = clips.delete_one({
				"_id":remove_id,
				"owner_id":USER_ID, #Mongo ids are not secure alone, make sure the clip belongs to this user before deleting. USER_ID is not spoofable since it cannot not come from the attacker. http://stackoverflow.com/questions/11577450/are-mongodb-ids-guessable
			}).deleted_count
			
			print "ROW ID: %s, DELETED: %s"%(remove_id,result)
			
			response.update(dict(
				answer="Delete!",
				data = {
					"success":bool(result),
					"location":location
				}
			))
						
		if question == "Upload?":
				
			container_name =  data
			
			PRINT("container_name", container_name)
			
			file_path = os.path.join(UPLOAD_DIR,container_name)
			
			container_exists = os.path.isfile(file_path)
			
			response.update(dict(
				answer = "Upload!",
				data = container_exists
			))
			
			PRINT("container_exists", container_exists)
	
		if question == "Update?":
				
			data["owner_id"]=USER_ID
			data['timestamp_server'] = time.time()
			
			prev = (list(clips.find({
				"starred":{"$ne":True},
				"owner_id":USER_ID,
			}).sort('_id',pymongo.DESCENDING).limit( 1 ) ) or [{}]).pop() #do not consider starred clips or friends #cannot bool iterators, so must convert to list, and then pop the row
			
			if prev.get("hash") != data.get("hash"):
			
				new_clip_id = clips.insert_one(data).inserted_id
				
				#find old crap
				tmp_free_user_limit = 5
				old = clips.find({
					"starred":{"$ne":True},
					"owner_id":USER_ID,
				}).sort('_id',pymongo.DESCENDING)[tmp_free_user_limit:]

				#delete old crap
				clips.delete_many({"_id":{'$in': map(lambda each: each["_id"], old) }  }   )
				
			else:
				
				new_clip_id = False #DO NOT SEND NONE as this NONE indicates bad connection to client (remember AsyncResult.wait() ) and will result in infinite loop

			response.update(dict(
				answer = "Update!",
				data = new_clip_id
			))
			
			PRINT("update", new_clip_id)
			
			#prev = hash
		
		OUTGOING_QUEUE.append(response)
			
		PRINT("incomming", "wait...")
		sleep(0.1)

	wsock.close() #OR IT WILL LEAVE THE GREENLET HANGING!
	
def outgoingGreenlet(wsock, timeout, USER_ID, OUTGOING_QUEUE):
	
	for second in xrange(timeout):
	
		sleep(0.1)
	
		try:
				
			send = OUTGOING_QUEUE.pop() #get all the queues first... raises index error when empty.
			
		except IndexError: #then monitor for external changes	
		
			try:	
				if server_latest_clips:
					server_latest_row = server_latest_clips[0]
			
				if server_latest_row.get('_id') != server_previous_row.get('_id'): #change to Reload if signature of last 50 clips changed
					PRINT("sending new",server_latest_row.get('_id'))
					wsock.send(json.dumps(dict(
						answer = "Newest!", #when there is a new clip from an outside source, or deletion
						data = server_latest_clips, 
					)))
					server_previous_row = server_latest_row #reset prev
					
				server_latest_clips = [each for each in clips.find({
					"_id":{"$gt":server_latest_row["_id"]},
					"owner_id":USER_ID,
				}).sort('_id',pymongo.DESCENDING).limit( 5 )] #DO NOT USE ASCENDING, USE DESCENDING AND THEN REVERSED THE LIST INSTEAD!... AS AFTER 50, THE LATEST CLIP ON DB WILL ALWAYS BE HIGHER THAN THE LATEST CLIP OF THE INITIAL 50 CLIPS SENT TO CLIENT. THIS WILL RESULT IN THE SENDING OF NEW CLIPS IN BATCHES OF 50 UNTIL THE LATEST CLIP MATCHES THAT ON DB.
			
			except UnboundLocalError:
				server_previous_row = {}
				server_latest_clips = [each for each in clips.find({"owner_id":USER_ID,}).sort('_id',pymongo.DESCENDING)]#.limit( 5 )] #returns an iterator but we want a list	
			
		else:
			print send
			wsock.send(json.dumps(send))
			
	wsock.close()

@app.route('/ws')
def handle_websocket():
	
	gevent.sleep(1) #prevent many connections
	
	websocket_id = uuid.uuid4()

	try:		
	
		wsock = request.environ.get('wsgi.websocket')
				
		if not wsock:
			abort(400, 'Expected WebSocket request.')

		
		###Uncomment to enable Login
		checked_login = login(request.query.email, request.query.password)

		if not checked_login['success']:
			
			wsock.send(json.dumps(dict(
				answer = "Error!",
				data = checked_login["reason"],
			)))
			
			return
		else:
			wsock.send(json.dumps(dict(
				answer = "Connected!",
				data = checked_login["reason"],
			)))
			
		

		timeout=40000
				
		OUTGOING_QUEUE = deque()
		
		USER_ID = checked_login["found"]["_id"]
		
		args = [wsock, timeout, USER_ID, OUTGOING_QUEUE] #Only objects in the main thread are visible to greenlets, all other cases, pass the objects as arguments to greenlet.

		#send_update_command.set(None)
				
		greenlets = [
			gevent.spawn(incommingGreenlet, *args),
			gevent.spawn(outgoingGreenlet, *args),
		]
		gevent.joinall(greenlets)

	except WebSocketError:
		abort(500, 'Websocket failure.')
	finally:
		wsock.close()
		
@app.get('/file_exists/<filename>')
def file_exists(filename):
	response.content_type =  "application/json; charset=UTF8"

	file_path = os.path.join(UPLOAD_DIR,filename)
	file_exists = os.path.isfile(file_path)
	
	PRINT("file exists", file_exists)
	
	return json.dumps({"result":file_exists})
		
@app.post('/upload')
def handle_upload():
	#print "HANDLE HANDLE HANDLE"
	result = "OK"
	save_path = UPLOAD_DIR

	upload    = request.files.get('upload')
	
	#name, ext = os.path.splitext(upload.filename)
	"""
	if ext not in (".txt",'.bmp','.png','.jpg','.jpeg', '.py'):
		result = 'File extension not allowed.'
	else:
		upload.save(save_path, overwrite=False) # appends upload.filename automatically
	"""
	try:
		upload.save(save_path, overwrite=False) # appends upload.filename automatically
	except IOError:
		pass
		
	response.content_type =  "application/json; charset=UTF8"
	return json.dumps({"upload_result":result})

@app.get('/static/<filename>')
def handle_download(filename):
	return static_file(filename, root=UPLOAD_DIR)
	
"""
@app.get('/auth/<email>/<password>')
def register(email,password):
	response.content_type =  "application/json; charset=UTF8"

	found = accounts.find_one({'email': email})

	if not validators.email(email):
		return json.dumps({"success": False, "reason":"Invalid email!"})
	if found:
		return json.dumps({"success": False, "reason":"Email already exists!"})
	if len(password) < 8:
		return json.dumps({"success": False, "reason":"Password too short!"})

	random_bytes = Crypto.Random.get_random_bytes(16).encode("base64")
	key_derivation = PBKDF2(password, random_bytes).encode("base64")
	new_account_id = accounts.insert_one({"email":email, "key_derivation":key_derivation, "salt":random_bytes})
	return {"success":True, "Reason":"Account %s successfully created!"%new_account_id}
"""
if __name__ == "__main__":
	#geventwebsocket implementation
	from gevent.pywsgi import WSGIServer
	from geventwebsocket import WebSocketError
	from geventwebsocket.handler import WebSocketHandler
	server = WSGIServer(("0.0.0.0", 8084), app,
						handler_class=WebSocketHandler)
	server.serve_forever()

"""
##ws4py implementation (doesn't work)
#from gevent import monkey; monkey.patch_all()
from ws4py.server.geventserver import WSGIServer
from ws4py.server.geventserver import WebSocketWSGIHandler
from ws4py.exc import WebSocketException

server = WSGIServer(("0.0.0.0", 8084), app,
					handler_class=WebSocketHandler )
server.serve_forever()
"""
