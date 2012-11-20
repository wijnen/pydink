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
import pango
import sys
import os
import datetime
import random

NONEBRAIN = gtkdink.dink.make_brain ('none')
DINKBRAIN = gtkdink.dink.make_brain ('dink')
HEADLESSBRAIN = gtkdink.dink.make_brain ('headless')
DUCKBRAIN = gtkdink.dink.make_brain ('duck')
PIGBRAIN = gtkdink.dink.make_brain ('pig')
MARKBRAIN = gtkdink.dink.make_brain ('mark')
REPEATBRAIN = gtkdink.dink.make_brain ('repeat')
PLAYBRAIN = gtkdink.dink.make_brain ('play')
TEXTBRAIN = gtkdink.dink.make_brain ('text')
MONSTERBRAIN = gtkdink.dink.make_brain ('monster')
ROOKBRAIN = gtkdink.dink.make_brain ('rook')
MISSILEBRAIN = gtkdink.dink.make_brain ('missile')
RESIZEBRAIN = gtkdink.dink.make_brain ('resize')
POINTERBRAIN = gtkdink.dink.make_brain ('pointer')
BUTTONBRAIN = gtkdink.dink.make_brain ('button')
SHADOWBRAIN = gtkdink.dink.make_brain ('shadow')
PERSONBRAIN = gtkdink.dink.make_brain ('person')
FLAREBRAIN = gtkdink.dink.make_brain ('flare')

