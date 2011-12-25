#!/usr/bin/env python

# play.py - pydink player: engine for playing for pydink games.
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

# Data management:
# Global data is stored by changing the game as an editor.
# Global variables are in the_globals.
# Local variables are in the_locals, which is a local variable of Script().
# Static variables are in the_statics[fname], which is a member of Sprite; see below.

# Current screen: scripts.
# A new script is instantiated whenever a function is called. This is different from the original game.
# It means that kill_this_task is useless (and not supported), and that you need static (or global) variables to communicate between event functions.
# function calls lock the calling function until the called function returns. This is implemented with generators.
# There is no way to communicate with a running script. It is not possible to count the scripts. There is no limit on the number of running scripts (except available memory).

# Current screen: sprites.
# Don't confuse Sprite and dink.Sprite! The former is a sprite on the screen, the latter a sprite in the editor.
# All dink.Sprites of a screen are copied into Sprites when load_screen() is called.
# A Sprite has the following members:
# visible, x, y, brain, hitpoints, defense, strength, gold, size, seq, frame, pseq, pframe, speed, base_walk, base_idle, base_attack, base_death, timing, que, hard, cropbox, warp, touch_seq, exp, sound, vision, nohit, touch_damage, script.
# src, num, editor_num, the_statics (dictionary of variables).
# Background sprites are drawn to the background pixmap, after that, the object is destroyed. It is impossible to adjust anything about them.

import gtkdink
import gtk
import gobject
import sys
import datetime

class Sprite:
	def __init__ (self, data, x = None, y = None, brain = None, seq = None, frame = None, script = None, src = None, name = None):
		self.data = data
		if src != None:
			assert brain == None and seq == None and frame == None and script == None
			self.visible = src.type != 3
			self.x = src.x if x == None else x
			self.y = src.y if y == None else y
			self.size = src.size
			self.seq = None
			self.frame = 1
			self.pseq = data.data.seq.find_seq (src.seq)
			self.pframe = src.frame
			if src.type == 0:
				return
			self.brain = src.brain
			self.hitpoints = src.hitpoints
			self.defense = src.defense
			self.strength = src.strength
			self.gold = src.gold
			self.speed = src.speed
			self.base_walk = data.data.seq.find_collection (src.base_walk)
			self.base_idle = data.data.seq.find_collection (src.base_idle)
			self.base_attack = data.data.seq.find_collection (src.base_attack)
			self.base_death = data.data.seq.find_collection (src.base_death)
			self.timing = src.timing
			self.que = src.que
			self.hard = src.hard
			self.cropbox = (src.left, src.top, src.right, src.bottom)
			self.warp = src.warp
			self.touch_seq = data.data.seq.find_seq (src.touch_seq)
			self.exp = src.exp
			self.sound = src.sound
			self.vision = src.vision
			self.nohit = src.nohit
			self.touch_damage = src.touch_damage
			self.editor_num = src.num
			self.script = src.script
		else:
			assert x != None and y != None and brain != None and ((brain == 'text' and seq == None and frame == None) or (brain != 'text' and seq != None and frame != None))
			self.visible = True
			self.x = x
			self.y = y
			self.brain = brain
			self.hitpoints = 0
			self.defense = 0
			self.strength = 0
			self.gold = 0
			self.size = 100
			self.seq = None
			self.frame = 1
			self.pseq = data.data.seq.find_seq (seq) if seq != None else None
			self.pframe = frame
			self.speed = 2
			self.base_walk = None
			self.base_idle = None
			self.base_attack = None
			self.base_death = None
			self.timing = 20
			self.que = 0
			self.hard = False
			self.cropbox = (0, 0, 0, 0)
			self.warp = None
			self.touch_seq = None
			self.exp = 0
			self.sound = ''
			self.vision = 0
			self.nohit = False
			self.touch_damage = 0
			self.editor_num = None
			self.script = script
		if self.brain in ('repeat', 'mark', 'play', 'flare', 'missile'):
			self.seq = self.pseq
			self.frame = self.pframe
		self.name = name
		self.frame_delay = self.pseq.delay if self.pseq != None else None
		self.killdelay = None
		self.state = None
		self.set_state ('passive')
		self.dir = 2
		self.clip = True
		self.frozen = False
		self.mx = 0
		self.my = 0
		self.ignore_hard = False
		self.bbox = (0, 0, 0, 0)	# This will be updated when it is drawn.
		self.the_statics = {}
		if self.script:
			for v in data.functions[self.script]['']:
				self.the_statics[v] = 0
		self.src = src
		self.num = data.next_sprite
		data.next_sprite += 1
		data.sprites[self.num] = self
	def set_state (self, state = None):
		if state != self.state:
			self.frame = 1
		if state != None:
			self.state = state
		# Set seq according to state.
		if self.state == 'passive':
			return
		elif self.state == 'idle':
			if self.base_idle:
				self.seq = self.data.data.seq.get_dir_seq (self.base_idle, self.dir)
		elif self.state == 'walk':
			if self.base_walk:
				self.seq = self.data.data.seq.get_dir_seq (self.base_walk, self.dir)
		elif self.state == 'attack':
			if self.base_attack:
				self.seq = self.data.data.seq.get_dir_seq (self.base_attack, self.dir)
		elif self.state == 'die':
			if self.base_death:
				self.seq = self.data.data.seq.get_dir_seq (self.base_death, self.dir)
		else:
			raise AssertionError ('invalid state %s' % state)

