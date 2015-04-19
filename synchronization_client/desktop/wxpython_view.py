import wx

#see http://zetcode.com/wxpython/skeletons/ for tips

class MyListCtrl(wx.ListCtrl):
	def __init__(self, parent):
		super(MyListCtrl, self).__init__(parent,
		style=wx.LC_REPORT)
		# Add three columns to the list
		self.InsertColumn(0, "#", width=33  )
		self.InsertColumn(1, "From",  width=111 )
		self.InsertColumn(2, "Clipping (Double-click to copy)", width=333 )
		self.InsertColumn(3, "Date",  width=111 )
		
		self.resizeColumns(self) #ListCtrl instance also has method GetSize()
		
		self.Bind(wx.EVT_LIST_ITEM_SELECTED,
		self.onItemSelected)
		
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, #DOUBLE CLICK ##SEE PDF http://www.blog.pythonlibrary.org/2013/12/12/wxpython-objectlistview-double-click-items/
			self.onItemDoubleClick)
		
		self.Bind(wx.EVT_SIZE,
			self.resizeColumns)
		
		# Setup
		#data = [ ("row %d" % x,"value %d" % x,"data %d" % x) for x in range(10) ]
		#self.PopulateList(data)

	
	def resizeColumns(self, resize_event):
		width = resize_event.GetSize()[0]
		bleed = 25 #make width sligtly smaller so that vScroll can be hidden
		width = width - bleed

		col0 = width*0.05
		col1 = width*0.20
		col2 = width*0.55
		col3 = width*0.20

		colwidths = [col0, col1, col2, col3]
		
		for number, width in enumerate(colwidths):
			if not wx.GetMouseState().LeftIsDown(): #left key is still up at the very last few resize events, so anything before left key down will be ignored, and resize of columns will be much faster
				wx.CallLater(0.01, lambda number=number, width=width: self.SetColumnWidth(number, width)) #wx calllater for smoother operation #https://groups.google.com/forum/#!topic/wxpython-users/tWiSDnbpWcM
	
	def PopulateList(self, data):
		"""Populate the list with the set of data. Data
		should be a list of tuples that have a value for each
		column in the list.
		[('hello', 'list', 'control'),]
		"""
		for item in data:
			self.Append(item)
		
	def onItemSelected(self, event):
		val = self.getEventItem(event)
		# Show what was selected in the frames status bar
		frame = self.GetTopLevelParent()
		frame.PushStatusText(
			' '.join(val[2].split()) #beautiful, get's rid of /n " " and "	" #http://stackoverflow.com/questions/4241757/python-django-how-to-remove-extra-white-spaces-tabs-from-a-string
		)
		
	def onItemDoubleClick(self, event):
		val = self.getEventItem(event)
		frame = self.GetTopLevelParent()
		frame.setClipboardContent(val[2])
		
	def getEventItem(self, event):
		selected_row = event.GetIndex()
		val = list()
		for column in range(self.GetColumnCount() ):
			item = self.GetItem(selected_row, column)
			val.append(item.GetText())
		return val
		
	def ListCompareFunction(self, item1, item2):
		if item1 > item2:
			return -1
		elif item1 < item2:
			return 1
		elif item1 ==  item2:
			return 0
		
class MyPanel(wx.Panel):
	def __init__(self, parent):
		super(MyPanel, self).__init__(parent)
		
		self.vsizer_main = wx.BoxSizer(wx.VERTICAL)
		
		self._addToolBar()
				
		self._addMyListCtrl()
		
		self.SetSizer(self.vsizer_main)
		
	def _addToolBar(self):
		self.hsizer_toolbar = wx.BoxSizer(wx.VERTICAL)
		
		button = wx.Button(self, -1, "Add device")
		self.hsizer_toolbar.Add(button, 1, wx.TOP | wx.LEFT | wx.RIGHT, 20)
		
		self.vsizer_main.Add(self.hsizer_toolbar)
		
	def _addMyListCtrl(self):
		# Attributes
		self.lst = MyListCtrl(self)
		# Layout
		self.vsizer_main.Add(self.lst, 1, wx.EXPAND | wx.ALL, 20)
		# Event Handlers