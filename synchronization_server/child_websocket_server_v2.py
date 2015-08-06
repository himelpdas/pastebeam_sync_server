from gevent import monkey; monkey.patch_all() #declare BEFORE all imports

from base_non_blocking_server import *

from gevent.event import AsyncResult
#from gevent.queue import Queue
from collections import deque

import uuid, time

from bottle import Bottle, static_file
app = Bottle()

UPLOAD_DIR="C:\\Users\\Himel\\Desktop\\test\\uploads"

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
			
def incommingGreenlet(wsock, timeout, OUTGOING_QUEUE): #these seem to run in another namespace, you must pass them global or inner variables

	#client_previous_clip = get_latest_row_and_clips()['latest_row'] or {} #SHOULD CHECK SERVER TO AVOID RACE CONDITIONS? #too much bandwidth if receiving row itself, only text and hash are fine (data)
	
	for second in xrange(timeout): #Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem

		received = wsock.receive()
		
		if not received:
			raise WebSocketError
			
		delivered = json.loads(received)
		
		question  = delivered['question']
		
		data = delivered['data']
		
		if question == "Alive?":
	
			OUTGOING_QUEUE.append(dict(
				answer = "Alive!",
				data = time.time()
			))
			
		if question == "Salt?":
		
			send_usr_crypt_salt.set(checked_login["found"]["salt"])
			
		if question == "Upload?":
				
			container_name =  data
			
			PRINT("container_name", container_name)
			
			file_path = os.path.join(UPLOAD_DIR,container_name)
			
			container_exists = os.path.isfile(file_path)
			
			OUTGOING_QUEUE.append(dict(
				answer = "Upload!",
				data = container_exists
			))
			
			PRINT("container_exists", container_exists)
	
		elif question == "Update?":
				
			data['timestamp_server'] = time.time()
			
			prev = (list(clips.find().sort('_id',pymongo.DESCENDING).limit( 1 ) ) or [{}]).pop() #cannot bool iterators, so must convert to list, and then pop the row
			
			if prev.get("hash") != data.get("hash"):
			
				new_clip_id = clips.insert_one(data).inserted_id
				
			else:
				
				new_clip_id = False #DO NOT SEND NONE as this NONE indicates bad connection to client (remember AsyncResult.wait() ) and will result in infinite loop
															
			OUTGOING_QUEUE.append(dict(
				answer = "Update!",
				data = new_clip_id
			))
			
			PRINT("update", new_clip_id)
			
			#prev = hash
			
		PRINT("incomming", "wait...")
		sleep(0.1)

	wsock.close() #OR IT WILL LEAVE THE GREENLET HANGING!
	
def outgoingGreenlet(wsock, timeout, OUTGOING_QUEUE):
	
	for second in xrange(timeout):
	
		sleep(1)
	
		try:
				
			send = OUTGOING_QUEUE.pop() #get all the queues first... raises index error when empty.
			
		except IndexError: #then monitor for external changes	
		
			try:	
				if server_latest_clips:
					server_latest_row = server_latest_clips[-1]
			
				if server_latest_row.get('_id') != server_previous_row.get('_id'): #change to Reload if signature of last 50 clips changed
					PRINT("sending new",server_latest_row.get('_id'))
					wsock.send(json.dumps(dict(
						answer = "Newest!", #when there is a new clip from an outside source, or deletion
						data = server_latest_clips,
					)))
					server_previous_row = server_latest_row #reset prev
					
				server_latest_clips = [each for each in clips.find({"_id":{"$gt":server_latest_row["_id"]}}).sort('_id',pymongo.ASCENDING).limit( 50 )]
			except UnboundLocalError:
				server_previous_row = {}
				server_latest_clips = [each for each in clips.find().sort('_id',pymongo.ASCENDING).limit( 50 )] #returns an iterator but we want a list
				
			
		else:
			wsock.send(json.dumps(send))
			
	wsock.close()

@app.route('/ws')
def handle_websocket():
	
	gevent.sleep(0.1) #prevent many connections
	
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
		
		args = [wsock, timeout, OUTGOING_QUEUE] #Only objects in the main thread are visible to greenlets, all other cases, pass the objects as arguments to greenlet.

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
	
	name, ext = os.path.splitext(upload.filename)
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