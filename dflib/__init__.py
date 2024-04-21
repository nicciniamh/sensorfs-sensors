'''
A set of tools to help run this mess.
Modules to import are:
	cfgjson: JSON based configuration
	debug: Debugging tools
	rest: RESTApi tools
	theme: Gtk theme tools
	widgets: Enhanced Gtk Widgets
'''
from enum import IntFlag
class IconState(IntFlag):
	INACTIVE = 0,
	DETAIL = 1,
	CHART = 2,
	BOTH = 3
