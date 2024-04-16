import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

from dflib.debug import debug

class IconWindow(Gtk.ScrolledWindow):
	def __init__(self, **kwargs):
		Gtk.ScrolledWindow.__init__(self)
		self.selected_x = self.selected_y = 0
		self.icon_dict = None
		self.activate_callback = None
		self.menu_callback = None
		self.context_menu = True
		self.icon_menu = True
		self.info_menu = False
		self.add_item_callback = False
		self.pixmap = {}
		self.sort_dir = Gtk.SortType.ASCENDING
		self.sort_column = 1
		self.activate_on_single_click = False
		self.active_windows = None
		self.config = None
		for k, v in kwargs.items():
			if k in [   'icon_dict', 'context_menu',
						'activate_callback', 'menu_callback', 'add_item_callback',
						'info_menu','icon_menu','info_menu','activate_on_single_click',
						'active_windows','config'
					]:
				setattr(self, k, v)
			else:
				raise AttributeError('Invalid keyword argument', k)

		if self.info_menu and not callable(self.info_menu):
			raise AttributeError('callback for info_menu must be callable')
		debug("activate_on_single_click",self.activate_on_single_click)
		self.icon_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
		self.icon_view = Gtk.IconView(model=self.icon_store)
		self.icon_view.set_activate_on_single_click(self.activate_on_single_click)
		self.icon_view.set_pixbuf_column(0)
		self.icon_view.set_text_column(1)
		self.icon_view.connect("item-activated", self.on_icon_double_click)
		if self.activate_on_single_click:
			self.icon_view.connect("item-activated", self.on_icon_double_click)
		self.icon_view.connect("button-press-event", self.on_icon_button_press)

		# Apply CSS styling to control padding around icons
		self.css_provider = Gtk.CssProvider()
		self.css_provider.load_from_data(b".view .cell { padding: 2px; }")  # Adjust padding value as needed
		self.style_context = self.icon_view.get_style_context()
		self.style_context.add_provider(self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

		# Create a scrolled window to contain the icon view
		self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
		self.add(self.icon_view)
		self.create_icons()

		self.show_all()  # Ensure the window is shown initially

		# Connect button-press-event to scrolled window
		self.connect("button-press-event", self.on_scrolled_window_button_press)

	def rename_icon(self,old,new):
		if old in self.icon_dict:
			tmp = self.icon_dict[old]
			self.icon_dict[old] = None
			del self.icon_dict[old]
			self.icon_dict[new] = tmp

	def _get_icon_store_by_name(self,name):
		index = 0
		for row in self.icon_store:
			if row[1] == name:
				return index
			index += 1
		return False

	def _signal_row_change(self, index):
		tree_path = Gtk.TreePath.new_from_indices([index])
		iter = self.icon_store.get_iter(tree_path)
		self.icon_store.emit('row-changed',tree_path, iter)

	def activate_icon(self,name):
		index = self._get_icon_store_by_name(name)
		if type(index) is int:
			row = self.icon_store[index]
			active_icon = self.pixmap[name]['active']
			icon_name = self.pixmap[name]['icon_name']
			debug(f"""
			activating: {name}
			icon_name: {icon_name}
			setting active: {active_icon}
			active set: {self.pixmap[name]['active']}
			inactive set: {self.pixmap[name]['inactive']}
			""")
			row[0] = active_icon
			self._signal_row_change(index)
		else:
			debug('bad index',type(index),index)
	
	def deactivate_icon(self,name):
		index = self._get_icon_store_by_name(name)
		if type(index) is int:
			row = self.icon_store[index]
			inactive_icon = self.pixmap[name]['inactive']
			debug(name,row[1],row[0],inactive_icon)
			row[0] = inactive_icon
			self._signal_row_change(index)

	def update_icon(self,old_name, new_name, icon_name):
		if old_name in self.icon_dict:
			del self.icon_dict[old_name]
		self.icon_dict[new_name] = {'name': new_name, 'icon': icon_name}
		self.create_icons()
	
	def delete_icon(self,item):
		if item in self.icon_dict:
			del self.icon_dict[item]
			self.icon_store.clear()
			self.create_icons()
			debug("icon removed and list regenderated")
		else:
			debug(f"no {item} in {self.icon_dict}")

	def add_icon(self,icon,item):
		self.icon_dict[item] = {'name': item, 'icon': icon}
		self.create_icons()

	def create_icons(self):
		self.icon_store.clear()
		for key, value in self.icon_dict.items():
			iaipath = value['icon']
			aipath,ext = os.path.splitext(iaipath)
			aipath = f'{aipath}-active{ext}'
			#icon_pixbuf_active = GdkPixbuf.Pixbuf.new_from_file(aipath)
			#icon_pixbuf_inactive = GdkPixbuf.Pixbuf.new_from_file(value["icon"])
			(icon_pixbuf_inactive,icon_pixbuf_active) = \
				self.get_icon_image(value['icon'])
			self.pixmap[value['name']] = {
				"icon_name": value['icon'],
				"active": icon_pixbuf_active, 
				"inactive": icon_pixbuf_inactive}

			if self.active_windows and value['name'] in self.active_windows:
				pimage = icon_pixbuf_active
			else:
				pimage = icon_pixbuf_inactive
			if 'type' in value:
				self.icon_store.append([pimage, value["name"], value['type']])
			else:
				self.icon_store.append([pimage, value["name"], "icon"])
			self.sort_by_name()

	def on_icon_button_press(self, widget, event):
		if event.button == Gdk.BUTTON_SECONDARY:
			path = self.icon_view.get_path_at_pos(int(event.x), int(event.y))
			if path and self.icon_menu:
				debug(event.x,event.y)
				self.selected_x = event.x
				self.selected_y = event.y
				path = self.icon_view.get_path_at_pos(event.x,event.y)
				if path:
					self.icon_view.select_path(path)
				menu = self.create_icon_context_menu(path)
				menu.show_all()
				menu.popup(None, None, None, None, event.button, event.time)
				return True
		return False

	def _xsort_menu(self):
		sort_item = Gtk.MenuItem(label="Sort By")
		sort_submenu = Gtk.Menu()
		sort_name_item = Gtk.MenuItem(label="Name")
		sort_type_item = Gtk.MenuItem(label="Type")
		sort_item.set_submenu(sort_submenu)
		sort_submenu.append(sort_name_item)
		sort_submenu.append(sort_type_item)

		return sort_item, sort_submenu

	def _sort_menu(self):
		sort_item = Gtk.MenuItem(label="Sort By")
		sort_submenu = Gtk.Menu()
		sort_item.set_submenu(sort_submenu)

		sort_name_item = Gtk.MenuItem(label="Name")
		sort_type_item = Gtk.MenuItem(label="Type")
		sort_submenu.append(sort_name_item)
		sort_submenu.append(sort_type_item)

		sort_name_item.connect("activate", self.sort_by_name)
		sort_type_item.connect("activate", self.sort_by_type)

		return sort_item, sort_submenu

	def create_scrolled_window_context_menu(self):
		menu = Gtk.Menu()
		sort_item, sort_submenu = self._sort_menu()

		add_item = Gtk.MenuItem(label="New Sensor")
		add_item.connect('activate', self.add_item_activate)
		menu.append(add_item)
		menu.append(sort_item)

		sort_dir_item = Gtk.MenuItem('Sort Direction')
		sort_dir_submenu = Gtk.Menu()
		sort_dir_asc_item = Gtk.MenuItem(label="Ascending")
		sort_dir_dsc_item = Gtk.MenuItem(label="Descending")
		sort_dir_item.set_submenu(sort_dir_submenu)
		sort_dir_submenu.append(sort_dir_asc_item)
		sort_dir_submenu.append(sort_dir_dsc_item)
		sort_dir_asc_item.connect("activate", self._set_sort_dir, Gtk.SortType.ASCENDING)
		sort_dir_dsc_item.connect("activate", self._set_sort_dir, Gtk.SortType.DESCENDING)
		menu.append(sort_dir_item)

		return menu

	def xcreate_scrolled_window_context_menu(self):
		menu = Gtk.Menu()
		sort_item, sort_submenu = self._sort_menu()

		add_item = Gtk.MenuItem(label="New Sensor")
		add_item.connect('activate', self.add_item_activate)
		menu.append(add_item)
		menu.append(sort_item)

		sort_dir_item = Gtk.MenuItem('Sort Direction')
		sort_dir_submenu = Gtk.Menu()
		sort_dir_asc_item = Gtk.MenuItem(label="Ascending")
		sort_dir_dsc_item = Gtk.MenuItem(label="Descending")
		sort_dir_item.set_submenu(sort_dir_submenu)
		sort_dir_submenu.append(sort_dir_asc_item)
		sort_dir_submenu.append(sort_dir_dsc_item)
		sort_dir_asc_item.connect("activate", self._set_sort_dir, Gtk.SortType.ASCENDING)
		sort_dir_dsc_item.connect("activate", self._set_sort_dir, Gtk.SortType.DESCENDING)
		menu.append(sort_dir_item)

		return menu

	def create_icon_context_menu(self, path):
		item = path[0]
		name = self.icon_store[item][1]
		detail_text = "Open Detail Window"
		show_item = None
		if name in self.config['sensors']:
			if self.config['sensors'][name]['active']:
				detail_text = "Close detail window"
				show_item = Gtk.MenuItem(label="Show")
				show_item.connect('activate',self.on_menu_show,path)

		menu = Gtk.Menu()
		edit_item = Gtk.MenuItem(label="Edit")
		remove_item = Gtk.MenuItem(label="Remove")
		edit_item.connect("activate", self.on_icon_edit_activate, path)
		remove_item.connect("activate", self.on_icon_remove_activate, path)

		detail_item = Gtk.MenuItem(detail_text)
		detail_item.connect('activate',self.on_icon_detail_activate, path)
		sort_item, sort_submenu = self._sort_menu()
		if show_item:
			menu.append(show_item)
		menu.append(detail_item)
		menu.append(edit_item)
		menu.append(remove_item)
		if self.info_menu:
			info_item = Gtk.MenuItem(label="Get Info")
			info_item.connect('activate',self.on_info_item_activate, path)
			menu.append(info_item)

		menu.append(sort_item)

		sort_dir_item = Gtk.MenuItem('Sort Direction')
		sort_dir_submenu = Gtk.Menu()
		sort_dir_asc_item = Gtk.MenuItem(label="Ascending")
		sort_dir_dsc_item = Gtk.MenuItem(label="Descending")
		sort_dir_item.set_submenu(sort_dir_submenu)
		sort_dir_submenu.append(sort_dir_asc_item)
		sort_dir_submenu.append(sort_dir_dsc_item)
		sort_dir_asc_item.connect("activate", self._set_sort_dir, Gtk.SortType.ASCENDING)
		sort_dir_dsc_item.connect("activate", self._set_sort_dir, Gtk.SortType.DESCENDING)
		menu.append(sort_dir_item)


		return menu

	def on_menu_detail(self,widget,path):
		item = path[0]
		name = self.icon_store[item][1]

	
	def on_info_item_activate(self, widget, path):
		if not self.info_menu:
			return
		if not callable(self.info_menu):
			raise AttributeError('info_menu is not callable')
		item = path[0]
		name = self.icon_store[item][1]
		self.info_menu(name)

	def on_menu_show(self,widget,path):
		item = path[0]
		name = self.icon_store[item][1]
		if callable(self.menu_callback):
			self.menu_callback('show', name)

	def on_icon_edit_activate(self, widget, path):
		# Retrieve the selected item and perform edit action
		item = path[0]
		name = self.icon_store[item][1]
		if callable(self.menu_callback):
			self.menu_callback('edit', name)

	def on_icon_detail_activate(self, widget, path):
		# Retrieve the selected item and perform edit action
		item = path[0]
		name = self.icon_store[item][1]
		if callable(self.menu_callback):
			self.menu_callback('detail', name)


	def on_icon_remove_activate(self, widget, path):
		# Retrieve the selected item and perform remove action
		item = path[0]
		name = self.icon_store[item][1]
		if callable(self.menu_callback):
			self.menu_callback('remove', name)

	def on_scrolled_window_button_press(self, widget, event):
		if event.button == Gdk.BUTTON_SECONDARY:
			if self.context_menu:
				menu = self.create_scrolled_window_context_menu()
				menu.show_all()
				menu.popup(None, None, None, None, event.button, event.time)
			return True
		return False

	def _set_sort_dir(self,widget,direction):
		d = f'unexpected({direction})'
		if direction == Gtk.SortType.ASCENDING:
			d = 'Ascending'
		elif direction == Gtk.SortType.DESCENDING:
			d = 'Descending'
		debug("direction",d)
		self.sort_dir = direction
		self.icon_store.set_sort_column_id(self.sort_column, self.sort_dir)

	def add_item_activate(self, widget, *args):
		if callable(self.add_item_callback):
			self.add_item_callback()
	
	def sort_by_name(self, *args):
		debug()
		self.sort_column = 1
		#self.icon_store.set_sort_func(1, self._name_sort_func)
		self.icon_store.set_sort_column_id(1, self.sort_dir)

	def sort_by_type(self, *args):
		debug()
		self.sort_column = 2
		# Example sorting by type if available in icon_dict
		#self.icon_store.set_sort_func(1, self._type_sort_func)
		self.icon_store.set_sort_column_id(2,  self.sort_dir)


	def on_icon_double_click(self, icon_view, path):
		name = self.icon_store[path][1]
		self.activate_icon(name)
		debug(name)
		if callable(self.activate_callback):
			self.activate_callback(name)

	def get_icon_image(self,image1_path):
		'''
		Create a suitable icon from a file for both regular and acive by 
		applying an image with the active badge to the source. Return both GdkPixbufs
		'''
		# Load images
		image2_path = os.path.join(os.path.dirname(image1_path),"active_badge.png")
		image1 = GdkPixbuf.Pixbuf.new_from_file(image1_path)
		image2 = GdkPixbuf.Pixbuf.new_from_file(image2_path)

		# Scale image1 to the desired dimensions
		scaled_image1 = image1.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)

		# Create a new transparent image to composite onto
		composite_image = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 64, 64)
		composite_image.fill(0x000000)  # Fill with black

		# Draw scaled_image1 onto the composite image
		scaled_image1.copy_area(0, 0, 64, 64, composite_image, 0, 0)

		# Calculate position to center image2 on composite_image
		x_offset = (64 - image2.get_width()) // 2
		y_offset = (64 - image2.get_height()) // 2

		# Draw image2 onto the composite image
		image2.composite(
			composite_image,
			x_offset,
			y_offset,
			image2.get_width(),
			image2.get_height(),
			x_offset,
			y_offset,
			1,
			1,
			GdkPixbuf.InterpType.BILINEAR,
			255,
		)
		return (scaled_image1, composite_image)

