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
import numpy
import pygame	# for sound

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

BUTTON_ACTION = 1
BUTTON_TALK = 2
BUTTON_MAGIC = 3
BUTTON_INVENTORY = 4
BUTTON_ESCAPE = 5
BUTTON_MAP = 6
BUTTON_DOWN = 12
BUTTON_LEFT = 14
BUTTON_RIGHT = 16
BUTTON_UP = 18

class Sprite:
	def __init__ (self, data, x = None, y = None, brain = None, seq = None, frame = None, script = None, src = None, view = None):
		self.data = data
		self.last_time = data.current_time
		self.alive = True
		self.have_brain = False
		if brain is not None:
			brain = gtkdink.dink.make_brain (brain)
		if src is not None:
			map = data.the_globals['player_map']
			map_x = (map - 1) % 32
			map_y = (map - 1) / 32
			assert brain == None and seq == None and frame == None and script == None
			self.name = src.name
			self.visible = src.is_visible ()
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
		self.text = None
		self.brain_parm = 0
		self.brain_parm2 = 0
		self.range = 40
		self.distance = 0
		self.reverse = False
		self.flying = False
		self.follow = 0
		self.target = 0
		self.nodraw = False
		self.nocontrol = False
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
			if self.script not in data.functions:
				print ("Warning: script %s doesn't exist" % self.script)
			else:
				for v in data.functions[self.script][''][0]:
					self.the_statics[v] = 0
		self.cache = (None,)
		self.src = src
		self.state = None
		self.num = 0
		self.set_state ('passive')
		self.view = view
		if view is not None:
			self.num = data.next_sprite
			data.next_sprite += 1
			view.sprites[self.num] = self
	def set_killdelay (self, delay):
		olddelay = self.kill_time is not None
		self.kill_time = self.data.current_time + datetime.timedelta (milliseconds = delay) if delay is not None else None
		if olddelay and not delay:
			self.view.kill_queue.remove (self)
		elif not olddelay and delay:
			self.view.kill_queue.append (self)
		if delay:
			self.view.kill_queue.sort (key = lambda x: x.kill_time)
	def kill (self):
		if not self.alive:
			return
		if self.num == 1:
			# Don't kill Dink; code everywhere depends on its existence.
			return
		del self.view.sprites[self.num]
		self.alive = False
		if self.brain == TEXTBRAIN and self.owner:
			self.owner.text = None
		if self in self.view.blocker:
			self.view.blocker.remove (self)
		if self.deathcb:
			self.view.events += ((self.data.current_time - datetime.timedelta (seconds = 1), self.deathcb[0], self.deathcb[1]),)
	def set_state (self, state = None):
		assert self.num != 1 or self.brain != NONEBRAIN
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
			elif self.base_walk:
				self.seq = None
				self.pseq = self.data.data.seq.get_dir_seq (self.base_walk, self.dir)
				self.pframe = 1
			else:
				self.seq = None
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

