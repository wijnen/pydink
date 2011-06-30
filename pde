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
import Image
import tempfile
import config

def keylist (x, keyfun):
	l = x.keys ()
	l.sort (key = keyfun)
	return l

def seqlist ():
	return keylist (data.seq.seq, lambda (x): data.seq.seq[x].code)

def collectionlist ():
	return keylist (data.seq.collection, lambda (x): data.seq.collection[x]['code'])

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

updating = False		# Flag if the edit-gui is being updated (which means don't respond to changes).
copybuffer = set ()		# Set of tile blocks currently in the buffer. Each element is (screen,x,y,tscreen,tx,ty), which is the location followed by the content. tscreen is always 0-41.
copystart = (0, 0, 0)		# Start tile at the time ctrl-c was pressed.
select = Select ()		# Current tiles selection. See Select class above for contents.
cselect = None			# Name of currently selected collection in sequence screen
sselect = None			# Name of currently selected sequence in sequence screen
fselect = None			# Currently selected frame in sequence screen or in normal view: seq or (collection, dir); frame; screen or None; name or None
warptargets = {'broken':set ()}		# Map of warp targets per room.

def add_warptarget (room, name):
	sp = data.world.room[room].sprite[name]
	if sp.warp == None:
		return
	if sp.warp[0] in warptargets:
		warptargets[sp.warp[0]].add ((room, name))
	elif sp.warp[0] in data.world.room:
		warptargets[sp.warp[0]] = set ([(room, name)])
	else:
		warptargets['broken'].add ((room, name))

def remove_warptarget (room, name):
	sp = data.world.room[room].sprite[name]
	if sp.warp == None or sp.warp[0] not in warptargets or (room, name) not in warptargets[sp.warp[0]]:
		return
	warptargets[sp.warp[0]].remove ((room, name))

