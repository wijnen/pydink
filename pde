#!/usr/bin/env python

# pde - pydink editor: editor for pydink games.
# Copyright 2011 Bas Wijnen
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gtk
import gui
import re
import os
import sys
import dink
import gtkdink
import StringIO
import math
import random
import Image
import tempfile
import glib

sys.path += (os.path.join (glib.get_user_config_dir (), 'pydink'),)
import dinkconfig

def keylist (x, keyfun):
	l = x.keys ()
	l.sort (key = keyfun)
	return l

def seqlist ():
	return keylist (data.seq.seq, lambda x: data.seq.seq[x].code)

def collectionlist ():
	return keylist (data.seq.collection, lambda x: data.seq.collection[x]['code'])

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
spriteselect = []		# Currently selected sprites: list of (screen, name, is_warp) tuples. 
warptargets = {'broken':set ()}	# Map of warp targets per room.
screenzoom = 50			# Number of pixels per tile in view.

def make_avg ():
	assert len (spriteselect) != 0
	avg = (0, 0)
	for s in spriteselect:
		if s[2]:
			# Don't paste warp points.
			continue
		# subtract the 20 pixels after computing the average.
		src = data.world.room[s[0]].sprite[s[1]]
		sx = (s[0] - 1) % 32 * 50 * 12
		sy = (s[0] - 1) / 32 * 50 * 8
		avg = avg[0] + src.x + sx, avg[1] + src.y + sy
	return avg[0] / len (spriteselect) - 20, avg[1] / len (spriteselect)