class Play (gtk.DrawingArea):
	"Widget for playing dink."
	def __init__ (self, data):
		"Arguments: dink data and number of pixels per tile"
		gtk.DrawingArea.__init__ (self)
		self.data = data
		self.offset = 20 * self.data.scale / 50
		self.current_time = datetime.datetime.utcnow ()
		self.checkpoint = self.current_time
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.pointer = True
		self.keep_mouse = False
		self.control_down = 0
		self.choice = None
		self.choice_title = None
		self.screenlock = False
		self.cursorkeys = (gtk.keysyms.Left, gtk.keysyms.Up, gtk.keysyms.Right, gtk.keysyms.Down)
		self.cursor = [False, False, False, False]
		self.brains = [ 'dink', 'bounce', 'duck', 'pig', 'mark', 'repeat', 'play', 'text', 'bisshop', 'rook', 'missile', 'resize', 'pointer', 'button', 'shadow', 'person', 'flare' ]
		self.the_globals = {}
		for v in gtkdink.dink.the_globals:
			self.the_globals[v] = gtkdink.dink.the_globals[v]
		self.scripts = data.script.compile ()
		self.functions = gtkdink.dink.functions
		self.sprites = {}
		self.next_sprite = 1
		self.the_globals['player_map'] = None
		self.box_start = None
		self.bow = False, 0
		self.fade = 0, True
		self.events = []
		self.item_selection = False
		self.items = [None] * 16
		self.magic = [None] * 8
		self.current_weapon = None
		self.current_magic = None
		self.make_hardmap ()
	def start (self, widget):
		gtk.DrawingArea.realize (self)
		pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
		color = gtk.gdk.Color()
		cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
		self.window.set_cursor (cursor)
		self.data.set_window (self.window)
		self.gc = gtk.gdk.GC (self.window)
		self.clipgc = gtk.gdk.GC (self.window)
		self.clipgc.set_clip_rectangle (gtk.gdk.Rectangle (self.offset, 0, self.data.scale * 12, self.data.scale * 8))
		self.winw = 12 * self.data.scale + 2 * self.offset
		self.winh = 8 * self.data.scale + 80 * self.data.scale / 50
		self.buffer = gtk.gdk.Pixmap (self.window, self.winw, self.winh)
		self.bg = gtk.gdk.Pixmap (self.window, self.winw, self.winh)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('key-release-event', self.keyrelease)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('enter-notify-event', self.enter)
		self.set_size_request (self.winw, self.winh)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.KEY_RELEASE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.ENTER_NOTIFY_MASK)
		self.gc.set_foreground (self.data.get_color (self.data.script.title_color))
		self.buffer.draw_rectangle (self.gc, True, 0, 0, self.winw, self.winh)
		if self.data.script.title_bg != '':
			self.buffer.draw_pixbuf (None, self.data.get_image (self.data.script.title_bg), 0, 0, 0, 0, self.winw, self.winh)
		p = self.add_sprite (self.data.script.title_pointer_seq, self.data.script.title_pointer_frame, 320, 240, 'pointer')
		p.clip = False
		p.que = -100000
		p.timing = 10
		for spr in self.data.script.title_sprite:
			s = self.add_sprite (*spr)
			s.clip = False
		if self.data.script.title_music != '':
			self.play_music (self.data.script.title_music)
		self.expose (widget, (0, 0, self.winw, self.winh));
		# Schedule first event immediately.
		self.events += ((self.current_time, self.update ()),)
		gobject.idle_add (self.next_event)
	def next_event (self):
		self.events.sort (key = lambda x: x[0])
		self.current_time = datetime.datetime.utcnow ()
		while self.current_time >= self.events[0][0]:
			now = self.events[0][0]
			target = self.events.pop (0)[1]
			result = next (target)
			if result[0] == 'return':
				pass
			elif result[0] == 'wait':
				if result[1] > 0:
					then = now + datetime.timedelta (milliseconds = result[1])
					if then < self.checkpoint:
						then = self.checkpoint
					self.events += ((then, target),)
				else:
					self.events += ((self.current_time + datetime.timedelta (milliseconds = -result[1]), target),)
			elif result[0] == 'error':
				print ('Error reported: %s' % result[1])
			elif result[0] == 'choice':
				self.choice_waiter = target
			else:
				raise AssertionError ('invalid return type %s' % result[0])
			self.events.sort (key = lambda x: x[0])
		assert self.events != []
		t = self.events[0][0] - self.current_time
		gobject.timeout_add ((t.days * 24 * 3600 + t.seconds) * 1000 + t.microseconds / 1000, self.next_event)
		return False
	def play_music (self, music):
		pass
	def add_sprite (self, seq, frame, x, y, brain, script = None):
		ret = Sprite (self, x, y, brain, seq, frame, script)
		ret.last_time = self.current_time
		if ret.script and 'main' in self.scripts[ret.script]:
			# current_time - datetime.timedelta (seconds = 1), so it runs before continuing the current script.
			self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (ret.script, 'main', (), ret)),)
		self.events += ((self.current_time + datetime.timedelta (milliseconds = ret.timing), self.do_brain (ret)),)
		return ret
	def do_brain (self, sprite):
		while True:
			# Reschedule callback. Do this at start, so continue can be used.
			yield ('wait', sprite.timing)
			# Move.
			if sprite.ignore_hard:
				c = [0, 0, 0, 0]
			elif not 0 <= sprite.y + sprite.my < 400 or not 0 <= sprite.x + sprite.mx - 20 < 600:
				if sprite.brain == 'dink' and not self.dink_can_walk_off_screen:
					# Move to new screen (if possible).
					if sprite.y + sprite.my < 0:
						self.try_move (0, -1)
					elif sprite.x + sprite.mx - 20 < 0:
						self.try_move (-1, 0)
					elif sprite.y + sprite.my >= 400:
						self.try_move (0, 1)
					elif sprite.x + sprite.mx - 20 >= 600:
						self.try_move (1, 0)
					continue
				c = [255, 255, 255, 255]
			else:
				c = self.hardmap[sprite.y + sprite.my][sprite.x + sprite.mx - 20]
			need_new_dir = False
			mx, my = sprite.mx, sprite.my
			if c[2] == 0:
				sprite.x += sprite.mx
				sprite.y += sprite.my
				mx, my = 0, 0
				self.push_delay = 0
			elif sprite.brain == 'dink':
				# Push.
				self.push_delay += 1
				if self.push_delay == 50:
					# TODO: Start pushing.
					pass
			elif sprite.brain in ('duck', 'pig', 'person'):
				# Stop walking.
				sprite.mx = 0
				sprite.my = 0
			elif sprite.brain in ('bisshop', 'rook'):
				# Choose new direction.
				need_new_dir = True
			if sprite.brain in ('duck', 'pig', 'bisshop', 'rook', 'person') and (need_new_dir or random.random () < (.01 if sprite.mx != 0 or sprite.my != 0 else .05)):
				if sprite.brain == 'rook':
					sprite.mx, sprite.my = random.choice ((-1, 0), (1, 0), (0, -1), (0, 1))
				else:
					sprite.mx, sprite.my = random.choice ((-1, -1), (-1, 1), (1, -1), (1, 1))
			if sprite.brain in ('dink', 'missile', 'flare'):
				# Test touch damage, warp and missile explosions.
				for s in self.sprites:
					spr = self.sprites[s]
					if spr == sprite or spr.brain == 'text':
						continue
					if spr.seq == None:
						assert spr.pseq != None
						seq = (spr.pseq, spr.pframe)
					else:
						seq = (spr.seq, spr.frame)
					box = seq[0].frames[seq[1]].hardbox
					if spr.x + box[0] <= sprite.x + mx <= spr.x + box[2] and spr.y + box[1] <= sprite.y + my <= spr.y + box[3]:
						if sprite.brain == 'dink':
							if spr.touch_damage != 0:
								if spr.touch_damage == -1:
									self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (spr.script, 'touch', (), None)),)
								elif not self.touch_delay:
									self.damage (spr.touch_damage, sprite)
							if spr.warp != None and spr.hard:
								# TODO: Warp.
								pass
						elif not spr.nohit:
							# TODO: Explode.
							pass
	def try_move (self, dx, dy):
		# Move to a new screen if possible, otherwise do nothing.
		screen = self.the_globals['player_map']
		if screen == None:
			return
		oldx = (screen - 1) % 32
		newscreen = screen + dx + 32 * dy
		if not 0 <= oldx + dx < 32 or newscreen not in self.data.world.room:
			return
		# TODO: Make cool transition.
		self.the_globals['player_map'] = newscreen
		self.sprites[1].x -= dx * 599
		self.sprites[1].y -= dy * 399
		self.load_screen ()
	def expose (self, widget, event):
		if type (event) == tuple:
			a = event
		else:
			a = event.area
		if self.window:
			self.window.draw_drawable (self.gc, self.buffer, a[0], a[1], a[0], a[1], a[2], a[3])
	def update (self):
		'''This is a generator to periodically update the screen.'''
		while True:
			if self.item_selection:
				# TODO: Item selection screen.
				return
			self.buffer.draw_drawable (self.gc, self.bg, 0, 0, 0, 0, self.winw, self.winh)
			spr = []
			for s in self.sprites:
				spr += ((self.sprites[s].y - self.sprites[s].que, self.sprites[s]),)
			spr.sort (key = lambda x: x[0])
			for s in spr:
				# Change frame.
				if s[1].seq != None:
					# Divide by 1000, so what's called microseconds is really milliseconds.
					time = (self.current_time - s[1].last_time) / 1000
					# Assume times to be smaller than 1000 s. Speed is more important than this obscure use case.
					num = time.microseconds / s[1].frame_delay
					if num > 0:
						s[1].last_time += datetime.timedelta (microseconds = s[1].frame_delay) * num
						if s[1].frame + num >= len (s[1].seq.frames):
							if s[1].brain == 'mark':
								self.draw_sprite (self.bg, s[1])
								self.kill_sprite (s[1])
								continue
							elif s[1].brain in ('play', 'flare'):
								self.kill_sprite (s[1])
								continue
							elif s[1].brain in self.brains:
								# Compute new frame, all the +/- 1 comes from the fact that frames start at 1.
								s[1].frame = (s[1].frame + num - 1) % (len (s[1].seq.frames) - 1) + 1
							else:
								s[1].seq = None
						else:
							s[1].frame += num
						if s[1].seq and s[1].seq.special == s[1].frame:
							# TODO: Hit things.
							pass
				self.draw_sprite (self.buffer, s[1])
			if self.choice != None:
				# TODO: Choice menu.
				pass
			self.expose (self, (0, 0, self.winw, self.winh))
			# Wait some time before being called again.
			yield ('wait', -50)
	def kill_sprite (self, sprite):
		del self.sprites[sprite.num]
	def draw_sprite (self, target, sprite, clip = True):
		if sprite.brain == 'text':
			# Print text.
			layout = target.create_pango_layout (sprite.text)
			if sprite.owner:
				offset = sprite.owner.x, sprite.owner.y
			else:
				offset = 0, 0
			target.draw_layout (self.clipgc if clip else self.gc, offset[0] + sprite.x, offset[1] + sprite.y, layout, sprite.fg, '#00000000')
			return
		if sprite.seq == None:
			assert sprite.pseq != None
			seq = (sprite.pseq, sprite.pframe)
		else:
			seq = (sprite.seq, sprite.frame)
		sprite.bbox = self.draw_frame (target, seq, (sprite.x, sprite.y), sprite.size, sprite.cropbox, sprite.clip)
	def draw_frame (self, target, seqframe, pos, size, cropbox, clip):
		seq, frame = seqframe
		(x, y), bbox, box = self.data.get_box (size, pos, seq.frames[frame], cropbox)
		left, top, right, bottom = bbox
		pb = self.data.get_seq (seq, frame)
		if box != None:
			pb = pb.subpixbuf (box[0], box[1], box[2] - box[0], box[3] - box[1])
		w = (right - left) * self.data.scale / 50
		h = (bottom - top) * self.data.scale / 50
		if w > 0 and h > 0:
			if w != pb.get_width () or h != pb.get_height ():
				pb = pb.scale_simple (w, h, gtk.gdk.INTERP_BILINEAR)
			target.draw_pixbuf (self.clipgc if clip else None, pb, 0, 0, self.offset + left * self.data.scale / 50, top * self.data.scale / 50)
		return bbox
	def make_bg (self):
		'''Write background to self.bg; return list of non-background sprites (sprite, x, y).'''
		ret = []
		# Draw tiles
		if self.the_globals['player_map'] not in self.data.world.room:
			self.gc.set_foreground (self.data.get_color (0))
			self.bg.draw_rectangle (self.gc, True, 0, 0, 12 * self.data.scale, 8 * self.data.scale)
			return
		screen = self.data.world.room[self.the_globals['player_map']]
		for y in range (8):
			for x in range (12):
				tile = screen.tiles[y][x]
				self.bg.draw_drawable (self.gc, self.data.get_tiles (tile[0]), self.data.scale * tile[1], self.data.scale * tile[2], self.offset + self.data.scale * x, self.data.scale * y, self.data.scale, self.data.scale)
		# Draw bg sprites
		for s in self.get_sprites ():
			if s[0].type != 0:
				ret += (s,)
				continue
			self.draw_sprite (self.bg, Sprite (self, src = s[0], x = s[1], y = s[2]))
		return ret
	def get_sprites (self):
		ret = []
		screens = []
		sy = (self.the_globals['player_map'] - 1) / 32
		sx = (self.the_globals['player_map'] - 1) % 32
		for y in (-1, 0, 1):
			if sy + y < 0:
				continue
			for x in (-1, 0, 1):
				if sx + x < 0 or sx + x >= 32:
					continue
				num = (sy + y) * 32 + sx + x + 1
				if num in self.data.world.room:
					screens += ((num, x, y),)
		for s in screens:
			for spr in self.data.world.room[s[0]].sprite:
				sp = self.data.world.room[s[0]].sprite[spr]
				ret += ((sp, sp.x + s[1] * 12 * 50, sp.y + s[2] * 8 * 50),)
		return ret
	def make_hardmap (self):
		# Add screen hardness.
		if self.the_globals['player_map'] in self.data.world.room:
			screen = self.data.world.room[self.the_globals['player_map']]
			hardbuf = self.data.get_hard_tiles (screen.hard)
			if hardbuf == None:
				hardbuf = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, True, 8, 600, 400)
				hardbuf.fill (0x00000000)
				for y in range (8):
					for x in range (12):
						h = self.data.get_hard_tiles (screen.tiles[y][x][0])
						h.copy_area (screen.tiles[y][x][1] * 50, screen.tiles[y][x][2] * 50, 50, 50, hardbuf, x * 50, y * 50)
		else:
			hardbuf = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, True, 8, 600, 400)
			hardbuf.fill (0x00000000)
		self.hardmap = hardbuf.get_pixels_array ()
		# Add sprite hardness.
		for s in self.sprites:
			spr = self.sprites[s]
			if not spr.hard or spr.brain == 'text':
				continue
			if spr.seq == None:
				assert spr.pseq != None
				seq = (spr.pseq, spr.pframe)
			else:
				seq = (spr.seq, spr.frame)
			box = list (seq[0].frames[seq[1]].hardbox[:])
			box[0] = max (0, min (599, box[0] + spr.x - 20))
			box[1] = max (0, min (399, box[1] + spr.y))
			box[2] = max (0, min (599, box[2] + spr.x - 20))
			box[3] = max (0, min (399, box[3] + spr.y))
			if box[0] != box[2] and box[1] != box[3]:
				self.hardmap[box[1]:box[3] + 1, box[0]:box[2] + 1, :] = [255, 255, 255, 255]
	def load_screen (self):
		spritelist = self.make_bg ()
		self.sprites = { 1: self.sprites[1] }
		self.sprites[1].frozen = False
		self.next_sprite = 2
		if self.the_globals['player_map'] in self.data.world.room:
			script = self.data.world.room[self.the_globals['player_map']].script
			if script and 'main' in self.scripts[script]:
				self.events += ((self.current_time - datetime.timedelta (seconds = 2), self.Script (script, 'main', (), None)),)
		for s in spritelist:
			spr = Sprite (self, src = s[0], x = s[1], y = s[2], name = s[0].name)
			spr.last_time = self.current_time
		self.make_hardmap ()
		self.current_time = datetime.datetime.utcnow ()
		self.checkpoint = self.current_time
		for s in self.sprites:
			if spr.script and 'main' in self.scripts[spr.script]:
				self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (spr.script, 'main', (), spr)),)
	def keypress (self, widget, event):
		self.push_delay = 0
		if self.sprites[1].brain not in ('dink', 'pointer') or self.sprites[1].frozen:
			# TODO: unfreeze in case of waiting for text.
			return
		if event.keyval in (gtk.keysyms.Control_R, gtk.keysyms.Control_L):
			self.control_down += 1
			self.attack ()
		if event.keyval in self.cursorkeys:
			i = self.cursorkeys.index (event.keyval)
			self.cursor[i] = True
			self.compute_dir ()
	def keyrelease (self, widget, event):
		self.push_delay = 0
		if self.sprites[1].brain not in ('dink', 'pointer') or self.sprites[1].frozen:
			return
		if event.keyval in (gtk.keysyms.Control_R, gtk.keysyms.Control_L):
			self.control_down -= 1
			if self.control_down <= 0:
				self.control_down = 0
				if self.bow[0]:
					self.bow[0] = False
					self.launch ()
		if event.keyval in self.cursorkeys:
			i = self.cursorkeys.index (event.keyval)
			self.cursor[i] = False
			self.compute_dir ()
	def compute_dir (self):
		mx = 1 + self.cursor[2] - self.cursor[0]
		my = 1 + self.cursor[1] - self.cursor[3]
		d = 1 + 3 * my + mx
		if d != 5:
			self.sprites[1].dir = d
			self.sprites[1].set_state ('walk')
		else:
			self.sprites[1].set_state ('idle')
		self.sprites[1].mx = mx - 1
		self.sprites[1].my = 1 - my
	def button_on (self, widget, event):
		if self.pointer == False:
			return
		self.control_down += 1
		self.attack ()
	def button_off (self, widget, event):
		if self.pointer == False:
			return
		self.control_down -= 1
		if self.control_down <= 0:
			self.control_down = 0
			if self.bow[0]:
				self.bow[0] = False
				self.launch ()
	def launch (self):
		# TODO: Launch missile with bow.
		pass
	def attack (self):
		a = False
		for i in self.sprites:
			if self.sprites[i].brain != 'button':
				continue
			if self.in_area ((self.sprites[1].x, self.sprites[1].y), self.sprites[i].bbox):
				if 'click' in self.scripts[self.sprites[i].script]:
					self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.sprites[i].script, 'click', (), self.sprites[i])),)
				a = True
		# Handle dink attacking.
		if self.current_weapon != None and self.items[self.current_weapon] != None:
			self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.items[self.current_weapon][0], 'use', (), None)),)
		else:
			if not a:
				self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script ('dnohit', 'main', (), None)),)
	def move (self, widget, event):
		if self.pointer == False or self.sprites[1].brain != 'pointer':
			return
		ex, ey, emask = self.window.get_pointer ()
		oldx, oldy = self.sprites[1].x, self.sprites[1].y
		self.sprites[1].x, self.sprites[1].y = int (ex) * 50 / self.data.scale, int (ey) * 50 / self.data.scale
		for i in self.sprites:
			if self.sprites[i].brain != 'button':
				continue
			o = self.in_area ((oldx, oldy), self.sprites[i].bbox)
			n = self.in_area ((self.sprites[1].x, self.sprites[1].y), self.sprites[i].bbox)
			if o == n:
				continue
			if n == True:
				if 'buttonon' in self.scripts[self.sprites[i].script]:
					self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.sprites[i].script, 'buttonon', (), self.sprites[i])),)
			else:
				if 'buttonoff' in self.scripts[self.sprites[i].script]:
					self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.sprites[i].script, 'buttonoff', (), self.sprites[i])),)
	def enter (self, widget, event):
		self.grab_focus ()
	def in_area (self, pos, area):
		return area[0] <= pos[0] <= area[2] and area[1] <= pos[1] <= area[3]
	def Script (self, fname, name, args, sprite):
		if fname not in self.functions:
			yield 'error', "script file doesn't exist: %s" % fname
			return
		if name not in self.functions[fname]:
			yield 'error', "script doesn't exist: %s.%s" % (fname, name)
			return
		retval, argnames = self.functions[fname][name]
		stack = [self.scripts[fname][name]]
		pos = [0]
		if sprite:
			the_statics = sprite.the_statics
			the_statics['current_sprite'] = sprite.num
		else:
			the_statics = {}
		the_locals = {}
		for i in range (len (argnames)):
			the_locals[argnames[i]] = self.compute (args[i], the_statics, the_locals)
		while True:
			popped = False
			while len (stack) > 0 and pos[-1] >= len (stack[-1][1]):
				stack.pop ()
				pos.pop ()
				popped = True
			if len (stack) == 0:
				yield ('return', 0)
				return
			statement = stack[-1][1][pos[-1]]
			pos[-1] += 1
			print 'running', statement
			if statement[0] == '{':
				stack += (statement,)
				pos += (0,)
			elif statement[0] == 'return':
				if statement[1] == None:
					yield ('return', 0)
				else:
					c = self.compute (statement[1], the_statics, the_locals)
					r = next (c)
					while r[0] == 'wait':
						yield r
						r = next (c)
					yield r
				return
			elif statement[0] == 'while':
				c = self.compute (statement[1], the_statics, the_locals)
				r = next (c)
				while r[0] == 'wait':
					yield r
					r = next (c)
				if r:
					pos[-1] -= 1
					stack += (statement[2],)
					pos += (0,)
			elif statement[0] == 'for':
				if popped:
					if statement[3] != None:
						c = self.compute (statement[3][2], the_statics, the_locals)
						r = next (c)
						while r[0] == 'wait':
							yield r
							r = next (c)
						self.assign (statement[3][0], statement[3][1], r, the_statics, the_locals)
				else:
					if statement[1] != None:
						c = self.compute (statement[1][2], the_statics, the_locals)
						r = next (c)
						while r[0] == 'wait':
							yield r
							r = next (c)
						self.assign (statement[1][0], statement[1][1], r, the_statics, the_locals)
				c = self.compute (statement[2], the_statics, the_locals)
				r = next (c)
				while r[0] == 'wait':
					yield r
					r = next (c)
				if r:
					pos[-1] -= 1
					stack += (statement[4],)
					pos += (0,)
			elif statement[0] == 'if':
				c = self.compute (statement[1], the_statics, the_locals)
				r = next (c)
				while r[0] == 'wait':
					yield r
					r = next (c)
				if r:
					stack += (statement[2],)
					pos += (0,)
				elif statement[3] != None:
					stack += (statement[3],)
					pos += (0,)
			elif statement[0] == 'int':
				if statement[2] != None:
					c = self.compute (statement[2], the_statics, the_locals)
					r = next (c)
					while r[0] == 'wait':
						yield r
						r = next (c)
				else:
					r = ('return', 0)
				assert r[0] == 'return'
				the_locals[statement[1]] = r[1]
			elif statement[0] == 'choice':
				self.choice = []
				for i in statement[1]:
					if i[0] == None:
						self.choice += (i[1],)
					else:
						c = self.compute (i[0], the_statics, the_locals)
						r = next (c)
						while r[0] == 'wait':
							yield r
							r = next (c)
						if r:
							self.choice += (i[1],)
				if len (self.choice) == 0:
					self.choice = None
				else:
					self.choice_title = statement[2]
					yield 'choice', 0
			elif statement[0] in ('()', 'internal'):
				ca = []
				for a in statement[2]:
					c = self.compute (a, the_statics, the_locals)
					r = next (c)
					while r[0] == 'wait':
						yield r
						r = next (c)
					ca += (r[1],)
				if statement[0] == '()':
					f = self.Script (statement[1][0], statement[1][1], ca, None)
				else:
					f = self.Internal (statement[1], ca)
				r = next (f)
				while r[0] == 'wait':
					yield r
					r = next (f)
			else:
				c = self.compute (statement[2], the_statics, the_locals)
				r = next (c)
				while r[0] == 'wait':
					yield r
					r = next (c)
				self.assign (statement[0], statement[1], r, the_statics, the_locals)
	def assign (self, op, name, value, the_statics, the_locals):
		assert value[0] == 'return'
		if op == '=':
			tmp = value[1]
		else:
			if name in the_locals:
				tmp = the_locals[name]
			elif name in the_statics:
				tmp = the_statics[name]
			elif name in self.the_globals:
				tmp = self.the_globals[name]
			else:
				raise AssertionError ('undefined variable %s' % name)
			tmp = eval ('tmp %s %d' % (op[0], value[1]))
		if name in the_locals:
			the_locals[name] = tmp
		elif name in the_statics:
			the_statics[name] = tmp
		elif name in self.the_globals:
			self.the_globals[name] = tmp
		else:
			raise AssertionError ('undefined variable %s' % name)
	def compute (self, expr, the_statics, the_locals):
		print 'computing', expr
		if type (expr) == int:
			yield ('return', expr)
			return
		elif type (expr) == str:
			if expr[0] == '"':
				yield ('return', expr[1:-1])
				return
			# Look up variable.
			if expr in the_locals:
				yield ('return', the_locals[expr])
			elif expr in the_statics:
				yield ('return', the_statics[expr])
			elif expr in self.the_globals:
				yield ('return', self.the_globals[expr])
			else:
				raise AssertionError ('Undefined variable %s' % expr)
			return
		elif expr[0] in ('||', '&&'):
			c = self.compute (expr[1][0], the_statics, the_locals)
			r = next (c)
			while r[0] == 'wait':
				yield r
				r = next (c)
			if r ^ expr[0] == '&&':
				yield ('return', r != 0)
				return
			c = self.compute (expr[1][1], the_statics, the_locals)
			r = next (c)
			while r[0] == 'wait':
				yield r
				r = next (c)
			if r ^ expr[0] == '&&':
				yield ('return', r != 0)
				return
			yield ('return', expr[0] == '&&')
			return
		elif expr[0] == '()':
			fname, name = expr[1]
			args = expr[2]
			s = Script (fname, name, args, None)
			r = next (s)
			while r[0] == 'wait':
				yield r
				r = next (s)
			yield r
			return
		elif expr[0] == 'internal':
			name = expr[1]
			args = []
			for a in expr[2]:
				c = self.compute (a, the_statics, the_locals)
				r = next (c)
				while r[0] == 'wait':
					yield r
					r = next (c)
				args += (r[1],)
			s = self.Internal (name, args)
			r = next (s)
			while r[0] == 'wait':
				yield r
				r = next (s)
			yield r
			return
		elif len (expr[1]) == 1:
			c = self.compute (expr[1][0], the_statics, the_locals)
			r = next (c)
			while r[0] == 'wait':
				yield r
				r = next (c)
			if r[0] == 'return':
				yield ('return', eval ('%s%d' % (expr[0], r[1])))
			else:
				yield ('error', 'invalid return value while computing expression')
			return
		else:
			c = self.compute (expr[1][0], the_statics, the_locals)
			r1 = next (c)
			while r1[0] == 'wait':
				yield r
				r1 = next (c)
			if r1[0] != 'return':
				yield ('error', 'invalid return value while computing expression')
			c = self.compute (expr[1][1], the_statics, the_locals)
			r2 = next (c)
			while r2[0] == 'wait':
				yield r
				r2 = next (c)
			if r2[0] != 'return':
				yield ('error', 'invalid return value while computing expression')
			yield ('return', eval ('%d %s %d' % (r1[1], expr[0], r2[1])))
			return
	def draw_status (self):
		# Draw status bar and borders.
		# These coordinates are directly related to the depth dots of the status sprites.
		self.draw_frame (self.bg, (self.data.seq.find_seq ('status'), 3), (426, 458), 100, (0, 0, 0, 0), False)
		if self.screenlock:
			self.draw_frame (self.bg, (self.data.seq.find_seq ('menu'), 9), (13, 287), 100, (0, 0, 0, 0), False)
			self.draw_frame (self.bg, (self.data.seq.find_seq ('menu'), 10), (633, 287), 100, (0, 0, 0, 0), False)
		else:
			self.draw_frame (self.bg, (self.data.seq.find_seq ('status'), 1), (13, 287), 100, (0, 0, 0, 0), False)
			self.draw_frame (self.bg, (self.data.seq.find_seq ('status'), 2), (633, 287), 100, (0, 0, 0, 0), False)
		# TODO: other status stuff?
	def add_text (self, x, y, text, fg = 'yellow', owner = None):
		t = Sprite (self, x = x, y = y, brain = 'text')
		t.text = text
		t.fg = fg
		t.owner = owner
		t.killdelay = 1000
		return t
	def Internal (self, name, args):
		if name == 'activate_bow':
			self.bow = True, 0
		elif name == 'add_exp':
			self.the_globals['exp'] += args[0]
			t = self.add_text (0, 0, str (args[0]), 'yellow', self.sprites[args[1]])
			t.my = -1
		elif name == 'add_item':
			try:
				idx = self.items.index (None)
			except ValueError:
				yield ('error', 'no more item slots available')
				return
			self.items[idx] = args
			yield ('return', idx)
			return
		elif name == 'add_magic':
			try:
				idx = self.magic.index (None)
			except ValueError:
				yield ('error', 'no more magic slots available')
				return
			self.magic[idx] = args
			yield ('return', idx)
			return
		elif name == 'arm_magic':
			self.current_magic = self.the_globals['cur_magic']
		elif name == 'arm_weapon':
			self.current_weapon = self.the_globals['cur_weapon']
		elif name == 'busy':
			if args[0] not in self.sprites:
				yield ('return', 0)
			else:
				sprite = self.sprites[args[0]]
				yield ('return', sprite.speech if sprite.speech != None else 0)
			return
		elif name == 'compare_sprite_script':
			if args[0] not in self.sprites:
				yield ('return', 0)
			else:
				sprite = self.sprites[args[0]]
				yield ('return', int (sprite.script == args[0]))
			return
		elif name == 'compare_magic':
			yield ('return', int (self.current_magic == args[0]))
			return
		elif name == 'compare_weapon':
			yield ('return', int (self.current_weapon == args[0]))
			return
		elif name == 'copy_bmp_to_screen':
			# TODO? handle palette stuff... If I want it...
			self.bg.draw_drawable (self.gc, self.data.get_image (args[0], self.data.scale), 0, 0, 0, 0, self.winw, self.winh)
		elif name == 'count_item':
			yield ('return', sum ([i[0] == args[0] for i in self.items if i != None]))
			return
		elif name == 'count_magic':
			yield ('return', sum ([i[0] == args[0] for i in self.magic if i != None]))
			return
		elif name == 'create_sprite':
			s = self.add_sprite (args[0], args[1], args[2], args[3], args[4], args[5])
			yield ('wait', 0)
			yield ('return', s.num)
			return
		elif name == 'debug':
			sys.stderr.write ('Debug: %s\n' % str (args[0]))
		elif name == 'dink_can_walk_off_screen':
			self.dink_can_walk_off_screen = args[0] != 0
		elif name == 'disable_all_sprites':
			self.enable_sprites = False
		elif name == 'enable_all_sprites':
			self.enable_sprites = True
		elif name == 'draw_background':
			make_bg ()
		elif name == 'draw_status':
			self.draw_status ()
		elif name == 'editor_seq':
			# TODO
			pass
		elif name == 'editor_frame':	#
			if len (args) == 1:
				yield ('return', self.sprites[args[0]].editor_num)
				return
			# TODO
		elif name == 'editor_type':	#
			# TODO
			pass
		elif name == 'fade_down':
			self.fade = 500, False
		elif name == 'fade_up':
			self.fade = 500, True
		elif name == 'fill_screen':
			self.bg.draw_rectangle (self.gc, True, 0, 0, 640 * self.data.scale / 50, 480 * self.data.scale / 50)
		elif name == 'free_items':
			yield ('return', sum ([i == None for i in self.items]))
			return
		elif name == 'free_magic':
			yield ('return', sum ([i == None for i in self.magic]))
			return
		elif name == 'freeze':
			if args[0] not in self.sprites:
				yield ('error', 'nonexistent sprite')
			else:
				sprite = self.sprites[args[0]]
				sprite.frozen = args[0] != 0
				yield ('return', 0)
			return
		elif name == 'game_exist':
			# TODO
			pass
		elif name == 'get_last_bow_power':
			yield ('return', self.bow[1])
			return
		elif name == 'get_rand_sprite_with_this_brain':
			pass
		elif name == 'get_sprite_with_this_brain':
			pass
		elif name == 'get_version':
			pass
		elif name == 'hurt':
			pass
		elif name == 'init':
			pass
		elif name == 'initfont':
			pass
		elif name == 'inside_box':
			pass
		elif name == 'is_script_attached':
			pass
		elif name == 'kill_all_sounds':
			pass
		elif name == 'kill_cur_item':
			pass
		elif name == 'kill_cur_magic':
			pass
		elif name == 'kill_game':
			sys.exit (0)
		elif name == 'kill_shadow':
			pass
		elif name == 'kill_this_item':
			pass
		elif name == 'kill_this_magic':
			pass
		elif name == 'kill_this_task':
			pass
		elif name == 'load_game':
			pass
		elif name == 'load_screen':
			self.load_screen ()
		elif name == 'move':
			pass
		elif name == 'move_stop':
			pass
		elif name == 'playmidi':
			pass
		elif name == 'playsound':
			pass
		elif name == 'preload_seq':
			pass
		elif name == 'push_active':
			pass
		elif name == 'random':
			pass
		elif name == 'reset_timer':
			pass
		elif name == 'run_script_by_number':
			pass
		elif name == 'save_game':
			pass
		elif name == 'say':
			pass
		elif name == 'say_stop':
			sprite = self.sprites[args[1]]
			self.add_text (0, 0, args[0], sprite)
		elif name == 'say_stop_npc':
			pass
		elif name == 'say_stop_xy':
			pass
		elif name == 'say_xy':
			pass
		elif name == 'screenlock':
			self.screenlock = args[0] != 0
		elif name == 'script_attach':
			pass
		elif name == 'scripts_used':
			pass
		elif name == 'set_button':
			pass
		elif name == 'set_callback_random':
			pass
		elif name == 'set_dink_speed':
			pass
		elif name == 'set_keep_mouse':
			self.keep_mouse = args[0] != 0
		elif name == 'show_bmp':
			pass
		elif name == 'sound_set_kill':
			pass
		elif name == 'sound_set_survive':
			pass
		elif name == 'sound_set_vol':
			pass
		elif name == 'sp':
			for s in self.sprites:
				if self.sprites[s].name == args[0]:
					yield ('return', s)
					return
			else:
				raise AssertionError ('reference to nonexistant sprite %s' % args[0])
		elif name == 'sp_active':	#
			pass
		elif name == 'sp_attack_hit_sound':
			pass
		elif name == 'sp_attack_hit_sound_speed':
			pass
		elif name == 'sp_attack_wait':
			pass
		elif name == 'sp_base_attack':	#
			pass
		elif name == 'sp_base_death':	#
			pass
		elif name == 'sp_base_idle':	#
			pass
		elif name == 'sp_base_walk':	#
			pass
		elif name == 'sp_brain':	#
			pass
		elif name == 'sp_brain_parm':	#
			pass
		elif name == 'sp_brain_parm2':	#
			pass
		elif name == 'sp_defense':	#
			pass
		elif name == 'sp_dir':	#
			pass
		elif name == 'sp_disabled':	#
			pass
		elif name == 'sp_distance':	#
			pass
		elif name == 'sp_editor_num':
			pass
		elif name == 'sp_exp':	#
			pass
		elif name == 'sp_flying':	#
			pass
		elif name == 'sp_follow':	#
			pass
		elif name == 'sp_frame':	#
			self.sprites[args[0]].frame = args[1]
		elif name == 'sp_frame_delay':	#
			pass
		elif name == 'sp_gold':	#
			pass
		elif name == 'sp_nohard':	#
			pass
		elif name == 'sp_hitpoints':	#
			pass
		elif name == 'sp_kill':
			pass
		elif name == 'sp_move_nohard':	#
			pass
		elif name == 'sp_mx':	#
			pass
		elif name == 'sp_my':	#
			pass
		elif name == 'sp_noclip':	#
			pass
		elif name == 'sp_nocontrol':	#
			pass
		elif name == 'sp_nodraw':	#
			pass
		elif name == 'sp_nohit':	#
			pass
		elif name == 'sp_notouch':	#
			pass
		elif name == 'sp_pframe':	#
			self.sprites[args[0]].pframe = args[1]
		elif name == 'sp_picfreeze':
			pass
		elif name == 'sp_pseq':	#
			pass
		elif name == 'sp_que':	#
			pass
		elif name == 'sp_range':	#
			pass
		elif name == 'sp_reverse':	#
			pass
		elif name == 'sp_script':
			pass
		elif name == 'sp_seq':	#
			pass
		elif name == 'sp_size':	#
			pass
		elif name == 'sp_sound':
			pass
		elif name == 'sp_speed':	#
			pass
		elif name == 'sp_strength':	#
			pass
		elif name == 'sp_target':	#
			pass
		elif name == 'sp_timing':	#
			self.sprites[args[0]].timing = args[1]
		elif name == 'sp_touch_damage':
			pass
		elif name == 'sp_x':	#
			pass
		elif name == 'sp_y':	#
			pass
		elif name == 'spawn':
			self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (args[0], 'main', (), None)),)
			yield ('wait', 0)
		elif name == 'start_game':
			# New function, translated as 'spawn ("start-game");' for dink.
			self.the_globals['player_map'] = self.data.script.start_map
			self.sprites[1].x = self.data.script.start_x
			self.sprites[1].y = self.data.script.start_y
			self.sprites[1].base_idle = 'idle'
			self.sprites[1].base_walk = 'walk'
			self.sprites[1].speed = 3
			if not self.keep_mouse:
				self.pointer = False
				# Hmm, this doesn't work on realized widgets...
				#self.set_events (self.get_events () & ~(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK))
			self.sprites[1].dir = 4
			self.sprites[1].brain = 'dink'
			self.sprites[1].set_state ('idle')
			self.sprites[1].que = 0
			self.sprites[1].clip = True
			if self.data.script.intro_script:
				s = self.Script (self.data.script.intro_script, 'main', (), None)
				r = next (s)
				while r[0] == 'wait':
					yield r
					r = next (s)
			self.dink_can_walk_off_screen = False
			self.the_globals['player_map'] = self.data.script.start_map
			self.sprites[1].x = self.data.script.start_x
			self.sprites[1].y = self.data.script.start_y
			self.draw_status ()
			if self.data.script.start_script:
				s = self.Script (self.data.script.start_script, 'main', (), None)
				r = next (s)
				while r[0] == 'wait':
					yield r
					r = next (s)
			self.load_screen ()
			if self.fade[1] == False:
				self.fade = 500, True
		elif name == 'stop_entire_game':
			pass
		elif name == 'stop_wait_for_button':
			pass
		elif name == 'stopcd':
			pass
		elif name == 'stopmidi':
			pass
		elif name == 'turn_midi_off':
			pass
		elif name == 'turn_midi_on':
			pass
		elif name == 'unfreeze':
			pass
		elif name == 'wait':
			yield ('wait', args[0])
		elif name == 'wait_for_button':
			pass
		yield ('return', 0)

game = Play (gtkdink.GtkDink (sys.argv[1], 50))
w = gtk.Window ()
w.set_title ('pyDink')
w.add (game)
w.connect ('destroy', gtk.main_quit)
w.show_all ()
gtk.main ()