class Sprite:
	def __init__ (self, data, x = None, y = None, brain = None, seq = None, frame = None, script = None, src = None):
		self.data = data
		self.alive = True
		self.have_brain = False
		if brain is not None:
			brain = gtkdink.dink.make_brain (brain)
		if src != None:
			map = data.the_globals['player_map']
			map_x = (map - 1) % 32
			map_y = (map - 1) / 32
			assert brain == None and seq == None and frame == None and script == None
			self.name = src.name
			self.visible = data.data.layer_visible[src.layer]
			self.x = (src.x - map_x * 12 * 50) if x is None else x
			self.y = (src.y - map_y * 8 * 50) if y is None else y
			self.size = src.size
			self.seq = None
			self.frame = 1
			self.pseq = data.data.seq.find_seq (src.seq)
			self.pframe = src.frame
			self.brain = gtkdink.dink.make_brain (src.brain)
			self.hitpoints = src.hitpoints
			self.defense = src.defense
			self.strength = src.strength
			self.gold = src.gold
			self.speed = src.speed
			self.base_walk = src.base_walk if src.base_walk is not None else ''
			self.base_idle = src.base_idle if src.base_idle is not None else ''
			self.base_attack = src.base_attack if src.base_attack is not None else ''
			self.base_death = src.base_death if src.base_death is not None else ''
			self.timing = src.timing
			self.que = src.que
			self.hard = src.hard
			self.cropbox = (src.left, src.top, src.right, src.bottom)
			self.warp = src.warp
			self.touch_seq = data.data.seq.find_seq (src.touch_seq)
			self.experience = src.experience
			self.sound = src.sound
			self.vision = src.vision
			self.nohit = src.nohit
			self.touch_damage = src.touch_damage
			self.editor_num = src.editcode
			self.script = src.script
		else:
			assert x != None and y != None and brain != None and ((brain == TEXTBRAIN and seq == None and frame == None) or (brain != TEXTBRAIN and seq != None and frame != None))
			self.name = None
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
			self.speed = 0
			self.base_walk = ''
			self.base_idle = ''
			self.base_attack = ''
			self.base_death = ''
			self.timing = 20
			self.que = 0
			self.hard = False
			self.cropbox = (0, 0, 0, 0)
			self.warp = None
			self.touch_seq = None
			self.experience = 0
			self.sound = ''
			self.vision = 0
			self.nohit = False
			self.touch_damage = 0
			self.editor_num = None
			self.script = script
		if self.brain in (REPEATBRAIN, MARKBRAIN, PLAYBRAIN, FLAREBRAIN, MISSILEBRAIN):
			self.seq = self.pseq
			self.frame = self.pframe
		self.brain_parm = 0
		self.brain_parm2 = 0
		self.frame_delay = None
		self.kill_time = None
		self.deathcb = None
		self.dir = 2
		self.clip = True
		self.frozen = False
		self.mx = 0
		self.my = 0
		self.mxlimit = None
		self.mylimit = None
		self.mblock = None
		self.bbox = (0, 0, 0, 0)	# This will be updated when it is drawn.
		self.the_statics = {}
		if self.script:
			for v in data.functions[self.script][''][0]:
				self.the_statics[v] = 0
		self.cache = (None,)
		self.src = src
		self.num = data.next_sprite
		self.state = None
		self.set_state ('passive')
		data.next_sprite += 1
		data.sprites[self.num] = self
	def set_killdelay (self, delay):
		olddelay = self.kill_time is not None
		self.kill_time = self.data.current_time + datetime.timedelta (milliseconds = delay) if delay is not None else None
		if olddelay and not delay:
			self.data.kill_queue.remove (self)
		elif not olddelay and delay:
			self.data.kill_queue.append (self)
		if delay:
			self.data.kill_queue.sort (key = lambda x: x.kill_time)
	def kill (self):
		if not self.alive:
			return
		del self.data.sprites[self.num]
		self.alive = False
		if self.deathcb:
			self.data.events += ((self.data.current_time - datetime.timedelta (seconds = 1), self.deathcb[0], self.deathcb[1]),)
	def set_state (self, state = None):
		# First set dir according to movement.
		if self.mx != 0 or self.my != 0:
			mx, my = [t / abs (t) if t != 0 else 0 for t in (self.mx, self.my)]
			self.dir = mx + 1 + 4 - 3 * my
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
		"Arguments: dink data"
		gtk.DrawingArea.__init__ (self)
		self.data = data
		self.offset = 20 * self.data.scale / 50
		self.current_time = datetime.datetime.utcnow ()
		self.checkpoint = self.current_time
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.control_down = 0
		self.choice = None
		self.choice_title = None
		self.screenlock = False
		self.cursorkeys = (gtk.keysyms.Left, gtk.keysyms.Up, gtk.keysyms.Right, gtk.keysyms.Down)
		self.cursor = [False, False, False, False]
		self.the_globals = {}
		self.blocker = []
		self.kill_queue = []
		nextcode = 1
		for s in data.world.sprite:
			s.editcode = nextcode
			nextcode += 1
		self.scripts = data.script.compile ()
		for v in gtkdink.dink.the_globals:
			self.the_globals[v] = gtkdink.dink.the_globals[v]
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
		self.winw = 12 * self.data.scale + 2 * self.offset
		self.winh = 8 * self.data.scale + 80 * self.data.scale / 50
		self.set_size_request (self.winw, self.winh)
	def start (self, widget):
		pixmap = gtk.gdk.Pixmap (None, 1, 1, 1)
		color = gtk.gdk.Color()
		cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
		self.window.set_cursor (cursor)
		self.data.set_window (self.window)
		self.gc = gtk.gdk.GC (self.window)
		self.clipgc = gtk.gdk.GC (self.window)
		self.clipgc.set_clip_rectangle (gtk.gdk.Rectangle (self.offset, 0, self.data.scale * 12, self.data.scale * 8))
		self.buffer = gtk.gdk.Pixmap (self.window, self.winw, self.winh)
		self.bg = gtk.gdk.Pixmap (self.window, self.winw, self.winh)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('key-release-event', self.keyrelease)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('enter-notify-event', self.enter)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.KEY_RELEASE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.ENTER_NOTIFY_MASK)
		p = self.add_sprite (320, 240, 'pointer', 'special', 8)
		# The last added event is for the brain; set it to survive screen load.
		self.events[-1] = (self.events[-1][0], self.events[-1][1], -1)
		p.clip = False
		p.que = -100000
		p.timing = 10
		# Run start.c (before first update).
		self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script ('start', 'main', (), None), -1),)
		self.expose (widget, (0, 0, self.winw, self.winh));
		self.events += ((self.current_time, self.update (), -1),)
		self.schedule_next ()
	def next_event (self):
		self.events.sort (key = lambda x: x[0])
		self.current_time = datetime.datetime.utcnow ()
		while self.current_time >= self.events[0][0]:
			now, target, sprite = self.events.pop (0)
			if sprite in self.sprites and not self.sprites[sprite].alive:
				continue
			result = next (target)
			if result[0] in ('return', 'kill'):
				pass
			elif result[0] == 'stop':
				result[1] ((target, sprite))
			elif result[0] == 'wait':
				if result[1] > 0:
					then = now + datetime.timedelta (milliseconds = result[1])
					if then < self.checkpoint:
						then = self.checkpoint
					self.events += ((then, target, sprite),)
				else:
					self.events += ((self.current_time + datetime.timedelta (milliseconds = -result[1]), target, sprite),)
			elif result[0] == 'error':
				print ('Error reported: %s' % result[1])
			elif result[0] == 'choice':
				self.choice_waiter = target
			else:
				raise AssertionError ('invalid return type %s' % result[0])
			self.events.sort (key = lambda x: x[0])
		self.schedule_next ()
		return False
	def next_kill (self):
		self.current_time = datetime.datetime.utcnow ()
		while len (self.kill_queue) > 0 and self.kill_queue[0].kill_time <= self.current_time:
			self.kill_queue.pop (0).kill ()
		self.schedule_next ()
		return False
	def schedule_next (self):
		assert self.events != []
		if len (self.kill_queue) > 0 and self.kill_queue[0].kill_time < self.events[0][0]:
			if self.kill_queue[0].kill_time > self.current_time:
				t = self.kill_queue[0].kill_time - self.current_time
				gobject.timeout_add ((t.days * 24 * 3600 + t.seconds) * 1000 + t.microseconds / 1000, self.next_kill)
			else:
				gobject.timeout_add (0, self.next_kill)
		else:
			if self.events[0][0] > self.current_time:
				t = self.events[0][0] - self.current_time
				gobject.timeout_add ((t.days * 24 * 3600 + t.seconds) * 1000 + t.microseconds / 1000, self.next_event)
			else:
				gobject.timeout_add (0, self.next_event)
	def play_music (self, music):
		pass
	def add_sprite (self, x = None, y = None, brain = None, seq = None, frame = None, script = None, src = None):
		ret = Sprite (self, x, y, brain, seq, frame, script, src = src)
		ret.last_time = self.current_time
		if ret.script and 'main' in self.scripts[ret.script]:
			# current_time - datetime.timedelta (seconds = 1), so it runs before continuing the current script.
			self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (ret.script, 'main', (), ret), ret.num),)
		# The brain must be the last added event, because its sprite number is set to -1, so it survives screen loads.
		ret.have_brain = True
		self.events += ((self.current_time, self.do_brain (ret), ret.num),)
		return ret
	def do_brain (self, sprite):
		while True:
			# Reschedule callback. Do this at start, so continue can be used.
			yield ('wait', sprite.timing)
			# If this sprite is passive or dead, don't reschedule this function.
			if not sprite.alive or ((sprite.brain >= len (gtkdink.dink.brains) or sprite.brain == NONEBRAIN) and sprite.mx == 0 and sprite.my == 0):
				sprite.have_brain = False
				yield ('return', 0)
				return
			# Move.
			if not (0 <= sprite.y + sprite.my < 400) or not (0 <= sprite.x + sprite.mx - 20 < 600):
				if sprite.brain == DINKBRAIN and not self.dink_can_walk_off_screen:
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
			if (c[2] == 0 and (mx != 0 or my != 0)) or sprite.mxlimit is not None or sprite.mylimit is not None:
				sprite.x += sprite.mx
				sprite.y += sprite.my
				mx, my = 0, 0
				sprite.set_state ('walk')
				self.push_delay = 0
				# limit[1] is True for negative movement, False for positive movement.
				if (sprite.mxlimit is not None and (sprite.x < sprite.mxlimit[0]) == sprite.mxlimit[1]) or (sprite.mylimit is not None and (sprite.y < sprite.mylimit[0]) == sprite.mylimit[1]):
					sprite.mx, sprite.my = 0, 0
					sprite.mxlimit, sprite.mylimit = None, None
					sprite.set_state ('idle')
					if sprite.mblock:
						self.events += ((self.current_time - datetime.timedelta (seconds = 1), sprite.mblock[0], sprite.mblock[1]),)
						sprite.mblock = None
			elif sprite.brain == DINKBRAIN:
				# Push.
				self.push_delay += 1
				if self.push_delay == 50:
					# TODO: Start pushing.
					pass
			elif sprite.brain in (DUCKBRAIN, PIGBRAIN, PERSONBRAIN):
				# Stop walking.
				sprite.mx = 0
				sprite.my = 0
				sprite.set_state ('idle')
			elif sprite.brain in (MONSTERBRAIN, ROOKBRAIN):
				# Choose new direction.
				need_new_dir = True
			if sprite.mxlimit is None and sprite.mylimit is None and sprite.speed > 0 and not sprite.frozen and sprite.brain in (DUCKBRAIN, PIGBRAIN, MONSTERBRAIN, ROOKBRAIN, PERSONBRAIN) and (need_new_dir or random.random () < (.01 if sprite.mx != 0 or sprite.my != 0 else .05)):
				r = (-1, 0), (1, 0), (0, -1), (0, 1)
				m = (-1, -1), (1, -1), (-1, 1), (1, 1)
				if sprite.brain == ROOKBRAIN:
					sprite.mx, sprite.my = random.choice (r)
					sprite.set_state ('walk')
				elif sprite.brain == MONSTERBRAIN:
					sprite.mx, sprite.my = random.choice (m)
					sprite.set_state ('walk')
				elif (sprite.mx, sprite.my) == (0, 0):
					sprite.mx, sprite.my = random.choice (r + m)
					sprite.set_state ('walk')
				else:
					sprite.mx, sprite.my = 0, 0
					sprite.set_state ('idle')
				sprite.dir = (mx + 1) + 3 * (my + 1) + 1
				sprite.mx *= sprite.speed
				sprite.my *= sprite.speed
			elif sprite.frozen and sprite.mxlimit is None and sprite.mylimit is None:
				sprite.mx, sprite.my = 0, 0
				sprite.set_state ('idle')
			if sprite.brain in (DINKBRAIN, MISSILEBRAIN, FLAREBRAIN, POINTERBRAIN):
				# Test touch damage, warp and missile explosions.
				for s in self.sprites:
					spr = self.sprites[s]
					if spr == sprite or spr.brain == TEXTBRAIN:
						continue
					if spr.seq == None:
						assert spr.pseq != None
						seq = (spr.pseq, spr.pframe)
					else:
						seq = (spr.seq, spr.frame)
					box = seq[0].frames[seq[1]].hardbox
					if spr.x + box[0] <= sprite.x + mx <= spr.x + box[2] and spr.y + box[1] <= sprite.y + my <= spr.y + box[3]:
						if sprite.brain in (DINKBRAIN, POINTERBRAIN):
							if spr.touch_damage != 0:
								if spr.touch_damage == -1:
									if spr.script in self.functions and 'touch' in self.functions[spr.script]:
										self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (spr.script, 'touch', (), None), spr.num),)
								elif not self.touch_delay:
									self.damage (spr.touch_damage, sprite)
							if spr.hard:
								if spr.warp != None:
									# TODO: Warp.
									pass
								sprite.mx = 0
								sprite.my = 0
								# TODO: only stop the direction in which the object is hit.
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
		if not 0 <= oldx + dx < 32 or newscreen not in self.data.world.map:
			return
		# TODO: Make cool transition.
		self.the_globals['player_map'] = newscreen
		self.sprites[1].x -= dx * 599
		self.sprites[1].y -= dy * 399
		self.load_screen ()
	def expose (self, widget, event):
		if isinstance (event, tuple):
			a = event
		else:
			a = event.area
		if self.window:
			self.window.draw_drawable (self.gc, self.buffer, a[0], a[1], a[0], a[1], a[2], a[3])
	def update (self):
		'''This is a generator to periodically update the screen.'''
		while True:
			# Wait some time before being called again. Do this at the start, so continue can be used.
			yield ('wait', -50)
			if self.item_selection:
				# TODO: Item selection screen.
				continue
			self.buffer.draw_drawable (self.gc, self.bg, 0, 0, 0, 0, self.winw, self.winh)
			spr = self.sprites.keys ()
			spr.sort (key = lambda s: (self.sprites[s].y - self.sprites[s].que))
			for s in spr:
				# Change frame.
				sprite = self.sprites[s]
				while sprite.seq != None:
					delay = sprite.frame_delay if sprite.frame_delay is not None else sprite.seq.frames[sprite.frame].delay
					# Divide by 1000, so what's called microseconds is really milliseconds.
					time = (self.current_time - sprite.last_time) / 1000
					# Assume times to be smaller than 1000 s. Speed is more important than this obscure use case.
					if time.microseconds < delay:
						break
					sprite.last_time += datetime.timedelta (microseconds = delay) * 1000
					if sprite.frame + 1 < len (sprite.seq.frames):
						sprite.frame += 1
					else:
						# This is reached if an animation has reached its last frame.
						if sprite.brain == MARKBRAIN:
							self.draw_sprite (self.bg, sprite)
							sprite.kill ()
							continue
						elif sprite.brain in (PLAYBRAIN, FLAREBRAIN):
							sprite.kill ()
							continue
						elif sprite.mx != 0 or sprite.my != 0 or (sprite.brain < len (gtkdink.dink.brains) and sprite.brain != NONEBRAIN):
							if sprite.state != 'idle' or sprite.base_idle != '' or sprite.mx != 0 or sprite.my != 0 or sprite.brain == REPEATBRAIN:
								# If idle without a seq, just freeze the walk seq by not returning to 1.
								sprite.frame = 1
						else:
							sprite.seq = None
					if sprite.seq and sprite.seq.special == sprite.frame:
						# TODO: Hit things.
						pass
				self.draw_sprite (self.buffer, sprite)
			if self.choice != None:
				# TODO: Choice menu.
				pass
			self.expose (self, (0, 0, self.winw, self.winh))
	def draw_sprite (self, target, sprite, clip = True):
		if sprite.brain == TEXTBRAIN:
			# Print text.
			if sprite.owner:
				offset = sprite.owner.x, sprite.owner.y
				x = offset[0] + sprite.offset[0] + sprite.x - sprite.size[0] / 2
				y = offset[1] + sprite.offset[1] + sprite.y
				if x < 0:
					x = 0
				if x + sprite.size[0] >= 620:
					x = 620 - sprite.size[0]
				if y < 0:
					y = 0
				if y + sprite.size[1] >= 400:
					y = 620 - sprite.size[1]
			else:
				offset = 320, 0
				x = offset[0] + sprite.offset[0] + sprite.x - sprite.size[0] / 2
				y = offset[1] + sprite.offset[1] + sprite.y
			target.draw_layout (self.clipgc if clip else self.gc, x, y, sprite.layout, sprite.fg, None)
			return
		if sprite.seq == None:
			assert sprite.pseq != None
			seq = (sprite.pseq, sprite.pframe)
		else:
			seq = (sprite.seq, sprite.frame)
		info = seq, sprite.size, sprite.cropbox, self.data.scale
		if sprite.cache[0] == info:
			target.draw_pixbuf (self.clipgc if sprite.clip else None, sprite.cache[1], 0, 0, self.offset + (sprite.x + sprite.cache[2]) * self.data.scale / 50, (sprite.y + sprite.cache[3]) * self.data.scale / 50)
		else:
			sprite.bbox, sprite.cache = self.draw_frame (target, seq, (sprite.x, sprite.y), sprite.size, sprite.cropbox, sprite.clip, info)
	def draw_frame (self, target, seqframe, pos, size, cropbox, clip, info = None):
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
		return bbox, (info, pb, left - pos[0], top - pos[1])
	def make_bg (self):
		'''Write background to self.bg; return list of non-background sprites (sprite, x, y).'''
		ret = []
		# Draw tiles
		if self.the_globals['player_map'] not in self.data.world.map:
			self.gc.set_foreground (self.data.get_color (0))
			self.bg.draw_rectangle (self.gc, True, 0, 0, 12 * self.data.scale, 8 * self.data.scale)
			return
		screen = self.data.world.map[self.the_globals['player_map']]
		for y in range (8):
			for x in range (12):
				tile = screen.tiles[y][x]
				self.bg.draw_drawable (self.gc, self.data.get_tiles (tile[0]), self.data.scale * tile[1], self.data.scale * tile[2], self.offset + self.data.scale * x, self.data.scale * y, self.data.scale, self.data.scale)
		# Draw bg sprites
		for s in self.data.world.map[self.the_globals['player_map']].sprite:
			if self.data.layer_visible[s.layer]:
				if self.data.layer_background[s.layer]:
					# TODO: draw hardness, warp, etc.
					pass
				else:
					ret += (s,)
			else:
				if self.data.layer_background[s.layer] == True:
					self.draw_sprite (self.bg, Sprite (self, src = s))
				else:
					# Do nothing: invisible foreground sprites are ignored.
					pass
		return ret
	def make_hardmap (self):
		# Add screen hardness.
		if self.the_globals['player_map'] in self.data.world.map:
			screen = self.data.world.map[self.the_globals['player_map']]
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
			if not spr.hard or spr.brain == TEXTBRAIN:
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
		while len (self.sprites) > 1:
			l = self.sprites.keys ()
			self.sprites[l[1] if l[0] == 1 else l[0]].kill ()
		# Kill all scripts, except those marked to survive and those linked to Dink.
		self.events = [x for x in self.events if x[2] == -1]
		spritelist = self.make_bg ()
		self.sprites = { 1: self.sprites[1] }
		self.sprites[1].frozen = False
		self.next_sprite = 2
		if self.the_globals['player_map'] in self.data.world.map:
			script = self.data.world.map[self.the_globals['player_map']].script
			if script in self.scripts and 'main' in self.scripts[script]:
				self.events += ((self.current_time - datetime.timedelta (seconds = 2), self.Script (script, 'main', (), None), -1),)
		for s in spritelist:
			self.add_sprite (src = s)
		self.make_hardmap ()
		self.current_time = datetime.datetime.utcnow ()
		self.checkpoint = self.current_time
		for s in self.sprites:
			spr = self.sprites[s]
			if spr.script in self.scripts and 'main' in self.scripts[spr.script]:
				self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (spr.script, 'main', (), spr), spr.num),)
	def keypress (self, widget, event):
		self.push_delay = 0
		frozen = False
		if self.sprites[1].brain not in (DINKBRAIN, POINTERBRAIN) or self.sprites[1].frozen:
			# Unfreeze in case of waiting for text.
			for i in self.blocker:
				i.kill ()
			frozen = True
		if event.keyval in (gtk.keysyms.Control_R, gtk.keysyms.Control_L):
			self.control_down += 1
			if not frozen:
				self.attack ()
		if event.keyval in self.cursorkeys:
			i = self.cursorkeys.index (event.keyval)
			self.cursor[i] = True
			if not frozen:
				self.compute_dir ()
	def keyrelease (self, widget, event):
		self.push_delay = 0
		frozen = False
		if self.sprites[1].brain not in (DINKBRAIN, POINTERBRAIN) or self.sprites[1].frozen:
			frozen = True
		if event.keyval in (gtk.keysyms.Control_R, gtk.keysyms.Control_L):
			self.control_down -= 1
			if self.control_down <= 0:
				self.control_down = 0
				if not frozen and self.bow[0]:
					self.bow[0] = False
					self.launch ()
		if event.keyval in self.cursorkeys:
			i = self.cursorkeys.index (event.keyval)
			self.cursor[i] = False
			if not frozen:
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
		self.control_down += 1
		if not self.sprites[1].frozen:
			self.attack ()
	def button_off (self, widget, event):
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
			if self.sprites[i].brain != BUTTONBRAIN or self.sprites[i].script not in self.scripts:
				continue
			if self.in_area ((self.sprites[1].x, self.sprites[1].y), self.sprites[i].bbox):
				if 'click' in self.scripts[self.sprites[i].script]:
					self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.sprites[i].script, 'click', (), self.sprites[i]), i),)
				a = True
		# Handle dink attacking.
		if self.current_weapon != None and self.items[self.current_weapon] != None:
			self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.items[self.current_weapon][0], 'use', (), None), -1),)
		else:
			if not a and 'dnohit' in self.functions and 'main' in self.functions['dnohit']:
				self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script ('dnohit', 'main', (), None), -1),)
	def move (self, widget, event):
		if self.sprites[1].brain != POINTERBRAIN or self.sprites[1].frozen:
			return
		ex, ey, emask = self.window.get_pointer ()
		oldx, oldy = self.sprites[1].x, self.sprites[1].y
		self.sprites[1].x, self.sprites[1].y = int (ex) * 50 / self.data.scale, int (ey) * 50 / self.data.scale
		for i in self.sprites:
			if self.sprites[i].brain != BUTTONBRAIN or self.sprites[i].script not in self.functions:
				continue
			o = self.in_area ((oldx, oldy), self.sprites[i].bbox)
			n = self.in_area ((self.sprites[1].x, self.sprites[1].y), self.sprites[i].bbox)
			if o == n:
				continue
			if n == True:
				if 'buttonon' in self.scripts[self.sprites[i].script]:
					self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.sprites[i].script, 'buttonon', (), self.sprites[i]), i),)
			else:
				if 'buttonoff' in self.scripts[self.sprites[i].script]:
					self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (self.sprites[i].script, 'buttonoff', (), self.sprites[i]), i),)
	def enter (self, widget, event):
		self.grab_focus ()
	def in_area (self, pos, area):
		return area[0] <= pos[0] <= area[2] and area[1] <= pos[1] <= area[3]
	def Script (self, fname, name, args, sprite):
		print 'running %s.%s' % (fname, name)
		if fname not in self.functions:
			yield 'error', "script file doesn't exist: %s" % fname
			return
		if name not in self.functions[fname]:
			yield 'error', "script doesn't exist: %s.%s" % (fname, name)
			return
		retval, argnames = self.functions[fname][name]
		stack = [[self.scripts[fname][name]]]
		pos = [0]
		if sprite:
			the_statics = sprite.the_statics
			the_statics['current_sprite'] = sprite.num
		else:
			the_statics = {}
		the_locals = {}
		for i in range (len (argnames)):
			c = self.compute (args[i], the_statics, the_locals)
			r = next (c)
			while r[0] != 'return':
				yield r
				r = next (c)
			assert r[0] == 'return'
			the_locals[argnames[i]] = r[1]
		while True:
			while len (stack) > 0 and pos[-1] >= len (stack[-1]):
				stack.pop ()
				pos.pop ()
			if len (stack) == 0:
				yield ('return', 0)
				return
			statement = stack[-1][pos[-1]]
			pos[-1] += 1
			if statement[0] == '{':
				for s in statement[1]:
					stack[-1] += (s,)
			elif statement[0] == 'return':
				if statement[1] == None:
					yield ('return', 0)
				else:
					c = self.compute (statement[1], the_statics, the_locals)
					r = next (c)
					while r[0] != 'return':
						yield r
						r = next (c)
					yield r
				return
			elif statement[0] == 'while':
				c = self.compute (statement[1], the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
					yield r
					r = next (c)
				if r:
					pos[-1] -= 1
					stack += ([statement[2]],)
					pos += (0,)
			elif statement[0] == 'for':
				if statement[1] != None:
					c = self.compute (statement[1][2], the_statics, the_locals)
					r = next (c)
					while r[0] != 'return':
						yield r
						r = next (c)
					self.assign (statement[1][0], statement[1][1], r, the_statics, the_locals)
				statement[1] = statement[3]
				c = self.compute (statement[2], the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
					yield r
					r = next (c)
				if r:
					pos[-1] -= 1
					stack += ([statement[4]],)
					pos += (0,)
			elif statement[0] == 'if':
				c = self.compute (statement[1], the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
					yield r
					r = next (c)
				if r[1]:
					stack += ([statement[2]],)
					pos += (0,)
				elif statement[3] != None:
					stack += ([statement[3]],)
					pos += (0,)
			elif statement[0] == 'int':
				for var, value in statement[1]:
					if value != None:
						c = self.compute (value, the_statics, the_locals)
						r = next (c)
						while r[0] != 'return':
							yield r
							r = next (c)
					else:
						r = ('return', 0)
					assert r[0] == 'return'
					the_locals[var] = r[1]
			elif statement[0] == 'choice':
				self.choice = []
				for i in statement[1]:
					if i[0] == None:
						self.choice += (i[1],)
					else:
						c = self.compute (i[0], the_statics, the_locals)
						r = next (c)
						while r[0] != 'return':
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
					while r[0] != 'return':
						yield r
						r = next (c)
					ca += (r[1],)
				if statement[0] == '()':
					f = self.Script (statement[1][0], statement[1][1], ca, None)
				else:
					f = self.Internal (statement[1], ca, the_statics, the_locals)
				r = next (f)
				while r[0] != 'return':
					yield r
					r = next (f)
			else:
				c = self.compute (statement[2], the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
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
		if expr[0] == 'const':
			yield ('return', expr[1])
			return
		elif expr[0] == '"':
			yield ('return', expr[1])
			return
		elif expr[0] == 'local':
			assert expr[1] in the_locals
			yield ('return', the_locals[expr[1]])
			return
		elif expr[0] == 'static':
			assert expr[1] in the_statics
			yield ('return', the_statics[expr[1]])
			return
		elif expr[0] == 'global':
			assert expr[1] in self.the_globals
			yield ('return', self.the_globals[expr[1]])
			return
		elif expr[0] in ('||', '&&'):
			c = self.compute (expr[1][0], the_statics, the_locals)
			r = next (c)
			while r[0] != 'return':
				yield r
				r = next (c)
			if r ^ expr[0] == '&&':
				yield ('return', r != 0)
				return
			c = self.compute (expr[1][1], the_statics, the_locals)
			r = next (c)
			while r[0] != 'return':
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
			s = self.Script (fname, name, args, None)
			r = next (s)
			while r[0] != 'return':
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
				while r[0] != 'return':
					yield r
					r = next (c)
				args += (r[1],)
			s = self.Internal (name, args, the_statics, the_locals)
			r = next (s)
			while r[0] != 'return':
				yield r
				r = next (s)
			yield r
			return
		elif len (expr[1]) == 1:
			c = self.compute (expr[1][0], the_statics, the_locals)
			r = next (c)
			while r[0] != 'return':
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
			while r1[0] != 'return':
				yield r
				r1 = next (c)
			if r1[0] != 'return':
				yield ('error', 'invalid return value while computing expression')
			c = self.compute (expr[1][1], the_statics, the_locals)
			r2 = next (c)
			while r2[0] != 'return':
				yield r
				r2 = next (c)
			if r2[0] != 'return':
				yield ('error', 'invalid return value while computing expression')
			yield ('return', int (eval ('%d %s %d' % (r1[1], expr[0], r2[1]))))
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
		if 0 < self.current_weapon < len (self.items) and self.items[self.current_weapon][1] is not None:
			weapon = self.items[self.current_weapon]
			self.draw_frame (self.bg, (self.data.seq.find_seq (weapon[1]), weapon[2]), (599, 454), 100, (0, 0, 0, 0), False)
		if 0 < self.current_magic < len (self.magic) and self.magic[self.current_magic][1] is not None:
			magic = self.magic[self.current_magic]
			self.draw_frame (self.bg, (self.data.seq.find_seq (magic[1]), magic[2]), (194, 454), 100, (0, 0, 0, 0), False)
	def build_string (self, text, the_statics, the_locals):
		if isinstance (text, int):
			return text
		ret = ''
		for i in range (0, len (text) - 1, 2):
			ret += text[i]
			if text[i + 1] in the_locals:
				ret += '%d' % the_locals[text[i + 1]]
			elif text[i + 1] in the_statics:
				ret += '%d' % the_statics[text[i + 1]]
			elif text[i + 1] in self.the_globals:
				ret += '%d' % self.the_globals[text[i + 1]]
		ret += text[-1]
		return ret
	def add_text (self, x, y, text, the_statics, the_locals, fg = -2, owner = None):
		# TODO: line wrapping and border detection
		t = Sprite (self, x = x, y = y, brain = 'text')
		t.que = -1000
		t.text = self.build_string (text, the_statics, the_locals)
		if len (t.text) >= 2 and t.text[0] == '`' and t.text[1] in gtkdink.dink.colornames:
			t.fg = self.data.colors[gtkdink.dink.colornames.index (t.text[1])]
			t.text = t.text[2:]
		else:
			t.fg = self.data.colors[fg]
		t.layout = self.create_pango_layout (t.text)
		attrs = pango.AttrList ()
		attrs.insert (pango.AttrWeight (pango.WEIGHT_BOLD, 0, len (t.text)))
		t.layout.set_attributes (attrs)
		t.size = t.layout.get_pixel_size ()
		t.owner = owner
		if owner is not None:
			seq, frame = (owner.seq, owner.frame) if owner.seq is not None else (owner.pseq, owner.pframe)
			t.offset = 0, seq.frames[frame].boundingbox[1]
		else:
			t.offset = 0, 0
		t.set_killdelay (max (2700, 77 * len (t.text)))
		return t
	def Internal (self, name, args, the_statics, the_locals):
		if name == 'activate_bow':
			self.bow = True, 0
		elif name == 'add_exp':
			self.the_globals['exp'] += args[0]
			t = self.add_text (0, 0, [str (args[0])], {}, {}, owner = self.sprites[args[1]])
			t.set_killdelay = (1000)
			t.my = -1
		elif name == 'add_item':
			try:
				idx = self.items.index (None)
			except ValueError:
				yield ('error', 'no more item slots available')
				return
			self.items[idx] = self.build_string (args[0], the_statics, the_locals), self.build_string (args[1], the_statics, the_locals), args[2]
			yield ('return', idx)
			return
		elif name == 'add_magic':
			try:
				idx = self.magic.index (None)
			except ValueError:
				yield ('error', 'no more magic slots available')
				return
			self.magic[idx] = self.build_string (args[0], the_statics, the_locals), self.build_string (args[1], the_statics, the_locals), args[2]
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
			s = self.add_sprite (args[0], args[1], self.build_string (args[2], the_statics, the_locals), self.build_string (args[3], the_statics, the_locals), args[4])
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
			if args[1] is None:
				yield ('return', self.sprites[args[0]].editcode if args[0] in self.sprites else 0)
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
				self.sprites[args[0]].frozen = True
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
			yield ('kill', 0)
		elif name == 'load_game':
			pass
		elif name == 'load_screen':
			self.load_screen ()
		elif name == 'move':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			d = ((-1, -1), (0, -1), (1, -1), (-1, 0), None, (1, 0), (-1, 1), (0, 1), (1, 1))
			self.sprites[args[0]].mx, self.sprites[args[0]].my = d[args[1] - 1]
			if self.sprites.args[0].mx != 0:
				self.sprites[args[0]].mxlimit = args[2]
				self.sprites[args[0]].mylimit = None
			else:
				self.sprites[args[0]].mxlimit = None
				self.sprites[args[0]].mylimit = args[2]
			if not self.sprites[args[0]].have_brain:
				self.sprites[args[0]].have_brain = True
				self.events += ((self.current_time, self.do_brain (self.sprites[args[0]]), args[0]),)
			# Always ignore hardness. TODO?
		elif name == 'move_stop':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			d = ((-1, 1), (0, 1), (1, 1), (-1, 0), None, (1, 0), (-1, -1), (0, -1), (1, -1))
			self.sprites[args[0]].mx, self.sprites[args[0]].my = d[args[1] - 1]
			if self.sprites[args[0]].mx != 0:
				self.sprites[args[0]].mxlimit = args[2], self.sprites[args[0]].mx < 0
				self.sprites[args[0]].mylimit = None
			else:
				self.sprites[args[0]].mxlimit = None
				self.sprites[args[0]].mylimit = args[2], self.sprites[args[0]].my < 0
			if not self.sprites[args[0]].have_brain:
				self.sprites[args[0]].have_brain = True
				self.events += ((self.current_time, self.do_brain (self.sprites[args[0]]), args[0]),)
			yield ('stop', lambda x: setattr (self.sprites[args[0]], 'mblock', x))
			# Always ignore hardness. TODO?
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
			if args[1] == 1000:
				ret = self.add_text (0, 0, args[0], the_statics, the_locals)
			elif args[1] not in self.sprites:
				yield ('return', 0)
				return
			else:
				sprite = self.sprites[args[1]]
				ret = self.add_text (0, 0, args[0], the_statics, the_locals, owner = sprite)
			yield ('return', ret.num)
		elif name == 'say_stop':
			if args[1] == 1000:
				ret = self.add_text (0, 0, args[0], the_statics, the_locals)
			elif args[1] not in self.sprites:
				yield ('return', 0)
				return
			else:
				sprite = self.sprites[args[1]]
				ret = self.add_text (0, 0, args[0], the_statics, the_locals, owner = sprite)
			if self.sprites[1].frozen:
				self.blocker.append (ret)
			yield ('stop', lambda x: setattr (ret, 'deathcb', x))
			yield ('return', 0)
		elif name == 'say_stop_npc':
			# Pause script to read, then continue. Don't allow skipping through it.
			if args[1] == 1000:
				ret = self.add_text (0, 0, args[0], the_statics, the_locals)
			elif args[1] not in self.sprites:
				yield ('return', 0)
				return
			else:
				sprite = self.sprites[args[1]]
				ret = self.add_text (0, 0, args[0], the_statics, the_locals, owner = sprite)
			yield ('stop', lambda x: setattr (ret, 'deathcb', x))
			yield ('return', 0)
		elif name == 'say_stop_xy':
			ret = self.add_text (args[1], args[2], args[0], the_statics, the_locals)
			if self.sprites[1].frozen:
				self.blocker.append (ret)
			yield ('stop', lambda x: setattr (ret, 'deathcb', x))
			yield ('return', 0)
		elif name == 'say_xy':
			yield ('return', self.add_text (args[1], args[2], args[0], the_statics, the_locals).num)
		elif name == 'screenlock':
			self.screenlock = args[0] != 0
			self.draw_status ()
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
			# The pointer is never disabled, even though it is usually not used.
			pass
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
				if self.sprites[s].name == self.build_string (args[0], the_statics, the_locals):
					yield ('return', s)
					return
		elif name == 'sp_active':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] == 0:
				self.sprites[args[0]].kill ()
		elif name == 'sp_attack_hit_sound':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_attack_hit_sound_speed':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_attack_wait':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_base_attack':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].base_attack = self.build_string (args[1], the_statics, the_locals)
		elif name == 'sp_base_death':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].base_death = self.build_string (args[1], the_statics, the_locals)
		elif name == 'sp_base_idle':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].base_idle = self.build_string (args[1], the_statics, the_locals)
		elif name == 'sp_base_walk':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].base_walk = self.build_string (args[1], the_statics, the_locals)
		elif name == 'sp_brain':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].brain)
				return
			self.sprites[args[0]].brain = gtkdink.dink.make_brain (self.build_string (args[1], the_statics, the_locals))
			if not self.sprites[args[0]].have_brain:
				self.sprites[args[0]].have_brain = True
				self.events += ((self.current_time, self.do_brain (self.sprites[args[0]]), args[0]),)
		elif name == 'sp_brain_parm':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].brain_parm)
				return
			self.sprites[args[0]].brain_parm = args[1]
		elif name == 'sp_brain_parm2':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].brain_parm2)
				return
			self.sprites[args[0]].brain_parm2 = args[1]
		elif name == 'sp_defense':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_dir':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_disabled':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_distance':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_editor_num':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			yield ('return', self.sprites[args[0]].editor_num)
		elif name == 'sp_exp':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_flying':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_follow':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_frame':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].frame)
				return
			self.sprites[args[0]].frame = args[1]
		elif name == 'sp_frame_delay':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_gold':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_nohard':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_hitpoints':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_kill':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].set_killdelay (args[1] if args[1] > 0 else None)
		elif name == 'sp_move_nohard':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_mx':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].mx)
				return
			self.sprites[args[0]].mx = args[1]
			if not self.sprites[args[0]].have_brain:
				self.sprites[args[0]].have_brain = True
				self.events += ((self.current_time, self.do_brain (self.sprites[args[0]]), args[0]),)
		elif name == 'sp_my':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].my)
				return
			self.sprites[args[0]].my = args[1]
			if not self.sprites[args[0]].have_brain:
				self.sprites[args[0]].have_brain = True
				self.events += ((self.current_time, self.do_brain (self.sprites[args[0]]), args[0]),)
		elif name == 'sp_noclip':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', not self.sprites[args[0]].clip)
				return
			self.sprites[args[0]].clip = not args[1]
		elif name == 'sp_nocontrol':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_nodraw':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_nohit':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_notouch':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_pframe':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', not self.sprites[args[0]].pframe)
				return
			self.sprites[args[0]].pframe = args[1]
		elif name == 'sp_picfreeze':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_pseq':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].pseq = self.data.seq.find_seq (self.build_string (args[1], the_statics, the_locals))
		elif name == 'sp_que':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_range':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_reverse':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_script':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].script = self.build_string (args[1], the_statics, the_locals)
		elif name == 'sp_seq':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			self.sprites[args[0]].seq = self.data.seq.find_seq (self.build_string (args[1], the_statics, the_locals))
		elif name == 'sp_size':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_sound':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_speed':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].speed)
				return
			self.sprites[args[0]].speed = args[1]
		elif name == 'sp_strength':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_target':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
		elif name == 'sp_timing':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].timing)
				return
			self.sprites[args[0]].timing = args[1]
		elif name == 'sp_touch_damage':
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].touch_damage)
				return
			self.sprites[args[0]].touch_damage = args[1]
		elif name == 'sp_x':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].x)
				return
			self.sprites[args[0]].x = args[1]
		elif name == 'sp_y':	#
			if args[0] not in self.sprites:
				yield ('return', 0)
				return
			if args[1] is None:
				yield ('return', self.sprites[args[0]].y)
				return
			self.sprites[args[0]].y = args[1]
		elif name == 'spawn':
			self.events += ((self.current_time - datetime.timedelta (seconds = 1), self.Script (args[0], 'main', (), None), -1),)
			yield ('wait', 0)
		elif name == 'start_game':
			# New function, translated as 'spawn ("_start_game");' for dink.
			self.sprites[1].base_idle = 'idle'
			self.sprites[1].base_walk = 'walk'
			self.sprites[1].speed = 3
			self.sprites[1].dir = 4
			self.sprites[1].brain = DINKBRAIN
			self.sprites[1].set_state ('idle')
			self.sprites[1].que = 0
			self.sprites[1].clip = True
			if 'intro' in self.functions and 'main' in self.functions['intro']:
				s = self.Script ('intro', 'main', (), None)
				r = next (s)
				while r[0] in ('wait', 'stop'):
					yield r
					r = next (s)
			self.dink_can_walk_off_screen = False
			if 'init' in self.functions and 'main' in self.functions['init']:
				s = self.Script ('init', 'main', (), None)
				r = next (s)
				while r[0] in ('wait', 'stop'):
					yield r
					r = next (s)
			self.load_screen ()
			self.draw_status ()
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
			self.sprites[args[0]].frozen = False
			if args[0] == 1:
				self.blocker = []
		elif name == 'wait':
			yield ('wait', args[0])
		elif name == 'wait_for_button':
			pass
		yield ('return', 0)

game = Play (gtkdink.GtkDink (sys.argv[1], 50))
window = gtk.Window ()
window.set_title ('%s - PyDink' % os.path.basename (sys.argv[1]))
window.add (game)
window.connect ('destroy', gtk.main_quit)
window.show_all ()
gtk.main ()
