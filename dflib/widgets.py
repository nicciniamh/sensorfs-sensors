'''
Some widgets I made :) 

Included are:
	MessageBox - A Gtk.Window derived message box
	ListBox - A simpler interface to a Gtk.ListBox
	Toggle - A labeled toggle button inside a Gtk.Box
	LabeledEntry - A labeled and Gtk.Entry field in a Gtk.Box
	Button - a button class with a convenient css handler
	yesno - a simple Gtk.Dialog function to ask a yesno question 
	and return the result
	MenuBar - a MenuBar that builds menus from a dictionary
'''	


import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GLib, GdkPixbuf

from dflib.debug import debug

def yesno(parent,message):
	message = message.split('\n')
	title = message[0]
	message = '\n'.join(message[1:])
	dialog = Gtk.MessageDialog(
		parent = None, #parent,
		flags = Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, 
		type = Gtk.MessageType.QUESTION, 
		buttons = (Gtk.STOCK_YES, Gtk.ResponseType.YES, Gtk.STOCK_NO, Gtk.ResponseType.NO),
		message_format = title)
	dialog.format_secondary_markup(message)
	dialog.show_all()
	response = dialog.run()
	dialog.destroy()

	if response == Gtk.ResponseType.YES:
		return 'yes'
	else:
		return 'no'

