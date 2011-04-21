#!/usr/bin/env python

import gtk
import gui
import re
import os
import sys
import layout

class View (gtk.DrawingArea):
	def __init__ (self):
		self.screen = (0,0)
		self.selection = {}
		self.selecting = False
		self.slot = 0
		self.lastslot = 0
		gtk.DrawingArea.__init__ (self)
		self.set_can_focus (True)
		self.set_size_request (2 * 50 * 12 + 20, 2 * 50 * 8 + 20)
		self.connect_after ('realize', self.start)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.add_events (gtk.gdk.KEY_PRESS_MASK)
		self.add_events (gtk.gdk.BUTTON_PRESS_MASK)
		self.add_events (gtk.gdk.BUTTON_RELEASE_MASK)
		self.add_events (gtk.gdk.BUTTON_MOTION_MASK)
	def start (self, widget):
		tiledir = '/usr/share/games/dink/dink/Tiles'
		bmps = [None] * 41
		# TODO: use local tile overrides.
		for f in os.listdir (tiledir):
			r = re.match ('ts(\d\d).bmp', f.lower ())
			if r == None:
				continue
			n = int (r.group (1))
			assert n > 0 and n <= 41
			bmps[n - 1] = f
		assert None not in bmps
		self.bmp = [None] * 41
		self.realize ()
		self.gc = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color ('black')
		self.gc.set_foreground (c)
		self.gc.set_line_attributes (3, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		self.lastgc = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color ('green')
		self.lastgc.set_foreground (c)
		self.lastgc.set_line_attributes (3, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		self.currentgc = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color ('red')
		self.currentgc.set_foreground (c)
		self.currentgc.set_line_attributes (3, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		self.invalidgc = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color ('magenta')
		self.invalidgc.set_foreground (c)
		for i in range (41):
			pb = gtk.gdk.pixbuf_new_from_file (os.path.join (tiledir, bmps[i]))
			self.bmp[i] = gtk.gdk.Pixmap (self.get_window (), pb.get_width (), pb.get_height ())
			self.bmp[i].draw_pixbuf (self.gc, pb, 0, 0, 0, 0)
	def set_screen (self, s):
		if type (self.screen) != int and type (s) == int:
			self.old_screen = self.screen
		self.screen = s
		self.update ()
	def put_tile (self, x, y, sx = 0, sy = 0):
		n = (self.screen[1] + sy) * 32 + self.screen[0] + sx + 1
		tx = sx * (50 * 12 + 10) + x * 50 + 6 * 50 + 10
		ty = sy * (50 * 8 + 10) + y * 50 + 4 * 50 + 10
		if n in data.world.room:
			b = data.world.room[n].tiles[y][x]
			self.get_window ().draw_drawable (self.gc, self.bmp[b[0]], b[1] * 50, b[2] * 50, tx, ty, 50, 50)
		else:
			self.get_window ().draw_rectangle (self.invalidgc, True, tx, ty, 50, 50)
	def update (self):
		if not self.get_window ():
			return
		self.get_window ().clear ()
		if type (self.screen) == int:
			for sy in range (2):
				for sx in range (2):
					bmp = self.screen * 4 + sy * 2 + sx
					if bmp >= 41:
						break
					self.get_window ().draw_drawable (self.gc, self.bmp[bmp], 0, 0, sx * (12 * 50 + 20), sy * (8 * 50 + 20), 12 * 50, 8 * 50)
		else:
			for sy in range (-1,2):
				if self.screen[1] + sy < 0 or self.screen[1] + sy >= 24:
					self.get_window ().clear_area (0, sy * (50 * 8 + 10) + 4 * 50 + 10, 2 * 12 * 50 + 20, 8 * 50 + 10)
					continue
				for sx in range (-1,2):
					if self.screen[0] + sx < 0 or self.screen[0] + sx >= 32:
						self.get_window ().clear_area (sx * (50 * 12 + 10) + 6 * 50 + 10, sy * (50 * 8 + 10) + 4 * 50 + 10, 12 * 50 + 10, 8 * 50 + 10)
						continue
					for y in range (8):
						if (sy < 0 and y < 4) or (sy > 0 and y >= 4):
							continue
						for x in range (12):
							if (sx < 0 and x < 6) or (sx > 0 and x >= 6):
								continue
							self.put_tile (x, y, sx, sy)
		self.draw_cursors ()
	def normalize (self, s):
		s = s[:]
		if s[0] > s[2]:
			t = s[0]
			s[0] = s[2]
			s[2] = t
		if s[1] > s[3]:
			t = s[1]
			s[1] = s[3]
			s[3] = t
		return s
	def put_cursor (self, slot, gc):
		assert slot in self.selection
		s = self.selection[slot][:]
		if s[4] != self.screen:
			return
		s = self.normalize (s)
		if type (s[4]) == int:
			if s[0] >= 12:
				ox1 = 20
			else:
				ox1 = 0
			if s[2] >= 12:
				ox2 = 20
			else:
				ox2 = 0
			if s[1] >= 8:
				oy1 = 20
			else:
				oy1 = 0
			if s[3] >= 8:
				oy2 = 20
			else:
				oy2 = 0
			self.get_window ().draw_rectangle (gc, False, ox1 + s[0] * 50 + 1, oy1 + s[1] * 50 + 1, ox2 - ox1 + (s[2] - s[0] + 1) * 50 - 3, oy2 - oy1 + (s[3] - s[1] + 1) * 50 - 3)
		else:
			self.get_window ().draw_rectangle (gc, False, 6 * 50 + 10 + s[0] * 50 + 1, 4 * 50 + 10 + s[1] * 50 + 1, (s[2] - s[0] + 1) * 50 - 3, (s[3] - s[1] + 1) * 50 - 3)
	def draw_cursors (self):
		for i in self.selection:
			if i == self.slot or i == self.lastslot:
				continue
			self.put_cursor (i, self.gc)
		if self.lastslot in self.selection:
			self.put_cursor (self.lastslot, self.lastgc)
		if self.slot in self.selection:
			self.put_cursor (self.slot, self.currentgc)
	def remove_cursor (self, slot):
		if slot not in self.selection:
			return
		s = self.selection[slot]
		del self.selection[slot]
		if s[4] != self.screen:
			return
		if type (s[4]) == int:
			self.update ()
			return
		if s[0] < s[2]:
			x = s[0], s[2]
		else:
			x = s[2], s[0]
		if s[1] < s[3]:
			y = s[1], s[3]
		else:
			y = s[3], s[1]
		for tx in range (x[0], x[1] + 1):
			self.put_tile (tx, y[0])
			self.put_tile (tx, y[1])
		for ty in range (y[0] + 1, y[1]):
			self.put_tile (x[0], ty)
			self.put_tile (x[1], ty)
		self.draw_cursors ()
	def expose (self, widget, e):
		self.update ()
	def keypress (self, widget, e):
		self.selecting = False
		if e.keyval == ord ('`') or (e.keyval >= ord ('0') and e.keyval <= ord ('9')):
			if e.keyval == ord ('`'):
				self.set_screen (10)
			else:
				self.set_screen (e.keyval - ord ('0'))
		elif e.keyval == 65307 and type (self.screen) == int:
			self.set_screen (self.old_screen)
		elif e.state & gtk.gdk.CONTROL_MASK:
			if e.keyval == ord ('c'):	# copy TODO
				print 'ctrl-c is not implemented yet'
			elif e.keyval == ord ('v'):	# paste TODO
				print 'ctrl-v is not implemented yet'
			elif e.keyval == ord ('s'):	# save TODO
				print 'ctrl-s is not implemented yet'
			elif e.keyval == ord ('S'):	# save as TODO
				print 'ctrl-shift-s is not implemented yet'
			elif e.keyval == ord ('q'):	# quit
				gui.quit ()
			elif e.keyval == ord ('a'):	# select all
				if type (self.screen) != int:
					if self.slot in self.selection:
						self.remove_cursor (self.slot)
					self.selection[self.slot] = [0, 0, 11, 7, self.screen]
					self.put_cursor (self.slot, self.currentgc)
			elif e.keyval == ord ('A'):	# unselect all
				if self.slot in self.selection:
					self.remove_cursor (self.slot)
		elif e.keyval >= ord ('a') and e.keyval <= ord ('z'):
			slot = e.keyval - ord ('a')
			if slot != self.slot:
				self.lastslot = self.slot
				self.slot = slot
				self.draw_cursors ()
	def button_on (self, widget, e):
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 1:
			if type (self.screen) != int and (e.x < 6 * 50 + 10 or e.x >= 18 * 50 + 20 or e.y < 4 * 50 + 10 or e.y >= 12 * 50 + 20):
				# Select a new screen.
				if e.x < 6 * 50 + 10 and self.screen[0] > 0:
					nx = self.screen[0] - 1
				elif e.x >= 18 * 50 + 20 and self.screen[0] < 31:
					nx = self.screen[0] + 1
				else:
					nx = self.screen[0]
				if e.y < 4 * 50 + 10 and self.screen[1] > 0:
					ny = self.screen[1] - 1
				elif e.y >= 12 * 50 + 20 and self.screen[1] < 23:
					ny = self.screen[1] + 1
				else:
					ny = self.screen[1]
				self.set_screen ((nx, ny))
				return
			x, y = self.pos_from_event (e)
			if self.slot in self.selection:
				self.remove_cursor (self.slot)
			self.selection[self.slot] = [x, y, x, y, self.screen]
			self.put_cursor (self.slot, self.currentgc)
			self.selecting = True
		elif e.button == 2:	# paste current selection to position.
			if type (self.screen) == int:
				return
			if self.slot not in self.selection:
				return
			s = self.normalize (self.selection[self.slot])
			x, y = self.pos_from_event (e)
			n = self.screen[1] * 32 + self.screen[0] + 1
			if n not in data.world.room:
				return
			for ty in range (s[3] - s[1] + 1):
				if y + ty >= 8:
					break
				for tx in range (s[2] - s[0] + 1):
					if x + tx >= 12:
						break
					if type (s[4]) == int:
						k = 0
						if s[0] >= 12:
							sx = s[0] - 12
							k += 1
						else:
							sx = s[0]
						if s[1] >= 8:
							sy = s[1] - 8
							k += 2
						else:
							sy = s[1]
						data.world.room[n].tiles[y + ty][x + tx] = [4 * s[4] + k, sx + tx, sy + ty]
						self.put_tile (x + tx, y + ty)
					else:
						sn = s[4][1] * 32 + s[4][0] + 1
						if sn in data.world.room:
							data.world.room[n].tiles[y + ty][x + tx] = data.world.room[sn].tiles[s[1] + ty][s[0] + tx]
							self.put_tile (x + tx, y + ty)
		elif e.button == 3:	# paste previous selection into current selection.
			if type (self.screen) == int:
				return
			# TODO
	def button_off (self, widget, e):
		if e.button == 1:
			self.selecting = False
			if type (self.screen) == int:
				self.set_screen (self.old_screen)
	def move (self, widget, e):
		if not self.selecting:
			return
		x, y = self.pos_from_event (e)
		c = self.selection[self.slot]
		if c[2:4] == [x, y]:
			return
		self.remove_cursor (self.slot)
		c[2:4] = [x, y]
		self.selection[self.slot] = c
		self.put_cursor (self.slot, self.currentgc)
	def pos_from_event (self, e):
		if type (self.screen) == int:
			if e.x >= 12 * 50:
				e.x -= 20
			if e.y >= 8 * 50:
				e.y -= 20
			x = int (e.x / 50)
			y = int (e.y / 50)
			if x >= 24:
				x = 23
			if y >= 16:
				y = 15
		else:
			x = int ((e.x - (6 * 50 + 10)) / 50)
			y = int ((e.y - (4 * 50 + 10)) / 50)
			if x >= 12:
				x = 11
			if y >= 8:
				y = 7
		if x < 0:
			x = 0
		if y < 0:
			y = 0
		return x, y

root = sys.argv[1]
data = layout.Dink (root)
gui.gui (external = {'view': View ()}) ()
