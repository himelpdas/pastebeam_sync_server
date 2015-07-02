import gevent
from PySide import QtCore

class WorkerMixin(object):
	def onIncommingSlot(self, progress):
		print "%s signal"%progress

class Worker(QtCore.QThread):

	#This is the signal that will be emitted during the processing.
	#By including int as an argument, it lets the signal know to expect
	#an integer argument when emitting.
	incommingSignal = QtCore.Signal(int)

	#You can do any extra things in this init you need, but for this example
	#nothing else needs to be done expect call the super's init
	def __init__(self):
		QtCore.QThread.__init__(self)

	#A QThread is run by calling it's start() function, which calls this run()
	#function in it's own "thread". 
	def run(self):
		greenlets = [
			gevent.spawn(self.incommingGreenlet) 
		]
		gevent.joinall(greenlets)
			
	def incommingGreenlet(self):
		for i in xrange(101):
			#Emit the signal so it can be received on the UI side.
			self.incommingSignal.emit(i)
			gevent.sleep(1)