class View (gtk.DrawingArea):
	components = []
	started = None
	def keypress (self, widget, e):
		if e.keyval == gtk.keysyms.s:	# save
			data.save ()
		elif e.keyval == gtk.keysyms.q:	# quit (and save)
			data.save ()
			gui.quit ()
		elif e.keyval == gtk.keysyms.x:	# exit (without saving)
			gui.quit ()
		else:
			return False
		return True
	def keypress_tiles (self, e):
		global copybuffer, copystart
		if e.keyval == gtk.keysyms.c:	# copy
			copybuffer.clear ()
			for i in select.data:
				s = View.find_tile (self, i, i[2])
				copybuffer.add ((i[0], i[1], i[2], s[0], s[1], s[2]))
			copystart = select.start
			return True
		return False
	def keypress_seq (self, key, seq):
		if seq == None:
			return False
		if key == gtk.keysyms.t:
			if type (seq[0]) == str:
				sel = seq[0]
			else:
				sel = '%s %d' % seq[0]
			the_gui.set_touchseq = sel
		else:
			if type (seq[0]) == str:
				sel = '*' + seq[0]
			else:
				sel = seq[0][0]
			if key == gtk.keysyms.a:
				the_gui.set_baseattack = sel
			elif key == gtk.keysyms.d:
				the_gui.set_basedie = sel
			elif key == gtk.keysyms.i:
				the_gui.set_baseidle = sel
			elif key == gtk.keysyms.w:
				the_gui.set_basewalk = sel
			else:
				return False
		return True
	def make_gc (self, color):
		ret = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color (the_gui[color])
		ret.set_foreground (c)
		ret.set_line_attributes (1, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		return ret
	def load_pixbuf (self, cache, black):
		i = Image.open (dink.filepart (*cache)).convert ('RGB')
		pb = gtk.gdk.pixbuf_new_from_data (i.tostring (), gtk.gdk.COLORSPACE_RGB, False, 8, i.size[0], i.size[1], i.size[0] * 3)
		if black:
			return pb.add_alpha (True, 0, 0, 0)
		else:
			return pb.add_alpha (True, 255, 255, 255)
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
	def get_pixbuf (self, pb):
		if View.pixbuf[pb][0] == None:
			# Throw a pixbuf out of the cache if required.
			if config.lowmem and len (View.cachedpb) >= config.maxcache:
				View.pixbuf[View.cachedpb[-1]][0] = None
				View.cachedpb = View.cachedpb[:-1]
			# Add pixbuf to cache.
			View.pixbuf[pb][0] = self.load_pixbuf (*View.pixbuf[pb][1])
		if pb in View.cachedpb:
			View.cachedpb.remove (pb)
		View.cachedpb = [pb] + View.cachedpb
		return View.pixbuf[pb][0]
	def start (self, widget):
		self.realize ()
		if View.started != None:
			View.update (self)
			return
		View.started = False
		View.cachedpb = []
		View.gc = self.make_gc ('default-gc')
		View.gridgc = self.make_gc ('grid-gc')
		View.bordergc = self.make_gc ('border-gc')
		View.invalidgc = self.make_gc ('invalid-gc')
		View.selectgc = self.make_gc ('select-gc')
		View.noselectgc = self.make_gc ('noselect-gc')
		View.hotspotgc = self.make_gc ('hotspot-gc')
		View.hardgc = self.make_gc ('hard-gc')
		View.pastegc = self.make_gc ('paste-gc')
		View.emptygc = self.make_gc ('empty-gc')
		View.whitegc = self.make_gc ('white-gc')
		View.bmp = [None] * 41
		View.hard = [None] * 41
		for i in range (41):
			size = data.tile.tile[i][0].size
			pb = gtk.gdk.pixbuf_new_from_data (data.tile.tile[i][0].tostring (), gtk.gdk.COLORSPACE_RGB, False, 8, size[0], size[1], size[0] * 3)
			View.bmp[i] = gtk.gdk.Pixmap (self.get_window (), pb.get_width (), pb.get_height ())
			View.bmp[i].draw_pixbuf (View.gc, pb, 0, 0, 0, 0)
			View.hard[i] = self.image2pixbuf (data.tile.tile[i][1])
		View.pixbufs = {}
		View.pixbuf = []
		for s in data.seq.seq:
			View.pixbufs[s] = [None]
			for f in data.seq.seq[s].frames[1:]:
				if f.source != None:
					View.pixbufs[s] += (None,)
					continue
				View.pixbufs[s] += (len (View.pixbuf),)
				View.pixbuf += ([None, (f.cache, data.seq.seq[s].type == 'black')],)
		View.cpixbufs = {}
		for c in data.seq.collection:
			View.cpixbufs[c] = [None] * 10
			for s in (1,2,3,4,6,7,8,9):
				if s not in data.seq.collection[c]:
					continue
				View.cpixbufs[c][s] = [None]
				for f in data.seq.collection[c][s].frames[1:]:
					if f.source != None:
						View.cpixbufs[c][s] += (None,)
						continue
					View.cpixbufs[c][s] += (len (View.pixbuf),)
					View.pixbuf += ([None, (f.cache, data.seq.collection[c][s].type == 'black')],)
		# Make links for copied frames.
		for c in data.seq.collection:
			for s in (1,2,3,4,6,7,8,9):
				if s not in data.seq.collection[c]:
					continue
				for n, f in zip (range (1, len (data.seq.collection[c][s].frames) + 1), data.seq.collection[c][s].frames[1:]):
					if f.source != None:
						src = data.seq.find_seq (f.source[0])
						if type (src.name) == str:
							View.cpixbufs[c][s][n] = View.pixbufs[src.name][f.source[1]]
						else:
							View.cpixbufs[c][s][n] = View.cpixbufs[src.name[0]][src.name[1]][f.source[1]]
		for s in data.seq.seq:
			for n, f in zip (range (1, len (data.seq.seq[s].frames) + 1), data.seq.seq[s].frames[1:]):
				if f.source != None:
					src = data.seq.find_seq (f.source[0])
					if type (src.name) == str:
						View.pixbufs[s][n] = View.pixbufs[src.name][f.source[1]]
					else:
						View.pixbufs[s][n] = View.cpixbufs[src.name[0]][src.name[1]][f.source[1]]
		View.started = True
		View.update (self)
	def __init__ (self):
		gtk.DrawingArea.__init__ (self)
		View.components += (self,)
		self.buffer = None		# Backing store for the screen.
		self.pointer_pos = (0, 0)	# Current position of pointer.
		self.selecting = False		# Whether tiles are being selected, or a sequence is being moved at this moment.
		self.panning = False		# Whether the screen is panned at this moment.
		self.offset = (0, 0)		# Current pan setting, one for each type.
		self.screensize = (0, 0)	# Size of the viewport in pixels (updated by configure).
		gtk.DrawingArea.__init__ (self)
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('key-release-event', self.keyrelease)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('configure-event', self.configure)
		self.connect ('enter-notify-event', self.enter)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.ENTER_NOTIFY_MASK)
	def enter (self, widget, dummy):
		self.grab_focus ()
	def configure (self, widget, e):
		x, y, width, height = widget.get_allocation()
		self.screensize = (width, height)
		if config.lowmem and config.nobackingstore:
			self.buffer = self.get_window ()
		else:
			self.buffer = gtk.gdk.Pixmap (self.get_window (), width, height)
		if View.started == True:
			self.move (None, None)
			View.update (self)
	def expose (self, widget, e):
		if config.lowmem and config.nobackingstore:
			self.update ()
		else:
			self.get_window ().draw_drawable (View.gc, self.buffer, e.area[0], e.area[1], e.area[0], e.area[1], e.area[2], e.area[3])
	def draw_tile (self, screenpos, worldpos, screen_lines):
		b = self.find_tile (worldpos)
		if b[0] >= 0:
			w, h = View.bmp[b[0]].get_size ()
			if b[1] * 50 >= w or b[2] * 50 >= h:
				self.buffer.draw_rectangle (View.invalidgc, True, screenpos[0] + 1, screenpos[1] + 1, 50, 50)
			else:
				self.buffer.draw_drawable (View.gc, View.bmp[b[0]], b[1] * 50, b[2] * 50, screenpos[0], screenpos[1], 50, 50)
			if screen_lines:
				if worldpos[1] % 8 != 0:
					self.buffer.draw_line (View.gridgc, screenpos[0], screenpos[1], screenpos[0] + 49, screenpos[1])
				if worldpos[0] % 12 != 0:
					self.buffer.draw_line (View.gridgc, screenpos[0], screenpos[1] + 1, screenpos[0], screenpos[1] + 49)
		else:
			self.buffer.draw_rectangle (View.invalidgc, True, screenpos[0], screenpos[1], 50, 50)
		if worldpos[1] % 8 == 0:
			self.buffer.draw_line (View.bordergc, screenpos[0], screenpos[1], screenpos[0] + 49, screenpos[1])
		if worldpos[0] % 12 == 0:
			self.buffer.draw_line (View.bordergc, screenpos[0], screenpos[1], screenpos[0], screenpos[1] + 49)
	def draw_tile_hard (self, screenpos, worldpos):
		b = self.find_tile (worldpos)
		if b[0] >= 0:
			w, h = View.bmp[b[0]].get_size ()
			if b[1] * 50 >= w or b[2] * 50 >= h:
				return
			self.buffer.draw_pixbuf (View.gc, View.hard[b[0]], b[1] * 50, b[2] * 50, screenpos[0], screenpos[1], 50, 50)
	def make_pixbuf50 (self, pb, newsize):
		size = [pb.get_width (), pb.get_height ()]
		if size[0] <= newsize and size[1] <= newsize:
			pass
		elif size[0] > size[1]:
			size[1] = (size[1] * newsize) / size[0]
			size[0] = newsize
		else:
			size[0] = (size[0] * newsize) / size[1]
			size[1] = newsize
		return pb.scale_simple (size[0], size[1], gtk.gdk.INTERP_NEAREST)
	def draw_tiles (self, which):
		origin = [x / 50 for x in self.offset]
		offset = [x % 50 for x in self.offset]
		screens = set ()
		# Fill screens with all screens from which sprites should be drawn.
		for y in range (self.offset[1] / (8 * 50), (self.offset[1] + self.screensize[1] + 8 * 50) / (8 * 50)):
			for x in range (self.offset[0] / (12 * 50), (self.offset[0] + self.screensize[0] + 12 * 50) / (12 * 50)):
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
		# Draw tiles.
		for y in range (offset[1] / 50, (self.screensize[1] + offset[1] + 50) / 50):
			for x in range (offset[0] / 50, (self.screensize[0] + offset[0] + 50) / 50):
				if (origin[0] + x < 0 or origin[0] + x >= self.tiles[0]) or (origin[1] + y < 0 or origin[1] + y >= self.tiles[1]):
					self.buffer.draw_rectangle (self.emptygc, True, x * 50 - offset[0], y * 50 - offset[1], 50, 50)
					continue
				screenpos = (x * 50 - offset[0], y * 50 - offset[1])
				worldpos = (origin[0] + x, origin[1] + y)
				self.draw_tile (screenpos, worldpos)
				check = (worldpos[0], worldpos[1], which)
				if check in select.data:
					if check == select.start:
						self.buffer.draw_rectangle (self.hotspotgc, False, screenpos[0] + 1, screenpos[1] + 1, 48, 48)
					else:
						self.buffer.draw_rectangle (self.selectgc, False, screenpos[0] + 1, screenpos[1] + 1, 48, 48)
		return screens
	def update (self):
		for c in View.components:
			if c.buffer == None:
				continue
			c.update ()
	def tileselect (self, x, y, clear, type):
		if clear:
			select.clear ()
		self.selecting = True
		select.start = (x, y, type)
		select.toggle ((x, y), type)
		# This is called from button_on, not move, so it's acceptable to be a bit slow.
		View.update (self)
	def button_off (self, widget, e):
		if e.button == 1:
			self.selecting = False
		if e.button == 3:
			self.panning = False
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		pos = int (ex), int (ey)
		diff = [pos[x] - self.pointer_pos[x] for x in range (2)]
		self.pointer_pos = pos
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
		self.update ()
	def pos_from_event (self, e):
		return [(self.offset[x] + int (e[x])) / 50 for x in range (2)]
	def select_tiles (self, tile, which):
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
			for x in range (*sort (select.start[0], tile[0], self.pointer_tile[0])):
				if x == select.start[0]:
					continue
				# The other axis is not yet adjusted, so use the old coordinate (tile), not the new one (self.pointer_tile).
				for y in range (*sort (select.start[1], select.start[1], tile[1])):
					select.toggle ((x, y), which)
		if self.pointer_tile[1] != tile[1]:
			# adjust vertical size of selection.
			for y in range (*sort (select.start[1], tile[1], self.pointer_tile[1])):
				if y == select.start[1]:
					continue
				# The other axis is already adjusted, so use the new coordinate (self.pointer_tile), not the old one (tile).
				for x in range (*sort (select.start[0], select.start[0], self.pointer_tile[0])):
					select.toggle ((x, y), which)
	def find_tile (self, pos, which):
		if which == 0:
			return viewmap.find_tile (pos)
		else:
			return viewtiles.find_tile (pos)
	def get_box (self, size, pos, seq, box):
		x = pos[0] - 20
		y = pos[1]
		bb = seq.boundingbox
		w = bb[2] - bb[0]
		h = bb[3] - bb[1]
		# Blame Seth for the computation below.
		x_compat = w * (size - 100) / 100 / 2
		y_compat = h * (size - 100) / 100 / 2
		l = x - seq.position[0] - x_compat
		t = y - seq.position[1] - y_compat
		r = l + w * size / 100
		b = t + h * size / 100
		if box[0] != 0 or box[1] != 0 or box[2] != 0:
			box = list (box)
			if box[0] > w:
				box[0] = w
			if box[1] > h:
				box[1] = h
			if box[2] > w:
				box[2] = w
			if box[3] > h:
				box[3] = h
			l += box[0]
			t += box[1]
			r += box[2] - w
			b += box[3] - h
			bx = box
		else:
			bx = None
		return (x, y), (l, t, r, b), bx

