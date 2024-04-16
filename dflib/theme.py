''' module to change dark gtk preferences '''
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from dflib.debug import debug, error

def change_theme(dark=False):
	''' Change Gtk theme from dark to light '''
	debug(f'Setting dark to {dark}')
	settings = Gtk.Settings.get_default()
	if settings:
		settings.set_property("gtk-application-prefer-dark-theme", dark)
	else:
		error('No Gtk settings')

