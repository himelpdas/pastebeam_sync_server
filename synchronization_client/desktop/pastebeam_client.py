# -*- coding: utf8 -*-
from gevent import monkey; monkey.patch_all() #no need to monkeypatch all, just sockets... Now we can bidirectionally communicate, unlike with blocking websocket client
from gevent.event import AsyncResult
import gevent

#socket stuff
from ws4py.client.geventclient import WebSocketClient
from ws4py import exc
from socket import error as SocketError
##from websocket import create_connection #old blocking library useless for bidirectional, might as well stick to long-polling then
#http stuff
import requests
from requests import ConnectionError

#ui stuff
import wx
from threading import *
from wxpython_view import *

#general stuff
import time, sys, zlib, datetime, uuid, os, tempfile, urllib

#debug
import pdb

#db stuff
import mmh3
from spooky import hash64
import bson.json_util as json

HTTP_BASE = lambda arg, port, scheme: "%s://192.168.0.190:%s/%s"%(scheme, port, arg)

TEMP_DIR = tempfile.mkdtemp(); print TEMP_DIR

# Button definitions
ID_START = wx.NewId()
ID_STOP = wx.NewId()

# Define notification event for thread completion
EVT_RESULT_ID = wx.NewId()

def BIND_EVT_RESULT(win, func):
	"""Define Result Event."""
	win.Connect(-1, -1, EVT_RESULT_ID, func)

class EVT_RESULT(wx.PyEvent):
	"""Simple event to carry arbitrary result data."""
	def __init__(self, data):
		"""Init Result Event."""
		wx.PyEvent.__init__(self)
		self.SetEventType(EVT_RESULT_ID)
		self.data = data

#interthread communication
#lock = Lock() #locks not needed in gevent, use AsyncResult
#with lock:
#...

SERVER_LATEST_CLIP, CLIENT_LATEST_CLIP = AsyncResult(), AsyncResult()
SERVER_LATEST_CLIP.set({'clip_hash_client':None}) #the latest clip's hash on server
CLIENT_LATEST_CLIP.set({'clip_hash_client':None}) #the latest clip's hash on client. Take no action if equal with above.
#HOST_CLIP_CONTENT.set(None) #the raw clip content from the client

class WorkerThread(Thread):
	"""Worker Thread Class."""

	KEEP_RUNNING = True
	USE_WEBSOCKET = True
	
	def __init__(self, notify_window):
		"""Init Worker Thread Class."""
		Thread.__init__(self)
		self._notify_window = notify_window
		#self.KEEP_RUNNING = True
		# This starts the thread running on creation, but you could
		# also make the GUI thread responsible for calling this
		self.start()

	@classmethod #similar to static, but passes the class as the first argument... useful for modifying static variables
	def abort(cls):
		"""abort worker thread."""
		# Method for use by main thread to signal an abort
		cls.KEEP_RUNNING = False
		