class ViewMap (View):
	def __init__ (self):
		View.__init__ (self)
		self.roomsource = None		# Source for a newly created room (for copying).
		self.pointer_tile = (0, 0)	# Tile that the pointer is currently pointing it, in world coordinates. That is: pointer_pos / 50.
		self.show_hard = False		# Whether hardness should be shown (this setting is combined with a gui setting to get the actual value).
		self.show_sprites = False	# Whether sprites should be shown (this setting is combined with a gui setting to get the actual value).
		self.edit_tiles = False		# Whether tiles or sprites are edited (this setting is combined with a gui setting to get the actual value).
		self.waitselect = None		# Selection to use if button is released without moving.
		self.tiles = (12 * 32, 8 * 24)	# Total number of tiles on map.
		self.selectoffset = (0, 0)	# Offset of current selection point in pixels from hotspot.
		self.set_size_request (50 * 12, 50 * 8)
		self.firstconfigure = True
		self.connect ('focus-out-event', self.focus_out)
	def configure (self, widget, e):
		View.configure (self, widget, e)
		if self.firstconfigure:
			self.firstconfigure = False
			# Initial offset is centered on dink starting screen.
			screen = data.script.start_map
			sc = ((screen - 1) % 32, (screen - 1) / 32)
			s = (12, 8)
			self.offset = [sc[x] * s[x] * 50 + (s[x] / 2) * 50 - self.screensize[x] / 2 for x in range (2)]
	def find_tile (self, worldpos):
		n = (worldpos[1] / 8) * 32 + (worldpos[0] / 12) + 1
		if n in data.world.room:
			return data.world.room[n].tiles[worldpos[1] % 8][worldpos[0] % 12]
		return [-1, -1, -1]
	def editing_sprites (self):
		if the_gui.editing_sprites:
			return not self.edit_tiles
		else:
			return self.edit_tiles
	def draw_tile (self, screenpos, worldpos):
		View.draw_tile (self, screenpos, worldpos, not self.editing_sprites ())
		if self.editing_sprites ():
			return
		if not self.selecting:
			if (worldpos[0] - self.pointer_tile[0] + select.start[0], worldpos[1] - self.pointer_tile[1] + select.start[1], select.start[2]) in select.data:
				self.buffer.draw_rectangle (self.pastegc, False, screenpos[0] + 1, screenpos[1] + 1, 48, 48)
	def update (self):
		screens = View.draw_tiles (self, 0)
		# Draw sprites (only in normal view when switched on).
		lst = []
		if (the_gui.show_sprites and not self.show_sprites) or (not the_gui.show_sprites and self.show_sprites):
			# First get a list of sprites to draw, with their que so they can be drawn in the right order.
			# Check only screens in (or near) the viewport.
			for s in screens:
				if s not in data.world.room:
					# This screen doesn't exist, so doesn't have sprites.
					continue
				# Origin of this screen.
				sy = ((s - 1) / 32) * 50 * 8
				sx = ((s - 1) % 32) * 50 * 12
				# Add all sprites from this screen to the list.
				for spr in data.world.room[s].sprite:
					sp = data.world.room[s].sprite[spr]
					pos = (sx + sp.x - self.offset[0], sy + sp.y - self.offset[1])
					seq = data.seq.find_seq (sp.seq)
					if fselect == None:
						is_selected = False
					else:
						is_selected = (s, spr) == fselect[2:4]
					lst += ((pos, sp, seq, is_selected),)
		# Add sprites which warp to here.
		for s in screens:
			if s not in warptargets:
				continue
			sy = ((s - 1) / 32) * 50 * 8
			sx = ((s - 1) % 32) * 50 * 12
			for n, spr in warptargets[s]:
				# If the sprite is near, don't duplicate it.
				if n in screens:
					continue
				sp = data.world.room[n].sprite[spr]
				seq = data.seq.find_seq (sp.seq)
				if fselect == None:
					is_selected = False
				else:
					is_selected = (n, spr) == fselect[2:4]
				lst += (((None, 0), sp, seq, is_selected),)
		if (the_gui.show_sprites and not self.show_sprites) or (not the_gui.show_sprites and self.show_sprites):
			# Sort the list by y coordinate, taking depth que into account.
			lst.sort (key = lambda (x): x[0][1] - x[1].que)
			# Now draw them all in the right order. First the pixbufs, then the hardbox, crop and selection wires.
			for s in lst:
				if s[0][0] == None:
					# This is only a warp target.
					continue
				(x, y), (left, top, right, bottom), box = self.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
				# Draw the pixbuf.
				if type (s[2].name) == str:
					pb = self.get_pixbuf (self.pixbufs[s[2].name][s[1].frame])
				else:
					pb = self.get_pixbuf (self.cpixbufs[s[2].name[0]][s[2].name[1]][s[1].frame])
				if box != None:
					pb = pb.subpixbuf (box[0], box[1], box[2] - box[0], box[3] - box[1])
				pb = pb.scale_simple (right - left, bottom - top, gtk.gdk.INTERP_NEAREST)
				self.buffer.draw_pixbuf (None, pb, 0, 0, left, top)
		origin = [x / 50 for x in self.offset]
		offset = [x % 50 for x in self.offset]
		if (self.show_hard and not the_gui.show_hard) or (not self.show_hard and the_gui.show_hard):
			for y in range (offset[1] / 50, (self.screensize[1] + offset[1] + 50) / 50):
				for x in range (offset[0] / 50, (self.screensize[0] + offset[0] + 50) / 50):
					if (origin[0] + x < 0 or origin[0] + x >= self.tiles[0]) or (origin[1] + y < 0 or origin[1] + y >= self.tiles[1]):
						continue
					self.draw_tile_hard ((x * 50 - offset[0], y * 50 - offset[1]), (origin[0] + x, origin[1] + y))
			for s in lst:
				if s[0][0] != None:
					(x, y), (left, top, right, bottom), box = self.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
					# Draw hardness box as a cross.
					self.buffer.draw_line (self.hardgc, x, y + s[2].frames[s[1].frame].hardbox[1], x, y + s[2].frames[s[1].frame].hardbox[3] - 1)
					self.buffer.draw_line (self.hardgc, x + s[2].frames[s[1].frame].hardbox[0], y, x + s[2].frames[s[1].frame].hardbox[2] - 1, y)
					# If hard, draw with box.
					if s[1].hard:
						self.buffer.draw_rectangle (self.hardgc, False, x + s[2].frames[s[1].frame].hardbox[0], y + s[2].frames[s[1].frame].hardbox[1], s[2].frames[s[1].frame].hardbox[2] - s[2].frames[s[1].frame].hardbox[0] - 1, s[2].frames[s[1].frame].hardbox[3] - s[2].frames[s[1].frame].hardbox[1] - 1)
					if not s[3]:
						self.buffer.draw_rectangle (self.noselectgc, False, left, top, right - left, bottom - top)
				if not s[3]:
					if s[1].warp != None:
						n, x, y = s[1].warp
						y += ((n - 1) / 32) * 8 * 50 - self.offset[1]
						x += ((n - 1) % 32) * 12 * 50 - self.offset[0] - 20
						self.buffer.draw_line (self.noselectgc, x - 20, y, x + 20, y)
						self.buffer.draw_line (self.noselectgc, x, y - 20, x, y + 20)
						self.buffer.draw_arc (self.noselectgc, False, x - 15, y - 15, 30, 30, 0, 64 * 360)
		# No matter what is visible, always show selected sprite stuff on top.
		for s in lst:
			if s[3]:
				if s[0][0] != None:
					(x, y), (left, top, right, bottom), box = self.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
					self.buffer.draw_rectangle (self.selectgc, False, left, top, right - left, bottom - top)
				if s[1].warp != None:
					n, x, y = s[1].warp
					y += ((n - 1) / 32) * 8 * 50 - self.offset[1]
					x += ((n - 1) % 32) * 12 * 50 - self.offset[0] - 20
					self.buffer.draw_line (self.selectgc, x - 20, y, x + 20, y)
					self.buffer.draw_line (self.selectgc, x, y - 20, x, y + 20)
					self.buffer.draw_arc (self.selectgc, False, x - 15, y - 15, 30, 30, 0, 64 * 360)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def make_global (self, screen, pos):
		s = (12, 8)
		spos = ((screen - 1) % 32, (screen - 1) / 32)
		return [pos[x] + s[x] * spos[x] * 50 for x in range (2)]
	def goto (self, pos):
		s = (12, 8)
		self.offset = [pos[x] - self.screensize[x] / 2 for x in range (2)]
		self.update ()
		viewworld.update ()
	def keypress (self, widget, e):
		global fselect
		self.selecting = False
		if View.keypress (self, widget, e):	# Handle global keys.
			pass
		elif e.keyval == gtk.keysyms.Control_L:
			self.show_hard = True
		elif e.keyval == gtk.keysyms.Alt_L:
			self.show_sprites = True
		elif e.keyval == gtk.keysyms.Shift_L:
			self.edit_tiles = True
		elif e.keyval == gtk.keysyms.p:	# play
			os.system (the_gui['sync'])
			for s in data.script.data:
				data.script.data[s] = open (os.path.join (tmpdir, s + '.c')).read ()
			p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
			n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
			data.play (n, p[0] % (12 * 50) + 20, p[1] % (8 * 50))
		elif e.keyval == gtk.keysyms.Insert:	# create screen
			p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
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
			p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
			n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
			if n in data.world.room:
				del data.world.room[n]
				if self.roomsource == n:
					self.roomsource = None
				View.update (self)
		elif e.keyval == gtk.keysyms.Home:	# center screen
			s = (12, 8)
			self.goto ([(self.pointer_pos[x] + self.offset[x]) / s[x] / 50 * s[x] * 50 + s[x] / 2 * 50 for x in range (2)])
		elif e.keyval == gtk.keysyms.g:		# go to sprite
			if fselect == None or fselect[3] == None:
				return
			sprite = data.world.room[fselect[2]].sprite[fselect[3]]
			self.goto (self.make_global (fselect[2], (sprite.x, sprite.y)))
		elif e.keyval == gtk.keysyms.j:		# jump to warp target
			if fselect == None or fselect[3] == None:
				return
			sprite = data.world.room[fselect[2]].sprite[fselect[3]]
			if sprite.warp == None:
				return
			self.goto (self.make_global (sprite.warp[0], (sprite.warp[1], sprite.warp[2])))
		else:
			if not self.editing_sprites ():
				if View.keypress_tiles (self, e):
					pass
				elif e.keyval == gtk.keysyms.f:	# fill
					if len (copybuffer) == 0:
						return
					tiles = list (copybuffer)
					min = [None, None]
					max = [None, None]
					for i in copybuffer:
						if i[2] != copystart[2]:
							continue
						for x in range (2):
							if min[x] == None or i[x] < min[x]:
								min[x] = i[x]
							if max[x] == None or i[x] > max[x]:
								max[x] = i[x]
					for i in select.data:
						# Don't try to paste into tile screens.
						if i[2] != 0:
							continue
						n = (i[1] / 8) * 32 + (i[0] / 12) + 1
						if n not in data.world.room:
							continue
						tile = None
						if min[0] != None:
							size = [max[x] - min[x] + 1 for x in range (2)]
							p = [(i[x] - select.start[x] + copystart[x]) % size[x] for x in range (2)]
							for b in copybuffer:
								if b[2] == copystart[2] and (b[0] - copystart[0]) % size[0] == p[0] and (b[1] - copystart[1]) % size[1] == p[1]:
									tile = b[3:6]
						if tile == None:
							tile = tiles[random.randrange (len (copybuffer))][3:6]
						data.world.room[n].tiles[i[1] % 8][i[0] % 12] = tile
				elif e.keyval == gtk.keysyms.r:	# random
					if len (copybuffer) == 0:
						return
					tiles = list (copybuffer)
					for i in select.data:
						# Don't try to paste into tile screens.
						if i[2] != 0:
							continue
						n = (i[1] / 8) * 32 + (i[0] / 12) + 1
						if n not in data.world.room:
							continue
						tile = tiles[random.randrange (len (copybuffer))][3:6]
						data.world.room[n].tiles[i[1] % 8][i[0] % 12] = tile
			else:
				# editing sprites
				if e.keyval == gtk.keysyms.k:
					if fselect == None or fselect[3] == None:
						return
					if fselect[4]:
						remove_warptarget (fselect[2], fselect[3])
						del data.world.room[fselect[2]].sprite[fselect[3]]
						fselect = (fselect[0], fselect[1], None, None, True)
						update_editgui ()
					else:
						# Delete warp point
						remove_warptarget (fselect[2], fselect[3])
						data.world.room[fselect[2]].sprite[fselect[3]].warp = None
						fselect[4] = True
						update_editgui ()
				if e.keyval == gtk.keysyms.w:
					global updating
					if fselect == None or fselect[3] == None:
						return
					updating = True
					remove_warptarget (fselect[2], fselect[3])
					p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
					p[0] += 20
					the_gui.set_warpscreen = (p[1] / (8 * 50)) * 32 + p[0] / (12 * 50) + 1
					the_gui.set_warpx = p[0] % (12 * 50)
					the_gui.set_warpy = p[1] % (8 * 50)
					the_gui.set_warp = True
					the_gui.set_ishard = True
					add_warptarget (fselect[2], fselect[3])
					updating = False
					update_gui (None)
		self.update ()
	def keyrelease (self, widget, e):
		if e.keyval == gtk.keysyms.Control_L:
			self.show_hard = False
			self.update ()
		elif e.keyval == gtk.keysyms.Alt_L:
			self.show_sprites = False
			self.update ()
		elif e.keyval == gtk.keysyms.ISO_Prev_Group: # This is what it gives instead of Shift_L:
			self.edit_tiles = False
			self.update ()
	def focus_out (self, widget, e):
		self.show_hard = False
		self.show_sprites = False
		self.edit_tiles = False
		self.update ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / 50 for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		if not self.editing_sprites ():
			if e.button == 1:
				x, y = self.pos_from_event ((e.x, e.y))
				View.tileselect (self, x, y, not e.state & gtk.gdk.CONTROL_MASK, 0)
			elif e.button == 2:	# paste.
				if select.empty ():
					return
				pos = self.pos_from_event ((e.x, e.y))
				for t in select.compute ():
					target = [pos[x] + t[x] for x in range (2)]
					n = (target[1] / 8) * 32 + (target[0] / 12) + 1
					if n not in data.world.room:
						continue
					p = [t[x] + select.start[x] for x in range (2)]
					data.world.room[n].tiles[target[1] % 8][target[0] % 12] = View.find_tile (self, p, select.start[2])
				self.update ()
		else:
			# sequence editing.
			if e.button == 1:	# select.
				global fselect, sselect, cselect
				x, y = [(self.offset[x] + self.pointer_pos[x]) for x in range (2)]
				# Find all sprites which are pointed at.
				sx = x / (12 * 50)
				sy = y / (8 * 50)
				screens = []
				for dy in range (-1, 2):
					if sy + dy < 0 or sy + dy >= 24:
						continue
					for dx in range (-1, 2):
						if sx + dx < 0 or sx + dx >= 32:
							continue
						screens += ((sy + dy) * 32 + (sx + dx) + 1,)
				lst = []
				for s in screens:
					# Origin of this screen.
					sy = ((s - 1) / 32) * 50 * 8
					sx = ((s - 1) % 32) * 50 * 12
					# Only look at existing screens.
					if s in data.world.room:
						for spr in data.world.room[s].sprite:
							sp = data.world.room[s].sprite[spr]
							pos = (sx + sp.x - 20, sy + sp.y) # 20, because sprite positions are relative to screen origin; first tile starts at (20,0).
							seq = data.seq.find_seq (sp.seq)
							(rx, ry), (left, top, right, bottom), box = self.get_box (sp.size, (sp.x, sp.y), seq.frames[sp.frame], (sp.left, sp.top, sp.right, sp.bottom))
							if x - sx >= left and y - sy >= top and x - sx < right and y - sy < bottom:
								lst += ((pos[1] - sp.que, (seq.name, sp.frame, s, spr, True), pos),)
					# Add all warp points, too.
					only_selected = not ((self.show_hard and not the_gui.show_hard) or (not self.show_hard and the_gui.show_hard))
					if s in warptargets:
						for n, spr in warptargets[s]:
							if only_selected and (fselect == None or fselect[2:4] != (n, spr)):
								continue
							sp = data.world.room[n].sprite[spr]
							pos = (sx + sp.warp[1] - 20, sy + sp.warp[2])
							if -20 <= x - pos[0] < 20 and -20 <= y - pos[1] < 20:
								seq = data.seq.find_seq (sp.seq)
								lst += ((pos[1] - sp.que, (None, None, n, spr, False), pos),)
				# Sort the sprites by depth.
				lst.sort (key = lambda (x): -x[0])
				# If the list is empty, clear the selection.
				if lst == []:
					# Select clicked screen.
					sx = x / (12 * 50)
					sy = y / (8 * 50)
					screen = sy * 32 + sx + 1
					if screen in data.world.room:
						fselect = (None, None, screen, None, True)
						update_editgui ()
					else:
						fselect = None
					return
				# If the currently selected sprite is in the list, select the next; otherwise select the first.
				if fselect != None:
					for s in range (len (lst)):
						if fselect == lst[s][1]:
							fselect, pos = lst[s][1:]
							if s == len (lst) - 1:
								self.waitselect = lst[0][1:]
							else:
								self.waitselect = lst[s + 1][1:]
							break
					else:
						# Current selection is not in the list. Select first and update gui.
						fselect, pos = lst[0][1:]
						sselect = fselect[0]
						if type (sselect) == str:
							cselect = None
						else:
							cselect = sselect[0]
						update_editgui ()
				else:
					# There was no selection. Select first and update gui.
					fselect, pos = lst[0][1:]
					sselect = fselect[0]
					if type (sselect) == str:
						cselect = None
					else:
						cselect = sselect[0]
					update_editgui ()
				self.selecting = True
				self.selectoffset = (x - pos[0], y - pos[1])
			elif e.button == 2:	# paste.
				if fselect != None and fselect[0] != None:
					x, y = [(self.offset[x] + self.pointer_pos[x]) for x in range (2)]
					sx = x / (12 * 50)
					sy = y / (8 * 50)
					ox = x - sx * 12 * 50 + 20
					oy = y - sy * 8 * 50
					n = sy * 32 + sx + 1
					if n in data.world.room:
						name = data.world.room[n].add_sprite ((ox, oy), fselect[0], fselect[1])
						sp = data.world.room[n].sprite[name]
						if fselect[3] != None:
							src = data.world.room[fselect[2]].sprite[fselect[3]]
							sp.type = src.type
							sp.size = src.size
							sp.brain = src.brain
							sp.script = src.script
							sp.speed = src.speed
							sp.base_walk = src.base_walk
							sp.base_idle = src.base_idle
							sp.base_attack = src.base_attack
							sp.base_die = src.base_die
							sp.timer = src.timer
							sp.que = src.que
							sp.hard = src.hard
							sp.left = src.left
							sp.top = src.top
							sp.right = src.right
							sp.bottom = src.bottom
							# warp
							sp.touch_seq = src.touch_seq
							sp.gold = src.gold
							sp.hitpoints = src.hitpoints
							sp.strength = src.strength
							sp.defense = src.defense
							sp.exp = src.exp
							sp.sound = src.sound
							sp.vision = src.vision
							sp.nohit = src.nohit
							sp.touch_damage = src.touch_damage
						else:
							try:
								sp.type = ('Background', 'Normal', None, 'Invisible').index (the_gui.get_type)
								sp.size = int (the_gui.get_size)
								sp.brain = the_gui.get_brain
								sp.script = the_gui.get_script
								sp.speed = int (the_gui.get_speed)
								sp.base_walk = the_gui.get_basewalk
								sp.base_idle = the_gui.get_baseidle
								sp.base_attack = the_gui.get_baseattack
								sp.base_die = the_gui.get_basedie
								sp.timer = int (the_gui.get_timer)
								sp.que = int (the_gui.get_que)
								sp.hard = the_gui.get_ishard
								sp.left = int (the_gui.get_left)
								sp.top = int (the_gui.get_top)
								sp.right = int (the_gui.get_right)
								sp.bottom = int (the_gui.get_bottom)
								# warp
								sp.touch_seq = the_gui.get_touchseq
								sp.gold = int (the_gui.get_gold)
								sp.hitpoints = int (the_gui.get_hitpoints)
								sp.strength = int (the_gui.get_strength)
								sp.defense = int (the_gui.get_defense)
								sp.exp = int (the_gui.get_exp)
								sp.sound = the_gui.get_sound
								sp.vision = int (the_gui.get_vision)
								sp.nohit = the_gui.get_nohit
								sp.touch_damage = int (the_gui.get_touchdamage)
							except:
								sp.type = 1
								sp.size = 100
								sp.brain = 'none'
								sp.script = ''
								sp.speed = 1
								sp.base_walk = ''
								sp.base_idle = ''
								sp.base_attack = ''
								sp.base_die = ''
								sp.timer = 33
								sp.que = 0
								sp.hard = False
								sp.left = 0
								sp.top = 0
								sp.right = 0
								sp.bottom = 0
								# warp
								sp.touch_seq = ''
								sp.gold = 0
								sp.hitpoints = 0
								sp.strength = 0
								sp.defense = 0
								sp.exp = 0
								sp.sound = ''
								sp.vision = 0
								sp.nohit = True
								sp.touch_damage = 0
								print 'Warning: unable to parse settings; using defaults.'
						fselect = (fselect[0], fselect[1], n, name, True)
						update_editgui ()
			View.update (self)
	def button_off (self, widget, e):
		global fselect, sselect, cselect
		if e.button == 1:
			self.selecting = False
			if self.waitselect != None:
				fselect, pos = self.waitselect
				sselect = fselect[0]
				if type (sselect) == str:
					cselect = None
				else:
					cselect = sselect[0]
				update_editgui ()
		elif e.button == 3:
			self.panning = False
		View.update (self)
	def move (self, widget, e):
		self.waitselect = None
		ex, ey, emask = self.get_window ().get_pointer ()
		tile = self.pointer_tile
		pos = int (ex), int (ey)
		diff = [pos[x] - self.pointer_pos[x] for x in range (2)]
		self.pointer_pos = pos
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / 50 for x in range (2)]
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
		if not self.editing_sprites ():
			# tile editing.
			if self.selecting:
				View.select_tiles (self, tile, 0)
		else:
			# sequence editing.
			if not self.selecting:
				# Ignore events without selection.
				self.update ()
				viewworld.update ()
				return
			global fselect
			room = fselect[2]
			sp = data.world.room[room].sprite[fselect[3]]
			if fselect[4]:
				s = [((room - 1) % 32) * (12 * 50), ((room - 1) / 32) * (8 * 50)]
				p = [pos[t] + self.offset[t] - self.selectoffset[t] - s[t] for t in range (2)]
				os = s
				op = p
				while p[0] < 0 and s[0] > 0:
					p[0] += 12 * 50
					s[0] -= 12 * 50
				while p[0] > 12 * 50 and s[0] < 32 * 8 * 50:
					p[0] -= 12 * 50
					s[0] += 12 * 50
				while p[1] < 0 and s[1] > 0:
					p[1] += 8 * 50
					s[1] -= 8 * 50
				while p[1] > 8 * 50 and s[1] < 24 * 8 * 50:
					p[1] -= 8 * 50
					s[1] += 8 * 50
				p[0] += 20
				sp.x, sp.y = p
				rm = (s[1] / (8 * 50)) * 32 + (s[0] / (12 * 50)) + 1
				if rm != room:
					if rm in data.world.room:
						# Move the sprite to a different room.
						name = fselect[3]
						del data.world.room[room].sprite[name]
						room = rm
						nm = name
						i = 0
						while nm in data.world.room[room].sprite:
							nm = '%s%d' % (name, i)
							i += 1
						data.world.room[room].sprite[nm] = sp
						fselect = (fselect[0], fselect[1], room, nm, True)
						update_editgui ()
					else:
						# New room doesn't exist; use old one.
						sp.x, sp.y = op
						update_editgui ()
				else:
					# Don't update entire gui, because it's too slow.
					global updating
					updating = True
					the_gui.set_x = int (sp.x)
					the_gui.set_y = int (sp.y)
					updating = False
			else:
				# Move the warp point.
				s = [((sp.warp[0] - 1) % 32) * (12 * 50), ((sp.warp[0] - 1) / 32) * (8 * 50)]
				p = [pos[t] + self.offset[t] - self.selectoffset[t] - s[t] for t in range (2)]
				while p[0] < 0 and s[0] > 0:
					p[0] += 12 * 50
					s[0] -= 12 * 50
				while p[0] > 12 * 50 and s[0] < 32 * 8 * 50:
					p[0] -= 12 * 50
					s[0] += 12 * 50
				while p[1] < 0 and s[1] > 0:
					p[1] += 8 * 50
					s[1] -= 8 * 50
				while p[1] > 8 * 50 and s[1] < 24 * 8 * 50:
					p[1] -= 8 * 50
					s[1] += 8 * 50
				remove_warptarget (room, fselect[3])
				sp.warp = ((s[1] / (8 * 50)) * 32 + (s[0] / (12 * 50)) + 1, p[0] + 20, p[1])
				add_warptarget (room, fselect[3])
				update_editgui ()
		self.update ()
		viewworld.update ()

