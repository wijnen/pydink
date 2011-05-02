#!/usr/bin/env python

import gtk
import gui
import re
import os
import sys
import dink
import StringIO
import math
import random

class Select:
	def __init__ (self):
		self.start = (0, 0, 0)
		self.data = set ()
	def clear (self):
		self.data.clear ()
	def toggle (self, pos, type):
		p = (pos[0], pos[1], type)
		if p in self.data:
			self.data.remove (p)
		else:
			self.data.add (p)
	def empty (self):
		return len (self.data) == 0
	def compute (self):
		return [[x[t] - self.start[t] for t in range (2)] for x in self.data if x[2] == self.start[2]]

class View (gtk.DrawingArea):
	def __init__ (self):
		self.started = False
		self.buffer = None
		self.copybuffer = set ()
		self.copystart = (0, 0, 0)
		self.roomsource = None
		self.show_hard = False
		self.show_sprites = False
		self.button_pos = (0, 0)
		self.pointer_tile = (0, 0)
		self.select = Select ()
		self.selecting = False
		self.panning = False
		self.type = 0
		self.edittype = 0
		self.offset = [(0, 0), (0, 0), (0, 0), (0, 0)]
		self.screensize = (50 * 12, 50 * 8)
		self.tiles = ((12 * 32, 8 * 24), (12 * 6, 8 * 7))
		gtk.DrawingArea.__init__ (self)
		self.set_can_focus (True)
		self.set_size_request (2 * 50 * 12, 2 * 50 * 8)
		self.connect_after ('realize', self.start)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('key-release-event', self.keyrelease)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('configure-event', self.configure)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
	def configure (self, widget, e):
		x, y, width, height = widget.get_allocation()
		self.screensize = (width, height)
		self.buffer = gtk.gdk.Pixmap (self.get_window (), width, height)
		if self.started:
			self.move (None, None)
	def make_gc (self, color):
		ret = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color (color)
		ret.set_foreground (c)
		ret.set_line_attributes (1, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		return ret
	def image2pixbuf (self, im):
		file1 = StringIO.StringIO ()
		im.save (file1, "png")
		contents = file1.getvalue ()
		file1.close ()
		loader = gtk.gdk.PixbufLoader ("png")
		loader.write (contents, len (contents))
		pixbuf = loader.get_pixbuf ()
		loader.close()
		return pixbuf
	def start (self, widget):
		self.realize ()
		self.gc = self.make_gc ('black')
		self.gridgc = self.make_gc ('gray')
		self.bordergc = self.make_gc ('red')
		self.invalidgc = self.make_gc ('magenta')
		self.selectgc = self.make_gc ('white')
		self.hotspotgc = self.make_gc ('yellow')
		self.pastegc = self.make_gc ('cyan')
		self.emptygc = self.make_gc ('#eee')
		self.bmp = [None] * 41
		self.hard = [None] * 41
		for i in range (41):
			size = data.tile.tile[i][0].size
			pb = gtk.gdk.pixbuf_new_from_data (data.tile.tile[i][0].tostring (), gtk.gdk.COLORSPACE_RGB, False, 8, size[0], size[1], size[0] * 3)
			self.bmp[i] = gtk.gdk.Pixmap (self.get_window (), pb.get_width (), pb.get_height ())
			self.bmp[i].draw_pixbuf (self.gc, pb, 0, 0, 0, 0)
			self.hard[i] = self.image2pixbuf (data.tile.tile[i][1])
		self.move (None, None)
		self.started = True
		self.update ()
	def find_tile (self, worldpos, type = None):
		if type == None:
			type = self.type
		if type == 0:	# normal view.
			n = (worldpos[1] / 8) * 32 + (worldpos[0] / 12) + 1
			if n in data.world.room:
				return data.world.room[n].tiles[worldpos[1] % 8][worldpos[0] % 12]
		else:		# tile screen view.
			if worldpos[0] >= 0 and worldpos[0] < 6 * 12 and worldpos[1] >= 0 and worldpos[1] < 7 * 8:
				n = (worldpos[1] / 8) * 6 + worldpos[0] / 12
				if n < 41:
					return [n, worldpos[0] % 12, worldpos[1] % 8]
		return [-1, -1, -1]
	def put_tile (self, screenpos, worldpos):
		b = self.find_tile (worldpos)
		if b[0] >= 0:
			w, h = self.bmp[b[0]].get_size ()
			if b[1] * 50 >= w or b[2] * 50 >= h:
				self.buffer.draw_rectangle (self.invalidgc, True, screenpos[0] + 1, screenpos[1] + 1, 49, 49)
			else:
				self.buffer.draw_drawable (self.gc, self.bmp[b[0]], b[1] * 50, b[2] * 50, screenpos[0], screenpos[1], 50, 50)
				if (self.show_hard and not the_gui.show_hard) or (not self.show_hard and the_gui.show_hard):
					self.buffer.draw_pixbuf (self.gc, self.hard[b[0]], b[1] * 50, b[2] * 50, screenpos[0], screenpos[1], 50, 50)
			if self.edittype == 0:
				if worldpos[1] % 8 != 0:
					self.buffer.draw_line (self.gridgc, screenpos[0], screenpos[1], screenpos[0] + 49, screenpos[1])
				if worldpos[0] % 12 != 0:
					self.buffer.draw_line (self.gridgc, screenpos[0], screenpos[1] + 1, screenpos[0], screenpos[1] + 49)
		else:
			self.buffer.draw_rectangle (self.invalidgc, True, screenpos[0], screenpos[1], 50, 50)
		if worldpos[1] % 8 == 0:
			self.buffer.draw_line (self.bordergc, screenpos[0], screenpos[1], screenpos[0] + 49, screenpos[1])
		if worldpos[0] % 12 == 0:
			self.buffer.draw_line (self.bordergc, screenpos[0], screenpos[1] + 1, screenpos[0], screenpos[1] + 49)
		if self.edittype == 0:
			if self.type == 0 and not self.selecting:
				if (worldpos[0] - self.pointer_tile[0] + self.select.start[0], worldpos[1] - self.pointer_tile[1] + self.select.start[1], self.select.start[2]) in self.select.data:
					self.buffer.draw_rectangle (self.pastegc, False, screenpos[0] + 1, screenpos[1] + 1, 48, 48)
					return
			check = (worldpos[0], worldpos[1], self.type)
			if check in self.select.data:
				if check == self.select.start:
					self.buffer.draw_rectangle (self.hotspotgc, False, screenpos[0] + 1, screenpos[1] + 1, 48, 48)
				else:
					self.buffer.draw_rectangle (self.selectgc, False, screenpos[0] + 1, screenpos[1] + 1, 48, 48)
	def update (self, dummy = None):
		if self.buffer == None:
			return
		self.grab ()
		if self.type == 0 or self.type == 1:	# normal view or tile screen view.
			origin = [x / 50 for x in self.offset[self.type]]
			offset = [x % 50 for x in self.offset[self.type]]
			screens = set ()
			for y in range ((self.screensize[1] + offset[1] + 49) / 50):
				for x in range ((self.screensize[0] + offset[0] + 49) / 50):
					screens.add (y * 32 + x + 1)
					# and screens around it, for sprites which stick out.
					screens.add (y * 32 + x + 1 + 1)
					screens.add (y * 32 + x + 1 - 1)
					screens.add (y * 32 + x + 1 + 32)
					screens.add (y * 32 + x + 1 - 32)
					screens.add (y * 32 + x + 1 + 1 + 32)
					screens.add (y * 32 + x + 1 + 1 - 32)
					screens.add (y * 32 + x + 1 - 1 + 32)
					screens.add (y * 32 + x + 1 - 1 - 32)
					if (origin[0] + x < 0 or origin[0] + x >= self.tiles[self.type][0]) or (origin[1] + y < 0 or origin[1] + y >= self.tiles[self.type][1]):
						self.buffer.draw_rectangle (self.emptygc, True, x * 50 - offset[0], y * 50 - offset[1], 50, 50)
						continue
					self.put_tile ((x * 50 - offset[0], y * 50 - offset[1]), (origin[0] + x, origin[1] + y))
			if self.type == 0 and ((the_gui.show_sprites and not self.show_sprites) or (not the_gui.show_sprites and self.show_sprites)):
				l = []
				for s in screens:
					# draw sprites.
					if s not in data.world.room:
						continue
					sy = ((s - 1) / 32) * 50 * 8
					sx = ((s - 1) % 32) * 50 * 12
					for spr in data.world.room[s].sprite:
						sp = data.world.room[s].sprite[spr]
						pos = (sx + sp.x - self.offset[0][0], sy + sp.y - self.offset[0][1])
						seq = data.seq.find_seq (sp.seq)
						l += ((pos, sp.que, seq, sp.size, sp.type,),)
				l.sort (key = lambda (x): x[1] - x[0][1])
				for s in l:
					# TODO
					self.buffer.draw_line (self.selectgc, s[0][0] - 10, s[0][1], s[0][0] + 10, s[0][1])
					self.buffer.draw_line (self.selectgc, s[0][0], s[0][1] - 10, s[0][0], s[0][1] + 10)
		elif self.type == 2:	# sequence view.
			pass	# TODO
		elif self.type == 3:	# world view.
			s = (32, 24)
			scrsize = (12, 8)
			tsize = [self.screensize[x] / s[x] for x in range (2)]
			off = [(self.screensize[x] - s[x] * tsize[x]) / 2 for x in range (2)]
			self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
			for y in range (s[1]):
				self.buffer.draw_line (self.bordergc, off[0], off[1] + y * tsize[1], off[0] + s[0] * tsize[0] - 1, off[1] + y * tsize[1])
				for x in range (s[0]):
					self.buffer.draw_line (self.bordergc, off[0] + x * tsize[0], off[1], off[0] + x * tsize[0], off[1] + s[1] * tsize[1] - 1)
					n = y * 32 + x + 1
					if n in data.world.room:
						self.buffer.draw_rectangle (self.hotspotgc, True, off[0] + tsize[0] * x + 1, off[1] + tsize[1] * y + 1, tsize[0] - 1, tsize[1] - 1)
					else:
						self.buffer.draw_rectangle (self.invalidgc, True, off[0] + tsize[0] * x + 1, off[1] + tsize[1] * y + 1, tsize[0] - 1, tsize[1] - 1)
			self.buffer.draw_line (self.bordergc, off[0], off[1] + s[1] * tsize[1], off[0] + s[0] * tsize[0] - 1, off[1] + s[1] * tsize[1])
			self.buffer.draw_line (self.bordergc, off[0] + s[0] * tsize[0], off[1], off[0] + s[0] * tsize[0], off[1] + s[1] * tsize[1] - 1)
			targetsize = [(self.screensize[x] / (50 * scrsize[x])) * tsize[x] for x in range (2)]
			self.buffer.draw_rectangle (self.selectgc, False, self.button_pos[0] - targetsize[0] / 2, self.button_pos[1] - targetsize[1] / 2, targetsize[0] - 1, targetsize[1] - 1)
		else:
			raise AssertionError ('unknown view type')
		self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def expose (self, widget, e):
		self.get_window ().draw_drawable (self.gc, self.buffer, e.area[0], e.area[1], e.area[0], e.area[1], e.area[2], e.area[3])
	def keypress (self, widget, e):
		self.selecting = False
		if e.keyval == gtk.keysyms.Control_L:
			self.show_hard = True
		elif e.keyval == gtk.keysyms.Alt_L:
			self.show_sprites = True
		elif e.keyval == gtk.keysyms.t:	# tile
			if self.edittype != 0:
				self.edittype = 0
				self.type = 0
			else:
				if self.type == 0:
					self.type = 1
				else:
					self.type = 0
		elif e.keyval == gtk.keysyms.s:	# sequence
			if self.edittype != 1:
				self.edittype = 1
				self.type = 0
			else:
				if self.type == 0:
					self.type = 2
				else:
					self.type = 0
		elif e.keyval == gtk.keysyms.w:	# world
			self.type = 3
		elif e.keyval == gtk.keysyms.p:	# play
			p = [self.button_pos[x] + self.offset[0][x] for x in range (2)]
			n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
			data.play (n, p[0] % (12 * 50), p[1] % (8 * 50))
		elif e.keyval == gtk.keysyms.k:	# save (keep)
			data.save ()
		elif e.keyval == gtk.keysyms.q:	# quit (and save)
			data.save ()
			gui.quit ()
			return
		elif e.keyval == gtk.keysyms.x:	# exit (without saving)
			gui.quit ()
			return
		else:
			if self.type != 3 and self.edittype == 0:
				# editing tiles.
				if e.keyval == gtk.keysyms.c:	# copy
					self.copybuffer.clear ()
					for i in self.select.data:
						s = self.find_tile (i, i[2])
						self.copybuffer.add ((i[0], i[1], i[2], s[0], s[1], s[2]))
					self.copystart = self.select.start
					return
				elif e.keyval == gtk.keysyms.f:	# fill
					tiles = list (self.copybuffer)
					min = [None, None]
					max = [None, None]
					for i in self.copybuffer:
						if i[2] != self.copystart[2]:
							continue
						for x in range (2):
							if min[x] == None or i[x] < min[x]:
								min[x] = i[x]
							if max[x] == None or i[x] > max[x]:
								max[x] = i[x]
					for i in self.select.data:
						# Don't try to paste into tile screens.
						if i[2] != 0:
							continue
						n = (i[1] / 8) * 32 + (i[0] / 12) + 1
						if n not in data.world.room:
							continue
						tile = None
						if min[0] != None:
							size = [max[x] - min[x] + 1 for x in range (2)]
							p = [(i[x] - self.select.start[x] + self.copystart[x]) % size[x] for x in range (2)]
							for b in self.copybuffer:
								if b[2] == self.copystart[2] and (b[0] - self.copystart[0]) % size[0] == p[0] and (b[1] - self.copystart[1]) % size[1] == p[1]:
									tile = b[3:6]
						if tile == None:
							tile = tiles[random.randrange (len (self.copybuffer))][3:6]
						data.world.room[n].tiles[i[1] % 8][i[0] % 12] = tile
				elif e.keyval == gtk.keysyms.r:	# random
					tiles = list (self.copybuffer)
					for i in self.select.data:
						# Don't try to paste into tile screens.
						if i[2] != 0:
							continue
						n = (i[1] / 8) * 32 + (i[0] / 12) + 1
						if n not in data.world.room:
							continue
						tile = tiles[random.randrange (len (self.copybuffer))][3:6]
						data.world.room[n].tiles[i[1] % 8][i[0] % 12] = tile
				elif e.keyval == gtk.keysyms.Insert:	# create screen
					p = [self.button_pos[x] + self.offset[0][x] for x in range (2)]
					n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
					if n in data.world.room:
						self.roomsource = n
					else:
						data.world.room[n] = dink.Room (data)
						if self.roomsource in data.world.room:
							for y in range (8):
								for x in range (12):
									data.world.room[n].tiles[y][x] = data.world.room[self.roomsource].tiles[y][x]
						self.update ()
				elif e.keyval == gtk.keysyms.Delete:	# delete screen
					p = [self.button_pos[x] + self.offset[0][x] for x in range (2)]
					n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
					if n in data.world.room:
						del data.world.room[n]
						self.update ()
				else:
					return
		self.update ()
	def keyrelease (self, widget, e):
		if e.keyval == gtk.keysyms.Control_L:
			self.show_hard = False
			self.update ()
		elif e.keyval == gtk.keysyms.Alt_L:
			self.show_sprites = False
			self.update ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.button_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.button_pos[x] + self.offset[self.type][x]) / 50 for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if self.type == 3:
			# map view. different from others.
			if e.button == 1:
				s = (32, 24)
				scrsize = (12, 8)
				tsize = [self.screensize[x] / s[x] for x in range (2)]
				off = [(self.screensize[x] - s[x] * tsize[x]) / 2 for x in range (2)]
				self.offset[0] = [(self.button_pos[x] - off[x]) * 50 * scrsize[x] / tsize[x] - self.screensize[x] / 2 for x in range (2)]
				self.type = 0
				self.update ()
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		if self.edittype == 0:
			# tile editing.
			if e.button == 1:	# select.
				x, y = self.pos_from_event ((e.x, e.y))
				if not e.state & gtk.gdk.CONTROL_MASK:
					self.select.clear ()
				self.selecting = True
				self.select.start = (x, y, self.type)
				self.select.toggle ((x, y), self.type)
				self.update ()
			elif e.button == 2:	# paste.
				if self.type != 0:	# normal view
					return
				if self.select.empty ():
					return
				pos = self.pos_from_event ((e.x, e.y))
				for t in self.select.compute ():
					target = [pos[x] + t[x] for x in range (2)]
					n = (target[1] / 8) * 32 + (target[0] / 12) + 1
					if n not in data.world.room:
						continue
					data.world.room[n].tiles[target[1] % 8][target[0] % 12] = self.get_tile (t)
				self.update ()
		else:
			# sequence editing.
			if e.button == 1:	# select.
				x, y = [(self.offset[self.type][x] + int (e[x])) for x in range (2)]
				# TODO
			elif e.button == 2:	# paste.
				pass	# TODO
	def get_tile (self, t):
		pos = [t[x] + self.select.start[x] for x in range (2)]
		return self.find_tile (pos, self.select.start[2])
	def button_off (self, widget, e):
		if e.button == 1:
			self.selecting = False
		elif e.button == 3:
			self.panning = False
		self.update ()
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		pos = int (ex), int (ey)
		tile = self.pointer_tile
		diff = [pos[x] - self.button_pos[x] for x in range (2)]
		self.button_pos = pos
		self.pointer_tile = [(self.button_pos[x] + self.offset[self.type][x]) / 50 for x in range (2)]
		if self.type == 3:
			# map view: differemnt from others.
			self.update ()
			return
		if self.panning:
			self.offset[self.type] = [self.offset[self.type][x] - diff[x] for x in range (2)]
		if self.edittype == 0:
			# tile editing.
			if self.selecting:
				if self.pointer_tile == tile:
					return
				def sort (ref, a, b):
					'Sort coordinates a and b with respect to a reference point; used for detrmining the effect of a pointer move. Return value is usable in range (), so the second value is one higher than the maximum.'
					if (a <= ref and b >= ref) or (a >= ref and b <= ref):
						if a < b:
							return a, b + 1
						return b, a + 1
					if a < ref:
						if a < b:
							return a, b
						return b, a
					if a < b:
						return a + 1, b + 1
					return b + 1, a + 1
				if self.pointer_tile[0] != tile[0]:
					# adjust horizontal size of selection.
					for x in range (*sort (self.select.start[0], tile[0], self.pointer_tile[0])):
						if x == self.select.start[0]:
							continue
						# The other axis is not yet adjusted, so use the old coordinate (tile), not the new one (self.pointer_tile).
						for y in range (*sort (self.select.start[1], self.select.start[1], tile[1])):
							self.select.toggle ((x, y), self.type)
				if self.pointer_tile[1] != tile[1]:
					# adjust vertical size of selection.
					for y in range (*sort (self.select.start[1], tile[1], self.pointer_tile[1])):
						if y == self.select.start[1]:
							continue
						# The other axis is already adjusted, so use the new coordinate (self.pointer_tile), not the old one (tile).
						for x in range (*sort (self.select.start[0], self.select.start[0], self.pointer_tile[0])):
							self.select.toggle ((x, y), self.type)
			self.update ()
		else:
			# sequence editing.
			pass	# TODO
	def pos_from_event (self, e):
		return [(self.offset[self.type][x] + int (e[x])) / 50 for x in range (2)]
	def create (self, n):
		if n in data.world.room:
			return
		data.world.room[n] = dink.Room (data)
		self.update ()
		self.grab_focus ()
	def grab (self, arg = None):
		self.grab_focus ()

root = sys.argv[1]
data = dink.Dink (root)
view = View ()
the_gui = gui.gui (external = {'view': view})
the_gui.update = view.update
the_gui ()