class View:
	cursorkeys = (gtk.keysyms.Left, gtk.keysyms.Up, gtk.keysyms.Right, gtk.keysyms.Down)
	def __init__ (self, data):
		self.data = data
		self.sprites = {}
		self.events = []
		self.choice = None
		self.choice_title = None
		self.choice_response = None
		self.choice_current = 0
		self.choice_waiter = None
		self.stopped = False
		self.wait_for_button = None
		self.warp_wait = None
		self.screenlock = False
		self.blocker = []
		self.fade_block = []
		self.enable_sprites = True
		self.kill_queue = []
		self.push_delay = 0
		self.touch_delay = 0
		self.push_active = True
		self.bow = [False, None, None, None]
		self.fade = (0, True, self.data.current_time)
		self.dink_can_walk_off_screen = False
		self.bg = gtk.gdk.Pixmap (self.data.window, self.data.winw, self.data.winh)
		self.choice_sprites = [Sprite (self.data, x, y, brain, seq, frame, '', view = None) for x, y, brain, seq, frame in ((181, 270, 'none', 'textbox', 2), (355, 254, 'none', 'textbox', 3), (528, 270, 'none', 'textbox', 4), (165, 104, 'repeat', 'arrow-l', 4), (503, 104, 'repeat', 'arrow-r', 4))]
		self.events += ((self.data.current_time, self.update (), -2),)
		# Create pointer sprite.
		self.sprites[1] = Sprite (self.data, 320, 240, 'pointer', 'special', 8, '', view = None)
		self.sprites[1].num = 1
		self.sprites[1].timing = 10
		self.sprites[1].have_brain = True
		self.events += ((self.data.current_time, self.do_brain (self.sprites[1]), -1),)
		self.sprites[1].last_time = self.data.current_time
		self.last_time = data.current_time
		self.stat_info = {}
		for stat, x, y, width, size, seq, step in (
				('strength', 126, 428, 16, 3, 'numr', 1),
				('defense',  126, 450, 16, 3, 'numb', 1),
				('magic',    126, 472, 16, 3, 'nump', 1),
				('exp',      450, 467, 10, 5, 'nums', 9),
				('gold',     373, 470, 16, 5, 'numy', 9),
				('level',    534, 471,  8, 1, 'level', 1),
			):
			self.stat_info[stat] = [0, Sprite (self.data, x, y, 'none', seq, 1, '', view = None), x, width, size, step]
			self.stat_info[stat][1].clip = False
		self.stat_info['life']  = [10, Sprite (self.data, 0, 425, 'none', 'health-r', 1, '', view = None), 300, 425, None, 1]
		self.stat_info['life'][1].clip = False
		self.stat_info['lifemax'] = [10, Sprite (self.data, 0, 425, 'none', 'health-w', 1, '', view = None), 300, 425, None, 1]
		self.stat_info['lifemax'][1].clip = False
	def add_sprite (self, x = None, y = None, brain = None, seq = None, frame = None, script = None, src = None):
		ret = Sprite (self.data, x, y, brain, seq, frame, script, src = src, view = self)
		self.data.run_script (ret.script, 'main', (), ret)
		ret.have_brain = True
		self.events += ((self.data.current_time, self.do_brain (ret), ret.num),)
		ret.last_time = self.data.current_time
		return ret
	def get_sprite_by_editor_num (self, num):
		for s in self.sprites:
			if self.sprites[s].editor_num == num:
				return self.sprites[s]
		return None
	def get_sprite_by_name (self, name):
		for s in self.sprites:
			if self.sprites[s].name == name:
				return s
		return 0
	def get_editor_sprite (self, num):
		for s in self.data.data.world.sprite:
			if s.editcode == num:
				return s
		return None
	def try_touch (self, target):
		if not target.touch_seq:
			return False
		# Play touch sequence before warping.
		# Find instantiated sprite.
		find = [self.sprites[x] for x in self.sprites if self.sprites[x].src == target]
		if len (find) > 0:
			spr = find[0]
			spr.seq = spr.touch_seq
			spr.frame = 1
			spr.brain = NONEBRAIN
			spr.frame_delay = None
			spr.last_time = self.data.current_time
		else:
			touch = self.data.data.seq.find_seq (target.touch_seq)
			if touch is None:
				print "Touch seq %s doesn't exist" % target.touch_seq
				return False
			# Create a new sprite.
			map = self.data.the_globals['player_map']
			map_x = (map - 1) % 32
			map_y = (map - 1) / 32
			spr = self.add_sprite (target.x - map_x * 12 * 50, target.y - map_y * 8 * 50, 'none', touch.code, 1)
			spr.seq = touch
			spr.frame = 1
			spr.que = target.que
		self.warp_wait = spr
		return True
	def do_brain (self, sprite):
		while True:
			# Reschedule callback. Do this at start, so continue can be used.
			yield ('wait', sprite.timing)
			# If this sprite is passive or dead, don't reschedule this function.
			if not sprite.alive or (sprite.brain not in (DINKBRAIN, DUCKBRAIN, PIGBRAIN, PERSONBRAIN, MONSTERBRAIN, ROOKBRAIN, MISSILEBRAIN, FLAREBRAIN, HEADLESSBRAIN) and sprite.mx == 0 and sprite.my == 0):
				sprite.have_brain = False
				yield ('return', 0)
				return
			if sprite.nocontrol:
				# Disable brain until control is back.
				continue
			# Move.
			if not (0 <= sprite.y + sprite.my < 400) or not (0 <= sprite.x + sprite.mx - 20 < 600):
				if sprite.brain == DINKBRAIN and not self.dink_can_walk_off_screen and not self.screenlock:
					# Move to new screen (if possible).
					if sprite.y + sprite.my < 0:
						self.try_move (0, -1)
					elif sprite.x + sprite.mx - 20 < 0:
						self.try_move (-1, 0)
					elif sprite.y + sprite.my >= 400:
						self.try_move (0, 1)
					elif sprite.x + sprite.mx - 20 >= 600:
						self.try_move (1, 0)
					# Whether it worked or not, don't do anything else.
					continue
				c = 1
			else:
				c = self.hardmap[sprite.y + sprite.my][sprite.x + sprite.mx - 20]
			need_new_dir = False
			mx, my = sprite.mx, sprite.my
			if ((c == 0 or c == 1 and sprite.flying) and (mx != 0 or my != 0)) or sprite.mxlimit is not None or sprite.mylimit is not None:
				sprite.x += sprite.mx
				sprite.y += sprite.my
				mx, my = 0, 0
				sprite.set_state ('walk')
				if sprite.brain == DINKBRAIN:
					self.push_delay = 0
				# limit[1] is True for negative movement, False for positive movement.
				if (sprite.mxlimit is not None and (sprite.x < sprite.mxlimit[0]) == sprite.mxlimit[1]) or (sprite.mylimit is not None and (sprite.y < sprite.mylimit[0]) == sprite.mylimit[1]):
					sprite.mx, sprite.my = 0, 0
					sprite.mxlimit, sprite.mylimit = None, None
					sprite.set_state ('idle')
					if sprite.mblock:
						self.events += ((self.data.current_time - datetime.timedelta (seconds = 1), sprite.mblock[0], sprite.mblock[1]),)
						sprite.mblock = None
			elif sprite.brain == DINKBRAIN and (mx != 0 or my != 0):
				if c > 2:
					target = self.get_editor_sprite (c)
					if target.warp != None:
						# Warp.
						if not self.try_touch (target):
							# Fade while warping.
							self.fade = 500, False, self.data.current_time
						# Freeze Dink during the touch sequence and fade down. He will be unfrozen at load_screen.
						sprite.frozen = True
						# Wake up when the fade is done. In case of a touch sequence, the fade is started from update.
						yield ('stop', lambda x: self.fade_block.append (x))
						self.data.the_globals['player_map'] = target.warp[0]
						self.sprites[1].x = target.warp[1]
						self.sprites[1].y = target.warp[2]
						self.load_screen ()
						self.fade = 500, True, self.data.current_time
				# Push.
				if self.push_active:
					self.push_delay += 1
					if self.push_delay == 50:
						# Start pushing. Note that this is triggered only once, but Dink keeps pushing until something happens.
						sprite.seq = self.data.data.seq.get_dir_seq ('push', sprite.dir)
						# Call push() on affected sprite.
						if c < 0 and -c in self.sprites:
							# Generated sprite.
							self.data.run_script (self.sprites[-c].script, 'push', (), self.sprites[-c])
						elif c > 2:
							# Editor sprite.
							target = self.get_sprite_by_editor_num (c)
							if target:
								self.data.run_script (target.script, 'push', (), target)
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
				elif sprite.brain == PIGBRAIN:
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
			if sprite.brain in (DINKBRAIN, MISSILEBRAIN, FLAREBRAIN, POINTERBRAIN) and sprite.mxlimit is None and sprite.mylimit is None:
				# Test touch damage, warp and missile explosions.
				for s in self.sprites.keys ():
					if s not in self.sprites:
						# This can happen because scripts are run from this loop.
						continue
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
						if sprite.brain == DINKBRAIN:
							if spr.touch_damage != 0 and not sprite.nohit and not self.touch_delay:
								if spr.touch_damage > 0:
									self.touch_delay = 10
									self.damage (spr.touch_damage, sprite, spr)
								self.data.run_script (spr.script, 'touch', (), spr)
							# TODO: only stop the direction in which the object is hit.
						elif not spr.nohit:
							# TODO: Explode.
							pass
			if self.data.space and sprite.brain == DINKBRAIN and not sprite.frozen:
				self.data.space = False
				# Talk.
				targets = [x for x in self.hit_list (sprite, sprite.seq) if x.script in self.data.scripts and 'talk' in self.data.scripts[x.script]]
				if len (targets) == 0:
					self.data.run_script ('dnotalk', 'main', (), None)
				else:
					# Find closest.
					targets.sort (key = lambda x: ((x.x - sprite.x) ** 2 + (x.y - sprite.y) ** 2))
					self.data.run_script (targets[0].script, 'talk', (), targets[0])
			if self.data.shift and sprite.brain == DINKBRAIN and not sprite.frozen:
				# Cast magic.
				if 0 < self.data.current_magic < len (self.data.magic) and self.data.magic[self.data.current_magic][0] is not None:
					if self.data.the_globals['magic_level'] >= self.data.the_globals['magic_cost']:
						self.data.the_globals['magic_level'] = 0
						self.data.run_script (self.data.magic[self.data.current_magic][0], 'use', (), None)
				else:
					self.data.run_script ('dnomagic', 'main', (), None)
					self.data.shift = False	# This will never work, and it shouldn't trigger this script again.
	def try_move (self, dx, dy):
		# Move to a new screen if possible, otherwise do nothing.
		screen = self.data.the_globals['player_map']
		if screen == None:
			return
		oldx = (screen - 1) % 32
		newscreen = screen + dx + 32 * dy
		if not 0 <= oldx + dx < 32 or newscreen not in self.data.data.world.map:
			return
		# TODO: Make cool transition.
		self.data.the_globals['player_map'] = newscreen
		self.sprites[1].x -= dx * 599
		self.sprites[1].y -= dy * 399
		self.load_screen ()
	def load_screen (self):
		while len (self.sprites) > 1:
			l = self.sprites.keys ()
			self.sprites[l[1] if l[0] == 1 else l[0]].kill ()
		# Kill all scripts, except those marked to survive.
		self.events = [x for x in self.events if x[2] < 0]
		spritelist = self.make_bg ()
		self.sprites = { 1: self.sprites[1] }
		self.sprites[1].frozen = False
		self.screenlock = False
		self.next_sprite = 2
		if self.data.the_globals['player_map'] in self.data.data.world.map:
			map = self.data.data.world.map[self.data.the_globals['player_map']]
			script = map.script
			self.data.run_script (script, 'main', (), None)
			if map.music:
				self.data.play_music (map.music)
		for s in spritelist:
			self.add_sprite (src = s)
		self.make_hardmap ()
		self.data.current_time = datetime.datetime.utcnow ()
		self.data.checkpoint = self.data.current_time
		for s in self.sprites:
			spr = self.sprites[s]
			self.data.run_script (spr.script, 'main', (), spr)
			if spr.sound:
				self.data.play_sound (spr.sound, True, spr)
		self.compute_dir ()
	def make_bg (self):
		'''Write background to self.bg; return list of non-background sprites (sprite, x, y).'''
		ret = []
		# Draw tiles
		if self.data.the_globals['player_map'] not in self.data.data.world.map:
			self.data.gc.set_foreground (self.data.data.get_color (0))
			self.bg.draw_rectangle (self.data.gc, True, 0, 0, 12 * self.data.data.scale, 8 * self.data.data.scale)
			return ret
		screen = self.data.data.world.map[self.data.the_globals['player_map']]
		for y in range (8):
			for x in range (12):
				tile = screen.tiles[y][x]
				self.bg.draw_drawable (self.data.gc, self.data.data.get_tiles (tile[0]), self.data.data.scale * tile[1], self.data.data.scale * tile[2], self.data.offset + self.data.data.scale * x, self.data.data.scale * y, self.data.data.scale, self.data.data.scale)
		# Draw bg sprites
		for s in self.data.data.world.map[self.data.the_globals['player_map']].sprite:
			layer = self.parent.editor_sprites (s.num)['layer']
			self.parent.is_visible (layer) and self.parent.is_bg (layer):
				self.draw_sprite (self.bg, Sprite (self.data, src = s, view = None))
			if self.parent.is_fg (layer):
				ret += (s,)
		return ret
	def handle_event (self, now, target, sprite):
		# This normally runs once, but a failed choice may need to run the whole function again.
		while True:
			if sprite in self.sprites and not self.sprites[sprite].alive:
				return
			result = next (target)
			if result[0] in ('return', 'kill'):
				pass
			elif result[0] == 'stop':
				result[1] ((target, sprite))
			elif result[0] == 'wait':
				if result[1] > 0:
					then = now + datetime.timedelta (milliseconds = result[1])
					if then < self.data.checkpoint:
						then = self.data.checkpoint
					if self.stopped:
						self.stopped[1].append ((then, target, sprite))
					else:
						self.data.get_view ().events += ((then, target, sprite),)
				else:
					self.data.get_view ().events += ((self.data.current_time + datetime.timedelta (milliseconds = -result[1]), target, sprite),)
			elif result[0] == 'error':
				print ('Error reported: %s' % result[1])
			elif result[0] == 'choice':
				# Fail if we're already in a choice.
				if self.choice_waiter is not None:
					# Immediately continue the script, returning 0.
					self.choice_response = 0
					continue
				self.choice_waiter = target, sprite
				self.choice_current = 0
			else:
				raise AssertionError ('invalid return type %s' % result[0])
			return
	def next_event (self):
		self.events.sort (key = lambda x: x[0])
		self.data.current_time = datetime.datetime.utcnow ()
		while self.data.current_time >= self.events[0][0] and self.data.get_view () == self:
			self.handle_event (*self.events.pop (0))
			self.events.sort (key = lambda x: x[0])
		self.data.schedule_next ()
		return False
	def next_kill (self):
		self.data.current_time = datetime.datetime.utcnow ()
		while len (self.kill_queue) > 0 and self.kill_queue[0].kill_time <= self.data.current_time:
			self.kill_queue.pop (0).kill ()
		self.data.schedule_next ()
		return False
	def schedule_next (self):
		if self.events == []:
			# If for some reason dying didn't work, try again.
			gtk.main_quit ()
			return
		if self.data.dying:
			# Don't schedule new events when dying.
			return
		if len (self.kill_queue) > 0 and self.kill_queue[0].kill_time < self.events[0][0]:
			if self.kill_queue[0].kill_time > self.data.current_time:
				t = self.kill_queue[0].kill_time - self.data.current_time
				gobject.timeout_add ((t.days * 24 * 3600 + t.seconds) * 1000 + t.microseconds / 1000, self.next_kill)
			else:
				gobject.timeout_add (0, self.next_kill)
		else:
			if self.events[0][0] > self.data.current_time:
				t = self.events[0][0] - self.data.current_time
				gobject.timeout_add ((t.days * 24 * 3600 + t.seconds) * 1000 + t.microseconds / 1000, self.next_event)
			else:
				gobject.timeout_add (0, self.next_event)
	def hit_list (self, sprite, seq):
		'''Return a list of sprites which can be hit by this one. Used for hit and talk.'''
		if seq is None or isinstance (seq.name, str) or seq.name[1] == 'die':
			mx, my = 0, 0
		else :
			mx, my = (None, (-1, 1), (0, 1), (1, 1), (-1, 0), None, (1, 0), (-1, -1), (0, -1), (1, -1))[seq.name[1]]
		x = sprite.x + mx * sprite.range
		y = sprite.y + my * sprite.range
		ret = []
		for s in self.sprites:
			spr = self.sprites[s]
			if spr == sprite:
				# Don't hit self.
				continue
			if spr.seq is not None:
				hardbox = spr.seq.frames[spr.frame].hardbox
			elif spr.pseq is not None:
				hardbox = spr.pseq.frames[spr.pframe].hardbox
			else:
				assert spr.brain == TEXTBRAIN
				continue
			r = sprite.range / 2
			if spr.x + hardbox[0] >= x + r:
				continue
			if spr.y + hardbox[1] >= y + r:
				continue
			if spr.x + hardbox[2] < x - r:
				continue
			if spr.y + hardbox[3] < y - r:
				continue
			ret.append (spr)
		return ret
	def update (self):
		'''This is a generator to periodically update the screen.'''
		while True:
			# Wait some time before being called again. Do this at the start, so continue can be used.
			yield ('wait', -50)
			if self.data.the_globals['update_status'] != 0:
				self.update_stats ()
			if self.fade[0] != 0:
				ticks = ((self.data.current_time - self.fade[2]) / 1000).microseconds
				self.fade = (max (0, self.fade[0] - ticks), self.fade[1], self.data.current_time)
				if self.fade[0] == 0:
					for b in self.fade_block:
						self.events += ((self.data.current_time, b[0], b[1]),)
					self.fade_block = []
			spr = self.sprites.keys ()
			spr.sort (key = lambda s: (self.sprites[s].y - self.sprites[s].que))
			if not self.stopped:
				if self.bow[0]:
					self.sprites[1].seq = None
					self.sprites[1].pseq = self.data.data.seq.get_dir_seq (self.bow[3], self.dir)
					ms = ((self.current_time - self.bow[1]) / 1000).microseconds
					if ms >= 1000:
						self.sprites[1].pframe = len (self.sprites[1].pseq.frames) - 1
					else:
						self.sprites[1].pframe = 1 + ms * (len (self.sprites[1].pseq.frames) - 1) / 1000
				for s in spr:
					if s not in self.sprites or self.sprites[s].nodraw:
						continue
					# Change frame.
					self.animate (self.sprites[s])
				if self.touch_delay:
					self.touch_delay -= 1
			if self.fade[:2] == (0, False):
				self.data.gc.set_foreground (self.data.data.colors[0])
				self.data.buffer.draw_rectangle (self.data.gc, True, 0, 0, self.data.winw, self.data.winh)
			else:
				self.data.buffer.draw_drawable (self.data.gc, self.bg, 0, 0, 0, 0, self.data.winw, self.data.winh)
			if self.enable_sprites and self.fade[:2] != (0, False):
				for s in spr:
					if s not in self.sprites or self.sprites[s].nodraw or self.sprites[s].brain == TEXTBRAIN:
						continue
					self.draw_sprite (self.data.buffer, self.sprites[s])
			if self.fade[:2] != (0, True):
				if self.fade[0] != 0:
					color = self.fade[0] * 255 / 500
					if not self.fade[1]:
						color = 255 - color
					self.data.fade_pixbuf.fill (color)
					self.data.buffer.draw_pixbuf (self.data.gc, self.data.fade_pixbuf, 0, 0, 0, 0)
			for s in spr:
				if s not in self.sprites or self.sprites[s].nodraw or self.sprites[s].brain != TEXTBRAIN:
					continue
				self.draw_textsprite (self.data.buffer, self.sprites[s])
			if self.choice != None:
				# Compute arrow position.
				y = self.choice_title[2] + self.choice_title[4] + 30 + 5
				for i in self.choice[:self.choice_current]:
					y += i[3] + 5
				y += self.choice[self.choice_current][3] / 2
				self.choice_sprites[-1].y = y
				self.choice_sprites[-2].y = y
				for s in self.choice_sprites:
					self.animate (s)
					self.draw_sprite (self.data.buffer, s)
				self.data.buffer.draw_layout (self.data.gc, self.choice_title[1], self.choice_title[2], self.choice_title[3], self.data.data.colors[-1], None)
				y = self.choice_title[2] + self.choice_title[4] + 30
				for n, i in enumerate (self.choice):
					self.data.buffer.draw_layout (self.data.gc, i[2], y, i[4], self.data.data.colors[-1 if n == self.choice_current else -2], None)
					y += i[3] + 5
			self.data.expose (self, (0, 0, self.data.winw, self.data.winh))
	def animate (self, sprite):
		if sprite.brain == RESIZEBRAIN:
			if ((self.data.current_time - sprite.last_time) / 1000).microseconds < 100:
				return
			if sprite.size == sprite.brain_parm:
				sprite.kill ()
				return
			if sprite.size < sprite.brain_parm:
				sprite.size = min (sprite.size + 10, sprite.brain_parm)
			else:
				sprite.size = max (sprite.size - 10, sprite.brain_parm)
			return
		if sprite.brain in (REPEATBRAIN, MARKBRAIN, PLAYBRAIN, FLAREBRAIN, MISSILEBRAIN) and sprite.seq is None:
			sprite.seq = sprite.pseq
			sprite.frame = 1
		while sprite.seq != None:
			if sprite.frame_delay is not None:
				delay = sprite.frame_delay
			else:
				if sprite.frame >= len (sprite.seq.frames):
					delay = 1
				else:
					delay = sprite.seq.frames[sprite.frame].delay
			# Divide by 1000, so what's called microseconds is really milliseconds.
			time = (self.data.current_time - sprite.last_time) / 1000
			# Assume times to be smaller than 1000 s. Speed is more important than this obscure use case.
			if time.microseconds < delay:
				break
			sprite.last_time += datetime.timedelta (microseconds = delay) * 1000
			if sprite.frame + 1 < len (sprite.seq.frames):
				sprite.frame += 1
			else:
				# This is reached if an animation has reached its last frame.
				if self.warp_wait == sprite:
					# We are waiting for this sequence to complete before warping.
					# The warp is triggered from fade_block, so we only have to fade the screen.
					self.fade = 500, False, self.data.current_time
				if sprite.brain == MARKBRAIN:
					self.draw_sprite (self.bg, sprite)
					sprite.kill ()
					continue
				elif sprite.brain in (PLAYBRAIN, FLAREBRAIN):
					sprite.kill ()
					continue
				elif sprite.mx != 0 or sprite.my != 0 or (sprite.brain < len (gtkdink.dink.brains) and sprite.brain != NONEBRAIN):
					# If nocontrol is set, we are waiting for the animation to finish. This happened now.
					if sprite.nocontrol:
						sprite.nocontrol = False
						sprite.frame = 1
						if sprite.brain == DINKBRAIN and not sprite.frozen:
							self.compute_dir ()
						else:
							sprite.set_state ('idle')
					elif sprite.state != 'idle' or sprite.base_idle != '' or sprite.mx != 0 or sprite.my != 0 or sprite.brain == REPEATBRAIN:
						# If idle without a seq, just freeze the walk seq by not returning to 1.
						sprite.set_state ('idle')	# reset idle sequence.
						sprite.frame = 1
				else:
					# Force current state to be the final frame of the animation.
					sprite.pseq = sprite.seq
					sprite.pframe = sprite.frame
					sprite.seq = None
			if sprite.seq and sprite.seq.frames[sprite.frame].special:
				# Hit things.
				targets = [x for x in self.hit_list (sprite, sprite.seq) if not x.nohit]
				for target in targets:
					# Hit this sprite.
					if target.hitpoints > 0:
						if sprite.brain in (DINKBRAIN, POINTERBRAIN):
							self.damage (self.data.the_globals['strength'], target, sprite)
						else:
							self.damage (sprite.strength, target, sprite)
					# Call script.
					target.the_statics['enemy_sprite'] = sprite.num
					target.the_statics['missile_source'] = 1
					self.data.run_script (target.script, 'hit', (), target)
	def make_layout (self, text, width):
		layout = self.data.create_pango_layout (text)
		attrs = pango.AttrList ()
		attrs.insert (pango.AttrWeight (pango.WEIGHT_BOLD, 0, len (text)))
		layout.set_attributes (attrs)
		layout.set_wrap (pango.WRAP_WORD)
		layout.set_width (width * pango.SCALE)
		return layout
	def damage (self, strength, target, source):
		self.hurt (strength / 2 + int (random.random () * strength / 2) + 1 - target.defense, target, source)
	def hurt (self, dam, target, source):
		if dam <= 0:
			dam = random.choice ((0, 1))
		if dam == 0:
			return
		seq, frame = (target.seq, target.frame) if target.seq is not None else (target.pseq, target.pframe)
		t = self.add_text (target.x - 320, target.y + seq.frames[frame].boundingbox[1], '%d' % dam, {}, {}, -1)
		t.my = -1
		t.set_killdelay (1000)
		t.mylimit = (0, True)	# this makes the move ignore hardness.
		t.have_brain = True
		self.events += ((self.data.current_time, self.do_brain (t), t.num),)
		if target.brain in (DINKBRAIN, POINTERBRAIN):
			self.data.the_globals['life'] -= dam
			death = self.data.the_globals['life'] <= 0
		else:
			target.hitpoints -= dam
			death = target.hitpoints <= 0
		if death:
			if source == self.sprites[1]:
				self.add_exp (target.experience, target)
			# Create death sprite.
			seq = None
			if self.data.data.seq.find_collection (target.base_death):
				seq = self.data.data.seq.get_dir_seq (target.base_death, target.dir)
			else:
				collection = self.data.data.seq.find_collection (target.base_walk)
				if collection and 'die' in collection:
					seq = collection['die']
			if seq:
				spr = self.add_sprite (target.x, target.y, 'mark', seq.code, 1)
				spr.nohit = True
			# Run die script.
			self.data.run_script (target.script, 'die', (), target)
			target.kill ()
	def add_exp (self, amount, source):
		if amount == 0:
			return
		self.data.the_globals['exp'] += amount
		seq, frame = (source.seq, source.frame) if source.seq is not None else (source.pseq, source.pframe)
		t = self.add_text (source.x - 320, source.y + seq.frames[frame].boundingbox[1] - 15, str (amount), {}, {})
		t.my = -1
		t.set_killdelay = (1000)
		t.mylimit = (0, True)
		t.have_brain = True
		self.events += ((self.data.current_time, self.do_brain (t), t.num),)
	def draw_textsprite (self, target, sprite, clip = True):
		if sprite.owner:
			offset = sprite.owner.x, sprite.owner.y
			x = offset[0] + sprite.offset[0] + sprite.x - sprite.size[0] / 2
			y = offset[1] + sprite.offset[1] + sprite.y - sprite.size[1]
		else:
			offset = 320, 0
			x = offset[0] + sprite.offset[0] + sprite.x - sprite.size[0] / 2
			y = offset[1] + sprite.offset[1] + sprite.y - sprite.size[1] / 2
		x = x * self.data.data.scale / 50
		y = y * self.data.data.scale / 50
		if x < 20 * self.data.data.scale / 50:
			x = 20 * self.data.data.scale / 50
		if x + sprite.size[0] >= 620 * self.data.data.scale / 50:
			x = 620 * self.data.data.scale / 50 - sprite.size[0]
		if y < 0:
			y = 0
		if clip:
			if y + sprite.size[1] >= 400 * self.data.data.scale / 50:
				y = 400 * self.data.data.scale / 50 - sprite.size[1]
		else:
			if y + sprite.size[1] >= 480 * self.data.data.scale / 50:
				y = 480 * self.data.data.scale / 50 - sprite.size[1]
		# Draw a black shadow first, then the text.
		target.draw_layout (self.data.clipgc if clip else self.data.gc, x - 1, y - 1, sprite.layout, self.data.data.colors[0], None)
		target.draw_layout (self.data.clipgc if clip else self.data.gc, x, y, sprite.layout, sprite.fg, None)
		return
	def draw_sprite (self, target, sprite, clip = True):
		if sprite.seq == None:
			assert sprite.pseq != None
			seq = (sprite.pseq, sprite.pframe)
		else:
			seq = (sprite.seq, sprite.frame)
		info = seq, sprite.size, sprite.cropbox, self.data.data.scale
		if sprite.cache[0] == info:
			target.draw_pixbuf (self.data.clipgc if sprite.clip else None, sprite.cache[1], 0, 0, self.data.offset + (sprite.x + sprite.cache[2]) * self.data.data.scale / 50, (sprite.y + sprite.cache[3]) * self.data.data.scale / 50)
		else:
			sprite.bbox, sprite.cache = self.draw_frame (target, seq, (sprite.x, sprite.y), sprite.size, sprite.cropbox, sprite.clip, info)
	def draw_frame (self, target, seqframe, pos, size, cropbox, clip, info = None):
		seq, frame = seqframe
		(x, y), bbox, box = self.data.data.get_box (size, pos, seq.frames[frame], cropbox)
		left, top, right, bottom = bbox
		w = (right - left) * self.data.data.scale / 50
		h = (bottom - top) * self.data.data.scale / 50
		if w > 0 and h > 0:
			pb = self.data.data.get_seq (seq, frame)
			if box != None:
				pb = pb.subpixbuf (box[0] * self.data.data.scale / 50, box[1] * self.data.data.scale / 50, (box[2] - box[0]) * self.data.data.scale / 50, (box[3] - box[1]) * self.data.data.scale / 50)
			if w != pb.get_width () or h != pb.get_height ():
				pb = pb.scale_simple (w, h, gtk.gdk.INTERP_BILINEAR)
			target.draw_pixbuf (self.data.clipgc if clip else None, pb, 0, 0, self.data.offset + left * self.data.data.scale / 50, top * self.data.data.scale / 50)
		else:
			pb = 0
		return bbox, (info, pb, left - pos[0], top - pos[1])
	def add_sprite_hard (self, spr):
		if not spr.hard or spr.brain == TEXTBRAIN:
			return
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
			self.hardmap[box[1]:box[3] + 1, box[0]:box[2] + 1] = (spr.editor_num if spr.editor_num is not None else -spr.num)
	def make_hardmap (self):
		# Add screen hardness.
		self.hardmap = numpy.zeros ((400, 600), dtype = numpy.int64)
		if self.data.the_globals['player_map'] in self.data.data.world.map:
			screen = self.data.data.world.map[self.data.the_globals['player_map']]
			hardmap = self.data.data.get_hard_tiles_PIL (screen.hard)
			if hardmap is None:
				for y in range (8):
					for x in range (12):
						tmap, tx, ty = screen.tiles[y][x]
						h = numpy.array (self.data.data.get_hard_tiles_PIL (tmap))
						tile = numpy.zeros ((50, 50), dtype = numpy.int64)
						tile[h[ty * 50:(ty + 1) * 50, 50 * x + tx * 50:(tx + 1) * 50, 2] == 255] = 1	# Set all "blue" hardness (sets white as well, but that will be overwritten)
						tile[h[ty * 50:(ty + 1) * 50, 50 * x + tx * 50:(tx + 1) * 50, 1] == 255] = 2	# Set all "white" hardness
						self.hardmap[y * 50:(y + 1) * 50, x * 50:(x + 1) * 50] = tile
			else:
				hardmap = numpy.array (hardmap)
				self.hardmap[hardmap[:, :, 2] == 255] = 1
				self.hardmap[hardmap[:, :, 1] == 255] = 2
			# Add background sprite hardness.
			for s in screen.sprite:
				if s.is_bg () and (s.hard or s.warp):
					self.add_sprite_hard (Sprite (self.data, src = s, view = None))
		# Add sprite hardness.
		for s in self.sprites:
			self.add_sprite_hard (self.sprites[s])
	def launch (self):
		# Launch missile with bow.
		self.bow[0] = False
		self.compute_dir ()
		self.handle_event (self.data.current_time, self.bow[2][0], self.bow[2][1])
	def attack (self):
		a = False
		clicking = []
		for i in self.sprites:
			if self.sprites[i].brain != BUTTONBRAIN or self.sprites[i].script not in self.data.scripts:
				continue
			if self.in_area ((self.sprites[1].x, self.sprites[1].y), self.sprites[i].bbox):
				if 'click' in self.data.scripts[self.sprites[i].script]:
					clicking.append (self.sprites[i])
				a = True
		for s in clicking:
			self.data.run_script (s.script, 'click', (), s)
		# Handle dink attacking.
		if self.data.current_weapon > 0 and self.data.items[self.data.current_weapon] != None:
			self.data.run_script (self.data.items[self.data.current_weapon][0], 'use', (), None)
		else:
			if not a:
				self.data.run_script ('dnohit', 'main', (), None)
	def in_area (self, pos, area):
		return area[0] <= pos[0] <= area[2] and area[1] <= pos[1] <= area[3]
	def choice_button (self, button):
		# Respond to buttons.
		if button == BUTTON_UP:
			self.choice_current = self.choice_current - 1 if self.choice_current > 0 else len (self.choice) - 1
		elif button == BUTTON_DOWN:
			self.choice_current = self.choice_current + 1 if self.choice_current < len (self.choice) - 1 else 0
		elif button == BUTTON_INVENTORY:
			# I'm using enter instead of control for accepting a choice, so it's less likely that you accept something by accident if a choice menu pops up during a fight.
			self.choice = None
			self.choice_title = None
			if self.stopped:
				# Adjust times.
				diff = self.data.current_time - self.stopped[0]
				self.events += [(x[0] + diff, x[1], x[2]) for x in self.stopped[1]]
				for k in self.stopped[2]:
					k.kill_time += diff
				self.kill_queue += self.stopped[2]
				for s in self.sprites:
					self.sprites[s].last_time += diff
			self.stopped = None
			# Run the choice waiter now, so there is no race on choice_response.
			self.choice_response = self.choice_current + 1
			target = self.choice_waiter
			self.choice_waiter = None
			self.handle_event (self.data.current_time, target[0], target[1])
			# Don't register wait_for_button now.
			return
		# Register wait_for_button again.
		self.wait_for_button = self.choice_button
	def draw_status (self):
		# Draw status bar and borders.
		# These coordinates are directly related to the depth dots of the status sprites.
		self.draw_frame (self.bg, (self.data.data.seq.find_seq ('status'), 3), (426, 458), 100, (0, 0, 0, 0), False)
		if self.screenlock:
			self.draw_frame (self.bg, (self.data.data.seq.find_seq ('menu'), 9), (13, 287), 100, (0, 0, 0, 0), False)
			self.draw_frame (self.bg, (self.data.data.seq.find_seq ('menu'), 10), (633, 287), 100, (0, 0, 0, 0), False)
		else:
			self.draw_frame (self.bg, (self.data.data.seq.find_seq ('status'), 1), (13, 287), 100, (0, 0, 0, 0), False)
			self.draw_frame (self.bg, (self.data.data.seq.find_seq ('status'), 2), (633, 287), 100, (0, 0, 0, 0), False)
		if 0 < self.data.current_weapon < len (self.data.items) and self.data.items[self.data.current_weapon] is not None and self.data.items[self.data.current_weapon][1] is not None:
			weapon = self.data.items[self.data.current_weapon]
			self.draw_frame (self.bg, (self.data.data.seq.find_seq (weapon[1]), weapon[2]), (599, 454), 100, (0, 0, 0, 0), False)
		if 0 < self.data.current_magic < len (self.data.magic) and self.data.magic[self.data.current_magic][1] is not None:
			magic = self.data.magic[self.data.current_magic]
			self.draw_frame (self.bg, (self.data.data.seq.find_seq (magic[1]), magic[2]), (194, 454), 100, (0, 0, 0, 0), False)
		for stat in ('strength', 'defense', 'magic', 'exp', 'lifemax', 'life', 'gold', 'level'):
			self.stat_info[stat][0] = self.data.the_globals[stat]
			if stat != 'lifemax':
				self.draw_stat (stat)
	def draw_stat (self, stat):
		if stat in ('life', 'lifemax'):
			# I don't like it at all, but I need to make the background white for these sprites. :-(
			self.data.gc.set_foreground (self.data.data.colors[-1])
			info = self.stat_info['lifemax']
			bb = info[1].pseq.frames[info[1].pframe].boundingbox
			self.bg.draw_rectangle (self.data.gc, True, info[2] + bb[0], info[3] + bb[1], self.stat_info['lifemax'][0] * 3, bb[3] - bb[1])
			# draw life bar.
			lifemax = self.stat_info['lifemax'][0]
			self.draw_lifebar (self.stat_info['lifemax'][1], lifemax * 3, lifemax * 3, info[2])
			self.draw_lifebar (self.stat_info['life'][1], self.stat_info['life'][0] * 3, lifemax * 3, self.stat_info['life'][2])
		else:
			info = self.stat_info[stat]
			if stat == 'exp':
				# I don't like it at all, but I need to make the background white for these sprites. :-(
				self.data.gc.set_foreground (self.data.data.colors[-1])
				#('exp',      450, 467, 10, 5, 'nums'),
				bb = info[1].pseq.boundingbox
				self.bg.draw_rectangle (self.data.gc, True, info[2] - (info[4] - 1) * info[3] + bb[0], 467 + bb[1], 11 * info[3], bb[3] - bb[1])
				self.draw_stat_digit ('exp', -1, 11)
				s = '%05d' % self.data.get_nextlevel ()
				for p, d in enumerate (s):
					self.draw_stat_digit (stat, -p - 2, ord (d) - ord ('0'))
				# Fall through to draw experience itself.
			# Draw number.
			s = '%0*d' % (info[4], info[0])
			for p, d in enumerate (s):
				self.draw_stat_digit (stat, len (s) - p - 1, ord (d) - ord ('0'))
	def draw_stat_digit (self, stat, pos, digit):
		if digit == 0:
			digit = 10
		self.stat_info[stat][1].x = self.stat_info[stat][2] - pos * self.stat_info[stat][3]
		self.stat_info[stat][1].pframe = digit
		self.draw_sprite (self.bg, self.stat_info[stat][1])
	def draw_lifebar (self, sprite, pixels, maxpixels, left):
		if pixels == 0:
			return
		sprite.x = left
		sprite.pframe = 1
		bbl = sprite.pseq.frames[1].boundingbox
		bbm = sprite.pseq.frames[2].boundingbox
		bbr = sprite.pseq.frames[3].boundingbox
		#print 'draw lifebar size %d, maxsize %d, sizes %d %d %d' % (pixels, maxpixels, bbl[2] - bbl[0], bbm[2] - bbm[0], bbr[2] - bbr[0])
		if bbl[2] - bbl[0] + bbr[2] - bbr[0] > maxpixels:
			offset = pixels / 2
			roffset = (pixels + 1) / 2
		else:
			offset = bbl[2] - bbl[0]
			roffset = bbr[2] - bbr[0]
		#print 'left size:', offset, 0
		sprite.cropbox = (0, 0, min (pixels, offset), bbl[3] - bbl[1])
		self.draw_sprite (self.bg, sprite)
		sprite.pframe = 2
		sprite.cropbox = (0, 0, bbm[2] - bbm[0], bbm[3] - bbm[1])
		while offset + bbm[2] - bbm[0] <= maxpixels - (bbr[2] - bbr[0]) and offset + bbm[2] - bbm[0] <= pixels:
			sprite.x = left + offset
			offset += bbm[2] - bbm[0]
			self.draw_sprite (self.bg, sprite)
			#print 'mid 1 size:', bbm[2] - bbm[0], offset - (bbm[2] - bbm[0])
		if offset + roffset < maxpixels and offset < pixels:
			sprite.x = left + offset
			size = min (pixels - offset, maxpixels - offset - roffset)
			sprite.cropbox = (0, 0, size, bbm[3] - bbm[1])
			offset += size
			self.draw_sprite (self.bg, sprite)
			#print 'mid 2 size:', size, offset - size
		sprite.pframe = 3
		start = bbr[2] - bbr[0] - roffset
		sprite.cropbox = (start, 0, pixels - offset + start, bbr[3] - bbr[1])
		sprite.x = left + offset - start
		self.draw_sprite (self.bg, sprite)
		#print 'right size:', pixels - offset, offset
	def update_stats (self):
		for stat in ('strength', 'defense', 'magic', 'exp', 'lifemax', 'life', 'gold', 'level'):
			value = self.stat_info[stat][0]
			target = self.data.the_globals[stat]
			if value == target:
				continue
			if self.data.the_globals['life'] > self.data.the_globals['lifemax']:
				self.data.the_globals['life'] = self.data.the_globals['lifemax']
				target = self.data.the_globals[stat]
				print ('Warning: Adjusting life, because it was larger than lifemax.')
			if self.data.the_globals['life'] < 0:
				self.data.the_globals['life'] = 0
				target = self.data.the_globals[stat]
				print ('Warning: Adjusting life, because it was smaller than 0.')
			if value < target:
				self.stat_info[stat][0] = min (target, value + self.stat_info[stat][5])
			else:
				self.stat_info[stat][0] = max (target, value - self.stat_info[stat][5])
			self.draw_stat (stat)
	def add_text (self, x, y, text, the_statics, the_locals, fg = -2, owner = None):
		t = Sprite (self.data, x = x, y = y, brain = 'text', view = self)
		t.que = -1000
		t.text = text
		if len (t.text) >= 2 and t.text[0] == '`' and t.text[1] in gtkdink.dink.colornames:
			t.fg = self.data.data.colors[gtkdink.dink.colornames.index (t.text[1])]
			t.text = t.text[2:]
		else:
			t.fg = self.data.data.colors[fg]
		t.layout = self.make_layout (t.text, 500 if owner is None else 200)
		t.size = t.layout.get_pixel_size ()
		t.owner = owner
		if owner is not None:
			assert owner.brain != TEXTBRAIN
			if owner.text is not None:
				owner.text.kill ()
			owner.text = t
			seq, frame = (owner.seq, owner.frame) if owner.seq is not None else (owner.pseq, owner.pframe)
			t.offset = 0, seq.frames[frame].boundingbox[1]
		else:
			t.offset = 0, 0
		t.set_killdelay (max (2700, 77 * len (t.text)))
		return t
	def move (self, event):
		if self.sprites[1].brain != POINTERBRAIN or self.sprites[1].frozen:
			return
		ex, ey, emask = self.data.window.get_pointer ()
		oldx, oldy = self.sprites[1].x, self.sprites[1].y
		self.sprites[1].x, self.sprites[1].y = int (ex) * 50 / self.data.data.scale, int (ey) * 50 / self.data.data.scale
		for i in self.sprites:
			if self.sprites[i].brain != BUTTONBRAIN or self.sprites[i].script not in self.data.functions:
				continue
			o = self.in_area ((oldx, oldy), self.sprites[i].bbox)
			n = self.in_area ((self.sprites[1].x, self.sprites[1].y), self.sprites[i].bbox)
			if o == n:
				continue
			if n == True:
				self.data.run_script (self.sprites[i].script, 'buttonon', (), self.sprites[i])
			else:
				self.data.run_script (self.sprites[i].script, 'buttonoff', (), self.sprites[i])
	def keypress (self, event):
		button = self.make_button (event.keyval)
		frozen = self.sprites[1].nocontrol or self.stopped or self.sprites[1].brain not in (DINKBRAIN, POINTERBRAIN) or self.sprites[1].frozen
		if button and self.wait_for_button:
			cb = self.wait_for_button
			self.wait_for_button = None
			cb (button)
			frozen = True
		if not self.wait_for_button and (self.sprites[1].brain not in (DINKBRAIN, POINTERBRAIN) or self.sprites[1].frozen) and not button:
			# Unfreeze in case of waiting for text and a non-button is pressed.
			for i in self.blocker:
				i.kill ()
			frozen = True
		if button == BUTTON_ACTION:
			self.push_delay = 0
			self.data.control_down += 1
			if not frozen:
				self.attack ()
		if event.keyval in self.cursorkeys:
			i = self.cursorkeys.index (event.keyval)
			if not self.data.cursor[i]:
				self.push_delay = 0
				self.data.cursor[i] = True
				if not frozen:
					self.compute_dir ()
		if not frozen and button == BUTTON_TALK:
			self.push_delay = 0
			self.data.space = True
		if button == BUTTON_MAGIC:
			self.push_delay = 0
			self.shift = True
		if not frozen and button == BUTTON_ESCAPE:
			self.push_delay = 0
			self.data.run_script ('escape', 'main', (), None)
		if not frozen and button == BUTTON_INVENTORY:
			self.push_delay = 0
			self.data.run_script ('inventory', 'main', (), None)
		if not frozen and button == BUTTON_MAP:
			self.push_delay = 0
			self.data.run_script ('map', 'main', (), None)
		# TODO: Respond to non-buttons.
	def keyrelease (self, event):
		self.push_delay = 0
		frozen = self.sprites[1].nocontrol or self.stopped or self.sprites[1].brain not in (DINKBRAIN, POINTERBRAIN) or self.sprites[1].frozen
		if event.keyval in (gtk.keysyms.Control_R, gtk.keysyms.Control_L):
			self.data.control_down -= 1
			if self.data.control_down <= 0:
				self.data.control_down = 0
				if not frozen and self.bow[0]:
					self.launch ()
		if event.keyval in self.cursorkeys:
			i = self.cursorkeys.index (event.keyval)
			self.data.cursor[i] = False
			if not frozen:
				self.compute_dir ()
		if event.keyval == gtk.keysyms.ISO_Prev_Group:
			self.shift = False
	def compute_dir (self):
		mx = 1 + self.data.cursor[2] - self.data.cursor[0]
		my = 1 + self.data.cursor[1] - self.data.cursor[3]
		d = 1 + 3 * my + mx
		if d != 5:
			self.sprites[1].dir = d
			if not self.bow[0]:
				self.sprites[1].set_state ('walk')
		else:
			if not self.bow[0]:
				self.sprites[1].set_state ('idle')
		if self.bow[0]:
			self.sprites[1].mx = 0
			self.sprites[1].my = 0
		else:
			self.sprites[1].mx = mx - 1
			self.sprites[1].my = 1 - my
	def button_on (self, event):
		self.data.control_down += 1
		if not self.sprites[1].frozen:
			self.attack ()
	def button_off (self, event):
		self.data.control_down -= 1
		if self.data.control_down <= 0:
			self.data.control_down = 0
			if self.bow[0]:
				self.launch ()
	def make_button (self, keyval):
		if keyval in (gtk.keysyms.Control_R, gtk.keysyms.Control_L):
			return BUTTON_ACTION
		if keyval in (gtk.keysyms.Shift_R, gtk.keysyms.Shift_L):
			return BUTTON_MAGIC
		if keyval == gtk.keysyms.space:
			return BUTTON_TALK
		if keyval == gtk.keysyms.Escape:
			return BUTTON_ESCAPE
		if keyval == gtk.keysyms.Return:
			return BUTTON_INVENTORY
		if keyval == gtk.keysyms.m:
			return BUTTON_MAP
		if keyval in self.cursorkeys:
			return (14, 18, 16, 12)[self.cursorkeys.index (keyval)]
		return None
	def prepare_choice (self, stop, title):
		for n, c in enumerate (self.choice):
			layout = self.make_layout (c[1], 250)
			size = layout.get_pixel_size ()
			self.choice[n] = (c[0], c[1], 320 - size[0] / 2, size[1], layout)
		if stop:
			self.stopped = self.data.current_time, [x for x in self.events if x[2] != -2], self.kill_queue
			self.kill_queue = []
			self.events = [x for x in self.events if x[2] == -2]
		layout = self.make_layout (title, 250)
		size = layout.get_pixel_size ()
		self.choice_title = (title, 320 - size[0] / 2, 100, layout, size[1])
		# Register choice_button as wait_for_button callback.
		self.wait_for_button = self.choice_button
	def warp_time (self):
		diff = self.data.current_time - self.last_time
		self.events = [(e[0] + diff, e[1], e[2]) for e in self.events]
		for k in self.kill_queue:
			k.kill_time += diff
		for s in self.sprites:
			self.sprites[s].last_time += diff
	def button_waiter (self, button):
		self.button_response = button
		self.handle_event (self.data.current_time, self.button_waiter_data[0], self.button_waiter_data[1])

