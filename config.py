'''
This module handles the main program config for sensors. 
In this module the server name, polling_interval and dark mode 
are set from the window presented here. 
'''
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GdkPixbuf
from dflib import widgets

from dflib.debug import debug, dump_object_properties, dpprint
from dflib.theme import change_theme

class SensorsConfig(Gtk.Window):
	''' 
	This class presents a window with three input widgets for 
	server name, polling interval and dark mode. 
	'''
	def __init__(self,**kwargs):
		self.on_select = None
		self.on_complete = None
		self.config = None
		self.modified = False
		for k,v in kwargs.items():
			if k in ['config','on_complete']:
				setattr(self,k,v)
			else:
				raise ValueError(f'Invalid keyword argument {k}')
 
		if not self.config:
			debug('keyword argument config must be set')
			raise AttributeError('keyword argument config must be set')
		
		sensors = self.config['sensors']
		Gtk.Window.__init__(self,title='Sensors Configuration')
		self.connect('delete-event',self.on_wm_delete_event)
		self.connect('destroy',self.on_complete_handler)
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		if None:
			sbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			sbox.pack_start(Gtk.Label(label="Server"),True,True,10)
			self.server_input = Gtk.Entry()
			self.server_input.set_text(self.config['server'])
			self.server_input.connect('changed',self.set_modified)
			self.server_input.connect('preedit-changed',self.set_modified)
			sbox.pack_start(self.server_input,True,True,0)
			box.pack_start(sbox,True,True,10)
			sbbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			sblabel = Gtk.Label()
			sblabel.set_markup('Poll Interval\n<small><i>Under 500ms may\ncause significant server load</i></small>')
			if 'poll_interval' in self.config:
				poll_interval = self.config['poll_interval']
			else:
				poll_interval = 300
			self.set_interval = Gtk.SpinButton.new_with_range(100,1500,50)
			self.set_interval.set_value(poll_interval)
			self.set_interval.connect('changed',self.set_modified)
			sbbox.pack_start(sblabel,True,True,10)
			sbbox.pack_start(self.set_interval,True,True,10)
			sbbox.pack_start(Gtk.Label(label="ms."),True,True,10)
			box.pack_start(sbbox,True,True,10)
		
		if 'dark_mode' in self.config:
			dark_mode = self.config['dark_mode']
		else:
			dark_mode = False
			self.config['dark_mode'] = dark_mode
		self.dark_entry = widgets.Toggle(
				label_text = ['Light','Dark'],
				state = dark_mode,
				caption = 'GUI Mode',
				before = True
			)
		if os.uname()[0] == 'Darwin':
			box.pack_start(self.dark_entry,True,True,10)
		okcbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		okbutton = Gtk.Button(label="Ok")
		okbutton.connect('clicked',self.on_ok_clicked)
		cancelbutton = Gtk.Button(label="Cancel")
		cancelbutton.connect('clicked',self.on_cancel_clicked)
		okcbox.pack_start(okbutton,True,True,0)
		okcbox.pack_start(cancelbutton,True,True,0)
		box.pack_start(okcbox,True,True,0)
		window_icon = GdkPixbuf.Pixbuf.new_from_file('icons/humidity.png')
		self.set_icon(window_icon)
		self.set_position(Gtk.WindowPosition.CENTER)
		self.add(box)
		self.show_all()

	def on_wm_delete_event(self,*args):
		''' if the user closes the window check to save changes first '''
		debug(f'on_wm_delete_event - modified: {self.modified}')
		if self.modified:
			dialog_message = "Changes have been made.\n"
			"Do you wish to save changes and exit?\n"
			"close this window?"
			if widgets.yesno(self,dialog_message) == 'yes':
				self.on_ok_clicked()
				return False
			else:
				return True
		return False

	def set_modified(self,*args):
		''' as the name says '''
		self.modified = True

	def on_ok_clicked(self, *args):
		''' when ok is clicked set config variables and callback to indicate
		to caller to save config '''
		debug(f'ok_clicked')
		modified = False
		if None:
			server = self.server_input.get_text()
			if self.config['server'] != server:
				self.config['server'] = server
			pi = self.set_interval.get_value()
			if self.config['poll_interval'] != pi:
				debug(f"poll interval changed to {pi}")
				self.config['poll_interval'] = pi
			else:
				debug(f"Poll Interval is unchanged")
		old_dark = self.config['dark_mode']
		new_dark = self.dark_entry.state
		if new_dark != old_dark:
			debug('dark_mode set to',new_dark)
			self.config['dark_mode'] = new_dark
			change_theme(new_dark)
		else:
			debug('dark_mode unchange')
		self.on_complete_handler()
		self.destroy()

	def on_cancel_clicked(self, *args):
		''' if cancel is clicked forget the whole thing '''
		debug(f'Cancel')
		self.destroy()

	def on_complete_handler(self,*args):
		''' callback if the callback is a callable and call me in the morning '''
		if callable(self.on_complete):
			debug("calling",self.on_complete)
			self.on_complete()
			return False
  