def make_dist (a, b):
	# Make sure it cannot be 0 by adding 1.
	return int (math.sqrt ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)) + 1

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
	collectiontype = None
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
				the_gui.set_basedeath = sel
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
	def start (self, widget):
		self.realize ()
		if View.started != None:
			View.update (self)
			return
		data.set_window (self.get_window ())
		View.started = False
		View.gc = self.make_gc ('default-gc')
		View.gridgc = self.make_gc ('grid-gc')
		View.bordergc = self.make_gc ('border-gc')
		View.invalidgc = self.make_gc ('invalid-gc')
		View.selectgc = self.make_gc ('select-gc')
		View.noselectgc = self.make_gc ('noselect-gc')
		View.noshowgc = self.make_gc ('noshow-gc')
		View.hardgc = self.make_gc ('hard-gc')
		View.pastegc = self.make_gc ('paste-gc')
		View.emptygc = self.make_gc ('empty-gc')
		View.whitegc = self.make_gc ('white-gc')
		View.started = True
		data.set_scale (screenzoom)
		View.update (self)
	def __init__ (self):
		gtk.DrawingArea.__init__ (self)
		View.components += (self,)
		self.buffer = None		# Backing store for the screen.
		self.pointer_pos = (0, 0)	# Current position of pointer.
		self.selecting = False		# Whether tiles are being selected, or a sequence is being moved at this moment.
		self.panning = False		# Whether the screen is panned at this moment.
		self.offset = (0, 0)		# Current pan setting
		self.screensize = (0, 0)	# Size of the viewport in pixels (updated by configure).
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
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
		if dinkconfig.lowmem and dinkconfig.nobackingstore:
			self.buffer = self.get_window ()
		else:
			self.buffer = gtk.gdk.Pixmap (self.get_window (), width, height)
		if View.started == True:
			self.move (None, None)
			View.update (self)
	def expose (self, widget, e):
		if dinkconfig.lowmem and dinkconfig.nobackingstore:
			self.update ()
		else:
			self.get_window ().draw_drawable (View.gc, self.buffer, e.area[0], e.area[1], e.area[0], e.area[1], e.area[2], e.area[3])
	def draw_tile (self, screenpos, worldpos, screen_lines):
		b = self.find_tile (worldpos)
		tiles = data.get_tiles (b[0])
		if tiles != None:
			w, h = tiles.get_size ()
			if b[1] * screenzoom >= w or b[2] * screenzoom >= h:
				self.buffer.draw_rectangle (View.invalidgc, True, screenpos[0] + 1, screenpos[1] + 1, screenzoom, screenzoom)
			else:
				self.buffer.draw_drawable (View.gc, tiles, b[1] * screenzoom, b[2] * screenzoom, screenpos[0], screenpos[1], screenzoom, screenzoom)
		else:
			self.buffer.draw_rectangle (View.invalidgc, True, screenpos[0], screenpos[1], screenzoom, screenzoom)
		if worldpos[1] % 8 == 0:
			self.buffer.draw_line (View.bordergc, screenpos[0], screenpos[1], screenpos[0] + screenzoom - 1, screenpos[1])
		if worldpos[0] % 12 == 0:
			self.buffer.draw_line (View.bordergc, screenpos[0], screenpos[1], screenpos[0], screenpos[1] + screenzoom - 1)
		if screen_lines:
			if worldpos[1] % 8 != 0:
				self.buffer.draw_line (View.gridgc, screenpos[0], screenpos[1], screenpos[0] + screenzoom - 1, screenpos[1])
			if worldpos[0] % 12 != 0:
				self.buffer.draw_line (View.gridgc, screenpos[0], screenpos[1] + 1, screenpos[0], screenpos[1] + screenzoom - 1)
	def draw_tile_hard (self, screenpos, worldpos):
		n = (worldpos[1] / 8) * 32 + (worldpos[0] / 12) + 1
		if n not in data.world.room:
			return
		h = data.world.room[n].hard
		if h != '':
			tiles = data.get_hard_tiles (h)
			if tiles:
				self.buffer.draw_pixbuf (View.gc, tiles, (worldpos[0] % 12) * screenzoom, (worldpos[1] % 8) * screenzoom, screenpos[0], screenpos[1], screenzoom, screenzoom)
			return
		b = self.find_tile (worldpos)
		if b[0] >= 0:
			tiles = data.get_hard_tiles (b[0])
			w, h = tiles.get_width (), tiles.get_height ()
			if b[1] * screenzoom >= w or b[2] * screenzoom >= h:
				return
			self.buffer.draw_pixbuf (None, tiles, b[1] * screenzoom, b[2] * screenzoom, screenpos[0], screenpos[1], screenzoom, screenzoom)
	def make_pixbuf50 (self, pb, newsize):	# TODO: scale to fit window.
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
		offset = [(x % 50) * screenzoom / 50 for x in self.offset]
		screens = set ()
		# Fill screens with all screens from which sprites should be drawn.
		for y in range (origin[1] / 8, origin[1] / 8 + self.screensize[1] / screenzoom / 8 + 1):
			for x in range (origin[0] / 12, origin[0] / 12 + self.screensize[0] / screenzoom / 12 + 1):
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
		for y in range (origin[1], origin[1] + self.screensize[1] / screenzoom + 1):
			for x in range (origin[0], origin[0] + self.screensize[0] / screenzoom + 1):
				if (x < 0 or x >= self.tiles[0]) or (y < 0 or y >= self.tiles[1]):
					self.buffer.draw_rectangle (self.emptygc, True, (x - origin[0]) * screenzoom, (y - origin[1]) * screenzoom, screenzoom, screenzoom)
					continue
				screenpos = (x - origin[0]) * screenzoom - offset[0], (y - origin[1]) * screenzoom - offset[1]
				worldpos = x, y
				self.draw_tile (screenpos, worldpos)
				check = (worldpos[0], worldpos[1], which)
				if check in select.data:
					if check == select.start:
						self.buffer.draw_rectangle (self.noshowgc, False, screenpos[0] + 1, screenpos[1] + 1, screenzoom - 2, screenzoom - 2)
					else:
						self.buffer.draw_rectangle (self.selectgc, False, screenpos[0] + 1, screenpos[1] + 1, screenzoom - 2, screenzoom - 2)
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
		diff = [(pos[x] - self.pointer_pos[x]) * 50 / screenzoom for x in range (2)]
		self.pointer_pos = pos
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
		self.update ()
	def pos_from_event (self, e):
		return [(self.offset[x] + int (e[x])) / screenzoom for x in range (2)]
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
	def draw_seq (self, pos, pixbuf):
		dpos = [pos[t] * self.tilesize - self.offset[t] for t in range (2)]
		if pixbuf == None:
			self.buffer.draw_rectangle (self.invalidgc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
		else:
			self.buffer.draw_rectangle (self.whitegc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
			self.buffer.draw_pixbuf (None, self.make_pixbuf50 (pixbuf, self.tilesize), 0, 0, dpos[0], dpos[1])

class ViewMap (View):
	def __init__ (self):
		View.__init__ (self)
		self.roomsource = None		# Source for a newly created room (for copying).
		self.moveinfo = None		# Information for what to do with pointer move events.
		self.pointer_tile = (0, 0)	# Tile that the pointer is currently pointing it, in world coordinates. That is: pointer_pos / 50.
		self.waitselect = None		# Selection to use if button is released without moving.
		self.tiles = (12 * 32, 8 * 24)	# Total number of tiles on map.
		self.current_selection = 0	# Index of "current" sprite in selection.
		self.set_size_request (50 * 12, 50 * 8)
		self.firstconfigure = True
	def configure (self, widget, e):
		View.configure (self, widget, e)
		if self.firstconfigure:
			self.firstconfigure = False
			# Initial offset is centered on dink starting screen.
			screen = data.script.start_map
			sc = ((screen - 1) % 32, (screen - 1) / 32)
			s = (12, 8)
			self.offset = [sc[x] * s[x] * screenzoom + (s[x] / 2) * screenzoom - self.screensize[x] / 2 for x in range (2)]
	def find_tile (self, worldpos):
		n = (worldpos[1] / 8) * 32 + (worldpos[0] / 12) + 1
		if n in data.world.room:
			return data.world.room[n].tiles[worldpos[1] % 8][worldpos[0] % 12]
		return [-1, -1, -1]
	def draw_tile (self, screenpos, worldpos):
		View.draw_tile (self, screenpos, worldpos, False)
		if not self.selecting:
			if (worldpos[0] - self.pointer_tile[0] + select.start[0], worldpos[1] - self.pointer_tile[1] + select.start[1], select.start[2]) in select.data:
				self.buffer.draw_rectangle (self.pastegc, False, screenpos[0] + 1, screenpos[1] + 1, screenzoom - 2, screenzoom - 2)
	def update (self):
		if self.buffer == None:
			return
		screens = View.draw_tiles (self, 0)
		# Draw sprites.
		lst = []
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
				is_selected = (s, spr, False) in spriteselect
				lst += ((pos, sp, seq, is_selected),)
		# Add warp targets.
		for s in screens:
			if s not in warptargets:
				continue
			sy = ((s - 1) / 32) * 50 * 8
			sx = ((s - 1) % 32) * 50 * 12
			for n, spr in warptargets[s]:
				sp = data.world.room[n].sprite[spr]
				seq = data.seq.find_seq (sp.seq)
				is_selected = (n, spr, True) in spriteselect
				lst += (((None, 0), sp, seq, is_selected),)
		# Sort the list by y coordinate, taking depth que into account.
		lst.sort (key = lambda x: x[0][1] - x[1].que)
		# Now draw them all in the right order. First the pixbufs, then hardness, then wireframe information.
		for s in lst:
			if s[0][0] == None:
				# This is a warp target.
				continue
			(x, y), (left, top, right, bottom), box = data.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
			# Draw the pixbuf.
			pb = data.get_seq (s[2], s[1].frame)
			if box != None:
				pb = pb.subpixbuf (box[0], box[1], box[2] - box[0], box[3] - box[1])
			w = (right - left) * screenzoom / 50
			h = (bottom - top) * screenzoom / 50
			if w > 0 and h > 0:
				pb = pb.scale_simple (w, h, gtk.gdk.INTERP_NEAREST)
				self.buffer.draw_pixbuf (None, pb, 0, 0, left * screenzoom / 50, top * screenzoom / 50)
		# Tile hardness.
		origin = [x / 50 for x in self.offset]
		offset = [(x % 50) * screenzoom / 50 for x in self.offset]
		for y in range (offset[1] / screenzoom, (self.screensize[1] + offset[1] + screenzoom) / screenzoom):
			for x in range (offset[0] / screenzoom, (self.screensize[0] + offset[0] + screenzoom) / screenzoom):
				if (origin[0] + x < 0 or origin[0] + x >= self.tiles[0]) or (origin[1] + y < 0 or origin[1] + y >= self.tiles[1]):
					continue
				self.draw_tile_hard (((x * 50 - offset[0]) * 50 / screenzoom, (y * 50 - offset[1]) * 50 / screenzoom), (origin[0] + x, origin[1] + y))
		# Sprite hardness.
		for spr in lst:
			if spr[0][0] == None:
				# This is a warp target.
				continue
			if not spr[1].hard:
				if spr[3]:
					(x, y), (left, top, right, bottom), box = data.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
					self.buffer.draw_rectangle (self.noshowgc, False, (x + spr[2].frames[spr[1].frame].hardbox[0]) * screenzoom / 50, (y + spr[2].frames[spr[1].frame].hardbox[1]) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[2] - spr[2].frames[spr[1].frame].hardbox[0] - 1) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[3] - spr[2].frames[spr[1].frame].hardbox[1] - 1) * screenzoom / 50)
				continue
			(x, y), (left, top, right, bottom), box = data.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
			if spr[3]:
				self.buffer.draw_rectangle (self.hardgc, False, (x + spr[2].frames[spr[1].frame].hardbox[0]) * screenzoom / 50, (y + spr[2].frames[spr[1].frame].hardbox[1]) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[2] - spr[2].frames[spr[1].frame].hardbox[0] - 1) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[3] - spr[2].frames[spr[1].frame].hardbox[1] - 1) * screenzoom / 50)
			else:
				self.buffer.draw_rectangle (self.hardgc, False, (x + spr[2].frames[spr[1].frame].hardbox[0]) * screenzoom / 50, (y + spr[2].frames[spr[1].frame].hardbox[1]) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[2] - spr[2].frames[spr[1].frame].hardbox[0] - 1) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[3] - spr[2].frames[spr[1].frame].hardbox[1] - 1) * screenzoom / 50)
		# Wireframe information for all except selected sprites.
		for spr in lst:
			if spr[3]:
				continue
			if spr[0][0] != None:
				# This is a sprite, not a warp target.
				(x, y), (left, top, right, bottom), box = data.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
				# Que: not drawn for not selected sprites.
				# Hotspot.
				self.buffer.draw_line (self.noselectgc, (x - 10) * screenzoom / 50, y * screenzoom / 50, (x + 10) * screenzoom / 50, y * screenzoom / 50)
				self.buffer.draw_line (self.noselectgc, x * screenzoom / 50, (y - 10) * screenzoom / 50, x * screenzoom / 50, (y + 10) * screenzoom / 50)
			else:
				# This is a warp target.
				n, x, y = spr[1].warp
				y += ((n - 1) / 32) * 8 * 50 - self.offset[1]
				x += ((n - 1) % 32) * 12 * 50 - self.offset[0] - 20
				self.buffer.draw_line (self.noselectgc, (x - 20) * screenzoom / 50, y * screenzoom / 50, (x + 20) * screenzoom / 50, y * screenzoom / 50)
				self.buffer.draw_line (self.noselectgc, x * screenzoom / 50, (y - 20) * screenzoom / 50, x * screenzoom / 50, (y + 20) * screenzoom / 50)
				self.buffer.draw_arc (self.noselectgc, False, (x - 15) * screenzoom / 50, (y - 15) * screenzoom / 50, 30 * screenzoom / 50, 30 * screenzoom / 50, 0, 64 * 360)
		# No matter what is visible, always show selected sprite's stuff on top.
		for spr in lst:
			if not spr[3]:
				continue
			if spr[0][0] != None:
				# This is a sprite, not a warp target.
				(x, y), (left, top, right, bottom), box = data.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
				# Que.
				self.buffer.draw_line (self.noshowgc, (x - 40) * screenzoom / 50, (y - spr[1].que) * screenzoom / 50, (x + 40) * screenzoom / 50, (y - spr[1].que) * screenzoom / 50)
				# Hotspot
				self.buffer.draw_line (self.selectgc, (x - 10) * screenzoom / 50, y * screenzoom / 50, (x + 10) * screenzoom / 50, y * screenzoom / 50)
				self.buffer.draw_line (self.selectgc, x * screenzoom / 50, (y - 10) * screenzoom / 50, x * screenzoom / 50, (y + 10) * screenzoom / 50)
			else:
				# This is a warp target.
				n, x, y = spr[1].warp
				y += ((n - 1) / 32) * 8 * 50 - self.offset[1]
				x += ((n - 1) % 32) * 12 * 50 - self.offset[0] - 20
				x = x * screenzoom / 50
				y = y + screenzoom / 50
				s = 20 * screenzoom / 50
				a = 15 * screenzoom / 50
				self.buffer.draw_line (self.selectgc, x - s, y, x + s, y)
				self.buffer.draw_line (self.selectgc, x, y - s, x, y + s)
				self.buffer.draw_arc (self.selectgc, False, x - a, y - a, a * 2, a * 2, 0, 64 * 360)
				self.buffer.draw_rectangle (self.selectgc, False, x - s, y - s, s * 2, s * 2)
		# Finally, draw a line if we're resizing or zooming.
		if self.moveinfo != None and self.moveinfo[0] == 'resize':
			avg = [self.moveinfo[1][0][t] - self.offset[t] for t in range (2)]
			self.buffer.draw_line (self.noshowgc, avg[0], avg[1], self.pointer_pos[0], self.pointer_pos[1])
		# And a box if we're selecting.
		if self.moveinfo != None and self.moveinfo[0] == 'spriteselect' and self.moveinfo[1][0][0] != self.moveinfo[1][1][0] and self.moveinfo[1][0][1] != self.moveinfo[1][1][1]:
			x = [(self.moveinfo[1][t][0] - self.offset[0]) * screenzoom / 50 for t in range (2)]
			y = [(self.moveinfo[1][t][1] - self.offset[1]) * screenzoom / 50 for t in range (2)]
			x.sort ()
			y.sort ()
			self.buffer.draw_rectangle (self.selectgc, False, x[0], y[0], x[1] - x[0], y[1] - y[0])
		if not (dinkconfig.lowmem and dinkconfig.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def make_global (self, screen, pos):
		s = (12, 8)
		spos = ((screen - 1) % 32, (screen - 1) / 32)
		return [pos[x] + s[x] * spos[x] * 50 for x in range (2)]
	def goto (self, pos):
		self.offset = [pos[x] - self.screensize[x] * screenzoom / 100 for x in range (2)]
		self.update ()
		viewworld.update ()
	def make_cancel (self):
		ret = [self.offset, [], screenzoom]
		for s in spriteselect:
			spr = data.world.room[s[0]].sprite[s[1]]
			if s[2]:
				ret[1] += (spr.warp,)
			else:
				ret[1] += (((spr.x, spr.y), spr.que, spr.size, (spr.left, spr.top, spr.right, spr.bottom)),)
		return ret
	def keypress (self, widget, e):
		global copystart
		global screenzoom
		self.selecting = False
		p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
		sx = p[0] / (12 * 50)
		sy = p[1] / (8 * 50)
		ox = p[0] - sx * 12 * 50 + 20
		oy = p[1] - sy * 8 * 50
		n = sy * 32 + sx + 1
		if e.keyval == gtk.keysyms.a: # set base attack
			View.collectiontype = 'attack'
			viewcollection.direction (None)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.b: # set base walk
			View.collectiontype = 'walk'
			the_gui.setcollection = True
			viewcollection.direction (None)
		elif e.keyval == gtk.keysyms.c: # start cropping
			t = []
			for s in spriteselect:
				spr = data.world.room[s[0]].sprite[s[1]]
				if s[2]:
					continue
				t += ([0, 0],)
				ssx = ((s[0] - 1) % 32) * 12 * 50
				ssy = ((s[0] - 1) / 32) * 8 * 50
				if p[0] < ssx + spr.left:
					t[-1][0] = -1
				elif p[0] >= ssx + spr.right:
					t[-1][0] = 1
				if p[1] < ssy + spr.top:
					t[-1][1] = -1
				elif p[1] >= ssy + spr.bottom:
					t[-1][1] = 1
			if len (t) == 0:
				return
			self.moveinfo = 'crop', t, self.make_cancel ()
		elif e.keyval == gtk.keysyms.d: # set base death
			View.collectiontype = 'death'
			viewcollection.direction (None)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.e: # edit script(s)
			for s in spriteselect:
				spr = data.world.room[s[0]].sprite[s[1]]
				if not spr.script:
					continue
				do_edit (spr.script)
		elif e.keyval == gtk.keysyms.f: # fill selected tiles with buffer
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
		elif e.keyval == gtk.keysyms.g: # TODO: make group.
			pass
		elif e.keyval == gtk.keysyms.h: # toggle is_hard
			for s in spriteselect:
				if s[2]:
					continue
				spr = data.world.room[s[0]].sprite[s[1]]
				spr.hard = not spr.hard
			update_editgui ()
		elif e.keyval == gtk.keysyms.i: # set base idle
			View.collectiontype = 'idle'
			viewcollection.direction (None)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.j: # jump to selected
			target = (0, 0)
			if len (spriteselect) > 0:
				for s in spriteselect:
					spr = data.world.room[s[0]].sprite[s[1]]
					if s[2]:
						n = self.make_global (spr.warp[0], spr.warp[1:])
					else:
						n = self.make_global (s[0], (spr.x, spr.y))
					target = (target[0] + n[0], target[1] + n[1])
				self.goto ([target[x] / len (spriteselect) for x in range (2)])
		elif e.keyval == gtk.keysyms.k: # kill sprite
			for killer in spriteselect:
				# Remove warp target in any case.
				remove_warptarget (killer[0], killer[1])
				if not killer[2]:
					del data.world.room[killer[0]].sprite[killer[1]]
				else:
					# Delete warp point
					data.world.room[killer[0]].sprite[killer[1]].warp = None
			spriteselect[:] = []
			update_editgui ()
		elif e.keyval == gtk.keysyms.l: # change largeness (start resizing)
			if len (spriteselect) != 0:
				# Required info:
				# - average hotspot of selected sprites
				# - current distance from hotspot
				# - current size value
				avg = make_avg ()
				dist = make_dist (avg, p)
				size = [data.world.room[x[0]].sprite[x[1]].size for x in spriteselect]
				self.moveinfo = 'resize', (avg, dist, size), self.make_cancel ()
		elif e.keyval == gtk.keysyms.m: # move selected sprites
			self.moveinfo = 'move', None, self.make_cancel ()
		elif e.keyval == gtk.keysyms.n: # jump to next
			if len (spriteselect) > 0:
				self.current_selection += 1
				if self.current_selection >= len (spriteselect):
					self.current_selection = 0
				s = spriteselect[self.current_selection]
				spr = data.world.room[s[0]].sprite[s[1]]
				self.goto (self.make_global (s[0], (spr.x, spr.y)))
		elif e.keyval == gtk.keysyms.o: # open group
			# TODO
			pass
		elif e.keyval == gtk.keysyms.p: # play
			os.system (the_gui['sync'])
			sync ()
			p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
			n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
			data.play (n, p[0] % (12 * 50) + 20, p[1] % (8 * 50))
		elif e.keyval == gtk.keysyms.q: # move que
			self.moveinfo = 'que', None, self.make_cancel ()
		elif e.keyval == gtk.keysyms.r: # random fill tiles
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
		elif e.keyval == gtk.keysyms.s: # save
			sync ()
			data.save ()
		elif e.keyval == gtk.keysyms.t: # show tilescreen
			the_gui.settiles = True
		elif e.keyval == gtk.keysyms.u: # undo
			# TODO
			pass
		elif e.keyval == gtk.keysyms.v: # set visual (of sprite? of view?)
			# TODO
			pass
		elif e.keyval == gtk.keysyms.w: # toggle select warp or sprite.
			if len (spriteselect) == 1:
				spr = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
				if spr.warp == None:
					global updating
					updating = True
					n = (p[1] / (50 * 8)) * 32 + (p[0] / (50 * 12)) + 1
					spr.warp = (n, p[0] % (50 * 12) + 20, p[1] % (50 * 8))
					the_gui.set_warpscreen = n
					the_gui.set_warpx = p[0] % (12 * 50)
					the_gui.set_warpy = p[1] % (8 * 50)
					the_gui.set_warp = True
					the_gui.set_ishard = True
					add_warptarget (spriteselect[0][0], spriteselect[0][1])
					updating = False
			newselect = []
			for s in spriteselect:
				spr = data.world.room[s[0]].sprite[s[1]]
				if spr.warp != None:
					newselect += ((s[0], s[1], not s[2]),)
			spriteselect[:] = newselect
		elif e.keyval == gtk.keysyms.x: # exit
			gui.quit ()
		elif e.keyval == gtk.keysyms.y: # yank (copy) selected tiles into buffer
			copybuffer.clear ()
			for i in select.data:
				s = View.find_tile (self, i, i[2])
				copybuffer.add ((i[0], i[1], i[2], s[0], s[1], s[2]))
			copystart = select.start
		elif e.keyval == gtk.keysyms.z: # start screen zoom
			center = self.screensize[0] / 2, self.screensize[1] / 2
			dist = make_dist (center, p)
			self.moveinfo = 'screenzoom', (center, dist, [screenzoom]), self.make_cancel ()
		elif e.keyval == gtk.keysyms.slash: # search sprite by pattern
			# TODO
			pass
		elif e.keyval == gtk.keysyms.quoteright: # toggle nohit
			for s in spriteselect:
				if s[2]:
					continue
				spr = data.world.room[s[0]].sprite[s[1]]
				spr.nohit = not spr.nohit
			update_editgui ()
		elif e.keyval == gtk.keysyms.quoteleft: # enter comand
			# TODO
			pass
		elif e.keyval == gtk.keysyms.minus: # unselect all
			spriteselect[:] = []
			select.clear ()
		elif e.keyval == gtk.keysyms.BackSpace: # restore screen zoom 100%
			mid = [self.offset[x] + self.screensize[x] * 25 / screenzoom for x in range (2)]
			screenzoom = 50
			self.offset = [mid[x] - self.screensize[x] / 2 for x in range (2)]
			data.set_scale (screenzoom)
		elif e.keyval == gtk.keysyms.Home: # center screen
			s = (12, 8)
			self.goto ([(self.pointer_pos[x] + self.offset[x]) / s[x] / 50 * s[x] * 50 + s[x] / 2 * 50 for x in range (2)])
		elif e.keyval == gtk.keysyms.Insert: # insert screen
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
		elif e.keyval == gtk.keysyms.Delete: # delete screen
			n = (p[1] / (8 * 50)) * 32 + (p[0] / (12 * 50)) + 1
			if n in data.world.room:
				del data.world.room[n]
				if self.roomsource == n:
					self.roomsource = None
				View.update (self)
		elif e.keyval == gtk.keysyms.Escape: # Abort current action
			# Reset change.
			if self.moveinfo != None:
				self.offset = self.moveinfo[2][0]
				screenzoom = self.moveinfo[2][2]
				data.set_scale (screenzoom)
				for s in range (len (spriteselect)):
					spr = data.world.room[spriteselect[s][0]].sprite[spriteselect[s][1]]
					if spriteselect[s][2]:
						spr.warp = self.moveinfo[2][s][1]
					else:
						spr.x, spr.y = self.moveinfo[2][1][s][0]
						spr.que = self.moveinfo[2][1][s][1]
						spr.size = self.moveinfo[2][1][s][2]
						spr.left, spr.top, spr.right, spr.bottom = self.moveinfo[2][1][s][3]
				update_editgui ()
				self.moveinfo = None
		elif e.keyval == gtk.keysyms.Return: # Confirm operation.
			self.moveinfo = None
		elif e.keyval == gtk.keysyms.space: # start screen pan
			self.moveinfo = 'pan', p, self.make_cancel ()
		elif e.keyval == gtk.keysyms.KP_0 or e.keyval == gtk.keysyms.KP_Insert: # new sprite from sequence
			self.newinfo = p, (ox, oy), n
			viewseq.update ()
			the_gui.setseq = True
		elif e.keyval == gtk.keysyms.KP_1 or e.keyval == gtk.keysyms.KP_End: # new sprite with direction 1
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (1)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_2 or e.keyval == gtk.keysyms.KP_Down: # new sprite with direction 2
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (2)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_3 or e.keyval == gtk.keysyms.KP_Next: # new sprite with direction 3
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (3)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_4 or e.keyval == gtk.keysyms.KP_Left: # new sprite with direction 4
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (4)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_5 or e.keyval == gtk.keysyms.KP_Begin: # new sprite from collection with any direction
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (None)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_6 or e.keyval == gtk.keysyms.KP_Right: # new sprite with direction 6
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (6)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_7 or e.keyval == gtk.keysyms.KP_Home: # new sprite with direction 7
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (7)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_8 or e.keyval == gtk.keysyms.KP_Up: # new sprite with direction 8
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (8)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.KP_9 or e.keyval == gtk.keysyms.KP_Prior: # new sprite with direction 9
			self.newinfo = p, (ox, oy), n
			viewcollection.direction (9)
			the_gui.setcollection = True
		elif e.keyval == gtk.keysyms.equal: # view world map
			self.moveinfo = None
			viewworld.old_offset = self.offset
			the_gui.setworld = True
		elif e.keyval == gtk.keysyms.Left:
			self.handle_cursor ((-1, 0))
		elif e.keyval == gtk.keysyms.Up:
			self.handle_cursor ((0, -1))
		elif e.keyval == gtk.keysyms.Right:
			self.handle_cursor ((1, 0))
		elif e.keyval == gtk.keysyms.Down:
			self.handle_cursor ((0, 1))
		self.update ()
		return True
	def handle_cursor (self, diff):
		p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
		if self.moveinfo == None:
			return
		elif self.moveinfo[0] == 'tileselect':
			# No response to cursor keys.
			pass
		elif self.moveinfo[0] == 'spriteselect':
			# No response to cursor keys.
			pass
		elif self.moveinfo[0] == 'resize':
			for s in spriteselect:
				if s[2]:
					continue
				data.world.room[s[0]].sprite[s[1]].size -= diff[1] * 10 + diff[0]
			# adjust moveinfo to use new data, but keep old cancel data.
			avg = make_avg ()
			dist = make_dist (avg, p)
			size = [data.world.room[x[0]].sprite[x[1]].size for x in spriteselect]
			self.moveinfo = 'resize', (avg, dist, size), self.moveinfo[2]
			update_editgui ()
		elif self.moveinfo[0] == 'move':
			self.do_move (diff)
		elif self.moveinfo[0] == 'que':
			for s in spriteselect:
				if s[2]:
					continue
				data.world.room[s[0]].sprite[s[1]].que -= diff[1] * 10 + diff[0]
			update_editgui ()
		elif self.moveinfo[0] == 'crop':
			# TODO
			pass
		elif self.moveinfo[0] == 'screenzoom':
			global screenzoom
			mid = [self.offset[x] + self.screensize[x] * 25 / screenzoom for x in range (2)]
			screenzoom += diff[1] * 10 + diff[0]
			if screenzoom < 1:
				screenzoom = 1
			self.offset = [mid[x] - self.screensize[x] * 25 / screenzoom for x in range (2)]
			data.set_scale (screenzoom)
			# adjust moveinfo to use new size
			dist = make_dist (self.moveinfo[1][0], p)
			self.moveinfo = 'screenzoom', (self.moveinfo[1][0], dist, [screenzoom]), self.moveinfo[2]
		elif self.moveinfo[0] == 'pan':
			self.offset = [self.offset[t] + diff[t] for t in range (2)]
		self.update ()
	def find_sprites (self, region, point):
		rx = [region[t][0] for t in range (2)]
		ry = [region[t][1] for t in range (2)]
		rx.sort ()
		ry.sort ()
		sx = [rx[t] / (12 * 50) for t in range (2)]
		sy = [ry[t] / (8 * 50) for t in range (2)]
		screens = []
		for dy in range (-1, sy[1] - sy[0] + 2):
			if sy[0] + dy < 0 or sy[0] + dy >= 24:
				continue
			for dx in range (-1, sx[1] - sx[0] + 2):
				if sx[0] + dx < 0 or sx[0] + dx >= 32:
					continue
				screens += ((sy[0] + dy) * 32 + (sx[0] + dx) + 1,)
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
					if point:
						seq = data.seq.find_seq (sp.seq)
						(hotx, hoty), (left, top, right, bottom), box = data.get_box (sp.size, (sp.x, sp.y), seq.frames[sp.frame], (sp.left, sp.top, sp.right, sp.bottom))
						if rx[0] - sx >= left and ry[0] - sy >= top and rx[0] - sx < right and ry[0] - sy < bottom:
							lst += ((pos[1] - sp.que, (s, spr, False), pos),)
					else:
						if pos[0] >= rx[0] and pos[0] < rx[1] and pos[1] >= ry[0] and pos[1] < ry[1]:
							lst += ((pos[1] - sp.que, (s, spr, False), pos),)
			# Add all warp points, too.
			if s in warptargets:
				for n, spr in warptargets[s]:
					sp = data.world.room[n].sprite[spr]
					pos = (sx + sp.warp[1] - 20, sy + sp.warp[2])
					if point:
						if -20 <= rx[0] - pos[0] < 20 and -20 <= ry[0] - pos[1] < 20:
							lst += ((pos[1] - sp.que, (n, spr, True), pos),)
					else:
						if pos[0] >= rx[0] and pos[0] < rx[1] and pos[1] >= ry[0] and pos[1] < ry[1]:
							lst += ((pos[1] - sp.que, (n, spr, True), pos),)
		return lst
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.offset[x] + self.pointer_pos[x] * 50 / screenzoom) / 50 for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if self.moveinfo != None and e.button == 1:
			# Finish move operation.
			self.moveinfo = None
			return
		# Select clicked screen.
		x, y = [(self.offset[x] + self.pointer_pos[x] * 50 / screenzoom) for x in range (2)]
		sx = x / (12 * 50)
		sy = y / (8 * 50)
		screen = sy * 32 + sx + 1
		if screen in data.world.room:
			selectedscreen = screen
			update_editgui ()
		keep_selection = e.state & gtk.gdk.CONTROL_MASK
		if e.button == 1: # select sprites
			# Clear tile selection.
			select.clear ()
			# Finish move operation.
			self.moveinfo = None
			# Find all sprites which are pointed at.
			lst = self.find_sprites (((x, y), (x, y)), True)
			# If the list is empty, clear the selection.
			if lst == []:
				if not keep_selection:
					spriteselect[:] = []
				self.moveinfo = 'spriteselect', [(x, y), (x, y), None], self.make_cancel ()
				return
			# Sort the sprites by depth.
			lst.sort (key = lambda x: -x[0])
			# If the currently selected sprite is in the list, select the next; otherwise select the first.
			if not keep_selection:
				if len (spriteselect) == 1:
					for s in range (len (lst)):
						if spriteselect[0] == lst[s][1]:
							spriteselect[:] = (lst[s][1],)
							pos = lst[s][2]
							if s == len (lst) - 1:
								self.waitselect = lst[0][1:]
							else:
								self.waitselect = lst[s + 1][1:]
							break
					else:
						# Current selection is not in the list. Select first and update gui.
						spriteselect[:] = (lst[0][1],)
						pos = lst[0][2]
						update_editgui ()
				else:
					# There was not a 1-sprite selection. Select first and update gui.
					spriteselect[:] = (lst[0][1],)
					pos = lst[0][2]
					update_editgui ()
			else:
				# Add first not-yet-selected sprite to the selection.
				for s in lst:
					if s[1] in spriteselect:
						continue
					spriteselect[:] = spriteselect + [s[1]]
					pos = s[2]
					break
			self.selecting = True
			self.moveinfo = 'spriteselect', [(x, y), (x, y), spriteselect[-1]], self.make_cancel ()
		elif e.button == 2:	# paste
			if select.empty ():
				# paste sprites.
				if screen not in data.world.room:
					return
				if len (spriteselect) != 0:
					newselect = []
					avg = make_avg ()
					for paster in spriteselect:
						if paster[2]:
							# Don't paste warp points.
							continue
						src = data.world.room[paster[0]].sprite[paster[1]]
						sx = (paster[0] - 1) % 32
						sy = (paster[0] - 1) / 32
						tx = x + sx * 12 * 50 + src.x - avg[0]
						ty = y + sy * 8 * 50 + src.y - avg[1]
						sx = tx / (12 * 50)
						sy = ty / (8 * 50)
						ox = tx - sx * 12 * 50 + 20
						oy = ty - sy * 8 * 50
						screen = sy * 32 + sx + 1
						name = data.world.room[screen].add_sprite ((ox, oy), src.seq, src.frame)
						sp = data.world.room[screen].sprite[name]
						sp.type = src.type
						sp.size = src.size
						sp.brain = src.brain
						sp.script = src.script
						sp.speed = src.speed
						sp.base_walk = src.base_walk
						sp.base_idle = src.base_idle
						sp.base_attack = src.base_attack
						sp.base_death = src.base_death
						sp.timing = src.timing
						sp.que = src.que
						sp.hard = src.hard
						sp.left = src.left
						sp.top = src.top
						sp.right = src.right
						sp.bottom = src.bottom
						sp.warp = None
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
						newselect += ((screen, name, False),)
					spriteselect[:] = newselect
					update_editgui ()
					self.update ()
				return
			# paste tiles.
			pos = self.pos_from_event ((e.x, e.y))
			for t in select.compute ():
				target = [pos[x] + t[x] for x in range (2)]
				n = (target[1] / 8) * 32 + (target[0] / 12) + 1
				if n not in data.world.room:
					continue
				p = [t[x] + select.start[x] for x in range (2)]
				data.world.room[n].tiles[target[1] % 8][target[0] % 12] = View.find_tile (self, p, select.start[2])
			self.update ()
		elif e.button == 3:	# select tiles
			# Clear sprite selection.
			spriteselect[:] = []
			x, y = self.pos_from_event ((e.x, e.y))
			View.tileselect (self, x, y, not e.state & gtk.gdk.CONTROL_MASK, 0)
			self.moveinfo = 'tileselect', (x, y), self.make_cancel ()
		self.update ()
	def button_off (self, widget, e):
		if e.button == 1:
			self.selecting = False
			self.moveinfo = None
			if self.waitselect != None:
				spriteselect[:] = (self.waitselect[0],)
				pos = self.waitselect[1]
				update_editgui ()
		elif e.button == 3:
			self.selecting = False
			self.moveinfo = None
		self.update ()
	def do_move (self, diff):
		for mover in range (len (spriteselect)):
			room = spriteselect[mover][0]
			sp = data.world.room[room].sprite[spriteselect[mover][1]]
			if not spriteselect[mover][2]:
				s = [((room - 1) % 32) * (12 * 50), ((room - 1) / 32) * (8 * 50)]
				p = [(sp.x - 20, sp.y)[t] + diff[t] for t in range (2)]
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
					print 'new room', rm, room
					if rm in data.world.room:
						# Move the sprite to a different room.
						name = spriteselect[mover][1]
						del data.world.room[room].sprite[name]
						room = rm
						nm = name
						i = 0
						while nm in data.world.room[room].sprite:
							nm = '%s%d' % (name, i)
							i += 1
						data.world.room[room].sprite[nm] = sp
						spriteselect[mover] = (room, nm, False)
					else:
						# New room doesn't exist; use old one.
						print 'old room after all', op
						sp.x, sp.y = op
						sp.x += 20
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
				p = [(sp.warp[1] - 20, sp.warp[2])[t] + diff[t] for t in range (2)]
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
				remove_warptarget (room, spriteselect[mover][1])
				sp.warp = ((s[1] / (8 * 50)) * 32 + (s[0] / (12 * 50)) + 1, p[0] + 20, p[1])
				add_warptarget (room, spriteselect[mover][1])
		update_editgui ()
	def move (self, widget, e):
		global screenzoom
		self.waitselect = None
		ex, ey, emask = self.get_window ().get_pointer ()
		tile = self.pointer_tile
		pos = int (ex), int (ey)
		diff = [(pos[t] - self.pointer_pos[t]) * 50 / screenzoom for t in range (2)]
		self.pointer_pos = pos
		self.pointer_tile = [(self.pointer_pos[t] + self.offset[t]) / screenzoom for t in range (2)]
		if self.moveinfo == None:
			if not select.empty ():
				self.update ()
			return
		elif self.moveinfo[0] == 'tileselect':
			View.select_tiles (self, tile, 0)
		elif self.moveinfo[0] == 'spriteselect':
			# Toggle selected-state of sprites on border.
			if self.moveinfo[1][2] != None:
				if self.moveinfo[1][2] in spriteselect:
					spriteselect.remove (self.moveinfo[1][2])
				else:
					spriteselect[:] = spriteselect + [self.moveinfo[1][2]]
				self.moveinfo[1][2] = None
			old = self.moveinfo[1][0:2]
			new = self.moveinfo[1][0], [pos[t] * 50 / screenzoom + self.offset[t] for t in range (2)]
			oldlst = self.find_sprites (old, False)
			newlst = self.find_sprites (new, False)
			for i in newlst + oldlst:
				if i not in oldlst or i not in newlst:
					if i[1] in spriteselect:
						spriteselect.remove (i[1])
					else:
						spriteselect[:] = spriteselect + [i[1]]
			self.moveinfo[1][1] = [pos[t] * 50 / screenzoom + self.offset[t] for t in range (2)]
		elif self.moveinfo[0] == 'resize':
			# moveinfo[1] is (hotspot, dist, size[]).
			p = [self.pointer_pos[t] + self.offset[t] for t in range (2)]
			dist = make_dist (self.moveinfo[1][0], p)
			for s in range (len (spriteselect)):
				if spriteselect[s][2]:
					continue
				data.world.room[spriteselect[s][0]].sprite[spriteselect[s][1]].size = self.moveinfo[1][2][s] * dist / self.moveinfo[1][1]
				# TODO: adjust position
		elif self.moveinfo[0] == 'move':
			self.do_move (diff)
		elif self.moveinfo[0] == 'que':
			for s in spriteselect:
				if s[2]:
					continue
				sp = data.world.room[s[0]].sprite[s[1]]
				sp.que -= diff[1]
		elif self.moveinfo[0] == 'crop':
			# TODO
			pass
		elif self.moveinfo[0] == 'screenzoom':
			p = [self.pointer_pos[t] + self.offset[t] for t in range (2)]
			dist = make_dist (self.moveinfo[1][0], p)
			mid = [self.offset[x] + self.screensize[x] * 25 / screenzoom for x in range (2)]
			screenzoom = self.moveinfo[1][2][0] * dist / self.moveinfo[1][1]
			if screenzoom < 1:
				screenzoom = 1
			self.offset = [mid[x] - self.screensize[x] * 25 / screenzoom for x in range (2)]
			data.set_scale (screenzoom)
		elif self.moveinfo[0] == 'pan':
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
		else:
			raise AssertionError ('invalid moveinfo type %s' % self.moveinfo[0])
		update_editgui ()
		self.update ()