class ViewSeq (View):
	def __init__ (self):
		View.__init__ (self)
		self.width = config.seqwidth
		self.tilesize = config.tilesize
		s = seqlist ()
		ns = (len (s) + self.width - 1) / self.width
		self.set_size_request (self.width * self.tilesize, ns * self.tilesize)
	def update (self):
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		s = seqlist ()
		ns = (len (s) + self.width - 1) / self.width
		# sequences
		for y in range (ns):
			for x in range (self.width):
				dpos = [(x, y)[t] * self.tilesize - self.offset[t] for t in range (2)]
				if y * self.width + x >= len (s):
					self.buffer.draw_rectangle (self.invalidgc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
					continue
				pb = self.pixbufs[s[y * self.width + x]][1]
				self.buffer.draw_rectangle (self.whitegc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
				self.buffer.draw_pixbuf (None, self.make_pixbuf50 (self.get_pixbuf (pb), self.tilesize), 0, 0, dpos[0], dpos[1])
				if sselect == s[y * self.width + x]:
					self.buffer.draw_rectangle (self.selectgc, False, dpos[0], dpos[1], self.tilesize - 1, self.tilesize - 1)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		self.selecting = False
		if View.keypress (self, widget, e):	# Handle global keys.
			pass
		elif e.keyval == gtk.keysyms.Home:	# restore sane panning
			self.offset = [0, 0]
			self.update ()
		else:
			sel = self.get_selected_sequence (self.pointer_pos[0], self.pointer_pos[1])
			View.keypress_seq (self, e.keyval, sel)
	def get_selected_sequence (self, x, y):
		s = seqlist ()
		ns = (len (s) + self.width - 1) / self.width
		if x >= 0 and x < self.tilesize * self.width and y >= 0 and y < self.tilesize * ns:
			target = (y / self.tilesize) * self.width + x / self.tilesize
			if len (s) > target:
				return (s[target], 1)
		return None
	def keyrelease (self, widget, e):
		pass
	def button_on (self, widget, e):
		global sselect, fselect
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		sel = self.get_selected_sequence (*self.pointer_pos)
		if sel == None:
			return
		sselect = sel[0]
		fselect = (sel[0], sel[1], None, None, True)
		View.update (self)

class ViewCollection (View):
	def __init__ (self):
		View.__init__ (self)
		self.width = config.seqwidth - 3
		self.tilesize = config.tilesize
		c = collectionlist ()
		nc = (len (c) + self.width - 1) / self.width
		self.set_size_request (self.width * self.tilesize, nc * self.tilesize)
	def update (self):
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		c = collectionlist ()
		nc = (len (c) + self.width - 1) / self.width
		for y in range (nc):
			for x in range (self.width):
				dpos = [(x, y)[t] * self.tilesize - self.offset[t] for t in range (2)]
				if y * self.width + x >= len (c):
					self.buffer.draw_rectangle (self.invalidgc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
					continue
				for d in (1, 2, 3, 4, 6, 7, 8, 9):
					if d in data.seq.collection[c[y * self.width + x]]:
						break
				pb = self.cpixbufs[c[y * self.width + x]][d][1]
				self.buffer.draw_rectangle (self.whitegc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
				self.buffer.draw_pixbuf (None, self.make_pixbuf50 (self.get_pixbuf (pb), self.tilesize), 0, 0, dpos[0], dpos[1])
				if cselect == c[y * self.width + x]:
					self.buffer.draw_rectangle (self.selectgc, False, dpos[0], dpos[1], self.tilesize - 1, self.tilesize - 1)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def get_selected_sequence (self, x, y):
		c = collectionlist ()
		nc = (len (c) + self.width - 1) / self.width
		if x >= 0 and x < self.tilesize * self.width and y >= 0 and y < self.tilesize * nc:
			target = (y / self.tilesize) * self.width + x / self.tilesize
			if target <= len (c):
				return ((c[target], [x for x in data.seq.collection[c[target]].keys () if type (x) == int][0]), 1)
		return None
	def keypress (self, widget, e):
		self.selecting = False
		if View.keypress (self, widget, e):	# Handle global keys.
			pass
		elif e.keyval == gtk.keysyms.Home:	# restore sane panning
			self.offset = [0, 0]
			self.update ()
		else:
			sel = self.get_selected_sequence (self.pointer_pos[0], self.pointer_pos[1])
			View.keypress_seq (self, e.keyval, sel)
	def keyrelease (self, widget, e):
		pass
	def button_on (self, widget, e):
		global cselect, sselect, fselect
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		if e.button != 1:
			return
		sel = self.get_selected_sequence (*self.pointer_pos)
		if sel == None:
			return
		cselect = sel[0][0]
		sselect = sel[0]
		fselect = (sselect, 1, None, None, True)
		View.update (self)

class ViewFrame (View):
	def __init__ (self):
		View.__init__ (self)
		self.width = config.seqwidth
		self.tilesize = config.tilesize
		# Count maximum frames
		m = 0
		for s in data.seq.seq:
			if len (data.seq.seq[s].frames) > m:
				m = len (data.seq.seq[s].frames)
		for c in data.seq.collection:
			for s in data.seq.collection[c]:
				if type (s) != int:
					continue
				if len (data.seq.collection[c][s].frames) > m:
					m = len (data.seq.collection[c][s].frames)
		self.set_size_request (self.width * self.tilesize, (m + self.width - 1) / self.width * self.tilesize)
	def update (self):
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		if sselect != None:
			if type (sselect) == str:
				# sequence selected
				selection = View.pixbufs[sselect]
			else:
				# collection direction selected
				selection = View.cpixbufs[sselect[0]][sselect[1]]
			dpos = [0, 0]
			for f in range (1, len (selection)):
				dpos[0] = ((f - 1) % self.width) * self.tilesize - self.offset[0]
				dpos[1] = (f - 1) / self.width * self.tilesize - self.offset[1]
				self.buffer.draw_rectangle (self.whitegc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
				self.buffer.draw_pixbuf (None, self.make_pixbuf50 (self.get_pixbuf (selection[f]), self.tilesize), 0, 0, dpos[0], dpos[1])
				if fselect != None and fselect[0:2] == (sselect, f):
					self.buffer.draw_rectangle (self.selectgc, False, dpos[0], dpos[1], self.tilesize - 1, self.tilesize - 1)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def get_selected_sequence (self, x, y):
		if sselect != None:
			if type (sselect) == str:
				# sequence selected
				selection = View.pixbufs[sselect]
			else:
				# collection direction selected
				selection = View.cpixbufs[sselect[0]][sselect[1]]
			n = len (selection)
			nn = (n + self.width - 1) / self.width
			if y + self.offset[1] < 0 or x + self.offset[0] < 0 or x + self.offset[0] >= self.tilesize * self.width:
				return None
			target = (y + self.offset[1]) / self.tilesize * self.width + (x + self.offset[0]) / self.tilesize
			if target >= len (selection):
				return None
			return (sselect, target + 1)
		return None
	def keyrelease (self, widget, e):
		pass
	def keypress (self, widget, e):
		if View.keypress (self, widget, e):
			pass
		elif e.keyval == gtk.keysyms.Home:	# restore sane panning
			self.offset = [0, 0]
			self.update ()
		else:
			sel = self.get_selected_sequence (*self.pointer_pos)
			View.keypress_seq (self, e.keyval, sel)
	def button_on (self, widget, e):
		global fselect
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		sel = self.get_selected_sequence (*self.pointer_pos)
		if sel == None:
			return
		fselect = (sel[0], sel[1], None, None, True)
		View.update (self)

class ViewDir (View):
	def __init__ (self):
		View.__init__ (self)
		self.tilesize = config.tilesize
		self.set_size_request (3 * self.tilesize, 3 * self.tilesize)
	def update (self):
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		if cselect != None:
			dirs = (None, (-1, 1), (0, 1), (1, 1), (-1, 0), None, (1, 0), (-1, -1), (0, -1), (1, -1))
			for d in (1,2,3,4,6,7,8,9):
				dpos = [(1 + dirs[d][t]) * self.tilesize - self.offset[t] for t in range (2)]
				if d not in data.seq.collection[cselect]:
					self.buffer.draw_rectangle (self.invalidgc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
					continue
				self.buffer.draw_rectangle (self.whitegc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
				pb = self.cpixbufs[cselect][d][1]
				self.buffer.draw_pixbuf (None, self.make_pixbuf50 (self.get_pixbuf (pb), self.tilesize), 0, 0, dpos[0], dpos[1])
				if sselect == (cselect, d):
					self.buffer.draw_rectangle (self.selectgc, False, dpos[0], dpos[1], self.tilesize - 1, self.tilesize - 1)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def get_selected_sequence (self, x, y):
		if cselect != None and x >= 0 and x < self.tilesize * 3 and y >= 0 and y < self.tilesize * 3:
			undir = (7, 8, 9, 4, None, 6, 1, 2, 3)
			d = undir[(y / self.tilesize) * 3 + x / self.tilesize]
			if d != None:
				if View.cpixbufs[cselect][d] != None:
					return ((cselect, d), 1)
		return None
	def keypress (self, widget, e):
		if View.keypress (self, widget, e):
			pass
		elif e.keyval == gtk.keysyms.Home:	# restore sane panning
			self.offset = [0, 0]
			self.update ()
		else:
			sel = self.get_selected_sequence (*self.pointer_pos)
			View.keypress_seq (self, e.keyval, sel)
	def keyrelease (self, widget, e):
		pass
	def button_on (self, widget, e):
		global sselect, fselect
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		sel = self.get_selected_sequence (*self.pointer_pos)
		if sel == None:
			return
		sselect = sel[0]
		fselect = (sel[0], sel[1], None, None, True)
		View.update (self)

class ViewTiles (View):
	def __init__ (self):
		View.__init__ (self)
		self.pointer_tile = (0, 0)	# Tile that the pointer is currently pointing it, in world coordinates. That is: pointer_pos / 50.
		self.tiles = (12 * 6, 8 * 7)	# Total number of tiles
		self.set_size_request (50 * 12, 50 * 8)
	def find_tile (self, worldpos):
		if worldpos[0] >= 0 and worldpos[0] < 6 * 12 and worldpos[1] >= 0 and worldpos[1] < 7 * 8:
			n = (worldpos[1] / 8) * 6 + worldpos[0] / 12
			if n < 41:
				return [n, worldpos[0] % 12, worldpos[1] % 8]
		return [-1, -1, -1]
	def draw_tile (self, screenpos, worldpos):
		View.draw_tile (self, screenpos, worldpos, False)
	def update (self):
		View.draw_tiles (self, 1)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		self.selecting = False
		if View.keypress (self, widget, e):	# Handle global keys.
			pass
		elif View.keypress_tiles (self, e):
			pass
		elif e.keyval == gtk.keysyms.Home:	# center screen
			s = (12, 8)
			self.offset = [((self.pointer_pos[x] + self.offset[x]) / s[x] / 50) * s[x] * 50 + (s[x] / 2) * 50 - self.screensize[x] / 2 for x in range (2)]
			self.update ()
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		tile = self.pointer_tile
		pos = int (ex), int (ey)
		diff = [pos[x] - self.pointer_pos[x] for x in range (2)]
		self.pointer_pos = pos
		self.pointer_tile = [(pos[x] + self.offset[x]) / 50 for x in range (2)]
		if not self.panning and not self.selecting:
			return
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
		if self.selecting:
			View.select_tiles (self, tile, 1)
		self.update ()
	def keyrelease (self, widget, e):
		pass
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / 50 for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 3:	# pan view.
			self.panning = True
			return
		if e.button == 1:
			x, y = self.pos_from_event ((e.x, e.y))
			View.tileselect (self, x, y, not e.state & gtk.gdk.CONTROL_MASK, 1)

class ViewWorld (View):
	def __init__ (self):
		View.__init__ (self)
		self.set_size_request (32 * 12, 24 * 8)
	def update (self):
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
		targetsize = [max (2, viewmap.screensize[x] * tsize[x] / 50 / scrsize[x]) for x in range (2)]
		current = [viewmap.offset[t] * tsize[t] / scrsize[t] / 50 + off[t] for t in range (2)]
		self.buffer.draw_rectangle (self.selectgc, False, current[0], current[1], targetsize[0] - 1, targetsize[1] - 1)
		self.buffer.draw_rectangle (self.pastegc, False, self.pointer_pos[0] - targetsize[0] / 2, self.pointer_pos[1] - targetsize[1] / 2, targetsize[0] - 1, targetsize[1] - 1)
		if not (config.lowmem and config.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keyrelease (self, widget, e):
		pass
	def select (self):
		self.selecting = True
		s = (32, 24)
		scrsize = (12, 8)
		tsize = [self.screensize[x] / s[x] for x in range (2)]
		off = [(self.screensize[x] - s[x] * tsize[x]) / 2 for x in range (2)]
		viewmap.offset = [(self.pointer_pos[x] - off[x]) * 50 * scrsize[x] / tsize[x] - viewmap.screensize[x] / 2 for x in range (2)]
		viewmap.update ()
		self.update ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 1:
			self.select ()
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		self.pointer_pos = int (ex), int (ey)
		if self.selecting:
			self.select ()
		self.update ()

def new_sprite (dummy):
	global fselect
	if updating:
		return
	screen = int (the_gui.get_screen)
	sprite = the_gui.get_sprite
	if screen not in data.world.room or sprite not in data.world.room[screen].sprite:
		return
	s = data.world.room[screen].sprite[sprite]
	fselect = (s.seq, s.frame, screen, sprite, True)
	update_editgui ()
	View.update (viewmap)

def update_editgui ():
	global updating
	if updating:
		# Not sure how this can happen, but prevent looping anyway.
		return
	if fselect == None or fselect[2] == None:
		# No selection, so nothing to update.
		return
	updating = True
	screen = fselect[2]
	the_gui.set_screen = screen
	the_gui.set_screen_script = data.world.room[screen].script
	the_gui.set_screen_music = data.world.room[screen].music
	the_gui.set_indoor = data.world.room[screen].indoor
	the_gui.set_spritelist = keylist (data.world.room[screen].sprite, lambda (x): x)
	if fselect[3] == None:
		# No selected sprite; don't touch sprite info.
		updating = False
		return
	sprite = data.world.room[fselect[2]].sprite[fselect[3]]
	the_gui.set_sprite = fselect[3]
	the_gui.set_name = fselect[3]
	the_gui.set_x = sprite.x
	the_gui.set_y = sprite.y
	if type (sprite.seq) == str:
		the_gui.set_seq = sprite.seq
	else:
		the_gui.set_seq = '%s %d' % sprite.seq
	the_gui.set_frame = sprite.frame
	if sprite.type == 0:
		the_gui.set_type = 'background'
	elif sprite.type == 1:
		the_gui.set_type = 'normal'
	else:
		the_gui.set_type = 'invisible'
	the_gui.set_size = sprite.size
	the_gui.set_brain = sprite.brain
	the_gui.set_script = sprite.script
	the_gui.set_speed = sprite.speed
	the_gui.set_basewalk = sprite.base_walk
	the_gui.set_baseidle = sprite.base_idle
	the_gui.set_baseattack = sprite.base_attack
	the_gui.set_timer = sprite.timer
	the_gui.set_que = sprite.que
	the_gui.set_ishard = sprite.hard
	the_gui.set_crop = sprite.left != 0 or sprite.right != 0 or sprite.top != 0 or sprite.bottom != 0
	the_gui.set_left = sprite.left
	the_gui.set_top = sprite.top
	the_gui.set_right = sprite.right
	the_gui.set_bottom = sprite.bottom
	if sprite.warp == None:
		the_gui.set_warp = False
	else:
		the_gui.set_warp = True
		the_gui.set_warpscreen = sprite.warp[0]
		the_gui.set_warpx = sprite.warp[1]
		the_gui.set_warpy = sprite.warp[2]
	if type (sprite.touch_seq) == str:
		the_gui.set_touchseq = sprite.touch_seq
	else:
		the_gui.set_touchseq = '%s %d' % sprite.touch_seq
	the_gui.set_basedie = sprite.base_die
	the_gui.set_gold = sprite.gold
	the_gui.set_hitpoints = sprite.hitpoints
	the_gui.set_strength = sprite.strength
	the_gui.set_defense = sprite.defense
	the_gui.set_exp = sprite.exp
	the_gui.set_sound = sprite.sound
	the_gui.set_vision = sprite.vision
	the_gui.set_nohit = sprite.nohit
	the_gui.set_touchdamage = sprite.touch_damage
	updating = False

def update_gui (dummy):
	"""Change selected screen and sprite to match values from settings window"""
	global fselect
	if updating:
		return
	screen = int (the_gui.get_screen)
	if screen not in data.world.room:
		View.update (viewmap)
		return
	# Selected screen: update
	# Screen script
	data.world.room[screen].script = the_gui.get_screen_script
	# Screen music
	data.world.room[screen].music = the_gui.get_screen_music
	# Indoor
	data.world.room[screen].indoor = the_gui.get_indoor
	# Changing the selected sprite is handled in its own function, so doesn't need anything here.
	# The rest is about the selected sprite, if any
	if fselect == None or fselect[3] == None:
		View.update (viewmap)
		return
	sprite = data.world.room[screen].sprite[fselect[3]]
	name = the_gui.get_name
	if name not in data.world.room[fselect[2]].sprite:
		# The name is not in the list, so it has changed (and is not equal to another name).
		s = data.world.room[fselect[2]].sprite[fselect[3]]
		del data.world.room[fselect[2]].sprite[fselect[3]]
		fselect = (fselect[0], fselect[1], fselect[2], name, fselect[4])
		data.world.room[fselect[2]].sprite[fselect[3]] = s
	sprite.x = int (the_gui.get_x)
	sprite.y = int (the_gui.get_y)
	seq = the_gui.get_seq.split ()
	if len (seq) == 1:
		if data.seq.find_seq (seq[0]) != None:
			sprite.seq = seq[0]
		else:
			print 'seq not found:', seq
	else:
		if data.seq.find_seq (seq) != None:
			sprite.seq = (seq[0], int (seq[1]))
		else:
			print 'collection not found:', seq
	frame = int (the_gui.get_frame)
	if frame < len (data.seq.find_seq (sprite.seq).frames):
		sprite.frame = frame
	type = the_gui.get_type
	if type == 'background':
		sprite.type = 0
	elif type == 'normal':
		sprite.type = 1
	elif type == 'invisible':
		sprite.type = 3
	else:
		raise AssertionError ('Invalid sprite type %s' % type)
	sprite.size = int (the_gui.get_size)
	brain = the_gui.get_brain
	if brain in dink.brains:
		sprite.brain = brain
	sprite.script = the_gui.get_script
	sprite.speed = int (the_gui.get_speed)
	collection = the_gui.get_basewalk
	if data.seq.find_collection (collection) != None:
		sprite.base_walk = collection
	collection = the_gui.get_baseidle
	if data.seq.find_collection (collection) != None:
		sprite.base_idle = collection
	collection = the_gui.get_baseattack
	if data.seq.find_collection (collection) != None:
		sprite.base_attack = collection
	sprite.timer = int (the_gui.get_timer)
	sprite.que = int (the_gui.get_que)
	sprite.hard = the_gui.get_ishard
	if the_gui.get_crop:
		sprite.left = int (the_gui.get_left)
		sprite.top = int (the_gui.get_top)
		sprite.right = int (the_gui.get_right)
		sprite.bottom = int (the_gui.get_bottom)
	else:
		sprite.left = 0
		sprite.top = 0
		sprite.right = 0
		sprite.bottom = 0
	if the_gui.get_warp:
		remove_warptarget (screen, name)
		sprite.warp = (int (the_gui.get_warpscreen), int (the_gui.get_warpx), int (the_gui.get_warpy))
		add_warptarget (screen, name)
	else:
		remove_warptarget (screen, name)
		sprite.warp = None
	seq = the_gui.get_touchseq.split ()
	if len (seq) == 1:
		if data.seq.find_seq (seq[0]) != None:
			sprite.touch_seq = seq[0]
	else:
		if data.seq.find_seq (seq) != None:
			sprite.touch_seq = seq
	collection = the_gui.get_basedie
	if data.seq.find_collection (collection) != None:
		sprite.base_die = collection
	sprite.gold = int (the_gui.get_gold)
	sprite.hitpoints = int (the_gui.get_hitpoints)
	sprite.strength = int (the_gui.get_strength)
	sprite.defense = int (the_gui.get_defense)
	sprite.exp = int (the_gui.get_exp)
	sprite.sound = the_gui.get_sound
	sprite.vision = int (the_gui.get_vision)
	sprite.nohit = the_gui.get_nohit
	sprite.touch_damage = int (the_gui.get_touchdamage)
	View.update (viewmap)

def do_edit (s):
	if s == '':
		return
	name = os.path.join (tmpdir, s + '.c')
	if s not in data.script.data:
		data.script.data[s] = ''
		# Create the empty file.
		open (name, 'w')
	os.system (the_gui['run-script'].replace ('$SCRIPT', name))

def edit_screen_script (self, dummy = None):
	do_edit (the_gui.get_screen_script)

def edit_script (self, dummy = None):
	do_edit (the_gui.get_script)

root = sys.argv[1]
data = dink.Dink (root)
# initialize warp targets.
for n in data.world.room.keys ():
	for s in data.world.room[n].sprite:
		add_warptarget (n, s)
viewmap = ViewMap ()
viewseq = ViewSeq ()
viewcollection = ViewCollection ()
viewframe = ViewFrame ()
viewdir = ViewDir ()
viewtiles = ViewTiles ()
viewworld = ViewWorld ()

tmpdir = tempfile.mkdtemp (prefix = 'dink-scripts-')
for s in data.script.data:
	open (os.path.join (tmpdir, s + '.c'), 'w').write (data.script.data[s])

the_gui = gui.gui (external = { 'viewmap': viewmap, 'viewseq': viewseq, 'viewcollection': viewcollection, 'viewframe': viewframe, 'viewdir': viewdir, 'viewtiles': viewtiles, 'viewworld': viewworld })
the_gui.update = update_gui
the_gui.new_sprite = new_sprite
the_gui.edit_screen_script = edit_screen_script
the_gui.edit_script = edit_script
the_gui ()

for s in data.script.data:
	os.unlink (os.path.join (tmpdir, s + '.c'))
os.rmdir (tmpdir)
