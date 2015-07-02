import gevent
from ws4py.client.geventclient import WebSocketClient
from PySide import QtCore

class WebsocketWorkerMixin(object):
	def onIncommingSlot(self, emitted):
		print emitted	
	
	def onOutgoingSlot(self, emitted):
		print emitted

class WebsocketWorker(QtCore.QThread):

	#This is the signal that will be emitted during the processing.
	#By including int as an argument, it lets the signal know to expect
	#an integer argument when emitting.
	incommingSignal = QtCore.Signal(str)
	outgoingSignal = QtCore.Signal(str)

	#You can do any extra things in this init you need, but for this example
	#nothing else needs to be done expect call the super's init
	def __init__(self):
		QtCore.QThread.__init__(self)
		
	#A QThread is run by calling it's start() function, which calls this run()
	#function in it's own "thread". 
	def run(self):
	
		self.wsock = WebSocketClient("ws://sandbox.kaazing.net/echo") #The websocket MUST be runned here, as running it in __init__ would put websocket in main thread
		self.wsock.connect()
	
		greenlets = [
			gevent.spawn(self.outgoingGreenlet),
			gevent.spawn(self.incommingGreenlet),
		]
		gevent.joinall(greenlets)
			
	def incommingGreenlet(self):
		while 1:
			received =  self.wsock.receive()
			self.outgoingSignal.emit("got %s"%received)
			gevent.sleep(1)

	def outgoingGreenlet(self):
		for i in xrange(101):
			#Emit the signal so it can be received on the UI side.
			msg = "hello %s"%i
			self.wsock.send(msg)
			self.incommingSignal.emit("sent %s"%msg)
			gevent.sleep(1)