class WebSocketThread(WorkerThread):
	"""
	Websocket.receive() blocks until there is a response.
	It also hangs indefinitely until there is socket.close() call in the server side
	If the server shuts down unexpectedly the client socket.recieve() will hang forever.
	
	"""
	
	def __init__(self, notify_window):
		#self.webSocketReconnect() #because threads have been "geventified" they no longer run in parallel, but rather asynchronously. So if this runs not within a greenlet, it will block the mainloop... gevent.sleep(1) only yields to another greenlet or couroutine (like wx.Yield) when it is called from within a greenlet.
		
		self.last_sent = self.last_alive = datetime.datetime.now()
		
		WorkerThread.__init__(self, notify_window)
	
	def webSocketReconnect(self):
		"""
		WSock.receive sometimes hangs, as in the case of a disconnect
		Receive blocks, but send does not, so we use send as a tester
		An ideal connection will have a 1:1 ratio of send and receive
		However, bad connections will have poorer ratios such as 10:1
		If ratio reaches 20:1 then this function will force reconnect
		This function is triggered when CLIENT_LATEST_CLIP is set, but
		SERVER_LATEST_CLIP is not, and the outgoing loop keeps calling
		"""
		while self.KEEP_RUNNING:
			try:
				self.wsock.close_connection() # Terminate Nones the environ and stream attributes, which is for servers
			except AttributeError:
				pass
			try:
				self.last_sent = self.last_alive = datetime.datetime.now()
				self.wsock=WebSocketClient(HTTP_BASE(arg="ws", port=8084, scheme="ws") ) #keep static to guarantee one socket for all instances
				self.wsock.connect()
				break
			except (SocketError, exc.HandshakeError, RuntimeError):
				#print "no connection..."
				gevent.sleep(1)
				
	def keepAlive(self, heartbeat = 5, timeout = 15): #increment of 60s times 20 unresponsive = 20 minutes
		"""
		Since send is the only way we can test a connection's status,
		and since send is only triggered when CLIENT_LATEST_CLIP has a
		change, we need to test the connection incrementally too, and
		therefore we can account for when the user is idle.
		"""
		now = datetime.datetime.now()
		if ( now - self.last_alive ).seconds > timeout:
			self.webSocketReconnect()
		elif ( now  - self.last_sent ).seconds > heartbeat:
			self.last_sent= datetime.datetime.now()
			return True
		return False
	
	def incoming(self):
		#pdb.set_trace()
		#print "start incoming..."
		while self.KEEP_RUNNING:
			#if CLIENT_LATEST_CLIP.get() != SERVER_LATEST_CLIP.get():
			#print "getting... c:%s, s:%s"%(CLIENT_LATEST_CLIP.get(),SERVER_LATEST_CLIP.get())
			try:
				received = self.wsock.receive() #WebSocket run method is implicitly called, "Performs the operation of reading from the underlying connection in order to feed the stream of bytes." According to WS4PY This method is blocking and should likely be run in a thread.
				
				if received == None:
					raise SocketError #disconnected!
				
				data = json.loads(str(received) ) #EXTREME: this can last forever, and when creating new connection, this greenlet will hang forever. #receive returns txtmessage object, must convert to string!!! 
				
				if data["message"] == "Download":
					server_latest_clip_rowS = data['data']
					server_latest_clip_row = server_latest_clip_rowS[0]
					#print server_latest_clip_row
					
					SERVER_LATEST_CLIP.set(server_latest_clip_row)
					CLIENT_LATEST_CLIP.set(server_latest_clip_row)
					
					print "GET %s"% server_latest_clip_row['clip_hash_client']
					
					wx.PostEvent(self._notify_window, EVT_RESULT(server_latest_clip_rowS) )

				elif data["message"] == "Alive!":
					#print "Alive!"
					self.last_alive = datetime.datetime.now()
	
			#except (SocketError, RuntimeError, AttributeError, ValueError, TypeError): #gevent traceback didn't mention it was a socket error, just "error", but googling the traceback proved it was. #if received is not None: #test if socket can send
			except:
				#print "can't get...%s"%str(sys.exc_info()[0])
				self.webSocketReconnect()
			
			gevent.sleep(0.25)
				
	def outgoing(self):
		#pdb.set_trace()
		#print "start outgoing..."
		while self.KEEP_RUNNING:
			sendit = False
			if CLIENT_LATEST_CLIP.get().get('clip_hash_client') != SERVER_LATEST_CLIP.get().get('clip_hash_client'): #start only when there is something to send
				print "sending...%s"	
				
				sendit = dict(
					data=CLIENT_LATEST_CLIP.get(),
					message="Upload"
				)
				print "\n\n\nSEND %s... %s"%(CLIENT_LATEST_CLIP.get().get('clip_hash_client'), SERVER_LATEST_CLIP.get().get('clip_hash_client'))
			elif self.keepAlive(): #also send alive messages and reset connection if receive block indefinitely
				sendit = dict(message="Alive?")
						
			if sendit:
				try:
					self.wsock.send(json.dumps(sendit))
					
					self.last_sent = datetime.datetime.now()

				#except (SocketError, RuntimeError, AttributeError, ValueError, TypeError): #if self.wsock.stream: #test if socket can get
				except:
					#print "can't send...%s"%str(sys.exc_info()[0])
					self.webSocketReconnect()
					
			
			gevent.sleep(0.25) #yield to next coroutine.
		
	
	def run(self):
		greenlets = [
			gevent.spawn(self.outgoing),
			gevent.spawn(self.incoming),
		]
		gevent.joinall(greenlets)
		#or you can do this in separate threads but that is annoying,
		#since gevent monkey patches threads to gevent-like
				
