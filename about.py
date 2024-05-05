import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from dflib import widgets, rest, psen
from dflib.debug import debug

class AboutDialog(widgets.AboutDialog):
	def __init__(self, parent, config, icon, version, position, move_cb):
		self.move_cb = move_cb
		self.version = version
		self.config = config
		about_markup = self.get_markup()
		self.keepgoing = True
		super().__init__(self, 
			title="About Sensors", 
			message=about_markup,
			parent=parent,
			icon=icon,
			buttons=None,
			orientation=Gtk.Orientation.VERTICAL,
			decorated=True
			)

		self._macos = True if 'Darwin' in os.uname()[0] else False

		if position:
			if '::main::' in position:
				position = list(self.config['sensors']['::main::']['pos'])
				for i in range(0,2):
					position[i] = position[i] + 25
				self.move(*position)
		self.connect('configure-event',self.on_window_config)
		self.connect("delete-event", self.stopit)
		self.set_about_text()
	
	def get_markup(self):
		stats = f"""

		PSen Reads   {psen.stats['reads']}
		Rest: Sent   {rest.stats['sent']}
		Rest: Errors {rest.stats['errors']}
		
		"""
		return f"""
		<span size="large"><b>Sensors {self.version}</b></span>
		A SensorFS RestAPI example.
		{stats}
		Copyright © 2024 Nicole Stevens
		<a href="https://github.com/nicciniamh">https://github.com/nicciniamh</a>
		"""

	def set_about_text(self):
		self.label.set_markup(self.get_markup())
		if self.keepgoing:
			GLib.timeout_add(1000, self.set_about_text)

	def stopit(self,*args):
		self.keepgoing = False
		self.destroy()

	def _xyfixup(self,x,y):
		if x + y != 0:
			yoffset = 28 if self._macos else 0
			y+=yoffset
			if x < 0:
				x=0
		return (x,y)

	def move(self,x,y):
		debug(f'{x},{y}')
		return super().move(*self._xyfixup(x,y))

	def on_window_config(self,*args):
		if callable(self.move_cb):
			position = tuple(self.get_position())
			self.move_cb(position)