class ViewSeq (View):
	def __init__ (self):
		View.__init__ (self)
		self.selected_seq = None
	def update (self):
		if self.buffer == None:
			return
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		s = seqlist ()
		# Compute tile size.
		self.tilesize = int (math.sqrt (self.screensize[0] * self.screensize[1] / len (s)))
		while True:
			self.width = self.screensize[0] / self.tilesize
			if self.width > 0:
				ns = (len (s) + self.width - 1) / self.width
				if ns * self.tilesize <= self.screensize[1]:
					break
			self.tilesize -= 1
		if self.selected_seq == None:
			for y in range (ns):
				for x in range (self.width):
					if y * self.width + x >= len (s):
						self.draw_seq ((x, y), None)
						continue
					pb = data.get_seq (data.seq.seq[s[y * self.width + x]], 1)
					self.draw_seq ((x, y), pb)
		else:
			# Draw clicked sequence.
			x0, y0 = self.selected_seq
			pos0 = y0 * self.width + x0
			pb = data.get_seq (data.seq.seq[s[pos0]], 1)
			self.draw_seq (self.selected_seq, pb)
			# Draw selectable frames.
			frames = data.seq.seq[s[pos0]].frames
			if x0 + len (frames) - 1 <= self.width:
				off = x0
			else:
				off = max (0, self.width - (len (frames) - 1))
			for f in range (1, len (frames)):
				pb = data.get_seq (data.seq.seq[s[pos0]], f)
				y = y0 + 1 + (f - 1 + off) / self.width
				x = (f - 1 + off) % self.width
				self.draw_seq ((x, y), pb)
		if not (dinkconfig.lowmem and dinkconfig.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		if e.keyval == gtk.keysyms.Escape: # Cancel operation.
			the_gui.setmap = True
		elif e.keyval == gtk.keysyms.Return: # Confirm operation.
			e.x, e.y, e.mask = self.get_window ().get_pointer ()
			e.type = gtk.gdk.BUTTON_PRESS
			e.button = 1
			self.button_on (widget, e)
	def get_selected_sequence (self, x, y):
		s = seqlist ()
		ns = (len (s) + self.width - 1) / self.width
		if x >= 0 and x < self.tilesize * self.width and y >= 0 and y < self.tilesize * ns:
			target = (y / self.tilesize) * self.width + x / self.tilesize
			if len (s) > target:
				return s[target]
		return None
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		seq = self.get_selected_sequence (*self.pointer_pos)
		if e.button == 1:	# perform action or change selected sequence
			if len (spriteselect) != 1:
				return
			if spriteselect[0][2]:
				spr = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
				spr.touch_seq = seq
				the_gui.setmap = True
				viewmap.update ()
			else:
				if seq != '':
					self.selected_seq = self.pointer_tile
					self.update ()
		elif e.button == 2:	# add new sprite
			if seq == '':
				return
			if viewmap.newinfo[2] not in data.world.room:
				# TODO: add for selected screen.
				return
			self.selected_seq = self.pointer_tile
			self.update ()
	def button_off (self, widget, e):
		if self.selected_seq == None:
			return
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		s = seqlist ()
		x0, y0 = self.selected_seq
		pos0 = y0 * self.width + x0
		frames = data.seq.seq[s[pos0]].frames
		if x0 + len (frames) - 1 <= self.width:
			off = x0
		else:
			off = max (0, self.width - (len (frames) - 1))
		lx = self.pointer_tile[0]
		ly = self.pointer_tile[1] - y0 - 1
		lframe = ly * self.width + lx + 1 - off
		if self.pointer_tile[0] == x0 and self.pointer_tile[1] == y0:
			frame = 1
		elif lframe >= 0 and lframe < len (frames):
			frame = lframe
		else:
			# Selected nothing; return to selection.
			self.selected_seq = None
			return
		if e.button == 1:
			spr = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
			# Don't accidentily change sprite when warp target is selected.
			if spriteselect[0][2]:
				# Don't return to the map.
				return
			spr.seq = s[y0 * self.width + x0]
			spr.frame = frame
		elif e.button == 2:
			(x, y), (ox, oy), n = viewmap.newinfo
			name = data.world.room[n].add_sprite ((ox, oy), s[pos0], frame)
			sp = data.world.room[n].sprite[name]
			spriteselect[:] = ((n, name, False),)
			update_editgui ()
		else:
			# Don't return to the map.
			return
		self.selected_seq = None
		the_gui.setmap = True
		viewmap.update ()

class ViewCollection (View):
	def __init__ (self):
		View.__init__ (self)
		self.available = []
		self.selected_seq = None
	def update (self):
		if self.buffer == None:
			return
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		c = self.available
		# Compute tile size.
		self.tilesize = int (math.sqrt (self.screensize[0] * self.screensize[1] / len (c)))
		while True:
			self.width = self.screensize[0] / self.tilesize
			if self.width > 0:
				nc = (len (c) + self.width - 1) / self.width
				if nc * self.tilesize <= self.screensize[1]:
					break
			self.tilesize -= 1
		if self.selected_seq == None:
			for y in range (nc):
				for x in range (self.width):
					if y * self.width + x >= len (c):
						self.draw_seq ((x, y), None)
						continue
					if c[y * self.width + x][0] == '':
						continue
					seq = c[y * self.width + x]
					pb = data.get_seq (data.seq.collection[seq[0]][seq[1]], 1)
					self.draw_seq ((x, y), pb)
		else:
			# Draw clicked sequence.
			x0, y0 = self.selected_seq
			pos0 = y0 * self.width + x0
			seq = c[pos0]
			pb = data.get_seq (data.seq.collection[seq[0]][seq[1]], 1)
			self.draw_seq (self.selected_seq, pb)
			# Draw selectable frames.
			frames = data.seq.collection[seq[0]][seq[1]].frames
			if x0 + len (frames) - 1 <= self.width:
				off = x0
			else:
				off = max (0, self.width - (len (frames) - 1))
			for f in range (1, len (frames)):
				pb = data.get_seq (data.seq.collection[seq[0]][seq[1]], f)
				y = y0 + 1 + (f - 1 + off) / self.width
				x = (f - 1 + off) % self.width
				self.draw_seq ((x, y), pb)
		if not (dinkconfig.lowmem and dinkconfig.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def direction (self, d):
		self.thedirection = d
		self.available = [('', None)]
		for c in collectionlist ():
			if d in data.seq.collection[c]:
				self.available += ((c, d),)
			elif d == None:
				self.available += ((c, [x for x in data.seq.collection[c].keys () if type (x) == int][0]),)
		self.update ()
	def get_selected_sequence (self, x, y):
		c = self.available
		nc = (len (c) + self.width - 1) / self.width
		if x >= 0 and x < self.tilesize * self.width and y >= 0 and y < self.tilesize * nc:
			target = (y / self.tilesize) * self.width + x / self.tilesize
			if target <= len (c):
				return c[target]
		return None
	def keypress (self, widget, e):
		if e.keyval == gtk.keysyms.Escape: # Cancel operation.
			the_gui.setmap = True
			return
		elif e.keyval == gtk.keysyms.Return: # Confirm operation.
			e.x, e.y, e.mask = self.get_window ().get_pointer ()
			e.type = gtk.gdk.BUTTON_PRESS
			e.button = 1
			self.button_on (widget, e)
		elif e.keyval == gtk.keysyms.a: # set base attack.
			View.collectiontype = 'attack'
		elif e.keyval == gtk.keysyms.b: # set base walk.
			View.collectiontype = 'walk'
		elif e.keyval == gtk.keysyms.d: # set base death.
			View.collectiontype = 'death'
		elif e.keyval == gtk.keysyms.i: # set base idle.
			View.collectiontype = 'idle'
		else:
			return
		self.button_on (widget, e)
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		seq = self.get_selected_sequence (*self.pointer_pos)
		if seq == None:
			return
		if e.button == 1:	# perform action or change selected sequence
			if View.collectiontype == None:
				if len (spriteselect) != 1:
					return
				if spriteselect[0][2]:
					spr = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
					spr.touch_seq = seq
					the_gui.setmap = True
					viewmap.update ()
				else:
					if seq[0] != '':
						self.selected_seq = self.pointer_tile
						self.update ()
			else:
				for s in spriteselect:
					if View.collectiontype == 'idle':
						data.world.room[s[0]].sprite[s[1]].base_idle = seq
					elif View.collectiontype == 'death':
						data.world.room[s[0]].sprite[s[1]].base_death = seq
					elif View.collectiontype == 'walk':
						data.world.room[s[0]].sprite[s[1]].base_walk = seq
					elif View.collectiontype == 'attack':
						data.world.room[s[0]].sprite[s[1]].base_attack = seq
					else:
						raise AssertionError ('invalid collection type %s' % View.collectiontype)
		elif e.button == 2:	# add new sprite
			if View.collectiontype != None or seq == '':
				return
			if viewmap.newinfo[2] not in data.world.room:
				# TODO: add for selected screen.
				return
			self.selected_seq = self.pointer_tile
			self.update ()
	def button_off (self, widget, e):
		if self.selected_seq == None:
			return
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / self.tilesize for x in range (2)]
		c = self.available
		x0, y0 = self.selected_seq
		pos0 = y0 * self.width + x0
		seq = c[pos0]
		frames = data.seq.collection[seq[0]][seq[1]].frames
		if x0 + len (frames) - 1 <= self.width:
			off = x0
		else:
			off = max (0, self.width - (len (frames) - 1))
		lx = self.pointer_tile[0]
		ly = self.pointer_tile[1] - y0 - 1
		lframe = ly * self.width + lx + 1 - off
		if self.pointer_tile[0] == x0 and self.pointer_tile[1] == y0:
			frame = 1
		elif lframe >= 0 and lframe < len (frames):
			frame = lframe
		else:
			# Selected nothing; return to selection.
			self.selected_seq = None
			return
		if e.button == 1:
			spr = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
			# Don't accidentily change sprite when warp target is selected.
			if spriteselect[0][2]:
				# Don't return to the map.
				return
			spr.seq = seq
			spr.frame = frame
		elif e.button == 2:	# add new sprite
			(x, y), (ox, oy), n = viewmap.newinfo
			if n not in data.world.room:
				# TODO: add for selected screen.
				return
			name = data.world.room[n].add_sprite ((ox, oy), seq, 1)
			sp = data.world.room[n].sprite[name]
			spriteselect[:] = ((n, name, False),)
			update_editgui ()
		else:
			return
		self.selected_seq = None
		the_gui.setmap = True
		viewmap.update ()

class ViewTiles (View):
	def __init__ (self):
		View.__init__ (self)
		self.pointer_tile = (0, 0)	# Tile that the pointer is currently pointing it, in world coordinates. That is: pointer_pos / screenzoom.
		self.tiles = (12 * 6, 8 * 7)	# Total number of tiles
		self.set_size_request (screenzoom * 12, screenzoom * 8)
	def find_tile (self, worldpos):
		if worldpos[0] >= 0 and worldpos[0] < 6 * 12 and worldpos[1] >= 0 and worldpos[1] < 7 * 8:
			n = (worldpos[1] / 8) * 6 + worldpos[0] / 12 + 1
			if 1 <= n <= 41:
				return [n, worldpos[0] % 12, worldpos[1] % 8]
		return [-1, -1, -1]
	def draw_tile (self, screenpos, worldpos):
		View.draw_tile (self, screenpos, worldpos, False)
	def update (self):
		if self.buffer == None:
			return
		View.draw_tiles (self, 1)
		if not (dinkconfig.lowmem and dinkconfig.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		global copystart
		self.selecting = False
		if e.keyval == gtk.keysyms.Home:	# center screen
			s = (12, 8)
			self.offset = [((self.pointer_pos[x] * 50 / screenzoom + self.offset[x]) / s[x] / 50) * s[x] * 50 + (s[x] / 2) * 50 - self.screensize[x] * 25 / screenzoom for x in range (2)]
			self.update ()
		elif e.keyval == gtk.keysyms.t:		# toggle tile screen
			the_gui.setmap = True
		elif e.keyval == gtk.keysyms.y:		# yank tiles into buffer
			copybuffer.clear ()
			for i in select.data:
				s = View.find_tile (self, i, i[2])
				copybuffer.add ((i[0], i[1], i[2], s[0], s[1], s[2]))
			copystart = select.start
			the_gui.setmap = True
		elif e.keyval == gtk.keysyms.space:	# start panning
			self.panning = True
			self.old_offset = self.offset
			return
		elif e.keyval == gtk.keysyms.Return:	# Confirm operation
			self.panning = False
			return
		elif e.keyval == gtk.keysyms.Escape:	# Abort operation
			self.panning = False
			self.offset = self.old_offset
			self.update ()
			return
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		tile = self.pointer_tile
		pos = int (ex), int (ey)
		diff = [(pos[x] - self.pointer_pos[x]) * 50 / screenzoom for x in range (2)]
		self.pointer_pos = pos
		self.pointer_tile = [(pos[x] + self.offset[x]) / screenzoom for x in range (2)]
		if not self.panning and not self.selecting and select.empty ():
			return
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
		if self.selecting:
			View.select_tiles (self, tile, 1)
		self.update ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / screenzoom for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 1:
			if self.panning:
				self.panning = False
			else:
				select.clear ()
		elif e.button == 3:
			x, y = self.pos_from_event ((e.x, e.y))
			View.tileselect (self, x, y, not e.state & gtk.gdk.CONTROL_MASK, 1)
	def button_off (self, widget, e):
		self.selecting = False

class ViewWorld (View):
	def __init__ (self):
		View.__init__ (self)
		self.set_size_request (32 * 12, 24 * 8)
	def update (self):
		if not self.buffer:
			return
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
					if data.world.room[n].indoor:
						self.buffer.draw_rectangle (self.noshowgc, True, off[0] + tsize[0] * x + 1, off[1] + tsize[1] * y + 1, tsize[0] - 1, tsize[1] - 1)
					else:
						self.buffer.draw_rectangle (self.noselectgc, True, off[0] + tsize[0] * x + 1, off[1] + tsize[1] * y + 1, tsize[0] - 1, tsize[1] - 1)
				else:
					self.buffer.draw_rectangle (self.invalidgc, True, off[0] + tsize[0] * x + 1, off[1] + tsize[1] * y + 1, tsize[0] - 1, tsize[1] - 1)
		self.buffer.draw_line (self.bordergc, off[0], off[1] + s[1] * tsize[1], off[0] + s[0] * tsize[0] - 1, off[1] + s[1] * tsize[1])
		self.buffer.draw_line (self.bordergc, off[0] + s[0] * tsize[0], off[1], off[0] + s[0] * tsize[0], off[1] + s[1] * tsize[1] - 1)
		targetsize = [max (2, viewmap.screensize[x] * tsize[x] / screenzoom / scrsize[x]) for x in range (2)]
		current = [viewmap.offset[t] * tsize[t] / scrsize[t] / screenzoom + off[t] for t in range (2)]
		self.buffer.draw_rectangle (self.selectgc, False, current[0], current[1], targetsize[0] - 1, targetsize[1] - 1)
		self.buffer.draw_rectangle (self.pastegc, False, self.pointer_pos[0] - targetsize[0] / 2, self.pointer_pos[1] - targetsize[1] / 2, targetsize[0] - 1, targetsize[1] - 1)
		if not (dinkconfig.lowmem and dinkconfig.nobackingstore):
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		if e.keyval == gtk.keysyms.Escape:	# abort current action
			viewmap.offset = self.old_offset
			viewmap.update ()
			the_gui.setmap = True
		elif e.keyval == gtk.keysyms.s: # save
			data.save ()
		elif e.keyval == gtk.keysyms.x: # exit
			gui.quit ()
		else:
			return False
		return True
	def select (self):
		self.selecting = True
		s = (32, 24)
		scrsize = (12, 8)
		tsize = [self.screensize[x] / s[x] for x in range (2)]
		off = [(self.screensize[x] - s[x] * tsize[x]) / 2 for x in range (2)]
		viewmap.offset = [(self.pointer_pos[x] - off[x]) * screenzoom * scrsize[x] / tsize[x] - viewmap.screensize[x] / 2 for x in range (2)]
		viewmap.update ()
		self.update ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 1:
			self.select ()
	def button_off (self, widget, e):
		the_gui.setmap = True
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		self.pointer_pos = int (ex), int (ey)
		if self.selecting:
			self.select ()
		self.update ()

def new_sprite (dummy):
	'''New sprite selected in the gui'''
	if updating:
		return
	screen = int (the_gui.get_screen)
	sprite = the_gui.get_sprite
	if screen not in data.world.room or sprite not in data.world.room[screen].sprite:
		return
	s = data.world.room[screen].sprite[sprite]
	spriteselect[:] = [(screen, sprite, False)]
	update_editgui ()
	View.update (viewmap)

def update_editgui ():
	global updating
	if updating:
		# Not sure how this can happen, but prevent looping anyway.
		return
	if len (spriteselect) != 1:
		# Not single selection, so nothing to update.
		return
	updating = True
	screen = spriteselect[0][0]
	the_gui.set_screen = screen
	the_gui.set_screen_script = data.world.room[screen].script
	the_gui.set_screen_hardness = data.world.room[screen].hard
	the_gui.set_screen_music = data.world.room[screen].music
	the_gui.set_indoor = data.world.room[screen].indoor
	the_gui.set_spritelist = keylist (data.world.room[screen].sprite, lambda x: x)
	sprite = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
	the_gui.set_sprite = spriteselect[0][1]
	the_gui.set_name = spriteselect[0][1]
	the_gui.set_x = sprite.x
	the_gui.set_y = sprite.y
	if type (sprite.seq) == str:
		the_gui.set_seq = sprite.seq
	else:
		the_gui.set_seq = '%s %d' % sprite.seq
	the_gui.set_frame = sprite.frame
	if sprite.type == 0:
		the_gui.set_type = 'Background'
	elif sprite.type == 1:
		the_gui.set_type = 'Normal'
	else:
		the_gui.set_type = 'Invisible'
	the_gui.set_size = sprite.size
	the_gui.set_brain = sprite.brain
	the_gui.set_script = sprite.script
	the_gui.set_speed = sprite.speed
	the_gui.set_basewalk = sprite.base_walk
	the_gui.set_baseidle = sprite.base_idle
	the_gui.set_baseattack = sprite.base_attack
	the_gui.set_timing = sprite.timing
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
	the_gui.set_basedeath = sprite.base_death
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
	if updating:
		return
	screen = int (the_gui.get_screen)
	if screen not in data.world.room:
		View.update (viewmap)
		return
	# Selected screen: update
	# Screen script
	data.world.room[screen].script = the_gui.get_screen_script
	# Screen hardness
	data.world.room[screen].hard = the_gui.get_screen_hardness
	# Screen music
	data.world.room[screen].music = the_gui.get_screen_music
	# Indoor
	data.world.room[screen].indoor = the_gui.get_indoor
	# Changing the selected sprite is handled in its own function, so doesn't need anything here.
	# The rest is about the selected sprite, if exactly one.
	if len (spriteselect) != 1:
		View.update (viewmap)
		return
	sprite = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
	name = the_gui.get_name
	if name not in data.world.room[spriteselect[0][0]].sprite:
		# The name is not in the list, so it has changed (and is not equal to another name).
		s = data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
		del data.world.room[spriteselect[0][0]].sprite[spriteselect[0][1]]
		spriteselect[0] = (spriteselect[0][0], name, spriteselect[0][2])
		data.world.room[spriteselect[0][0]].sprite[name] = s
	sprite.x = int (the_gui.get_x)
	sprite.y = int (the_gui.get_y)
	seq = the_gui.get_seq.split ()
	if len (seq) == 1:
		if data.seq.find_seq (seq[0]) != None:
			sprite.seq = seq[0]
		else:
			print ('seq not found:', seq)
			return
	else:
		if data.seq.find_collection (seq[0]) != None:
			sprite.seq = (seq[0], int (seq[1]))
		else:
			print ('collection not found:', seq)
			return
	frame = int (the_gui.get_frame)
	if frame < len (data.seq.find_seq (sprite.seq).frames):
		sprite.frame = frame
	type = the_gui.get_type
	if type == 'Background':
		sprite.type = 0
	elif type == 'Normal':
		sprite.type = 1
	elif type == 'Invisible':
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
	sprite.timing = int (the_gui.get_timing)
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
	collection = the_gui.get_basedeath
	if data.seq.find_collection (collection) != None:
		sprite.base_death = collection
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
	name = os.path.join (tmpdir, s + os.extsep + 'c')
	if s not in data.script.data:
		data.script.data[s] = ''
		# Create the empty file.
		open (name, 'w')
	os.system (the_gui['run-script'].replace ('$SCRIPT', name))

def do_edit_hard (h, room):
	if h == '' or room not in data.world.room:
		return
	name = os.path.join (tmpdir, h + os.extsep + 'png')
	if os.path.exists (name):
		# Update hardness.
		dink.make_hard_image (name).save (name)
		data.tile.hard[h] = (name, 0, os.stat (name).st_size)
	image = Image.new ('RGB', (50 * 12, 50 * 8), (0, 0, 0))
	# Write all tiles
	for y in range (8):
		for x in range (12):
			n, tx, ty = data.world.room[room].tiles[y][x]
			image.paste (Image.open (dink.filepart (*(data.tile.get_file (n)[:-1]))).crop ((tx * 50, ty * 50, (tx + 1) * 50, (ty + 1) * 50)), (x * 50, y * 50))
	# Write all sprites. Ignore sprites from other screens.
	lst = []
	for spr in data.world.room[room].sprite:
		sp = data.world.room[room].sprite[spr]
		pos = (sp.x, sp.y)
		seq = data.seq.find_seq (sp.seq)
		lst += ((pos, sp, seq),)
	lst.sort (key = lambda x: x[0][1] - x[1].que)
	for spr in lst:
		frame = spr[2].frames[spr[1].frame]
		(x, y), (left, top, right, bottom), box = data.get_box (spr[1].size, spr[0], frame, (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
		if right <= left or bottom <= top:
			continue
		# Draw the pixbuf.
		sprite = Image.open (dink.filepart (*frame.cache)).convert ('RGBA')
		p = sprite.load ()
		for y in range (sprite.size[1]):
			for x in range (sprite.size[0]):
				if (spr[2].type == 'black' and p[x, y][:3] == (0, 0, 0)) or (spr[2].type != 'black' and p[x, y][:3] == (255, 255, 255)):
					p[x, y] = (0, 0, 0, 0)
		if box != None:
			sprite = image.crop (box)
		sprite = sprite.resize ((right - left, bottom - top))
		image.paste (sprite, (left, top), sprite)
	# Write sprite hardness as red boxes (ignored when reading back.
	pixels = image.load ()
	for spr in lst:
		if spr[1].hard:
			frame = spr[2].frames[spr[1].frame]
			for x in range (frame.hardbox[2] - frame.hardbox[0]):
				px = spr[0][0] - 20 + frame.hardbox[0] + x
				if not 0 <= px < 600:
					continue
				y = spr[0][1] + frame.hardbox[1]
				if 0 <= y < 400:
					p = px, y
					pixels[p] = tuple ([255] + list (pixels[p])[1:])
				y = spr[0][1] + frame.hardbox[3]
				if 0 <= y < 400:
					p = px, y
					pixels[p] = tuple ([255] + list (pixels[p])[1:])
			for y in range (frame.hardbox[3] - frame.hardbox[1]):
				py = spr[0][1] + frame.hardbox[1] + y
				if not 0 <= py < 400:
					continue
				x = spr[0][0] + frame.hardbox[0] - 20
				if 0 <= x < 600:
					p = x, py
					pixels[p] = tuple ([255] + list (pixels[p])[1:])
				x = spr[0][0] + frame.hardbox[2] - 20
				if 0 <= x < 600:
					p = x, py
					pixels[p] = tuple ([255] + list (pixels[p])[1:])
	# Make dark
	image = Image.eval (image, lambda v: v / 2)
	# Add hardness
	f = data.tile.get_hard_file (h)
	if f == None:
		# Fill with default hardness for tiles.
		for y in range (8):
			for x in range (12):
				n, tx, ty = data.world.room[room].tiles[y][x]
				hard = Image.open (dink.filepart (*(data.tile.get_hard_file (n)[:-1]))).crop ((tx * 50, ty * 50, (tx + 1) * 50, (ty + 1) * 50))
				# Paste twice for extra intensity (190 minimum)
				image.paste (hard, (x * 50, y * 50), hard)
				image.paste (hard, (x * 50, y * 50), hard)
	else:
		im = Image.open (dink.filepart (*(f[:-1])))
		# Paste twice for extra intensity (190 minimum)
		image.paste (im, None, im)
		image.paste (im, None, im)
	image.save (name)
	os.system (the_gui['edit-hardness'].replace ('$IMAGE', name))
	data.cache_flush_hard (h)
	data.tile.hard[h] = (name, 0, os.stat (name).st_size)
	sync ()
	viewmap.update ()

def edit_screen_hardness (self, dummy = None):
	do_edit_hard (the_gui.get_screen_hardness, int (the_gui.get_screen))

def edit_screen_script (self, dummy = None):
	do_edit (the_gui.get_screen_script)

def edit_script (self, dummy = None):
	do_edit (the_gui.get_script)

def sync ():
	for s in data.script.data:
		data.script.data[s] = open (os.path.join (tmpdir, s + os.extsep + 'c')).read ()
	for h in data.tile.hard:
		p = os.path.join (tmpdir, h + os.extsep + 'png')
		if os.path.exists (p):
			dink.make_hard_image (p).save (p)
			data.tile.hard[h] = (p, 0, os.stat (p).st_size)

if len (sys.argv) == 2:
	root = sys.argv[1]
elif len (sys.argv) > 2:
	sys.stderr.write ('Give no arguments or only a game directory.\n')
	sys.exit (1)
else:
	w = gtk.FileChooserDialog ('Select game directory to edit', action = gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER)
	w.add_button (gtk.STOCK_OPEN, gtk.RESPONSE_OK)
	w.add_button (gtk.STOCK_CANCEL, gtk.RESPONSE_NONE)
	w.set_do_overwrite_confirmation (False)
	w.show ()
	if w.run () != gtk.RESPONSE_OK:
		sys.exit (0)
	root = w.get_filename ()
	w.destroy ()

data = gtkdink.GtkDink (root, screenzoom)
# initialize warp targets.
for n in data.world.room.keys ():
	for s in data.world.room[n].sprite:
		add_warptarget (n, s)
viewmap = ViewMap ()
viewseq = ViewSeq ()
viewcollection = ViewCollection ()
viewtiles = ViewTiles ()
viewworld = ViewWorld ()

tmpdir = tempfile.mkdtemp (prefix = 'dink-scripts-')
for s in data.script.data:
	open (os.path.join (tmpdir, s + os.extsep + 'c'), 'w').write (data.script.data[s])
sync ()

the_gui = gui.gui (external = { 'viewmap': viewmap, 'viewseq': viewseq, 'viewcollection': viewcollection, 'viewtiles': viewtiles, 'viewworld': viewworld })
the_gui.update = update_gui
the_gui.new_sprite = new_sprite
the_gui.edit_screen_script = edit_screen_script
the_gui.edit_screen_hardness = edit_screen_hardness
the_gui.edit_script = edit_script
the_gui ()

for s in data.script.data:
	os.unlink (os.path.join (tmpdir, s + os.extsep + 'c'))
for h in data.tile.hard:
	p = os.path.join (tmpdir, h + os.extsep + 'png')
	if os.path.exists (p):
		os.unlink (p)
os.rmdir (tmpdir)