class Main(wx.Frame):
	ID_NEW = 1
	ID_RENAME = 2
	ID_CLEAR = 3
	ID_DELETE = 4
	
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "PasteBeam")
		self._do_interface()
		self._do_threads_and_async()

	def _do_interface(self): #_ used because it is meant to be internal to instance
		self.panel = MyPanel(self)
		
		"""
		panel = wx.Panel(self)
		panel.SetBackgroundColour(wx.GREEN)
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		
		self.editor = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
		hbox.Add(self.editor, 1, wx.EXPAND | wx.ALL, 20)
		
		btnPanel = wx.Panel(panel, -1)
		vbox = wx.BoxSizer(wx.VERTICAL)
		new = wx.Button(btnPanel, self.ID_NEW, 'New', size=(90, 30))
		ren = wx.Button(btnPanel, self.ID_RENAME, 'Rename', size=(90, 30))
		dlt = wx.Button(btnPanel, self.ID_DELETE, 'Delete', size=(90, 30))
		clr = wx.Button(btnPanel, self.ID_CLEAR, 'Clear', size=(90, 30))
		self.Bind(wx.EVT_BUTTON, self.clearText, id=self.ID_CLEAR)

		vbox.Add((-1, 20))
		vbox.Add(new)
		vbox.Add(ren, 0, wx.TOP, 5)
		vbox.Add(dlt, 0, wx.TOP, 5)
		vbox.Add(clr, 0, wx.TOP, 5)

		btnPanel.SetSizer(vbox)
		hbox.Add(btnPanel, 0.6, wx.EXPAND | wx.RIGHT, 20)
		
		panel.SetSizer(hbox)
		"""
		self.CreateStatusBar()

	def _do_threads_and_async(self):
		# Set up event handler for any worker thread results
		BIND_EVT_RESULT(self,self.onResult)
		# And indicate we don't have a worker thread yet
		self.websocket_worker = self.long_poller_worker = self.async_worker = None
		# Temporary... no button event, so pass None
		wx.CallLater(1, lambda: self.onStart(None))

	def appendText(self, content):

		def _alternate_new_row_color():
			new_item_index = self.panel.lst.GetItemCount() - 1
			if (new_item_index % 2) == 0:
				color_hex = '#E6FCFF' #second lightest at http://www.hitmill.com/html/pastels.html
			else:
				color_hex = '#FFFFE3'
				
			self.panel.lst.SetItemBackgroundColour(new_item_index, color_hex)
			
		def _descending_order():
			self.panel.lst.SetItemData( new_index, new_index) #SetItemData(self, item, data) Associates data with this item. The data part is used by SortItems to compare two values via the ListCompareFunction
			self.panel.lst.SortItems(self.panel.lst.ListCompareFunction)
		
			
		new_item_number_to_be = self.panel.lst.GetItemCount() + 1
		new_index = self.panel.lst.Append( (new_item_number_to_be, "None", content, "None") )		#self.editor.AppendText(content)
		
		_alternate_new_row_color()
		
		_descending_order()
		
	def clearList(self):
		self.panel.lst.DeleteAllItems()

	def onStart(self, button_event):
		"""Start Computation."""
		# Trigger the worker thread unless it's already busy
		if WorkerThread.USE_WEBSOCKET:
			self.websocket_worker = WebSocketThread(self)
		else:
			self.long_poller_worker = LongPollerThread(self)
		self.runAsyncWorker()

	def onStop(self, button_event):
		"""Stop Computation."""
		# Flag the worker thread to stop if running
		WorkerThread.abort()
		self.async_worker = False

	def onResult(self, result_event):
		"""Show Result status."""
		if result_event.data is None:
			# Thread aborted (using our convention of None return)
			self.appendText('Computation aborted\n')
		else:
			
			first_to_latest_data = result_event.data[::-1]
			self.clearList()
			for each_clip in first_to_latest_data:
				#print each_clip
				try:
					#print "DECODE CLIP %s"%each_clip['clip_text']
					each_clip['clip_text'] = self.decodeClip(each_clip['clip_text'])
				except (zlib.error, UnicodeDecodeError):
					pass
					#print "DECODE/DECRYPT/UNZIP ERROR"
					#purge all data on server
				self.appendText(each_clip['clip_text'])
				
			# Process results here
			latest_content = first_to_latest_data[-1]
			
			self.setClipboardContent(latest_content)
		# In either event, the worker is done
		self.websocket_worker = self.long_poller_worker = None
		
	@staticmethod
	def decodeClip(clip):
		return (clip or '').decode("base64").decode("zlib").decode("utf-8", "replace")
	
	@staticmethod
	def encodeClip(clip):
		return (clip or '').encode("utf-8", "replace").encode("zlib").encode("base64") #MUST ENCODE in base64 before transmitting obsfucated data #null clip causes serious looping problems, put some text! Prevent setText's TypeError: String or Unicode type required 
		
	@staticmethod
	def setClipboardContent(content): 
		#NEEDS TO BE IN MAIN LOOP FOR WRITING TO WORK, OR ELSE WE WILL 
		#GET SOMETHING LIKE: "Failed to put data on the clipboard 
		#(error 2147221008: coInitialize has not been called.)"
		success = False
		try:
			with wx.TheClipboard.Get() as clipboard:
				if content['clip_type'] == "text":
					clip_text = content['clip_text']
					clip_data = wx.TextDataObject()
					clip_data.SetText(clip_text)
					success = clipboard.SetData(clip_data)
				elif content['clip_type'] == "bitmap":
					img_file_name = content['clip_file_name']
					img_file_path = os.path.join(TEMP_DIR,img_file_name)
					print img_file_path
					
					if not os.path.isfile(img_file_path):
						urllib.urlretrieve(HTTP_BASE(arg="static/%s"%img_file_name,port=8084,scheme="http"), img_file_path)

					bitmap=wx.Bitmap(img_file_path, wx.BITMAP_TYPE_BMP)
					#bitmap.LoadFile(img_file_path, wx.BITMAP_TYPE_BMP)
					clip_data = wx.BitmapDataObject(bitmap)
					success = clipboard.SetData(clip_data)
					print "SUCCESS = %s"%success
		except ZeroDivisionError:
			wx.MessageBox("Unable to access the clipboard. Another application seems to be locking it.", "Error")
		
	def getClipboardContent(self):
		try:
			with wx.TheClipboard.Get() as clipboard:
			
				def _return_if_text():
					clip_data = wx.TextDataObject()
					success = clipboard.GetData(clip_data)
					if success:
						clip_text = self.encodeClip(clip_data.GetText())
						clip_hash_client = hex( mmh3.hash( clip_text ) )
						clip_content = {
							'clip_type' : "text",
							'clip_text' : clip_text,
							'clip_hash_client' : clip_hash_client,
						}						
						return clip_content
					
				def _return_if_bitmap():
					clip_data = wx.BitmapDataObject() #http://stackoverflow.com/questions/2629907/reading-an-image-from-the-clipboard-with-wxpython
					success = clipboard.GetData(clip_data)

					if success:
						
						img_hash_old = CLIENT_LATEST_CLIP.get()['clip_hash_client']
						#print "img_hash_old %s"%img_hash_old
						
						bitmap = clip_data.GetBitmap()
						img_hash_new  = hex(mmh3.hash(bitmap.ConvertToImage().GetData())) #GET DATA IS HIDDEN METHOD, IT RETURNS BYTE ARRAY... DO NOT USE GETDATABUFFER AS IT CRASHES. BESIDES GETDATABUFFER IS ONLY GOOD TO CHANGE BYTES IN MEMORY http://wxpython.org/Phoenix/docs/html/MigrationGuide.html
						#print "img_hash_new %s"%img_hash_new
						if img_hash_new != img_hash_old:
						
							img_file_name = "%s.bmp"%img_hash_new
							img_file_path = os.path.join(TEMP_DIR,img_file_name)
							bitmap.SaveFile(img_file_path, wx.BITMAP_TYPE_BMP) #change to or compliment upload
							clip_text = self.encodeClip("Clipboard image %s"%img_file_name)
							
							try:
								r = requests.post(HTTP_BASE(arg="upload",port=8084,scheme="http"), files={"upload": open(img_file_path, 'rb')})
								print r
							except:
								pass
							else:
								clip_content = {
									"clip_type" : "bitmap",
									"clip_text" : clip_text,
									"clip_file_name" : img_file_name,
									"clip_hash_client" : img_hash_new, #for performance reasons we are not using the bmp for hash, but rather the wx Image GetData array
								}
								print img_hash_new
								return clip_content
							
				return (_return_if_text() or _return_if_bitmap() or None)
				
		except ZeroDivisionError:# TypeError:
			wx.MessageBox("Unable to access the clipboard. Another application seems to be locking it.", "Error")
			return None
		
	def runAsyncWorker(self): 
		##pdb.set_trace()
		#since reading/writing clipboard takes very little time, 
		#and since we must access clipboard in main loop, we should 
		#use async to modify a global variable (with a lock to prevent
		#race issues). wx.Yield simply switches back and forth
		#between mainloop and this coroutine.
		while WorkerThread.KEEP_RUNNING:
			clip_content = self.getClipboardContent()
			if clip_content:
				#HOST_CLIP_CONTENT.set( clip_content['clip_text'] )#encode it to a data compatible with murmurhash and wxpython settext, which only expect ascii ie "heart symbol" to u/2339
				CLIENT_LATEST_CLIP.set( clip_content )  #NOTE SERVER_LATEST_CLIP.get() was not set
			gevent.sleep(0.25) #SLEEP HERE WILL CAUSE FILEEXPLORER TO SLOW
			wx.Yield() #http://goo.gl/6Jea2t

if __name__ == "__main__":
	app = wx.App(False)
	frame = Main()
	frame.Show(True)
	app.MainLoop()