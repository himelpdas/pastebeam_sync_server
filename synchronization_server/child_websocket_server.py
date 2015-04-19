from gevent import monkey; monkey.patch_all() #declare BEFORE all imports

from base_non_blocking_server import *

from gevent.event import AsyncResult

import uuid

from bottle import Bottle, static_file
app = Bottle()

UPLOAD_DIR="C:\\Users\\Himel\\Desktop\\test\\uploads"

@app.route('/test_async_websocket')
def test_async_websocket():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')

	while True:
		try:	
			message = wsock.receive()
			sleep(8)
			wsock.send(message)
		except WebSocketError:
			break
	
@app.route('/ws')
def handle_websocket():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')
		
	def _get_real_hash(clip):
		clip_hash_server  = clip_data_server = None
		if clip['clip_type'] == 'text':
			clip_data_server = clip['clip_text']
		elif clip['clip_type'] == 'bitmap':
			with open(UPLOAD_DIR +"\\"+ clip["clip_file_name"], 'rb') as clip_file:
				clip_data_server = clip_file.read() #WARNING!!! NEED TO USE 'rb' MODE OR WILL RESULT IN SAME HASH, PROBABLY BECAUSE CHARACTERS ARE IGNORED AS BLANK
				#print clip_hash_server

		if clip_data_server:
			hex(hash128(clip_data_server))

		return clip_hash_server

	def _initialize_client(client_previous_clip_data):
		wsock.send(json.dumps(client_previous_clip_data ) ) #Do this once to start outgoing greenlet by populating SERVER_LATEST_SIG variable
	
	class _live():
		uid = uuid.uuid4() #in a webSocket's lifetime, state is maintained
		def __init__(self, data):
			pass
			#print ("="*30+"\n%s:\n%s\n"+"="*30)%(self.uid,data)
				
	send_im_still_alive = AsyncResult()
	send_im_still_alive.set(0)
				
	def _incoming(wsock, timeout): #these seem to run in another namespace, you must pass them global or inner variables

		try:
			client_previous_clip = {'clip_hash_server':None} #too much bandwidth if receiving row itself, only text and hash are fine (data)
			#_initialize_client(client_previous_clip_data)
			for second in range(timeout): #Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem

				received = wsock.receive()
				
				if not received:
					raise WebSocketError
					
				data = json.loads(received)
				
				if data['message'] == "Alive?":
			
					send_im_still_alive.set(1)
			
				elif data['message'] == "Upload":
					
					client_latest_clip = data['data']
										
					client_latest_clip['clip_hash_server'] = _get_real_hash(client_latest_clip) #for security reasons, get rid of client's hash, perhaps block client if different hashes
				
					if client_latest_clip['clip_hash_server'] != client_previous_clip['clip_hash_server']: #else just wait
						
						new_clip_id = clips.insert(client_latest_clip) 
						
						print "INSERTED:%s "% new_clip_id

						client_previous_clip = client_latest_clip #reset prev
					
					else:
						print "hashes match, request rejected"
						print "OLD: \n%s - %s\nNEW:%s - %s"%(client_previous_clip['clip_hash_server'], client_previous_clip["clip_file_name"], client_latest_clip['clip_hash_server'], client_latest_clip['clip_file_name'])
				
				_live("incoming wait...")
				sleep(0.25)
		except ZeroDivisionError:
			#print "incoming error...%s"%str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
			pass
		finally:
			wsock.close() #OR IT WILL LEAVE THE CLIENT HANGING!

	def _outgoing(wsock, timeout):
		try:
			server_previous_clip_row = {'_id':None}
			for second in range(timeout):
				if send_im_still_alive.get():
					wsock.send(json.dumps(dict(
						message = "Alive!"
					))) #send blank list of clips to tell client's incoming server is still alive.
					send_im_still_alive.set(0)
				else:
					server_latest_clip_rowS = get_latest_clip_rows()
					if server_latest_clip_rowS.count():
						server_latest_clip_row  = server_latest_clip_rowS[0]
						#print server_latest_clip_row
						if server_latest_clip_row['_id'] != server_previous_clip_row['_id']:
							#_live("if server_latest_clip_row['_id'] != server_previous_clip_row['_id']")
							wsock.send(json.dumps(dict(
								message = "Download",
								data = server_latest_clip_rowS,
							)))
							#_live(server_latest_clip_row)
							
							server_previous_clip_row = server_latest_clip_row #reset prev
				
				#_live("outgoing wait...")
				sleep(0.25)
		except ZeroDivisionError:
			#print "outgoing error...%s"%str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
			pass
		finally:
			wsock.close()


	try:		
		timeout=40000
				
		args = [wsock, timeout] #Only objects in the main thread are visible to greenlets, all other cases, pass the objects as arguments to greenlet.
				
		greenlets = [
			gevent.spawn(_incoming, *args),
			gevent.spawn(_outgoing, *args),
		]
		gevent.joinall(greenlets)

	except WebSocketError:
		abort(500, 'Websocket failure.')
	finally:
		wsock.close()
		
@app.post('/upload')
def handle_upload():
	#print "HANDLE HANDLE HANDLE"
	result = "OK"
	save_path = UPLOAD_DIR

	upload     = request.files.get('upload')
	
	name, ext = os.path.splitext(upload.filename)
	if ext not in ('.png','.jpg','.jpeg'):
		result = 'File extension not allowed.'

	upload.save(save_path, overwrite=False) # appends upload.filename automatically

	response.content_type =  "application/json; charset=UTF8"
	return json.dumps({"upload_result":result})

@app.get('/static/<filename>')
def handle_download(filename):
	return static_file(filename, root=UPLOAD_DIR)

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