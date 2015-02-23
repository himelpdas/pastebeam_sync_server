from base_non_blocking_server import *

from gevent.event import AsyncResult

import uuid

from bottle import Bottle
app = Bottle()

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
		
	def _prepare_data(content):
		return dict(
			content = content, 
			sig = hex( mmh3.hash( content ) ) ,
		) 

	def _initialize_client(client_previous_clip_data):
		wsock.send(json.dumps(client_previous_clip_data ) ) #Do this once to start outgoing greenlet by populating SERVER_LATEST_SIG variable
	
	class _live():
		uid = uuid.uuid4() #in a webSocket's lifetime, state is maintained
		def __init__(self, data):
			print ("="*30+"\n%s:\n%s\n"+"="*30)%(self.uid,data)
				
	send_im_still_alive = AsyncResult()
	send_im_still_alive.set(0)
				
	def _incoming(wsock, timeout): #these seem to run in another namespace, you must pass them global or inner variables

		try:
			client_previous_clip_data = {'sig':None} #too much bandwidth if receiving row itself, only text and hash are fine (data)
			#_initialize_client(client_previous_clip_data)
			for second in range(timeout): #Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem

				received = wsock.receive()
				
				if not received:
					raise WebSocketError
					
				data = json.loads(received)
				
				if data['message'] == "Alive?":
			
					send_im_still_alive.set(1)
			
				elif data['message'] == "Upload":
				
					client_latest_clip_data = _prepare_data(data['data'] )

					if client_latest_clip_data['sig'] != client_previous_clip_data['sig']: #else just wait
						
						new_clip_sig = client_latest_clip_data['sig']
						new_clip_id = clips.insert(dict(content=client_latest_clip_data['content'] , sig = new_clip_sig ) ) 

						client_previous_clip_data = client_latest_clip_data #reset prev
				
				_live("incoming wait...")
				sleep(0.25)
		except:
			print "incoming error...%s"%str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
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
		except:
			print "outgoing error...%s"%str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
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