class Play (gtk.DrawingArea):
	"Widget for playing dink."
	def load_game (self):
		self.sounds = {}
		for s in self.data.sound.sound:
			self.sounds[s] = pygame.mixer.Sound (gtkdink.dink.filepart (*self.data.sound.sound[s][1]))
		self.data.set_window (self.window)
		self.offset = 20 * self.data.scale / 50
		self.current_time = datetime.datetime.utcnow ()
		self.checkpoint = self.current_time
		self.the_globals = {}
		# Start codes at 3, so 1 and 2 can be reserved for map hardness.
		nextcode = 10
		for s in self.data.world.sprite:
			s.editcode = nextcode
			nextcode += 1
		self.editor_sprites = {}
		for s in self.data.world.sprite:
			self.editor_sprites[s.editcode] = {'layer': s.layer, 'dead': None, 'hard': s.hard, 'seq': s.seq, 'frame': s.frame}
		self.scripts = self.data.script.compile (set (('PYDINK',)))
		for v in gtkdink.dink.the_globals:
			self.the_globals[v] = gtkdink.dink.the_globals[v]
		self.functions = gtkdink.dink.functions
		self.next_sprite = 2
		self.the_globals['player_map'] = None
		self.items = [None] * 17
		self.magic = [None] * 9
		self.current_weapon = 0
		self.current_magic = 0
		self.winw = 12 * self.data.scale + 2 * self.offset
		self.winh = 8 * self.data.scale + 80 * self.data.scale / 50
		self.set_size_request (self.winw, self.winh)
		self.clipgc.set_clip_rectangle (gtk.gdk.Rectangle (self.offset, 0, self.data.scale * 12, self.data.scale * 8))
		self.buffer = gtk.gdk.Pixmap (self.window, self.winw, self.winh)
		self.fade_pixbuf = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, True, 8, self.winw, self.winh)
		self.views = [View (self)]
		self.current_view = 0
		self.views[0].make_hardmap ()
		self.views[0].sprites[1].clip = False
		self.views[0].sprites[1].que = -100000
		self.views[0].sprites[1].script = 'dinfo'
		self.views[0].sprites[1].range = 40
		# Run start.c (before first update).
		self.run_script ('start', 'main', (), None)
		self.expose (self, (0, 0, self.winw, self.winh));
		self.schedule_next ()
	def __init__ (self, data):
		self.data = data
		gtk.DrawingArea.__init__ (self)
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.control_down = 0
		self.cursor = [False, False, False, False]
		self.space = False
		self.shift = False
		self.dying = False
		self.music = None
		self.offset = 20 * self.data.scale / 50
		self.winw = 12 * self.data.scale + 2 * self.offset
		self.winh = 8 * self.data.scale + 80 * self.data.scale / 50
		self.set_size_request (self.winw, self.winh)
	def start (self, widget):
		# Hide cursor in window.
		pixmap = gtk.gdk.Pixmap (None, 1, 1, 1)
		color = gtk.gdk.Color ()
		cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
		self.window.set_cursor (cursor)
		# Set up GCs and pixmaps.
		self.gc = gtk.gdk.GC (self.window)
		self.clipgc = gtk.gdk.GC (self.window)
		# Set up events.
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('key-release-event', self.keyrelease)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('enter-notify-event', self.enter)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.KEY_RELEASE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.ENTER_NOTIFY_MASK)
		self.load_game ()
	def get_nextlevel (self):
		levels = (100, 400, 800, 1600, 2500, 3600)
		l = self.the_globals['level']
		if not 0 < l <= len (levels):
			return 0
		return levels[l - 1]
	def schedule_next (self):
		self.get_view ().schedule_next ()
	def play_music (self, music):
		if self.music == music:
			return
		self.music = music
		pygame.mixer.music.load (gtkdink.dink.filepart (*self.data.sound.music[music][1]))
		pygame.mixer.music.play (-1)
	def play_sound (self, sound, repeat, sprite):
		channel = self.sounds[sound].play ()
		# TODO: repeat; follow sprite.
	def expose (self, widget, event):
		if isinstance (event, tuple):
			a = event
		else:
			a = event.area
		if self.window:
			self.window.draw_drawable (self.gc, self.buffer, a[0], a[1], a[0], a[1], a[2], a[3])
	def keypress (self, widget, event):
		self.get_view ().keypress (event)
	def keyrelease (self, widget, event):
		self.get_view ().keyrelease (event)
	def button_on (self, widget, event):
		self.get_view ().button_on (event)
	def button_off (self, widget, event):
		self.get_view ().button_off (event)
	def move (self, widget, event):
		self.get_view ().move (event)
	def enter (self, widget, event):
		self.grab_focus ()
	def run_script (self, fname, name, args, sprite):
		if not fname:
			return
		if fname not in self.scripts:
			print ("Warning: script %s doesn't exist" % fname)
			return
		if name not in self.scripts[fname]:
			return
		script = self.Script (fname, name, args, sprite)
		if sprite and sprite.view:
			view = sprite.view
		else:
			view = self.get_view ()
		view.handle_event (self.current_time, script, 0 if sprite is None else sprite.num)
	def Script (self, fname, name, args, sprite):
		#print 'running %s:%s' % (fname, name)
		if fname not in self.functions:
			yield 'error', "script file doesn't exist: %s" % fname
			return
		if name not in self.functions[fname]:
			yield 'error', "script doesn't exist: %s.%s" % (fname, name)
			return
		#print 'running %s.%s' % (fname, name)
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
				stack[-1][pos[-1] - 1] = (statement[0], statement[3], statement[2], statement[3], statement[4])
				c = self.compute (statement[2], the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
					yield r
					r = next (c)
				if r[1]:
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
			elif statement[0] in ('choice', 'choice_stop'):
				c = self.compute (statement, the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
					yield r
					r = next (c)
				# Ignore return value.
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
			elif statement[0] == 'break':
				stack.pop ()
				pos.pop ()
				while pos[-1] >= len (stack[-1]) or stack[-1][pos[-1]][0] not in ('while', 'for'):
					stack.pop ()
					pos.pop ()
				pos[-1] += 1
			elif statement[0] == 'continue':
				stack.pop ()
				pos.pop ()
				while pos[-1] >= len (stack[-1]) or stack[-1][pos[-1]][0] not in ('while', 'for'):
					stack.pop ()
					pos.pop ()
			else:
				c = self.compute (statement[2], the_statics, the_locals)
				r = next (c)
				while r[0] != 'return':
					yield r
					r = next (c)
				self.assign (statement[0], statement[1], r, the_statics, the_locals)
	def assign (self, op, name, value, the_statics, the_locals):
		assert value[0] == 'return'
		if name[0] == 'local':
			store = the_locals
		elif name[0] == 'static':
			store = the_statics
		elif name[0] == 'global':
			store = self.the_globals
		else:
			raise AssertionError ('undefined variable type %s' % name[0])
		if op == '=':
			store[name[1]] = value[1]
		else:
			store[name[1]] = eval ('%d %s %d' % (store[name[1]], op[0], value[1]))
	def compute (self, expr, the_statics, the_locals):
		if expr[0] == 'const':
			yield ('return', expr[1])
			return
		elif expr[0] == '"':
			yield ('return', self.build_string (expr[1], the_statics, the_locals))
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
			if bool (r[1]) ^ (expr[0] == '&&'):
				yield ('return', bool (r[1]))
				return
			c = self.compute (expr[1][1], the_statics, the_locals)
			r = next (c)
			while r[0] != 'return':
				yield r
				r = next (c)
			if bool (r[1]) ^ (expr[0] == '&&'):
				yield ('return', bool (r[1]))
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
		elif expr[0] in ('choice', 'choice_stop'):
			self.get_view ().choice = []
			for num, i in enumerate (expr[1]):
				t = self.build_string (i[1][1], the_statics, the_locals)
				if i[0] == None:
					self.get_view ().choice += ((num, t),)
				else:
					c = self.compute (i[0], the_statics, the_locals)
					r = next (c)
					while r[0] != 'return':
						yield r
						r = next (c)
					if r[1]:
						self.get_view ().choice += ((num, t),)
			if len (self.get_view ().choice) == 0:
				self.get_view ().choice = None
				yield ('return', 0)
			else:
				self.get_view ().prepare_choice (expr[0] == 'choice_stop', title = '' if expr[2] is None else self.build_string (expr[2][0][1], the_statics, the_locals))
				yield ('choice', 0)
				ret = self.get_view ().choice_response
				yield ('return', ret)
			return
		elif len (expr[1]) == 1:
			c = self.compute (expr[1][0], the_statics, the_locals)
			r = next (c)
			while r[0] != 'return':
				yield r
				r = next (c)
			if r[0] == 'return':
				if expr[0] == '!':
					yield ('return', not r[1])
				else:
					yield ('return', eval ('%s%d' % (expr[0], r[1])))
			else:
				yield ('error', 'invalid return value while computing expression')
			return
		else:
			c = self.compute (expr[1][0], the_statics, the_locals)
			r1 = next (c)
			while r1[0] != 'return':
				yield r1
				r1 = next (c)
			if r1[0] != 'return':
				yield ('error', 'invalid return value while computing expression')
			c = self.compute (expr[1][1], the_statics, the_locals)
			r2 = next (c)
			while r2[0] != 'return':
				yield r2
				r2 = next (c)
			if r2[0] != 'return':
				yield ('error', 'invalid return value while computing expression')
			yield ('return', int (eval ('%d %s %d' % (r1[1], expr[0], r2[1]))))
			return
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
	def get_view (self):
		return self.views[self.current_view]
	def Internal (self, name, args, the_statics, the_locals):
		view = self.get_view ()
		if name.startswith ('sp_'):
			if args[0] not in view.sprites:
				yield ('return', 0)
				return
		if name == 'activate_bow':
			if self.control_down <= 0 or view.bow[0]:
				yield ('return', 0)
				return
			yield ('stop', lambda x: setattr (view.bow, [True, self.current_time, x, args[0]]))
			ms = ((self.current_time - view.bow[1]) / 1000).microseconds
			yield ('return', 500 if ms >= 1000 else ms / 2)
			return
		elif name == 'add_exp':
			view.add_exp (args[0], args[1])
		elif name == 'add_item':
			try:
				idx = self.items[1:].index (None) + 1
			except ValueError:
				yield ('error', 'no more item slots available')
				return
			self.items[idx] = args[0], args[1], args[2]
			yield ('return', idx)
			return
		elif name == 'add_magic':
			try:
				idx = self.magic[1:].index (None) + 1
			except ValueError:
				yield ('error', 'no more magic slots available')
				return
			self.magic[idx] = args[0], args[1], args[2]
			yield ('return', idx)
			return
		elif name == 'arm_magic':
			if 1 <= self.the_globals['cur_magic'] < len (self.magic) and self.magic[self.the_globals['cur_magic']] is not None:
				self.current_magic = self.the_globals['cur_magic']
			else:
				self.current_magic = 0
		elif name == 'arm_weapon':
			if 1 <= self.the_globals['cur_weapon'] < len (self.items) and self.items[self.the_globals['cur_weapon']] is not None:
				self.current_weapon = self.the_globals['cur_weapon']
			else:
				self.current_weapon = 0
		elif name == 'busy':
			if args[0] not in view.sprites:
				yield ('return', 0)
			else:
				sprite = view.sprites[args[0]]
				yield ('return', sprite.speech if sprite.speech != None else 0)
			return
		elif name == 'compare_item_script':
			yield ('return', int (0 < args[0] < len (self.items) and self.items[args[0]] is not None and self.items[args[0]] == args[1]))
			return
		elif name == 'compare_sprite_script':
			if args[0] not in view.sprites:
				yield ('return', 0)
			else:
				sprite = view.sprites[args[0]]
				yield ('return', int (sprite.script == args[0]))
			return
		elif name == 'compare_magic':
			yield ('return', int (0 < self.current_magic < len (self.magic) and self.magic[self.current_magic] is not None and self.magic[self.current_magic][0] == args[0]))
			return
		elif name == 'compare_magic_script':
			yield ('return', int (0 < args[0] < len (self.magic) and self.magic[args[0]] is not None and self.magic[args[0]][0] == args[1]))
			return
		elif name == 'compare_weapon':
			yield ('return', int (0 < self.current_weapon < len (self.items) and self.items[self.current_weapon] is not None and self.items[self.current_weapon][0] == args[0]))
			return
		elif name == 'copy_bmp_to_screen':
			view.bg.draw_drawable (self.gc, self.data.get_image (args[0], self.data.scale), 0, 0, 0, 0, self.winw, self.winh)
		elif name == 'count_item':
			yield ('return', sum ([i[0] == args[0] for i in self.items[1:] if i != None]))
			return
		elif name == 'count_magic':
			yield ('return', sum ([i[0] == args[0] for i in self.magic[1:] if i != None]))
			return
		elif name == 'create_sprite':
			s = view.add_sprite (args[0], args[1], args[2], args[3], args[4])
			yield ('return', s.num)
			return
		elif name == 'create_view':
			if None in self.views:
				v = self.views.index (None)
				self.views[v] = View (self)
			else:
				v = len (self.views)
				self.views.append (View (self))
			yield ('return', v)
			return
		elif name == 'debug':
			sys.stderr.write ('Debug: %s\n' % str (args[0]))
		elif name == 'dink_can_walk_off_screen':
			view.dink_can_walk_off_screen = args[0] != 0
		elif name == 'disable_all_sprites':
			view.enable_sprites = False
		elif name == 'enable_all_sprites':
			view.enable_sprites = True
		elif name == 'draw_background':
			view.make_bg ()
		elif name == 'draw_hard_map':
			view.make_hardmap ()
		elif name == 'draw_hard_sprite':
			if args[0] in view.sprites:
				view.add_sprite_hard (view.sprites[args[0]])
		elif name == 'draw_status':
			view.draw_status ()
		elif name == 'editor_seq':
			if args[0] not in self.editor_sprites:
				yield ('return', 0)
			else:
				spr = self.editor_sprites[args[0]]
				if len (args) <= 1:
					yield ('return', self.data.find_seq (spr['seq']).code)
				else:
					spr['seq'] = args[0]
					yield ('return', 0)
			return
		elif name == 'editor_frame':	#
			if args[0] not in self.editor_sprites:
				yield ('return', 0)
			else:
				spr = self.editor_sprites[args[0]]
				if len (args) <= 1:
					yield ('return', spr['frame'])
				else:
					spr['frame'] = args[0]
					yield ('return', 0)
			return
		elif name == 'editor_set_sprite':	#
			if args[0] in self.editor_sprites:
				spr = self.editor_sprites[args[0]]
				spr['layer'] = args[1]
				spr['hard'] = args[2]
			yield ('return', 0)
			return
		elif name == 'editor_kill_sprite':	#
			if args[0] in self.editor_sprites:
				spr = self.editor_sprites[args[0]]
				spr['dead'] = now + 60000 * args[1]
				# TODO: record time that a sprite should be disabled. This should not be wall clock time like in the original Dink.
		elif name in ('fade_down', 'fade_down_stop'):
			if view.fade[1]:
				if view.fade[0] != 0:
					view.fade = (501 - view.fade[0], False, view.fade[2])
				else:
					view.fade = 500, False, self.current_time
			if name == 'fade_down_stop':
				yield ('stop', lambda x: view.fade_block.append (x))
		elif name in ('fade_up', 'fade_up_stop'):
			if not view.fade[1]:
				if view.fade[0] != 0:
					view.fade = (501 - view.fade[0], True, view.fade[2])
				else:
					view.fade = 500, True, self.current_time
			if name == 'fade_up_stop':
				yield ('stop', lambda x: view.fade_block.append (x))
		elif name == 'fill_screen':
			view.bg.draw_rectangle (self.gc, True, 0, 0, 640 * self.data.scale / 50, 480 * self.data.scale / 50)
		elif name == 'free_items':
			yield ('return', sum ([i == None for i in self.items[1:]]))
			return
		elif name == 'free_magic':
			yield ('return', sum ([i == None for i in self.magic[1:]]))
			return
		elif name == 'freeze':
			if args[0] in view.sprites:
				view.sprites[args[0]].frozen = True
				if view.sprites[args[0]].mxlimit is None and view.sprites[args[0]].mylimit is None:
					view.sprites[args[0]].mx = 0
					view.sprites[args[0]].my = 0
					view.sprites[args[0]].set_state ('idle')
			yield ('return', 0)
			return
		elif name == 'game_exist':
			# TODO
			pass
		elif name == 'get_item_frame':
			yield ('return', 0 if not 0 <= args[0] < len (self.items) or self.items[args[0]] is None else self.items[args[0]][2])
			return
		elif name == 'get_item_seq':
			yield ('return', 0 if not 0 <= args[0] < len (self.items) or self.items[args[0]] is None else self.data.seq.find_seq (self.items[args[0]][1]).code)
			return
		elif name == 'get_magic_frame':
			yield ('return', 0 if not 0 <= args[0] < len (self.magic) or self.magic[args[0]] is None else self.magic[args[0]][2])
			return
		elif name == 'get_magic_seq':
			yield ('return', 0 if not 0 <= args[0] < len (self.magic) or self.magic[args[0]] is None else self.data.seq.find_seq (self.magic[args[0]][1]).code)
			return
		elif name == 'get_next_sprite_with_this_brain':
			# TODO
			pass
		elif name == 'get_rand_sprite_with_this_brain':
			# TODO
			pass
		elif name == 'get_sprite_with_this_brain':
			# TODO
			pass
		elif name == 'get_version':
			yield ('return', 10000)
			return
		elif name == 'hurt':
			if args[0] in view.sprites:
				view.hurt (args[1], view.sprites[args[0]], None)
		elif name == 'initfont':
			# TODO
			pass
		elif name == 'inside_box':
			# TODO
			pass
		elif name == 'is_script_attached':
			# TODO
			pass
		elif name == 'kill_all_sounds':
			# TODO
			pass
		elif name == 'kill_cur_item':
			# TODO
			pass
		elif name == 'kill_cur_magic':
			# TODO
			pass
		elif name == 'kill_game':
			self.dying = True
			gtk.main_quit ()
			yield ('kill', 0)
		elif name == 'kill_shadow':
			# TODO
			pass
		elif name == 'kill_this_item':
			find = [idx for idx, x in enumerate (self.items) if x is not None and x[0] == args[0]]
			if len (find) == 0:
				sys.stderr.write ("trying to kill item %s, which isn't in inventory" % args[0])
			else:
				self.items[find[0]] = None
		elif name == 'kill_this_magic':
			find = [idx for idx, x in enumerate (self.magic) if x is not None and x[0] == args[0]]
			if len (find) == 0:
				sys.stderr.write ("trying to kill item %s, which isn't in inventory" % args[0])
			else:
				self.magic[find[0]] = None
		elif name == 'kill_this_task':
			yield ('kill', 0)
		elif name == 'kill_view':
			if 1 <= args[0] < len (self.views) and self.views[args[0]] is not None:
				if args[0] == self.current_view:
					self.current_view = 0
				self.views[args[0]] = None
				while self.views[-1] is None:
					self.views.pop ()
			else:
				print ("Warning: not killing view %d: it doesn't exist" % args[0])
		elif name == 'load_game':
			# TODO
			pass
		elif name == 'load_screen':
			view.load_screen ()
		elif name in ('move', 'move_stop'):
			if args[0] not in view.sprites:
				yield ('return', 0)
				return
			d = ((-1, 1), (0, 1), (1, 1), (-1, 0), None, (1, 0), (-1, -1), (0, -1), (1, -1))
			view.sprites[args[0]].mx, view.sprites[args[0]].my = d[args[1] - 1]
			if view.sprites[args[0]].mx != 0:
				view.sprites[args[0]].mxlimit = (args[2], view.sprites[args[0]].mx < 0)
				view.sprites[args[0]].mylimit = None
			else:
				view.sprites[args[0]].mxlimit = None
				view.sprites[args[0]].mylimit = (args[2], view.sprites[args[0]].my < 0)
			if not view.sprites[args[0]].have_brain:
				view.sprites[args[0]].have_brain = True
				view.events += ((self.current_time, view.do_brain (view.sprites[args[0]]), args[0]),)
			if name == 'move_stop':
				yield ('stop', lambda x: setattr (view.sprites[args[0]], 'mblock', x))
			# Always ignore hardness. TODO?
		elif name == 'playmusic':
			self.play_music (args[0])
		elif name == 'playsound':
			self.sounds[args[0]].play ()
			# TODO: speed adjust
		elif name == 'preload_seq':
			# TODO
			pass
		elif name == 'push_active':
			view.push_active = args[0]
		elif name == 'random':
			# TODO
			pass
		elif name == 'reset_timer':
			# Ignored.
			pass
		elif name == 'restart_game':
			self.data = gtkdink.GtkDink (gamename, gamescale, False)
			self.load_game ()
			yield ('kill', 0)
		elif name == 'save_game':
			# TODO
			pass
		elif name == 'say':
			if args[1] not in view.sprites:
				print ("Warning: not saying '%s', because sprite %d doesn't exist" % (args[0], args[1]))
				yield ('return', 0)
				return
			else:
				sprite = view.sprites[args[1]]
				ret = view.add_text (0, 0, args[0], the_statics, the_locals, owner = sprite)
			yield ('return', ret.num)
		elif name == 'say_stop':
			if args[1] not in view.sprites:
				print ("Warning: not saying '%s', because sprite %d doesn't exist" % (args[0], args[1]))
				yield ('return', 0)
				return
			else:
				sprite = view.sprites[args[1]]
				ret = view.add_text (0, 0, args[0], the_statics, the_locals, owner = sprite)
			if view.sprites[1].frozen:
				view.blocker.append (ret)
			yield ('stop', lambda x: setattr (ret, 'deathcb', x))
			yield ('return', 0)
		elif name == 'say_stop_npc':
			# Pause script to read, then continue. Don't allow skipping through it.
			if args[1] not in view.sprites:
				print ("Warning: not saying '%s', because sprite %d doesn't exist" % (args[0], args[1]))
				yield ('return', 0)
				return
			else:
				sprite = view.sprites[args[1]]
				ret = view.add_text (0, 0, args[0], the_statics, the_locals, owner = sprite)
			yield ('stop', lambda x: setattr (ret, 'deathcb', x))
			yield ('return', 0)
		elif name == 'say_stop_xy':
			ret = view.add_text (args[1], args[2], args[0], the_statics, the_locals)
			if view.sprites[1].frozen:
				view.blocker.append (ret)
			yield ('stop', lambda x: setattr (ret, 'deathcb', x))
			yield ('return', 0)
		elif name == 'say_xy':
			yield ('return', view.add_text (args[1], args[2], args[0], the_statics, the_locals).num)
		elif name == 'screenlock':
			view.screenlock = args[0] != 0
			view.draw_status ()
		elif name == 'script_attach':
			# TODO
			pass
		elif name == 'set_callback_random':
			# TODO
			pass
		elif name == 'set_dink_speed':
			# TODO
			pass
		elif name == 'set_keep_mouse':
			# The pointer is never disabled, even though it is usually not used.
			pass
		elif name == 'set_view':
			self.views[self.current_view].last_time = self.current_time
			if 0 <= args[0] < len (self.views) and self.views[args[0]] is not None:
				self.current_view = args[0]
			self.views[self.current_view].warp_time ()
		elif name == 'show_bmp':
			# TODO
			pass
		elif name == 'sound_set_kill':
			# TODO
			pass
		elif name == 'sound_set_survive':
			# TODO
			pass
		elif name == 'sound_set_vol':
			# TODO
			pass
		elif name == 'sp':
			yield ('return', view.get_sprite_by_name (args[0]))
			return
		elif name == 'sp_active':	#
			if args[1] == 0:
				view.sprites[args[0]].kill ()
		elif name == 'sp_attack_hit_sound':
			# TODO
			pass
		elif name == 'sp_attack_hit_sound_speed':
			# TODO
			pass
		elif name == 'sp_attack_wait':
			# TODO
			pass
		elif name == 'sp_base_attack':	#
			view.sprites[args[0]].base_attack = args[1]
		elif name == 'sp_base_death':	#
			view.sprites[args[0]].base_death = args[1]
		elif name == 'sp_base_idle':	#
			view.sprites[args[0]].base_idle = args[1]
		elif name == 'sp_base_walk':	#
			view.sprites[args[0]].base_walk = args[1]
		elif name == 'sp_brain':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].brain)
				return
			b = gtkdink.dink.make_brain (args[1])
			if (view.sprites[args[0]].brain == TEXTBRAIN) ^ (b == TEXTBRAIN):
				print ('Warning: changing brain to or from text is not allowed')
			else:
				view.sprites[args[0]].brain = gtkdink.dink.make_brain (args[1])
				if not view.sprites[args[0]].have_brain:
					view.sprites[args[0]].have_brain = True
					view.events += ((self.current_time, view.do_brain (view.sprites[args[0]]), args[0]),)
		elif name == 'sp_brain_parm':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].brain_parm)
				return
			view.sprites[args[0]].brain_parm = args[1]
		elif name == 'sp_brain_parm2':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].brain_parm2)
				return
			view.sprites[args[0]].brain_parm2 = args[1]
		elif name == 'sp_defense':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].defense)
				return
			view.sprites[args[0]].defense = args[1]
		elif name == 'sp_dir':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].dir)
				return
			view.sprites[args[0]].dir = args[1]
			view.sprites[args[0]].set_state (view.sprites[args[0]].state)
		elif name == 'sp_disabled':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].disabled)
				return
			view.sprites[args[0]].disabled = args[1]
		elif name == 'sp_distance':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].distance)
				return
			view.sprites[args[0]].distance = args[1]
		elif name == 'sp_editor_num':
			yield ('return', view.sprites[args[0]].editor_num)
			return
		elif name == 'sp_exp':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].experience)
				return
			view.sprites[args[0]].experience = args[1]
		elif name == 'sp_flying':	#
			if len (args) <= 1:
				yield ('return', int (view.sprites[args[0]].flying))
				return
			view.sprites[args[0]].flying = bool (args[1])
		elif name == 'sp_follow':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].follow)
				return
			view.sprites[args[0]].follow = args[1]
		elif name == 'sp_frame':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].frame)
				return
			view.sprites[args[0]].frame = args[1]
		elif name == 'sp_frame_delay':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].frame_delay)
				return
			view.sprites[args[0]].frame_delay = args[1]
		elif name == 'sp_gold':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].gold)
				return
			view.sprites[args[0]].gold = args[1]
		elif name == 'sp_nohard':	#
			if len (args) <= 1:
				yield ('return', not view.sprites[args[0]].hard)
				return
			view.sprites[args[0]].hard = args[1] == 0
		elif name == 'sp_hitpoints':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].hitpoints)
				return
			view.sprites[args[0]].hitpoints = args[1]
		elif name == 'sp_kill':
			view.sprites[args[0]].set_killdelay (args[1] if args[1] > 0 else None)
		elif name == 'sp_mx':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].mx)
				return
			view.sprites[args[0]].mx = args[1]
			if not view.sprites[args[0]].have_brain:
				view.sprites[args[0]].have_brain = True
				view.events += ((self.current_time, self.do_brain (view.sprites[args[0]]), args[0]),)
		elif name == 'sp_my':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].my)
				return
			view.sprites[args[0]].my = args[1]
			if not view.sprites[args[0]].have_brain:
				view.sprites[args[0]].have_brain = True
				view.events += ((self.current_time, self.do_brain (view.sprites[args[0]]), args[0]),)
		elif name == 'sp_noclip':	#
			if len (args) <= 1:
				yield ('return', not view.sprites[args[0]].clip)
				return
			view.sprites[args[0]].clip = not args[1]
		elif name == 'sp_nocontrol':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].nocontrol)
				return
			view.sprites[args[0]].nocontrol = args[1]
		elif name == 'sp_nodraw':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].nodraw)
				return
			view.sprites[args[0]].nodraw = args[1]
		elif name == 'sp_nohit':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].nohit)
				return
			view.sprites[args[0]].nohit = args[1]
		elif name == 'sp_pframe':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].pframe)
				return
			view.sprites[args[0]].pframe = args[1]
		elif name == 'sp_pseq':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].pseq.code)
				return
			view.sprites[args[0]].pseq = self.data.seq.find_seq (args[1])
		elif name == 'sp_que':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].que)
				return
			view.sprites[args[0]].que = args[1]
		elif name == 'sp_range':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].range)
				return
			view.sprites[args[0]].range = args[1]
		elif name == 'sp_reverse':	#
			if len (args) <= 1:
				yield ('return', int (view.sprites[args[0]].reverse))
				return
			view.sprites[args[0]].reverse = bool (args[1])
		elif name == 'sp_script':
			view.sprites[args[0]].script = args[1]
		elif name == 'sp_seq':	#
			if len (args) <= 1:
				yield ('return', 0 if view.sprites[args[0]].seq is None else view.sprites[args[0]].seq.code)
				return
			view.sprites[args[0]].seq = self.data.seq.find_seq (args[1])
			view.sprites[args[0]].last_time = self.current_time
			if not view.sprites[args[0]].have_brain:
				view.sprites[args[0]].have_brain = True
				view.events += ((self.current_time, view.do_brain (view.sprites[args[0]]), args[0]),)
		elif name == 'sp_size':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].size)
				return
			view.sprites[args[0]].size = args[1]
		elif name == 'sp_sound':
			# TODO
			pass
		elif name == 'sp_speed':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].speed)
				return
			view.sprites[args[0]].speed = args[1]
		elif name == 'sp_strength':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].strength)
				return
			view.sprites[args[0]].strength = args[1]
		elif name == 'sp_target':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].target)
				return
			view.sprites[args[0]].target = args[1]
		elif name == 'sp_timing':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].timing)
				return
			view.sprites[args[0]].timing = args[1]
		elif name == 'sp_touch_damage':
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].touch_damage)
				return
			view.sprites[args[0]].touch_damage = args[1]
		elif name == 'sp_x':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].x)
				return
			view.sprites[args[0]].x = args[1]
		elif name == 'sp_y':	#
			if len (args) <= 1:
				yield ('return', view.sprites[args[0]].y)
				return
			view.sprites[args[0]].y = args[1]
		elif name == 'spawn':
			self.run_script (args[0], 'main', (), None)
			yield ('wait', 0)
		elif name == 'start_game':
			# New function, translated as 'spawn ("_start_game");' for dink.
			view.sprites[1].base_idle = 'idle'
			view.sprites[1].base_walk = 'walk'
			view.sprites[1].speed = 3
			view.sprites[1].dir = 4
			view.sprites[1].brain = DINKBRAIN
			view.sprites[1].set_state ('idle')
			view.sprites[1].que = 0
			view.sprites[1].clip = True
			if not view.sprites[1].have_brain:
				view.sprites[1].have_brain = True
				view.events += ((self.current_time, view.do_brain (view.sprites[1]), -1),)
			if 'intro' in self.functions and 'main' in self.functions['intro']:
				s = self.Script ('intro', 'main', (), None)
				r = next (s)
				while r[0] in ('wait', 'stop'):
					yield r
					r = next (s)
			view.dink_can_walk_off_screen = False
			if 'init' in self.functions and 'main' in self.functions['init']:
				s = self.Script ('init', 'main', (), None)
				r = next (s)
				while r[0] in ('wait', 'stop'):
					yield r
					r = next (s)
			view.load_screen ()
			view.draw_status ()
			self.the_globals['update_status'] = 1
			if view.fade[1] == False:
				view.fade = 500, True, self.current_time
		elif name == 'stop_wait_for_button':
			pass
		elif name == 'stopcd':
			# TODO
			pass
		elif name == 'stopmidi':
			# TODO
			pass
		elif name == 'turn_midi_off':
			# TODO
			pass
		elif name == 'turn_midi_on':
			# TODO
			pass
		elif name == 'unfreeze':
			view.sprites[args[0]].frozen = False
			if args[0] == 1:
				view.blocker = []
		elif name == 'wait':
			yield ('wait', args[0])
		elif name == 'wait_for_button':
			if self.get_view ().wait_for_button:
				yield ('return', 0)
				return
			self.get_view ().wait_for_button = self.get_view ().button_waiter
			yield ('stop', lambda x: setattr (self.get_view (), 'button_waiter_data', x))
			yield ('return', self.get_view ().button_response)
			return
		yield ('return', 0)

pygame.mixer.init ()
gamescale = 50
gamename = sys.argv[1]
game = Play (gtkdink.GtkDink (gamename, gamescale, False))
window = gtk.Window ()
shortname = os.path.basename (gamename)
if shortname == '':
	shortname = os.path.basename (os.path.dirname (gamename))
window.set_title ('%s - PyDink player' % os.path.basename (shortname))
window.add (game)
window.connect ('destroy', gtk.main_quit)
window.show_all ()
gtk.main ()
pygame.mixer.music.stop ()
pygame.mixer.quit ()
