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
from threading import Thread # import * BREAKS enumerate!!!
from wxpython_view import *

#general stuff
import time, sys, zlib, datetime, uuid, os, tempfile, urllib, platform, gc
from functions import *
import compress_encrypt

#debug
import pdb

#db stuff
import mmh3
from spooky import hash128
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

SERVER_LATEST_CLIP, CLIENT_LATEST_CLIP, CLIENT_RECENT_DATA = AsyncResult(), AsyncResult(), AsyncResult()
SERVER_LATEST_CLIP.set({}) #the latest clip's hash on server
CLIENT_LATEST_CLIP.set({}) #the latest clip's hash on client. Take no action if equal with above.
CLIENT_RECENT_DATA.set(None)
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
				
	def keepAlive(self, heartbeat = 100, timeout = 1000): #increment of 60s times 20 unresponsive = 20 minutes
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
					
					SERVER_LATEST_CLIP.set(server_latest_clip_row) #should move this to after postevent or race condition may occur, but since this is gevent, it might not be necessary
					CLIENT_LATEST_CLIP.set(server_latest_clip_row)
					
					#print "GET %s"% server_latest_clip_row['clip_hash_client']
					
					wx.PostEvent(self._notify_window, EVT_RESULT(server_latest_clip_rowS) )

				elif data["message"] == "Alive!":
					print "Alive!"
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
			if self.keepAlive(): #also send alive messages and reset connection if receive block indefinitely
				sendit = dict(message="Alive?")
			elif CLIENT_LATEST_CLIP.get().get('clip_hash_client') != SERVER_LATEST_CLIP.get().get('clip_hash_client'): #start only when there is something to send
				print "sending...%s"%CLIENT_LATEST_CLIP.get()	
				
				sendit = dict(
					data=CLIENT_LATEST_CLIP.get(),
					message="Upload"
				)
				print "\n\n\nSEND %s... %s"%(CLIENT_LATEST_CLIP.get().get('clip_hash_client'), SERVER_LATEST_CLIP.get().get('clip_hash_client'))
						
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
	#ID_NEW = 1
	#ID_RENAME = 2
	#ID_CLEAR = 3
	#ID_DELETE = 4
	TEMP_DIR = TEMP_DIR
	
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
		
		self.setThrottle()
		wx.CallLater(1, lambda: self.onStart(None))

	def appendClipToListCtrl(self, clip, is_newest):

		def _stylize_new_row():
			new_item_index = self.panel.lst.GetItemCount() - 1
			if (new_item_index % 2) != 0:
				#color_hex = '#E6FCFF' #second lightest at http://www.hitmill.com/html/pastels.html
				#color_hex = '#f1f1f1'
			#else:
				#color_hex = '#FFFFE3'
				
				self.panel.lst.SetItemBackgroundColour(new_item_index, "#f1f1f1") #many ways to set colors, see http://www.wxpython.org/docs/api/wx.Colour-class.html and http://wxpython.org/Phoenix/docs/html/ColourDatabase.html #win.SetBackgroundColour(wxColour(0,0,255)), win.SetBackgroundColour('BLUE'), win.SetBackgroundColour('#0000FF'), win.SetBackgroundColour((0,0,255))
				
			clip_file_ext = os.path.splitext(clip['clip_file_name'])[1]
			file_image_number = self.panel.lst.icon_extensions.index("._clip")
			if clip['clip_type'] == "file":
				try:
					file_image_number = self.panel.lst.icon_extensions.index(clip_file_ext) #http://stackoverflow.com/questions/176918/finding-the-index-of-an-item-given-a-list-containing-it-in-python
				except ValueError:
					file_image_number = self.panel.lst.icon_extensions.index("._blank")
			elif clip['clip_type'] == "bitmap":
				file_image_number = self.panel.lst.icon_extensions.index("._bitmap")			
			elif clip['clip_type'] == "link":
				file_image_number = self.panel.lst.icon_extensions.index("._page")
			self.panel.lst.SetItemImage(new_item_index, file_image_number)
			#self.panel.lst.SetItemBackgroundColour(new_item_index, color_hex)
			
			if is_newest: #make bold if newest
				item = self.panel.lst.GetItem(new_index)
				#item.SetBackgroundColour("#B8B8B8")
				#item.SetTextColour("WHITE")
				font = item.GetFont()
				font.SetWeight(wx.FONTWEIGHT_BOLD)
				item.SetFont(font)
				self.panel.lst.SetItem(item)
			
		def _descending_order():
			self.panel.lst.SetItemData( new_index, new_index) #SetItemData(self, item, data) Associates data with this item. The data part is used by SortItems to compare two values via the ListCompareFunction
			self.panel.lst.SortItems(self.panel.lst.ListCompareFunction)
		
			
		#new_item_number_to_be = self.panel.lst.GetItemCount() + 1;  self.panel.lst.Append( (new_item_number_to_be...))
		#timestamp_human = datetime.datetime.fromtimestamp(clip['timestamp_server']).strftime(u'%H:%M:%S \u2219 %Y-%m-%d'.encode("utf-8") ).decode("utf-8") #broken pipe \u00A6
		timestamp_human = u'{dt.hour}:{dt:%M}:{dt:%S} {dt:%p} \u2219 {dt.month}-{dt.day}-{dt.year}'.format(dt=datetime.datetime.fromtimestamp(clip['timestamp_server'] ) ) #http://stackoverflow.com/questions/904928/python-strftime-date-without-leading-0
		new_index = self.panel.lst.Append( (clip['clip_file_name'], clip['host_name_client'], clip['clip_type'], clip['clip_display'], timestamp_human ) ) #unicodedecode error fix	#http://stackoverflow.com/questions/2571515/using-a-unicode-format-for-pythons-time-strftime
		
		_stylize_new_row()
		
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
		#if result_event.data is None:
		#	# Thread aborted (using our convention of None return)
		#	self.appendClipToListCtrl('Computation aborted\n')
		if result_event.data:
			
			oldest_to_newest_clips = result_event.data[::-1] #reversed copy
			newest_index = len(oldest_to_newest_clips)-1
			self.clearList()
			for item_index, each_clip in enumerate(oldest_to_newest_clips):
				#print each_clip
				try:
					#print "DECODE CLIP %s"%each_clip['clip_display']
					each_clip['clip_display'] = self.decodeClip(each_clip['clip_display'])
				except (zlib.error, UnicodeDecodeError):
					newest_index-=1 #the list will be smaller if some items are duds, so make the newest_index smaller too
					#print "DECODE/DECRYPT/UNZIP ERROR"
				else:
					self.appendClipToListCtrl(each_clip, is_newest = (True if item_index==newest_index else False) )
				
			# Process results here
			latest_content = oldest_to_newest_clips[-1]
			
			self.setClipboardContent(file_name= latest_content['clip_file_name'], clip_type =latest_content['clip_type'])
			
			self.destroyBusyDialog()

		
	@staticmethod
	def decodeClip(clip):
		return (clip or '').decode("base64").decode("zlib").decode("utf-8", "replace")
	
	@staticmethod
	def encodeClip(clip):
		return (clip or '').encode("utf-8", "replace").encode("zlib").encode("base64") #MUST ENCODE in base64 before transmitting obsfucated data #null clip causes serious looping problems, put some text! Prevent setText's TypeError: String or Unicode type required 
		
	def downloadClipFileIfNotExist(self, file_name):
		file_path = os.path.join(TEMP_DIR,file_name)
		print file_path
		
		if os.path.isfile(file_path):
			return file_path
		else:
			#TODO- show downloading file dialogue
			try:
				#urllib.urlretrieve(HTTP_BASE(arg="static/%s"%file_name,port=8084,scheme="http"), file_path)
				urllib.URLopener().retrieve(HTTP_BASE(arg="static/%s"%file_name,port=8084,scheme="http"), file_path) #http://stackoverflow.com/questions/1308542/how-to-catch-404-error-in-urllib-urlretrieve
			except IOError:
				pass
			else:
				return file_path
				
	def destroyBusyDialog(self):
		#this will be invoked if another client has a new clip
		#so always check if busy_dialog in attributes
		if 'busy_dialog' in self.__dict__ and self.busy_dialog:
			self.busy_dialog.Destroy()
			self.busy_dialog = None
		self.SetTransparent( 255 )
		
	def showBusyDialog(self):
		self.busy_dialog = wx.BusyInfo("Please wait a moment...", self)
		self.SetTransparent( 222 )
		
	def setClipboardContent(self, file_name, clip_type): 
		#NEEDS TO BE IN MAIN LOOP FOR WRITING TO WORK, OR ELSE WE WILL 
		#GET SOMETHING LIKE: "Failed to put data on the clipboard 
		#(error 2147221008: coInitialize has not been called.)"
		success = False
		try:
			with wx.TheClipboard.Get() as clipboard:
	
				file_path = self.downloadClipFileIfNotExist(file_name)
				
				if file_path:
					
					if clip_type in ["text","link"]:
						with open(file_path, 'r') as clip_file:
							clip_text = self.decodeClip(clip_file.read())
							clip_data = wx.TextDataObject()
							clip_data.SetText(clip_text)
							success = clipboard.SetData(clip_data)

					elif clip_type == "bitmap":
						bitmap=wx.Bitmap(file_path, wx.BITMAP_TYPE_BMP)
						#bitmap.LoadFile(img_file_path, wx.BITMAP_TYPE_BMP)
						clip_data = wx.BitmapDataObject(bitmap)
						success = clipboard.SetData(clip_data)
				else:
					wx.MessageBox("Unable to download this clip from the server", "Error")

		except ZeroDivisionError:
			wx.MessageBox("Unable to access the clipboard. Another application seems to be locking it.", "Error")
					
		print "SUCCESS = %s"%success
		#PUT MESSAGEBOX HERE? ALSO destroyBusyDialog
		
	def getClipboardContent(self):
		try:
			with wx.TheClipboard.Get() as clipboard:
			
				def __upload(file_path, clip_type, clip_display_encoded, clip_file_name, clip_hash_client, raw_comparison_data):
						response = requests.get(HTTP_BASE(arg="file_exists/%s"%clip_file_name,port=8084,scheme="http"))
						file_exists = json.loads(response.content)
						if not file_exists['result']:
							r = requests.post(HTTP_BASE(arg="upload",port=8084,scheme="http"), files={"upload": open(file_path, 'rb')})
							print r

						clip_content = {
							"clip_type" : clip_type,
							"clip_display" : clip_display_encoded,
							"clip_file_name" : clip_file_name,
							"clip_hash_client" : clip_hash_client, #http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x
							"host_name_client" : "%s (%s %s)"%(wx.GetHostName(), platform.system(), platform.release()),
							"timestamp_client" : time.time(),
						}
						
						CLIENT_RECENT_DATA.set(raw_comparison_data)
						
						return clip_content
			
				def _return_if_text_or_url():
					clip_data = wx.TextDataObject()
					success = clipboard.GetData(clip_data)
					
					if success:
						self.setThrottle("fast")
					
						clip_text_old = CLIENT_RECENT_DATA.get()
						
						clip_text_new = clip_data.GetText()
						
						if clip_text_new != clip_text_old: #UnicodeWarning: Unicode equal comparison failed to convert both arguments to Unicode - interpreting them as being unequal
							clip_text_is_url = string_is_url(clip_text_new)
							
							clip_text_encoded = self.encodeClip(clip_text_new)
							
							if clip_text_is_url:
								clip_display_encoded = self.encodeClip(clip_text_new[:250] )
							else:
								clip_display_encoded = self.encodeClip(clip_text_new)

							clip_hash_client = format( hash128( clip_text_encoded ), "x") #hex( hash128( clip_text_encoded ) ) #use instead to get rid of 0x for better looking filenames
							
							txt_file_name = "%s.txt"%clip_hash_client
							txt_file_path = os.path.join(TEMP_DIR,txt_file_name)
							
							with open(txt_file_path, 'w') as txt_file:
								txt_file.write(clip_text_encoded)
								
							return __upload(
								file_path = txt_file_path, 
								clip_type = "text" if not clip_text_is_url else "link", 
								clip_display_encoded = clip_display_encoded, 
								clip_file_name = txt_file_name, 
								clip_hash_client = clip_hash_client, 
								raw_comparison_data = clip_text_new
							)
						
				def _return_if_bitmap():
					clip_data = wx.BitmapDataObject() #http://stackoverflow.com/questions/2629907/reading-an-image-from-the-clipboard-with-wxpython
					success = clipboard.GetData(clip_data)

					if success:
						self.setThrottle("slow")
						
						img_array_old = CLIENT_RECENT_DATA.get()
						#print "img_array_old %s"%img_array_old
						
						bitmap = clip_data.GetBitmap()
						img_array_new  = bitmap.ConvertToImage().GetData() #GET DATA IS HIDDEN METHOD, IT RETURNS BYTE ARRAY... DO NOT USE GETDATABUFFER AS IT CRASHES. BESIDES GETDATABUFFER IS ONLY GOOD TO CHANGE BYTES IN MEMORY http://wxpython.org/Phoenix/docs/html/MigrationGuide.html
						#print "img_array_new %s"%img_array_new
												
						if img_array_new != img_array_old: #for performance reasons we are not using the bmp for hash, but rather the wx Image GetData array
							
							print len(img_array_new)
							
							clip_hash_client = format(hash128(img_array_new), "x") #hex(hash128(img_array_new))
							img_file_name = "%s.bmp"%clip_hash_client
							img_file_path = os.path.join(TEMP_DIR,img_file_name)
							bitmap.SaveFile(img_file_path, wx.BITMAP_TYPE_BMP) #change to or compliment upload
							clip_display_encoded = self.encodeClip("Clipboard image on %s"%datetime.datetime.now())
							
							compress_encrypt.compress_encrypt(img_file_path)
							
							return __upload(
								file_path = img_file_path, 
								clip_type = "bitmap", 
								clip_display_encoded = clip_display_encoded, 
								clip_file_name = img_file_name, 
								clip_hash_client = clip_hash_client, 
								raw_comparison_data = img_array_new
							)
							
							gc.collect() #free up previous references to img_array_new and img_array_old arrays, since they are so large #http://stackoverflow.com/questions/1316767/how-can-i-explicitly-free-memory-in-python
							
				def _return_if_file():
					clip_data = wx.FileDataObject()
					success = clipboard.GetData(clip_data)

					if success:
						#self.setThrottle("slow")
						print clip_data.GetFilenames()
							
							
				return (_return_if_text_or_url() or _return_if_bitmap() or _return_if_file() or None)
				
		except requests.exceptions.ConnectionError:
			self.destroyBusyDialog()
			wx.MessageBox("Unable to connect to the internet.", "Error")
			return None
		except ZeroDivisionError:# TypeError:
			self.destroyBusyDialog()
			wx.MessageBox("Unable to access the clipboard. Another application seems to be locking it.", "Error")
			return None
			
	def setThrottle(self, speed="fast"):
		#the seconds before self.getClipboardContent() runs again
		#set to slow when dealing with files and bitmaps to prevent memory leaks
		if speed == "fast":
			milliseconds = 1111
		elif speed == "slow":
			milliseconds = 5555		
		self.throttle = milliseconds
		
	def runAsyncWorker(self): 
		##pdb.set_trace()
		#since reading/writing clipboard takes very little time, 
		#and since we must access clipboard in main loop, we should 
		#use async to modify a global variable (with a lock to prevent
		#race issues). wx.Yield simply switches back and forth
		#between mainloop and this coroutine.
		counter = 0
		while WorkerThread.KEEP_RUNNING:
			if counter % self.throttle == 0:# only run every second, letting it run without this restriction will call memory failure and high cpu
				clip_content = self.getClipboardContent()
				if clip_content:
					#HOST_CLIP_CONTENT.set( clip_content['clip_text'] )#encode it to a data compatible with murmurhash and wxpython settext, which only expect ascii ie "heart symbol" to u/2339
					CLIENT_LATEST_CLIP.set( clip_content )  #NOTE SERVER_LATEST_CLIP.get() was not set
			counter += 1
			gevent.sleep(0.001) #SLEEP HERE WILL CAUSE FILEEXPLORER AND UI TO SLOW
			wx.Yield() #http://goo.gl/6Jea2t
				

if __name__ == "__main__":
	app = wx.App(False)
	frame = Main()
	frame.Show(True)
	app.MainLoop()