def _widget_set_css(widget, classname, css_data):
	'''
	this function takes an arbitrary widget and applies the classname as it's class
	the css_data is applied to the widget.
	'''
	if type(css_data) is str:
		css_data = bytes(css_data.encode('ascii'))
	if type(css_data) is not bytes:
		raise TypeError(f'{type(css_data)} is not appropriate for css_data')
	css_provider = Gtk.CssProvider()
	css_provider.load_from_data(css_data)
	context = widget.get_style_context()
	context.add_class(classname)
	context.add_provider(css_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class MessageDialog(Gtk.Window):
	'''
	MessageDialog
	Ths class implments a MessageBox as a Gtk.Window

	Constructor parameters:
		buttons: list of strings to be placed on buttons (ok, cancel etc) default: ["OK"]
		callback: function to run if button is pressed. The str label of the button is passed
		icon: name of icon to use, eother Gtk.ICON_xxx or a filename. Default is Gtk.ICON_DIALOG_INFO
		message: message to show
		parent: if set the window becomes modal and transient for the parent. 
		title: title of window

		Callback is option and if not set, clicking a button destroys the dialog. 
		Title and message must be set.
	'''
	def __init__(self, *args, **kwargs):
		css_data = ".about_label { padding-left: 15px;padding-right: 15px;}"
		self.parent = None
		self.icon = 'dialog-info'
		self.title = "Message Dialog"
		self.callback = None
		self.message = "Stupid programmer forgot to add a message"
		self.buttons = None
		self.orientation = Gtk.Orientation.HORIZONTAL
		for k,v in kwargs.items():
			if k in ['message', 'parent','title','callback','icon','buttons','orientation']:
				setattr(self,k,v)
			else:
				raise ValueError('invalid keyword argument {l}')

		self.icon_file = self.icon
		if self.icon:
			if os.path.exists(self.icon):
				self.icon = Gtk.Image.new_from_file(self.icon)
				self.icon.set_pixel_size(64)
			else:
				try:
					self.icon = Gtk.Image.new_from_icon_name(self.icon, Gtk.IconSize.DIALOG)
				except:
					self.icon = Gtk.Image.new_from_icon_name('dialog-info', Gtk.IconSize.DIALOG)

		Gtk.Window.__init__(self, title=self.title)
		if self.icon_file:
			window_icon = GdkPixbuf.Pixbuf.new_from_file(self.icon_file)
			self.set_icon(window_icon)

		self.icon.set_halign(Gtk.Align.END)
		#self.set_default_size(500, 100)
		
		self.label = label = Gtk.Label()
		_widget_set_css(label,'about_label',css_data)
		label.set_markup(self.message)
		#title = f'<b>{self.title}</b>'
		#tlabel = Gtk.Label()
		#tlabel.set_markup(title)
		vb = Gtk.Box(orientation=self.orientation)
		self.add(vb)
		#vb.pack_start(tlabel,True,True,0)
		hb = Gtk.Box(orientation=self.orientation)
		vb.pack_start(hb,True,True,0)
		if self.icon:
			hb.pack_start(self.icon,True,True,0)

		hb.pack_start(label,True,True,0)
		bb = Gtk.Box(orientation=self.orientation)
		vb.pack_start(bb,True,True,0)
		if self.buttons:
			if type(self.buttons) is str:
				self.buttons = [self.buttons]
			for b in self.buttons:
				button = Gtk.Button(label=b)
				bb.pack_start(button,True,True,0)
				button.connect('clicked',self.on_response)

		if(self.parent):
			self.set_transient_for(self.parent)
			self.set_modal(True)

		self.show_all()
		self.present()
	
	def on_response(self, button,*args):
		text = button.get_label()
		if callable(self.callback):
			self.callback(text)
		self.destroy()

class AboutDialog(MessageDialog):
	''' Display an AboutDialog implemented as a MessageDialog
		kwargs:
			title - window title
			message - message to display
			parent - parent widget, if set dialog is modal
			icon - name or path of icon 
			buttons - list of buttons to show
	'''
	def __init__(self, *args, **kwargs):
		self.title= None
		self.message= None
		self.parent= None
		self.icon= None
		self.decorated = True
		self.buttons=["Close"]
		for k,v in kwargs.items():
			setattr(self,k,v)

		super().__init__(self, 
			title=self.title,
			message=self.message,
			parent=self.parent,
			icon=self.icon,
			buttons=self.buttons)
		self.show_all()
		if not self.decorated:
			self.connect('key-press-event', self.on_key_press)
			self.connect('focus-out-event', self.on_focus_out)
		self.set_decorated(self.decorated)
		self.present()

	def on_focus_out(self,*args):
		self.destroy()

	def on_key_press(self,widget,event,*args):
		if event.keyval == Gdk.KEY_Escape:
			self.destroy()

class Toggle(Gtk.Box):
	'''
	Toggle is a control that has a label either above or to the left of the 
	toggle button. 

	kwargs:
		label_text - a list of two strings to show on the button  for toggled or not
		orientation - should be a Gtk.Orientation type
		caption - label to show next to or above button
		state - boolean initial state
		callback - function to call on state change, receives button label text
	'''

	def __init__(self,*args,**kwargs):
		self.label_text = None
		self.state = False
		self.orientation = Gtk.Orientation.HORIZONTAL
		self.caption = None
		self.callback = None
		self.before = True
		self._button_images = False
		self.button = Gtk.ToggleButton()

		for k,v in kwargs.items():
			if k in ['label_text','orientation','caption','before','state','callback']:
				setattr(self,k,v)

		if not self.caption or not self.label_text:
			raise ValueError('label_text and caption must be specified.')

		self.state_text = self._buttonText()

		Gtk.Box.__init__(self)
		self.set_orientation(self.orientation)
		label = Gtk.Label()
		label.set_markup(self.caption)
		debug(f'Checking to see if we were passed an image name on {self.label_text[0]}')
		debug(self.label_text[0],os.path.exists(self.label_text[0]))
		if os.path.exists(self.label_text[0]):
			self._button_images = True
			self.label_text = [Gtk.Image.new_from_file(lt) for lt in self.label_text]
			debug(self._button_images,self.label_text)
		self.change_button()
		self.button.connect('toggled',self._on_button_toggled)
		self.button.set_active(self.state)
		if self.before:
			self.pack_start(label,True,True,0)
			self.pack_start(self.button,True,True,0)
		else:
			self.pack_start(self.button,True,True,0)
			self.pack_start(label,True,True,0)
		self.show_all()

	def label_set_css(self,classname, css_data):
		if not self._button_images:
			_widget_set_css(self,self.label,classname, css_data)

	def button_set_css(self,classname, css_data):
		if not self._button_images:
			_widget_set_css(self,self.button,classname, css_data)

	def change_button(self):
		getattr(self,'button')
		if self.state:
			i = 1
		else:
			i = 0
		if self._button_images:
			self.button.set_image(self.label_text[i])
		else:
			self.button.set_label(self.label_text[i])

	def _on_button_toggled(self,button):
		self.state = button.get_active()
		debug(f'button state is ',self.state)
		self.state_text =self._buttonText()
		self.change_button()
		if callable(self.callback):
			self.callback(self.state_text)

	def _buttonText(self):
		if self.state:
			i = 1
		else:
			i = 0
		if self._button_images:
			self.state_text = ['off','on'][i]
		else:
			self.state_text = self.label_text[i]
		return self.state_text

	@property
	def text(self): return self._buttonText()

class ListBox(Gtk.ListBox):
	''' Simplified interface for a GtkListBos
	keyword arguments:
		onSelect: activated when a row is selected, callback receives label text
		onActivate: activated when a row is activated (double clicked) same as above
	'''
	def __init__(self, items, **kwargs):
		self.onSelect = None
		self.onActivate = None
		self.selected = None
		self.items = items
		for k,v in kwargs.items():
			if k in ['onSelect','onActivate']:
				setattr(self,k,v)
			else:
				raise ValueError(f'{k} is not a valid keyword argument')
		super().__init__()
		self.populate(self.items)

	def select_row_by_label(self,text):
		'''
		set the row with that has the label in text
		'''
		for child in self.get_children():
			if child.get_child().get_text() == text:
				self.select_row(child)

	def remove_row_by_label(self, text):
		'''
		remove a row by the row's label
		'''
		for child in self.get_children():
			if child.get_child().get_text() == text:
				self.remove(child)

	def populate(self, items):
		'''
		Clear and reload the ListBox with items
		'''
		for child in self.get_children():
			self.remove(child)

		self.items = items
		
		for i in items:
			self.add(Gtk.Label(label=i))

		self.show_all()
		self.connect('row-selected',self.on_row_selected)
		self.connect('row-activated',self.on_row_activated)

	def on_row_activated(self, widget, selected):
		'''
		callack when row is activated. Call the supplied callback with the label
		'''
		if callable(self.onActivate):
			self.onActivate(self, selected.get_child().get_text())

	def on_row_selected(self, widget, selected):
		'''
		callack when row is selected. Call the supplied callback with the label
		'''
		if not selected:
			return
		selected = selected.get_child().get_text()
		self.selected = selected
		if callable(self.onSelect):
			self.onSelect(self, selected)

	def get_selected_item(self):
		''' get current selected row '''
		return self.selected

class LabeledEntry(Gtk.Box):
	'''
	LabeledEntry is a control that has a label either above or to the left of an
	entry field.

	__init__ kwargs:
		text - text to load in the entry field
		orientation - should be a Gtk.Orientation type
		caption - label to show next to or above button
		callback - function to call on entry change
	'''

	def __init__(self,*args,**kwargs):
		self.text = None
		self.orientation = Gtk.Orientation.HORIZONTAL
		self.caption = None
		self.callback = None

		kwa = {}

		for k,v in kwargs.items():
			if k in ['orientation','caption','text','callback']:
				setattr(self,k,v)
			else:
				kwa[k] = v

		if not self.caption:
			raise ValueError('caption must be specified.')

		self.state_text = self._buttonText()

		Gtk.Box.__init__(self,**kwa)
		self.set_orientation(self.orientation)
		self.label = Gtk.Label()
		self.label.set_markup(self.caption)
		self.entry = Gtk.Entry()
		if self.text:
			self.entry.set_text(self.text)
		self.entry.connect('change',self._on_entry_changed)
		self.pack_start(self.label,True,True,0)
		self.pack_start(self.entry,True,True,0)
		self.show_all()

	def _on_entry_changed(self,widget,*args):
		if callable(self.callback):
			self.callback(widget,*args)

	def get_entry_text(self):
		return self.entry.get_text()

	def set_entry_text(self,text):
		return self.entry.set_text(text)

	def get_label_text(self):
		return self.label.get_text()

	def set_label_text(self,text):
		return self.label.set_text(text)

	def _widget_set_css(self, widget, classname, css_data):
		if type(css_data) is str:
			css_data = bytes(css_data.decode('ascii'))
		if type(css_data) is not bytes:
			raise TypeError(f'{type(css_data)} is not appropriate for css_data')
		css_provider = Gtk.CssProvider()
		css_provider.load_from_data(css_data)
		context = widget.get_style_context()
		context.add_class(classname)
		context.add_provider(css_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

	def label_set_css(self,classname, css_data):
		_widget_set_css(self,self.label,classname, css_data)

	def entry_set_css(self,classname, css_data):
		_widget_set_css(self,self.entry,classname, css_data)


class Button(Gtk.Button):
	'''
	wrapper for gtk.Button
	kwargs:
		style: css styles to use
		css_class: css class name to use
		name: name of widget
		icon_name Gtk icon name to use
		label = label text to use (markup ok)
		relief: wheter to use Gtk relief on the button
	'''
	def __init__(self,*args,**kwargs):
		self.style = None
		self.css_class = None
		self.name = None
		self.icon_name = None
		self.label = None
		self.relief = Gtk.ReliefStyle.NONE
		for k,v in kwargs.items():
			if k in ['style','css_class','name','icon_name','label','relief']:
				setattr(self,k,v)
			else:
				raise ValueError('invalid keyword argument')

		Gtk.Button.__init__(self)

		self.set_relief(self.relief)
		if self.name:
			self.set_name(self.name)
		if self.label:
			self.set_label(self.label)

		if self.icon_name:
			self.set_icon_name(self.icon_name)

		if self.css_class and self.style:
			self.set_css_class(self.css_class)

	def set_css_class(self,css_class,style=None):
		if style:
			self.style = style
		if not css_class in self.style:
			raise KeyError(f'{css_class}: no such style')
		self.css_class = css_class
		if self.css_class and self.style:
			#debug(f'setting class {self.get_label()} {self.css_class}')
			_widget_set_css(self,self.css_class,self.style[css_class])
		#else:
			#debug(f'no matching css style for {self.get_label()} {self.css_class}')

class MenuBar(Gtk.MenuBar):
	'''
	MenuBar creates a set of menus based on the dictionary menu_items. 
	it is organized as A dict of menu bar entry, list of entry items. Each
	entry item consists of a caption and an action. See example below. 

		menu_items = {
			"File": [
				{"caption": "About", "action": self.handler},
				{"caption": "---", "action": self.handler},
				{"caption": "Open", "action": self.handler},
				{"caption": "Save As","action": self.handler},
				{"caption": "---", "action": self.handler},
				{"caption": "Quit", "action": self.handler},
			], 
			"Configuration": [
				{"caption": "Configuation Editor", "action": self.handler},
			]
		}


	'''
	def __init__(self,menu_entries):
		Gtk.MenuItem.__init__(self)
		self.menu_actions = menu_entries
		self.full_menu = {}
		for caption,entries in self.menu_actions.items():
			menu = Gtk.Menu()
			menu_item = Gtk.MenuItem(label=caption)
			self.full_menu[caption] = {"menu": menu, "menu_item": menu_item}
			menu_item.set_submenu(menu)
			fentries = {}
			for entry_cfg in entries:
				entry = entry_cfg['caption']
				action = entry_cfg['action']
				if entry == '---':
					menu.append(Gtk.SeparatorMenuItem())
				else:
					entry_item = Gtk.MenuItem(label=entry)
					if action:
						entry_item.connect("activate",action)

					menu.append(entry_item)
					entry_cfg['entry_item'] = entry_item
					entry_cfg['menu_item'] = menu_item
					fentries[entry] = entry_item
			self.full_menu[caption]['entries'] = fentries
			self.append(menu_item)

	def get_menu_entry_by_label(self,label):
		if label in self.full_menu:
			return self.full_menu[label]['menu']
		for caption, details in self.full_menu.items():
			for cap, entry in details.items():
				if cap == 'label':
					return entry
		return None


class ErrorDialog(Gtk.Window):
	def __init__(self,title, message, on_close):
		css_data = '.errorfmt {padding-left: 15px; padding-right: 15px; color: red; }'
		Gtk.Window.__init__(self,title=title)
		label = Gtk.Label()
		label.set_markup(f'\n{message}\n\n')
		_widget_set_css(label, 'errorfmt,error', css_data)
		button = Gtk.Button(label='Close')
		button.connect('clicked',on_close)
		icon = Gtk.Image.new_from_icon_name('dialog-error',Gtk.IconSize.DIALOG)
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		box.pack_start(icon,False,True,0)
		box.pack_start(label,True,True,0)
		box.pack_start(button,True,True,0)
		self.add(box)
		self.show_all()
