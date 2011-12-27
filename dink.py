#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

# dink.py - library for using pydink games.
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

#world
#	nnn-xx-yy
#		info.txt		script, tiles, hardness
#		sprite
#			id.txt		script, x, y, etc.
#tile
#	name-tile.png			tile map (01-41)
#	name-hard.png			hardness for tile map, or for screen
#seq
#	name.gif			sequence
#	name.txt			info about name.gif if it exists, generated sequence otherwise
#sound.txt				list of name filename (number)?
#music.txt				list of name filename (number)?
#script
#	name.c				script to be preprocessed (sound and music names, possibly spacing)

import sys
import os
import re
import Image
import tempfile
import shutil
import StringIO
import pickle
import glib

sys.path += (os.path.join (glib.get_user_config_dir (), 'pydink'),)
import dinkconfig

cachedir = os.path.join (glib.get_user_cache_dir (), 'pydink')
tilefiles, collections, sequences, codes = pickle.load (open (os.path.join (cachedir, 'data')))
filename = ''

def error (message):
	sys.stderr.write ('%s: Error: %s\n' % (filename, message))
	#raise AssertionError ('assertion failed')

def nice_assert (test, message):
	if test:
		return
	error (message)

def make_hard_image (path):
	src = Image.open (path).convert ('RGB')
	spix = src.load ()
	ret = Image.new ('RGBA', src.size)
	rpix = ret.load ()
	for y in range (src.size[1]):
		for x in range (src.size[0]):
			if spix[x, y][2] < 150:
				rpix[x, y] = (0, 0, 0, 0)
			elif spix[x, y][1] >= 150:
				rpix[x, y] = (255, 255, 255, 128)
			else:
				rpix[x, y] = (0, 0, 255, 128)
	return ret

#class filepart:
#	def __init__ (self, name, offset, length):
#		self.offset = offset
#		self.length = length
#		self.file = open (name)
#		self.file.seek (offset)
#		self.pos = 0
#	def read (self, size):
#		assert (size > 0)
#		if self.pos + size >= self.length:
#			size = self.length - self.pos
#		self.pos += size
#		return self.file.read (size)
#	def tell (self):
#		return self.pos
#	def seek (self, p, how):
#		if how == 1:
#			p += self.pos
#		elif how == 2:
#			p += self.length
#		else:
#			nice_assert (how == 0, 'invalid seek type')
#		nice_assert (p <= self.length, 'seek beyond end of file')
#		self.file.seek (self.offset + p)
def filepart (name, offset, length):
	f = open (name)
	f.seek (offset)
	return StringIO.StringIO (f.read (length))

# brain 0: no brain -- sprite will not do anything automatically
# brain 1: Human [that is, sprite 1 / Dink] brain.
# brain 2: ["Dumb Sprite Bouncer", per DinkEdit.  See below.]
# brain 3: Duck brain.
# brain 4: Pig brain.
# brain 5: When seq is done, kills but leaves last frame drawn to the background
# brain 6: Repeat brain - does the active SEQ over and over.
# brain 7: Same as brain 5 but does not draw last frame to the background.
# [brain 8: text sprite brain]
# brain 9: Person/monster ([Only] diagonals)
# brain 10: Person/monster ([No] diagonals)
# brain 11: Missile brain - repeats SEQ [compare brain 17].
# brain 12: Will shrink/grow to match size in sp_brain_parm(), then die [WITHOUT giving any experience...]
# brain 13: Mouse brain (for intro, the pointer) (do a set_keep_mouse() to use inside game as well)
# brain 14: Button brain.  (intro buttons, can be used in game as well)
# brain 15: Shadow brain.  Shadows for fireballs, etc.
# brain 16: Smart People brain.  They can walk around, stop and look.
# brain 17: Missile brain, [like 11] but kills itself when SEQ is done.

brains = ['none', 'dink', 'bounce', 'duck', 'pig', 'mark', 'repeat', 'play', 'text', 'bisshop', 'rook', 'missile', 'resize', 'pointer', 'button', 'shadow', 'person', 'flare']

def make_brain (name):
	if name in brains:
		return brains.index (name)
	try:
		ret = int (name)
	except:
		error ('unknown and non-numeric brain %s' % name)
		ret = 0
	if ret >= len (brains):
		error ('accessing named brain %s by number (%d)' % (brains[ret], ret))
	return ret

predefined = [
		"current_sprite"
	]
default_globals = {
		"exp": 0,
		"strength": 3,
		"defense": 0,
		"cur_weapon": 0,
		"cur_magic": 0,
		"gold": 0,
		"magic": 0,
		"magic_level": 0,
		"vision": 0,
		"result": 0,
		"speed": 1,
		"timing": 0,
		"lifemax": 10,
		"life": 10,
		"level": 1,
		"player_map": 1,
		"last_text": 0,
		"update_status": 0,
		"missile_target": 0,
		"enemy_sprite": 0,
		"magic_cost": 0,
		"missle_source": 0,

		"story": 0,
		"old_womans_duck": 0,
		"nuttree": 0,
		"letter": 0,
		"little_girl": 0,
		"farmer_quest": 0,
		"save_x": 0,
		"save_y": 0,
		"safe": 0,
		"pig_story": 0,
		"wizard_see": 0,
		"mlibby": 0,
		"wizard_again": 0,
		"snowc": 0,
		"duckgame": 0,

		"gossip": 0,
		"robbed": 0,
		"dinklogo": 0,
		"rock_placement": 0,
		"temphold": 0,
		"temp1hold": 0,
		"temp2hold": 0,
		"temp3hold": 0,
		"temp4hold": 0,
		"temp5hold": 0,
		"temp6hold": 0,
		"town1": 0,
		"s2-milder": 0,
		"thief": 0,
		"caveguy": 0,
		"s2-aunt": 0,
		"tombob": 0,
		"mayor": 0,
		"hero": 0,
		"s2-nad": 0,
		"gobpass": 0,
		"bowlore": 0,
		"s4-duck": 0,
		"s5-jop": 0,
		"s7-boat": 0,
		"s2-map": 0
	}
the_locals = {}
the_globals = {}
for i in default_globals:
	the_globals[i] = default_globals[i]
choice_title = [None, False]

def convert_image (im):
	k = Image.eval (im.convert ('RGBA'), lambda v: [v, 254][v == 255])
	bg = Image.new ('RGB', k.size, (255, 255, 255))
	bg.paste (k)
	return bg

def readlines (f):
	ret = {}
	while True:
		l = f.readline ()
		if l.strip () == '':
			break
		if l.strip ()[0] == '#':
			continue
		r = re.match (r'(.*)=(.*)', l.strip ())
		nice_assert (r != None, 'invalid line in input file: %s' % l)
		nice_assert (r.group (1) not in ret, 'duplicate definition of %s' % r.group (1))
		ret[r.group (1).strip ()] = r.group (2).strip ()
	return ret

def get (d, member, default = None):
	if member not in d:
		nice_assert (default != None and default != int, 'member %s has no default, but is missing in file' % member)
		return d, default
	if default == None:
		ret = d[member]
	elif type (default) == bool:
		if d[member].lower () in ['true', 'yes', '1']:
			ret = True
		else:
			nice_assert (d[member].lower () in ['false', 'no', '0'], 'invalid value for boolean setting %s' % member)
			ret = False
	elif default == int:
		ret = int (d[member])
	else:
		ret = type (default)(d[member])
	del d[member]
	return d, ret

def put (f, member, value, default = None):
	nice_assert (value != None, "Writing %s without a value" % member)
	if value == default:
		return
	if type (value) == bool:
		v = '%s' % ['no', 'yes'][value]
	else:
		v = str (value)
	f.write ('%s = %s\n' % (member, v))

def make_lsb (num, size):
	ret = ''
	for i in range (size):
		ret += '%c' % (num & 0xff)
		num >>= 8
	return ret

def make_string (s, size):
	nice_assert (len (s) < size, "String %s of length %d doesn't fit in field of size %d" % (s, len (s), size))
	return s + '\0' * (size - len (s))

def token (script, allow_returning_comment = False):
	s = script.lstrip ()
	if s == '':
		return None, None, False
	if not allow_returning_comment:
		while True:
			if s.startswith ('//'):
				p = s.find ('\n', 2)
				if p < 0:
					s = ''
					continue
				s = s[p + 1:].lstrip ()
				continue
			if s.startswith ('/*'):
				p = s.find ('*/', 2)
				nice_assert (p >= 0, 'unfinished comment')
				s = s[p + 2:].lstrip ()
				continue
			break
	l = ['//', '/*', '&&', '||', '==', '!=', '>=', '<=', '>', '<', '!', '+=', '-=', '/=', '*=', '=', '+', '-', '*', '/', ',', ';', '{', '}', '?', ':', '(', ')', '.']
	for i in l:
		if s.startswith (i):
			return i, s[len (i):].lstrip (), False
	if s[0] == '"':
		p = s.find ('"', 1)
		nice_assert (p >= 0, 'unfinished string')
		n = s.find ('\n', 1)
		nice_assert (n == -1 or n > p, 'unfinished string')
		return s[:p + 1], s[p + 1:].lstrip (), False
	is_name = True
	r = re.match ('[a-zA-Z_][a-zA-Z_0-9]*', s)
	if r == None:
		is_name = False
		r = re.match ('[0-9]+', s)
		nice_assert (r != None, 'unrecognized token %s' % s.split ()[0])
	key = r.group (0)
	return key, s[len (key):].lstrip (), is_name

def push (ret, operators):
	args = operators[-1][1]
	r = ret[-args:]
	ret = ret[:-args]
	op = operators.pop ()[0]
	# Precompute constant expressions.
	if sum ([type (x) is not int for x in r]) == 0:
		if len (r) == 1:
			ret += (int (eval ('%s%d' % (op, r[0]))),)
		else:
			ret += (int (eval ('%d %s %d' % (r[0], op, r[1]))),)
	else:
		ret += ([op, r],)
	return ret, operators

functions = {}
max_args = 0
max_tmp = 0
current_tmp = 0
next_mangled = 0
mangled_names = {}

def mangle (name):
	global next_mangled
	if name in default_globals or name in predefined:
		return '&' + name
	if name not in mangled_names:
		mangled_names[name] = next_mangled
		next_mangled += 1
	return '&m%d%s' % (mangled_names[name], name)

def build_internal_function (name, args, indent, dink, fname, use_retval):
	'''\
	Build dinkc code for an internal function.
	Handle special arguments of:
	add_item
	add_magic
	create_sprite
	editor_type
	get_rand_sprite_with_this_brain
	get_sprite_with_this_brain
	playmidi
	playsound
	preload_seq
	sp
	sp_base_attack
	sp_base_death
	sp_base_idle
	sp_base_walk
	sp_brain
	sp_sound
	sp_seq
	sp_pseq

	Change function name of sp_nohard into sp_hard, because of its inverted argument.

	return before, expression result.'''
	global current_tmp
	a = list (args)
	nice_assert (len (a) == 0 or a[-1] != -1 or internal_functions[name][-1] not in 'SI', 'last argument of %s may be omitted, but must not be -1' % name)
	if len (a) < len (internal_functions[name]):
		a += (-1,)
	if name == 'add_item' or name == 'add_magic':
		a[1] = dink.seq.find_seq (a[1][1:-1]).code
	elif name == 'create_sprite':
		a[2] = make_brain (a[2][1:-1])
		a[3] = dink.seq.find_seq (a[3][1:-1]).code
	elif name == 'get_rand_sprite_with_this_brain' or name == 'get_sprite_with_this_brain':
		a[0] = make_brain (a[0][1:-1])
	elif name == 'playmidi':
		a[0] = dink.sound.find_music (a[0][1:-1])
	elif name == 'playsound':
		a[0] = dink.sound.find_sound (a[0][1:-1])
	elif name == 'preload_seq':
		a[0] = dink.seq.find_seq (a[0][1:-1]).code
	elif name == 'sp':
		nm = a[0][1:-1]
		sprite = None
		# Sprite names used with sp () must be unique in the entire game, because the script doesn't know from which room it's called.
		for r in dink.world.room:
			if nm in dink.world.room[r].sprite:
				nice_assert (sprite == None, 'referenced sprite %s is not unique' % nm)
				sprite = dink.world.room[r].sprite[nm]
		a[0] = sprite.editcode
	elif name == 'sp_base_attack' or name == 'sp_base_death' or name == 'sp_base_idle' or name == 'sp_base_walk':
		if type (a[1]) == str and a[1][0] == '"':
			a[1] = dink.seq.collection_code (a[1][1:-1])
	elif name == 'sp_brain':
		if type (a[1]) == str and a[1][0] == '"':
			a[1] = make_brain (a[1][1:-1])
	elif name == 'sp_sound':
		if type (a[1]) == str and a[1][0] == '"':
			a[1] = dink.sound.find_sound (a[1][1:-1])
	elif name == 'sp_seq' or name == 'sp_pseq':
		if a[1] == '""':
			a[1] = 0
		elif type (a[1]) == str and a[1][0] == '"':
			s = dink.seq.find_seq (a[1][1:-1])
			a[1] = s.code
	elif name == 'sp_nohard':
		name = 'sp_hard'
	bt = ''
	at = []
	for i in a:
		if type (i) == str and i[0] == '"':
			at += (i,)
		else:
			b, e = build_expr (dink, fname, i, indent)
			bt += b
			at += (e,)
	if use_retval:
		t = current_tmp
		current_tmp += 1
		return bt + indent + 'int &tmp%d = ' % t + name + '(' + ', '.join (at) + ');\r\n', '&tmp%d' % t
	else:
		return bt + indent + name + '(' + ', '.join (at) + ');\r\n', ''

def read_args (dink, script):
	args = []
	b = ''
	if script[0] == ')':
		t, script, isname = token (script)
	else:
		while True:
			if script[0] == '"':
				p = script.find ('"', 1)
				nice_assert (p >= 0, 'unterminated string')
				# mangle variable references.
				s = script[:p + 1]
				pos = 0
				sp = ''
				while True:
					pos = s.find ('&')
					if pos < 0:
						sp += s
						break
					sp += s[:pos]
					s = s[pos + 1:]
					e = s.find (';')
					nice_assert (e >= 0, 'incomplete reference in string %s' % s)
					var = s[:e]
					s = s[e + 1:]
					if var == '':
						# empty variable is escape for & itself.
						sp += '&'
					else:
						# variable found: mangle.
						sp += mangle (var)
				args += (sp,)
				script = script[p + 1:]
			else:
				script, a = tokenize_expr (dink, script, as_bool = False)
				args += (a,)
			t, script, isname = token (script)
			if t != ',':
				break
	nice_assert (t == ')', 'unterminated argument list')
	return script, args

def build_expr (dink, fname, expr, indent, invert = False):
	global current_tmp
	eq = ('>', '<=', '>=', '<', '==', '!=')
	if type (expr) == int:
		return '', str (expr)
	elif type (expr) == str:
		return '', mangle (expr)
	elif expr[0] in eq:
		if invert:
			op = eq[eq.index (expr[0]) ^ 1]
		else:
			op = expr[0]
		b1, e1 = build_expr (dink, fname, expr[1][0], indent)
		b2, e2 = build_expr (dink, fname, expr[1][1], indent)
		return b1 + b2, e1 + ' ' + op + ' ' + e2
	elif expr[0] in ('+', '-', '*', '/'):
		if len (expr[1]) == 1:
			if invert:
				return build_expr (dink, fname, ['==', 0, expr[1][0]], indent)
			return build_expr (dink, fname, [expr[0], 0, expr[1][0]], indent)
		else:
			if invert:
				return build_expr (dink, fname, ['==', 0, expr], indent)
			tmp = current_tmp
			b1, e1 = build_expr (dink, fname, expr[1][0], indent)
			current_tmp = tmp + 1
			if e1 == '&tmp%d' % tmp:
				b = b1
			else:
				b = b1 + indent + 'int &tmp%d = ' % tmp + e1 + ';\r\n'
			b2, e2 = build_expr (dink, fname, expr[1][1], indent)
			current_tmp = tmp + 1
			extra = '' if expr[0] in ('*', '/') else '='
			b += b2 + indent + '&tmp%d ' % tmp + expr[0] + extra + ' ' + e2 + ';\r\n'
			return b, '&tmp%d' % tmp
	elif expr[0] in ('&&', '||'):
		# Turn everything into &&.
		# a && b == a && b
		# a || b == !(!a && !b)
		# !(a && b) == !(a && b)
		# !(a || b) == !a && !b
		tmp = current_tmp
		b1, e1 = build_expr (dink, fname, expr[1][0], indent, expr[0] == '||')
		current_tmp = tmp + 1
		b = b1 + indent + 'int &tmp%d = 0;\r\n' % tmp + indent + 'if (' + e1 + ')\r\n' + indent + '{\r\n'
		b2, e2 = build_expr (dink, fname, expr[1][1], indent + '\t', expr[0] == '||')
		current_tmp = tmp + 1
		b += b2 + indent + '\tif (' + e2 + ')\r\n' + indent + '\t{\r\n' + indent + '\t\t&tmp%d = 1;\r\n' % tmp + indent + '\t}\r\n' + indent + '}\r\n'
		if invert ^ (expr[0] == '||'):
			return b, '&tmp%d == 0' % tmp
		else:
			return b, '&tmp%d != 0' % tmp
	elif expr[0] == '!':
		return build_expr (dink, fname, ['==', 0, expr[1][0]], indent, invert)
	elif type (expr[0]) == str:	# internal function call
		return build_internal_function (expr[1], expr[2], indent, dink, fname, True)
	elif len (expr[0]) == 1:	# function call in same file
		return build_function (expr[0][0], expr[1], indent, fname)
	else:				# remote function call
		return build_function (expr[0][1], expr[1], indent, expr[0][0])

internal_functions = {
		'activate_bow': '',
		'add_exp': 'ii',
		'add_item': 's*i',
		'add_magic': 's*i',
		'arm_magic': '',
		'arm_weapon': '',
		'busy': 'i',
		'compare_sprite_script': 'is',
		'compare_weapon': 's',
		'copy_bmp_to_screen': 's',
		'count_item': 's',
		'count_magic': 's',
		'create_sprite': 'ii**i',
		'debug': 's',
		'dink_can_walk_off_screen': 'i',
		'disable_all_sprites': '',
		'enable_all_sprites': '',
		'draw_background': '',
		'draw_hard_map': '',
		'draw_hard_sprite': 'i',
		'draw_screen': '',
		'draw_status': '',
		'editor_seq': 'iI',
		'editor_frame': 'iI',
		'editor_type': 'iI',
		'fade_down': '',
		'fade_up': '',
		'fill_screen': 'i',
		'free_items': '',
		'free_magic': '',
		'freeze': 'i',
		'game_exist': 'i',
		'get_last_bow_power': '',
		'get_rand_sprite_with_this_brain': '*i',
		'get_sprite_with_this_brain': '*i',
		'get_version': '',
		'hurt': 'ii',
		'init': 's',
		'initfont': 's',
		'inside_box': 'iiiiii',
		'is_script_attached': 'i',
		'kill_all_sounds': '',
		'kill_cur_item': '',
		'kill_cur_magic': '',
		'kill_game': '',
		'kill_shadow': 'i',
		'kill_this_item': 's',
		'kill_this_magic': 's',
		'kill_this_task': '',
		'load_game': 'i',
		'load_screen': '',
		'move': 'iiii',
		'move_stop': 'iiii',
		'playmidi': 's',
		'playsound': 'siiii',
		'preload_seq': 'i',
		'push_active': 'i',
		'random': 'ii',
		'reset_timer': '',
		'run_script_by_number': 'is',
		'save_game': 'i',
		'say': 'si',
		'say_stop': 'si',
		'say_stop_npc': 'si',
		'say_stop_xy': 'sii',
		'say_xy': 'sii',
		'screenlock': 'i',
		'script_attach': 'i',
		'scripts_used': '',
		'set_button': 'ii',
		'set_callback_random': 'sii',
		'set_dink_speed': 'i',
		'set_keep_mouse': 'i',
		'show_bmp': 'sii',
		'sound_set_kill': 'i',
		'sound_set_survive': 'ii',
		'sound_set_vol': 'ii',
		'sp': 's',
		'sp_active': 'iI',
		'sp_attack_hit_sound': 'ii',
		'sp_attack_hit_sound_speed': 'ii',
		'sp_attack_wait': 'ii',
		'sp_base_attack': 'i*',
		'sp_base_death': 'i*',
		'sp_base_idle': 'i*',
		'sp_base_walk': 'i*',
		'sp_brain': 'iS',
		'sp_brain_parm': 'iI',
		'sp_brain_parm2': 'iI',
		'sp_defense': 'iI',
		'sp_dir': 'iI',
		'sp_disabled': 'iI',
		'sp_distance': 'ii',
		'sp_editor_num': 'i',
		'sp_exp': 'iI',
		'sp_flying': 'iI',
		'sp_follow': 'iI',
		'sp_frame': 'iI',
		'sp_frame_delay': 'iI',
		'sp_gold': 'iI',
		'sp_nohard': 'iI',
		'sp_hitpoints': 'iI',
		'sp_kill': 'ii',
		'sp_move_nohard': 'iI',
		'sp_mx': 'iI',
		'sp_my': 'iI',
		'sp_noclip': 'iI',
		'sp_nocontrol': 'iI',
		'sp_nodraw': 'iI',
		'sp_nohit': 'iI',
		'sp_notouch': 'iI',
		'sp_pframe': 'iI',
		'sp_picfreeze': 'ii',
		'sp_pseq': 'iS',
		'sp_que': 'iI',
		'sp_range': 'iI',
		'sp_reverse': 'iI',
		'sp_script': 'is',
		'sp_seq': 'iS',
		'sp_size': 'iI',
		'sp_sound': 'i*',
		'sp_speed': 'iI',
		'sp_strength': 'iI',
		'sp_target': 'iI',
		'sp_timing': 'iI',
		'sp_touch_damage': 'ii',
		'sp_x': 'iI',
		'sp_y': 'iI',
		'spawn': 's',
		'start_game': '',
		'stop_entire_game': 'i',
		'stop_wait_for_button': '',
		'stopcd': '',
		'stopmidi': '',
		'turn_midi_off': '',
		'turn_midi_on': '',
		'unfreeze': 'i',
		'wait': 'i',
		'wait_for_button': '',
		'sp_code': 's',
		'seq_code': 's',
		'brain_code': 's',
		'collection_code': 's'
		}

def make_direct (dink, name, args):
	# Check validity of name and arguments.
	nice_assert (name in internal_functions, 'use of undefined function %s' % name)
	ia = internal_functions[name]
	a = list (args)
	if len (a) < len (ia) and (ia.endswith ('I') or ia.endswith ('S')):
		a += (None,)
	nice_assert (len (a) == len (ia), 'incorrect number of arguments for %s (must be %d; is %d)' % (name, len (ia), len (a)))
	for i in range (len (ia)):
		if ia[i] in ('i', 'I'):
			nice_assert (type (a[i]) is not str or a[i][0] != '"', 'argument %d of %s must not be a string' % (i, name))
		elif ia[i] == 's':
			nice_assert (type (a[i]) is str and a[i][0] == '"', 'argument %d of %s must be a string' % (i, name))
		elif ia[i] in ('*', 'S'):
			pass
		else:
			raise AssertionError ('invalid character in internal_functions %s' % ia)
	# Find direct functions.
	if name == 'brain_code':
		return make_brain (args[0][1:-1])
	elif name == 'seq_code':
		return dink.seq.find_seq (args[0][1:-1]).code
	elif name == 'collection_code':
		return dink.seq.find_collection (args[0][1:-1])['code']
	elif name == 'sp_code':
		nm = args[0][1:-1]
		sprite = None
		for r in dink.world.room:
			if nm in dink.world.room[r].sprite:
				nice_assert (sprite == None, 'referenced sprite %s is not unique' % nm)
				sprite = dink.world.room[r].sprite[nm]
		nice_assert (sprite is not None, "referenced sprite %s doesn't exist" % nm)
		return sprite.editcode
	else:
		# Nothing special.
		return None

def tokenize_expr (parent, script, as_bool = None):
	assert as_bool in (True, False)
	need_operator = False
	ret = []
	operators = []
	while True:
		t, script, isname = token (script)
		if need_operator:
			if t == ')' and ['(', 0, 100] in operators:
				while operators[-1] != ['(', 0, 100]:
					ret, operators = push (ret, operators)
				continue
			if t == ',' or t == ';' or t == ')':
				nice_assert (['(', 0, 100] not in operators, 'incomplete subexpression')
				while operators != []:
					ret, operators = push (ret, operators)
				assert len (ret) == 1
				return t + ' ' + script, ret[0]
			elif t == '||':
				while operators != [] and operators[-1][2] < 5:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 5],)
			elif t == '&&':
				while operators != [] and operators[-1][2] < 4:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 4],)
			elif t in ['==', '!=', '>=', '<=', '>', '<']:
				while operators != [] and operators[-1][2] <= 3:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 3],)
			elif t in ['+', '-']:
				while operators != [] and operators[-1][2] <= 2:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 2],)
			elif t in ['*', '/']:
				while operators != [] and operators[-1][2] <= 1:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 1],)
			else:
				raise AssertionError ('no valid operator found in expression (%s)' % t)
			need_operator = False
		else:
			if t == '(':
				operators += (['(', 0, 100],)
			elif t in ['+', '-', '!']:
				operators += ([t, 1, 0],)
			else:
				nice_assert (t and (isname or (t[0] >= '0' and t[0] <= '9')), 'syntax error')
				if isname:
					name = t
					if script.startswith ('.'):
						# Read away the period.
						t, script, isname = token (script)
						# Get the function name.
						t, script, isname = token (script)
						name = (name.lower (), t)
						nice_assert (name[0] in functions and name[1] in functions[name[0]], 'function %s not found in file %s' % (name[1], name[0]))
						nice_assert (script.startswith ('('), 'external function %s.%s is not called' % (name[0], name[1]))
					if script.startswith ('('):
						# Read away the opening parenthesis.
						t, script, isname = token (script)
						script, args = read_args (parent, script)
						if type (name) == str:
							if filename in functions and name in functions[filename]:
								# local function.
								nice_assert (len (args) == len (functions[filename][name][1]), 'incorrect number of arguments when calling %s (%d, needs %d)' % (name, len (args), len (functions[filename][name][1])))
								ret += (['()', (filename, name), args],)
							else:
								# internal function.
								if name == 'choice':
									ret += (['choice', args, choice_title[0]])
									choice_title[:] = [None, False]
								direct = make_direct (parent, name, args)
								if direct is not None:
									ret += (direct,)
								else:
									ret += (['internal', name, args],)
						else:
							# function in other file.
							nice_assert (len (args) == len (functions[name[0]][name[1]][1]), 'incorrect number of arguments when calling %s.%s (%d, needs %d)' % (name[0], name[1], len (args), len (functions[name[0]][name[1]][1])))
							ret += (['()', name, args],)
						need_operator = True
						continue
					# variable reference.
					ret += (t,)
				else:
					# numerical constant.
					ret += (int (t),)
				need_operator = True

def check_exists (the_locals, name):
	return name in the_locals or name in the_globals

def tokenize (script, dink, fname):
	'''Tokenize a script completely. Return a list of functions (name, (rettype, args), definition-statement).'''
	global the_locals
	the_locals = []
	ret = []
	indent = []
	numlabels = 0
	while True:
		choice_title[1] = False
		t, script, isname = token (script)
		if not t:
			break
		if t == 'extern':
			t, script, isname = token (script)
			if t == 'int':
				t, script, isname = token (script)
			nice_assert (isname, 'invalid argument for extern')
			name = t
			t, script, isname = token (script)
			nice_assert (t == ';', 'junk after extern')
			nice_assert (name not in the_locals, 'global variable %s already defined as local' % name)
			if name not in the_globals:
				the_globals[name] = 0
			continue
		nice_assert (t == 'void' or t == 'int', 'invalid token at top level; only extern, void or int allowed (not %s)' % t)
		t, script, isname = token (script)
		nice_assert (isname, 'function name required after top level void (not %s)' % t)
		name = t
		t, script, isname = token (script)
		nice_assert (t == '(', '(possibly empty) argument list required for function definition (not %s)' % t)
		while True:
			# find_functions parsed the arguments already.
			t, script, isname = token (script)
			if t == ')':
				break
		t, script, isname = token (script)
		nice_assert (t == '{', 'function body not defined')
		script, s = tokenize_statement ('{ ' + script, dink, fname, name)
		ret += ((name, functions[fname][name], s),)
	return ret

def tokenize_statement (script, dink, fname, own_name):
	global the_locals
	t, script, isname = token (script, False)
	nice_assert (t != None, 'missing statement')
	need_semicolon = True
	if t == '{':
		statements = []
		while True:
			t, script, isname = token (script, False)
			nice_assert (t, 'incomplete block')
			if t == '}':
				ret = '{', statements
				need_semicolon = False
				break
			script, s = tokenize_statement (t + ' ' + script, dink, fname, own_name)
			statements += (s,)
	elif t == ';':
		ret = None
		need_semicolon = False
	elif t == 'return':
		if functions[fname][own_name][0] == 'int':
			script, e = tokenize_expr (dink, script, as_bool = False)
			ret = 'return', e
		else:
			ret = 'return', None
	elif t == 'while':
		t, script, isname = token (script)
		nice_assert (t == '(', 'parenthesis required after while')
		script, e = tokenize_expr (dink, script, as_bool = True)
		t, script, isname = token (script)
		nice_assert (t == ')', 'parenthesis for while not closed')
		script, s = tokenize_statement (script, dink, fname, own_name)
		need_semicolon = False
		ret = 'while', e, s
	elif t == 'for':
		t, script, isname = token (script)
		nice_assert (t == '(', 'parenthesis required after for')
		if script[0] != ';':
			n, script, isname = token (script)
			nice_assert (isname, 'first for-expression must be empty or assignment (not %s)' % n)
			a, script, isname = token (script)
			nice_assert (a in ('=', '+=', '-=', '*=', '/='), 'first for-expression must be empty or assignment (not %s)' % a)
			script, e = tokenize_expr (dink, script, as_bool = False)
			f1 = (a, n, e)
			nice_assert (n in the_locals or n in the_globals, 'use of undefined variable %s in for loop' % n)
		else:
			f1 = None
		t, script, isname = token (script)
		nice_assert (t == ';', 'two semicolons required in for argument')
		script, f2 = tokenize_expr (dink, script, as_bool = True)
		t, script, isname = token (script)
		nice_assert (t == ';', 'two semicolons required in for argument')
		if script[0] != ')':
			n, script, isname = token (script)
			nice_assert (isname, 'third for-expression must be empty or assignment (not %s)' % n)
			a, script, isname = token (script)
			nice_assert (a in ('=', '+=', '-=', '*=', '/='), 'third for-expression must be empty or assignment (not %s)' % a)
			script, e = tokenize_expr (dink, script, as_bool = False)
			nice_assert (n in the_locals or n in the_globals, 'use of undefined variable %s in for loop' % n)
			f3 = (a, n, e)
		else:
			f3 = None
		t, script, isname = token (script)
		nice_assert (t == ')', 'parenthesis for for not closed')
		script, s = tokenize_statement (script, dink, fname, own_name)
		need_semicolon = False
		ret = 'for', f1, f2, f3, s
	elif t == 'if':
		t, script, isname = token (script)
		nice_assert (t == '(', 'parenthesis required after if')
		script, e = tokenize_expr (dink, script, as_bool = True)
		t, script, isname = token (script)
		nice_assert (t == ')', 'parenthesis not closed for if')
		script, s1 = tokenize_statement (script, dink, fname, own_name)
		t, script, isname = token (script)
		if t == 'else':
			script, s2 = tokenize_statement (script, dink, fname, own_name)
		else:
			script = t + ' ' + script
			s2 = None
		need_semicolon = False
		ret = 'if', e, s1, s2
	elif t == 'int':
		t, script, isname = token (script)
		nice_assert (isname, 'local definition without name')
		name = t
		if name not in the_locals:
			the_locals += (name,)
		t, script, isname = token (script)
		if t == '=':
			script, e = tokenize_expr (dink, script, as_bool = False)
		else:
			e = None
			script = t + ' ' + script
		ret = 'int', name, e
	elif t == 'goto':
		t, script, isname = token (script)
		nice_assert (isname, 'goto without target')
		print (filename + ": Warning: script is using goto; DON'T DO THAT!")
		ret = 'goto', t
	else:
		nice_assert (isname, 'syntax error')
		name = t
		t, script, isname = token (script)
		if t == ':':
			print (filename + ": Warning: defining a label is only useful for goto; DON'T DO THAT!")
			ret = ':', name
		elif t in ['=', '+=', '-=', '*=', '/=']:
			nice_assert (check_exists (the_locals, name), 'use of undefined variable %s' % name)
			op = t
			script, e = tokenize_expr (dink, script, as_bool = False)
			ret = op, name, e
		else:
			if t == '.':
				# Remote function call.
				t, script, isname = token (script)
				nice_assert (isname, 'syntax error')
				name = (name.lower (), t)
				t, script, isname = token (script)
			nice_assert (t == '(', 'syntax error')
			if name == 'choice_title':
				nice_assert (choice_title[1] == False, 'duplicate choice_title without a choice')
				choice_title[1] = True
				script, args = read_args (dink, script)
				nice_assert (len (args) >= 1 and len (args) <= 3 and args[0][0] == '"', 'invalid argument list for %s' % name)
				choice_title[0] = args
				ret = None
			elif name == 'choice':
				choices = []
				while True:
					t, script, isname = token (script)
					if t[0] != '"':
						script, e = tokenize_expr (dink, t + ' ' + script, as_bool = True)
						t, script, isname = token (script)
						nice_assert (t[0] == '"', 'choice requires a string')
					else:
						e = None
					choices += ((e, t),)
					t, script, isname = token (script)
					if t == ')':
						break
					nice_assert (t == ',', 'choice requires a comma')
				nice_assert (choices != [], 'choice requires at least one option')
				ret = 'choice', choices, choice_title[0]
				choice_title[:] = [None, False]
			else:
				script, args = read_args (dink, script)
				if type (name) == str:
					if name in functions[fname]:
						nice_assert (len (args) == len (functions[fname][name][1]), 'incorrect number of arguments when calling %s (%d, needs %d)' % (name, len (args), len (functions[fname][name][1])))
						ret = '()', (fname, name), args
					else:
						direct = make_direct (dink, name, args)
						if direct is not None:
							ret = direct
						else:
							ret = 'internal', name, args
				else:
					nice_assert (name[0] in functions and name[1] in functions[name[0]], 'function %s not found in file %s' % (name[1], name[0]))
					nice_assert (len (args) == len (functions[name[0]][name[1]][1]), 'incorrect number of arguments when calling %s.%s (%d, needs %d)' % (name[0], name[1], len (args), len (functions[name[0]][name[1]][1])))
					ret = '()', name, args
	nice_assert (choice_title[1] == False or choice_title[0] == None, 'unused choice_title')
	if need_semicolon:
		t, script, isname = token (script)
		nice_assert ((t == ';'), 'missing semicolon')
	return script, ret

def preprocess (script, dink, fname):
	global numlabels
	numlabels = 0
	fs = tokenize (script, dink, fname)
	return '\r\n'.join ([build_function_def (x, fname, dink) for x in fs])

def build_function_def (data, fname, dink):
	name, ra, impl = data
	ret = 'void %s (void)\r\n{\r\n' % name
	for a in range (len (ra[1])):
		ret += '\tint %s = &arg%d;\r\n' % (mangle (ra[1][a]), a)
	assert impl[0] == '{'
	for s in impl[1]:
		ret += build_statement (s, ra[0], '\t', fname, dink)
	return ret + '}\r\n'

def build_function (name, args, indent, fname):
	global current_tmp
	if type (name) == str:
		if name == 'start_game':
			# Special case: start_game is a generated function when a dmod is built.
			return indent + "spawn ('start_game')\r\n"
		f = functions[fname][name]
	else:
		f = functions[name[0]][name[1]]
	tb = ''
	old_current_tmp = current_tmp
	for i in range (len (f[1])):
		b, e = build_expr (dink, fname, args[i], indent)
		tb += b + indent + '&arg%d = ' % i + e + ';\r\n'
		current_tmp = old_current_tmp
	if type (name) == str:
		return tb + indent + name + '();\r\n'
	else:
		return tb + indent + 'external("%s", "%s");\r\n' % name

def build_choice (choices, title):
	# data[1] = sequence of choices (expr or None, string)
	# data[2] = None or title (sequence of 1, 2 or 3 arguments)
	tb = ''
	ret = indent + 'choice_start()\r\n'
	if title != None:
		if len (title) == 3:
			b, e = build_expr (dink, fname, title[2])
			tb += b
			ret += indent + 'set_y %d\r\n' % e
		if len (title) >= 2:
			b, e = build_expr (dink, fname, title[1])
			tb += b
			ret += indent + 'set_title_color %d\r\n' % e
		ret += indent + 'title_start()\r\n' + title[0] + indent + 'title_end()\r\n'
	for i in len (choices):
		ret += indent
		if choices[i][0] != None:
			b, e = build_expr (dink, fname, choices[i][0], indent)
			tb += b
			ret += '(%s) ' % e
		ret += choices[i][1] + '\r\n'
	return tb + ret + indent + 'choice_end()\r\n'

def build_statement (data, retval, indent, fname, dink):
	global numlabels
	global current_tmp
	current_tmp = 0
	if data[0] == '{':
		ret = ''
		for s in data[1]:
			ret += build_statement (s, retval, indent + '\t', fname, dink)
		return ret
	elif data[0] == 'return':
		if data[1] == None:
			return indent + 'return;\r\n'
		else:
			b, e = build_expr (dink, fname, data[1], indent)
			return b + indent + '&result = ' + e + ';\r\n' + indent + 'return;\r\n'
	elif data[0] == 'while':
		start = 'while%d' % numlabels
		numlabels += 1
		end = 'while%d' % numlabels
		numlabels += 1
		b, e = build_expr (dink, fname, data[1], indent)
		ret = indent + start + ':\r\n'
		ret += b + indent + 'if (' + e + ')\r\n' + indent + '{\r\n' + indent + '\tgoto ' + end + ';\r\n' + indent + '}\r\n'
		ret += build_statement (data[2], retval, indent + '\t', fname, dink)
		ret += indent + 'goto ' + start + ';\r\n' + i + end + ':\r\n'
		return ret
	elif data[0] == 'for':
		# for (i = 0; i < 4; ++i) foo;
		# i = 0;
		# loop:
		# 	if (!(i < 4))
		#		goto end
		# 	foo;
		#	++i;
		# 	goto loop
		# end:
		start = 'for%d' % numlabels
		numlabels += 1
		end = 'for%d' % numlabels
		numlabels += 1
		ret = ''
		if data[1] != None:
			a, n, te = data[1]
			if a[0] in ('*', '/'):
				a = a[0]
			b, e = build_expr (dink, fname, te, indent)
			ret += b + mangle (n) + ' ' + a + ' ' + e + ';\r\n'
		ret += indent + start + ':\r\n'
		b, e = build_expr (dink, fname, data[2], invert = True)
		ret += b + indent + 'if (' + e + ')\r\n' + indent + '{\r\n' + indent + '\tgoto ' + end + ';\r\n' + indent + '}\r\n'
		ret += build_statement (data[4], retval, indent, fname, dink)
		if data[3] != None:
			a, n, te = data[3]
			if a[0] in ('*', '/'):
				a = a[0]
			b, e = build_expr (dink, fname, te, indent)
			ret += b + mangle (n) + ' ' + a + ' ' + e + ';\r\n'
		ret += indent + 'goto ' + start + ';\r\n'
		return ret
	elif data[0] == 'if':
		ret = ''
		b, e = build_expr (dink, fname, data[1], indent)
		ret += b + indent + 'if (' + e + ')\r\n' + indent + '{\r\n'
		ret += build_statement (data[2], retval, indent + '\t', fname, dink)
		ret += indent + '}\r\n'
		if data[3] != None:
			ret += indent + 'else\r\n' + indent + '{\r\n'
			ret += build_statement (data[3], retval, indent + '\t', fname, dink)
			ret += indent + '}\r\n'
		return ret
	elif data[0] == 'int':
		if data[2] != None:
			b, e = build_expr (dink, fname, data[2], indent)
			return b + indent + 'int ' + mangle (data[1]) + ' = ' + e + ';\r\n'
		else:
			return indent + 'int ' + mangle (data[1]) + ';\r\n'
	elif data[0] == 'goto':
		return indent + 'goto ' + data[1] + ';\r\n'
	elif data[0] == 'choice':
		b, e = build_choice (data[1], data[2], indent)
		# discard return value
		return b
	elif data[0] == '()':
		return build_function (data[1], data[2], indent, fname)
	elif data[0] == 'internal':
		b, e = build_internal_function (data[1], data[2], indent, dink, fname, False)
		# discard return value.
		return b
	else:
		a, n, te = data
		if a[0] in ('*', '/'):
			a = a[0]
		b, e = build_expr (dink, fname, te, indent)
		return b + indent + mangle (n) + ' ' + a + ' ' + e + ';\r\n'

class Sprite:
	pass

class Room:
	def __init__ (self, parent, root = None):
		self.parent = parent
		self.sprite = {}
		if root == None:
			self.tiles = [[[1, 0, 0] for x in range (12)] for y in range (8)]
			self.hard = ''
			self.script = ''
			self.music = ''
			self.indoor = False
			self.codes = []
			return
		global filename
		filename = 'info' + os.extsep + 'txt'
		f = open (os.path.join (root, filename))
		self.tiles = []
		for ty in range (8):
			ln = f.readline ()
			self.tiles += ([[int (z) for z in y.split (',')] for y in ln.split ()],)
			nice_assert (len (self.tiles[-1]) == 12, 'invalid line in %s/info.txt: not 12 tiles on a line' % root)
		info = readlines (f)
		info, self.hard = get (info, 'hard', '')
		info, self.script = get (info, 'script', '')
		info, self.music = get (info, 'music', '')
		info, self.indoor = get (info, 'indoor', False)
		nice_assert (info == {}, 'unused data in %s/info.txt' % root)
		sdir = os.path.join (root, "sprite")
		self.codes = []
		for s in os.listdir (sdir):
			filename = os.path.join (sdir, s)
			info = readlines (open (filename))
			r = re.match ('(.+?)(-(\d*?))?(\..*)?$', s)
			base = r.group (1)
			s = base
			i = 0
			while s in self.sprite:
				s = base + '-%d' % i
				i += 1
			self.sprite[s] = Sprite ()
			if r.group (3) != None:
				self.sprite[s].num = int (r.group (3))
				if self.sprite[s].num in self.codes:
					error ('duplicate definition of sprite code %d' % self.sprite[s].num)
					self.sprite[s].num = None
				else:
					self.codes += (self.sprite[s].num,)
			else:
				self.sprite[s].num = None
			info, self.sprite[s].x = get (info, 'x', int)
			info, self.sprite[s].y = get (info, 'y', int)
			info, seq = get (info, 'seq', base)
			seq = seq.split ()
			if len (seq) == 1:
				self.sprite[s].seq = seq[0]
			elif len (seq) == 2:
				self.sprite[s].seq = (seq[0], int (seq[1]))
			else:
				print 'Warning: strange seq:', seq
				self.sprite[s].seq = None
			self.sprite[s].name = base
			info, self.sprite[s].frame = get (info, 'frame', 1)
			info, self.sprite[s].type = get (info, 'type', 1)	# 0 for background, 1 for person or sprite, 3 for invisible
			info, self.sprite[s].size = get (info, 'size', 100)
			info, self.sprite[s].brain = get (info, 'brain', 'none')
			info, self.sprite[s].script = get (info, 'script', '')
			info, self.sprite[s].speed = get (info, 'speed', 1)
			info, self.sprite[s].base_walk = get (info, 'base_walk', '')
			info, self.sprite[s].base_idle = get (info, 'base_idle', '')
			info, self.sprite[s].base_attack = get (info, 'base_attack', '')
			info, self.sprite[s].timing = get (info, 'timing', 33)
			info, self.sprite[s].que = get (info, 'que', 0)
			info, self.sprite[s].hard = get (info, 'hard', True)
			info, self.sprite[s].left = get (info, 'left', 0)
			info, self.sprite[s].top = get (info, 'top', 0)
			info, self.sprite[s].right = get (info, 'right', 0)
			info, self.sprite[s].bottom = get (info, 'bottom', 0)
			info, w = get (info, 'warp', '')
			if w == '':
				self.sprite[s].warp = None
			else:
				self.sprite[s].warp = [int (x) for x in w.split ()]
			info, self.sprite[s].touch_seq = get (info, 'touch_seq', '')
			info, self.sprite[s].base_death = get (info, 'base_death', '')
			info, self.sprite[s].gold = get (info, 'gold', 0)
			info, self.sprite[s].hitpoints = get (info, 'hitpoints', 0)
			info, self.sprite[s].strength = get (info, 'strength', 0)
			info, self.sprite[s].defense = get (info, 'defense', 0)
			info, self.sprite[s].exp = get (info, 'exp', 0)
			info, self.sprite[s].sound = get (info, 'sound', '')
			info, self.sprite[s].vision = get (info, 'vision', 0)
			info, self.sprite[s].nohit = get (info, 'nohit', False)
			info, self.sprite[s].touch_damage = get (info, 'touch_damage', 0)
			nice_assert (info == {}, 'unused data for sprite %s' % s)
		code = 0
		for s in self.sprite:
			if self.sprite[s].num != None:
				continue
			while code in self.codes:
				code += 1
			self.sprite[s].num = code
			self.codes += (code,)
	def add_sprite (self, pos, seq, frame):
		if type (seq) == str:
			s = seq
			the_seq = self.parent.seq.find_seq (s)
			if the_seq == None:
				print ('seq %s not found' % s)
				return None
			brain = the_seq.brain
			script = the_seq.script
			walk = ''
			attack = ''
			death = ''
			hard = the_seq.hard
		else:
			s = seq[0]
			the_collection = self.parent.seq.find_collection (s)
			if the_collection == None:
				print ('collection %s not found' % s)
				return None
			if seq[1] not in the_collection:
				print ('direction %d not in collection %s' % (seq[1], seq[0]))
				return None
			the_seq = the_collection[seq[1]]
			brain = the_collection['brain']
			script = the_collection['script']
			walk = seq[0]
			attack = the_collection['attack']
			death = the_collection['death']
			hard = False
		os = s
		i = 0
		while s in self.sprite:
			s = os + '-%d' % i
			i += 1
		self.sprite[s] = Sprite ()
		self.sprite[s].x = pos[0]
		self.sprite[s].y = pos[1]
		self.sprite[s].seq = seq
		self.sprite[s].frame = frame
		self.sprite[s].type = 1
		self.sprite[s].size = 100
		self.sprite[s].brain = brain
		self.sprite[s].script = script
		self.sprite[s].speed = 1
		self.sprite[s].base_walk = walk
		self.sprite[s].base_idle = ''
		self.sprite[s].base_attack = attack
		self.sprite[s].timing = 33
		self.sprite[s].que = 0
		self.sprite[s].hard = hard
		self.sprite[s].left = 0
		self.sprite[s].top = 0
		self.sprite[s].right = 0
		self.sprite[s].bottom = 0
		self.sprite[s].warp = None
		self.sprite[s].touch_seq = ''
		self.sprite[s].base_death = death
		self.sprite[s].gold = 0
		self.sprite[s].hitpoints = 0
		self.sprite[s].strength = 0
		self.sprite[s].defense = 0
		self.sprite[s].exp = 0
		self.sprite[s].sound = ''
		self.sprite[s].vision = 0
		self.sprite[s].nohit = False
		self.sprite[s].touch_damage = 0
		code = 0
		while code in self.codes:
			code += 1
		self.sprite[s].num = code
		self.codes += (code,)
		return s
	def save (self, n):
		y = (n - 1) / 32
		x = n - y * 32 - 1
		d = os.path.join (self.parent.root, 'world', '%03d-%02d-%02d' % (n, x, y))
		if not os.path.isdir (d):
			os.mkdir (d)
		f = open (os.path.join (d, 'info' + os.extsep + 'txt'), 'w')
		for y in range (8):
			f.write (' '.join ([','.join ([str (z) for z in self.tiles[y][x]]) for x in range (12)]) + '\n')
		put (f, 'hard', self.hard, '')
		put (f, 'script', self.script, '')
		put (f, 'music', self.music, '')
		put (f, 'indoor', self.indoor, False)
		sd = os.path.join (d, 'sprite')
		os.mkdir (sd)
		for s in self.sprite:
			r = re.match ('(.+?)(-\d*?)?(\..*)?$', s)
			base = r.group (1)
			f = open (os.path.join (sd, '%s-%d' % (base, self.sprite[s].num)), 'w')
			put (f, 'x', self.sprite[s].x)
			put (f, 'y', self.sprite[s].y)
			if type (self.sprite[s].seq) == str:
				seq = self.sprite[s].seq
			else:
				seq = '%s %d' % self.sprite[s].seq
			put (f, 'seq', seq, base)
			put (f, 'frame', self.sprite[s].frame, 1)
			put (f, 'type', self.sprite[s].type, 1)
			put (f, 'size', self.sprite[s].size, 100)
			put (f, 'brain', self.sprite[s].brain, 'none')
			put (f, 'script', self.sprite[s].script, '')
			put (f, 'speed', self.sprite[s].speed, 1)
			put (f, 'base_walk', self.sprite[s].base_walk, '')
			put (f, 'base_idle', self.sprite[s].base_idle, '')
			put (f, 'base_attack', self.sprite[s].base_attack, '')
			put (f, 'timing', self.sprite[s].timing, 33)
			put (f, 'que', self.sprite[s].que, 0)
			put (f, 'hard', self.sprite[s].hard, True)
			put (f, 'left', self.sprite[s].left, 0)
			put (f, 'top', self.sprite[s].top, 0)
			put (f, 'right', self.sprite[s].right, 0)
			put (f, 'bottom', self.sprite[s].bottom, 0)
			if self.sprite[s].warp != None:
				put (f, 'warp', ' '.join ([str (x) for x in self.sprite[s].warp]))
			put (f, 'touch_seq', self.sprite[s].touch_seq, '')
			put (f, 'base_death', self.sprite[s].base_death, '')
			put (f, 'gold', self.sprite[s].gold, 0)
			put (f, 'hitpoints', self.sprite[s].hitpoints, 0)
			put (f, 'strength', self.sprite[s].strength, 0)
			put (f, 'defense', self.sprite[s].defense, 0)
			put (f, 'exp', self.sprite[s].exp, 0)
			put (f, 'sound', self.sprite[s].sound, '')
			put (f, 'vision', self.sprite[s].vision, 0)
			put (f, 'nohit', self.sprite[s].nohit, False)
			put (f, 'touch_damage', self.sprite[s].touch_damage, 0)

class World:
	def __init__ (self, parent):
		self.parent = parent
		self.room = {}
		if self.parent.root == None:
			return
		d = os.path.join (parent.root, 'world')
		for y in range (24):
			for x in range (32):
				n = y * 32 + x + 1
				dirname = os.path.join (d, '%03d-%02d-%02d' % (n, x, y))
				if not os.path.exists (dirname):
					continue
				self.room[n] = Room (parent, dirname)
		for f in os.listdir (d):
			r = re.match ('(\d{3})-(\d{2})-(\d{2})$', f)
			if r == None:
				if re.match ('\d+-', f) != None:
					sys.stderr.write ("Warning: not using %s as room\n" % f)
				continue
			n, x, y = [int (k) for k in r.groups ()]
			if x >= 32 or y >= 24 or n != y * 32 + x + 1:
				sys.stderr.write ("Warning: not using %s as room (%d != %d * 32 + %d + 1)\n" % (f, n, y, x))
		# Assign initial sprite codes
		self.set_codes (False)
	def save (self):
		os.mkdir (os.path.join (self.parent.root, 'world'))
		for r in self.room:
			self.room[r].save (r)
	def write_sprite (self, spr, mdat, x, y):
		mdat.write (make_lsb (x, 4))
		mdat.write (make_lsb (y, 4))
		sq = self.parent.seq.find_seq (spr.seq)
		if sq == None:
			mdat.write (make_lsb (-1, 4))
		else:
			mdat.write (make_lsb (sq.code, 4))
		mdat.write (make_lsb (spr.frame, 4))
		mdat.write (make_lsb (spr.type, 4))
		mdat.write (make_lsb (spr.size, 4))
		mdat.write (make_lsb (1, 4))	# active
		mdat.write (make_lsb (0, 4))	# rotation
		mdat.write (make_lsb (0, 4))	# special
		mdat.write (make_lsb (make_brain (spr.brain), 4))
		mdat.write (make_string (spr.script, 14))
		mdat.write ('\0' * 38)
		mdat.write (make_lsb (spr.speed, 4))
		def coll (which):
			if which == '':
				return 0
			return self.parent.seq.collection_code (which)
		mdat.write (make_lsb (coll (spr.base_walk), 4))
		mdat.write (make_lsb (coll (spr.base_idle), 4))
		mdat.write (make_lsb (coll (spr.base_attack), 4))
		mdat.write (make_lsb (0, 4))	# hit
		mdat.write (make_lsb (spr.timing, 4))
		mdat.write (make_lsb (0 if spr.que == 0 else max (0, y - spr.que), 4))
		mdat.write (make_lsb (not spr.hard, 4))
		mdat.write (make_lsb (spr.left, 4))
		mdat.write (make_lsb (spr.top, 4))
		mdat.write (make_lsb (spr.right, 4))
		mdat.write (make_lsb (spr.bottom, 4))
		if spr.warp != None:
			mdat.write (make_lsb (1, 4))
			mdat.write (make_lsb (spr.warp[0], 4))
			mdat.write (make_lsb (spr.warp[1], 4))
			mdat.write (make_lsb (spr.warp[2], 4))
		else:
			mdat.write ('\0' * 16)
		if spr.touch_seq == '':
			mdat.write (make_lsb (0, 4))
		else:
			mdat.write (make_lsb (self.parent.seq.find_seq (spr.touch_seq).code, 4))
		mdat.write (make_lsb (coll (spr.base_death), 4))
		mdat.write (make_lsb (spr.gold, 4))
		mdat.write (make_lsb (spr.hitpoints, 4))
		mdat.write (make_lsb (spr.strength, 4))
		mdat.write (make_lsb (spr.defense, 4))
		mdat.write (make_lsb (spr.exp, 4))
		mdat.write (make_lsb (self.parent.sound.find_sound (spr.sound), 4))
		mdat.write (make_lsb (spr.vision, 4))
		mdat.write (make_lsb (int (spr.nohit), 4))
		mdat.write (make_lsb (spr.touch_damage, 4))
		mdat.write ('\0' * 20)
	def build (self, root):
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink' + os.extsep + 'dat'), "wb")
		ddat.write ('Smallwood' + '\0' * 15)
		rooms = []
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 4))
				continue
			rooms += (i,)
			# Note that the write is after the append, because the index must start at 1.
			ddat.write (make_lsb (len (rooms), 4))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 4))
				continue
			ddat.write (make_lsb (self.parent.sound.find_music (self.room[i].music), 4))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.room or not self.room[i].indoor:
				ddat.write (make_lsb (0, 4))
			else:
				ddat.write (make_lsb (1, 4))
		# Write map.dat
		mdat = open (os.path.join (root, 'map.dat'), "wb")
		for s in rooms:
			mdat.write ('\0' * 20)
			# tiles and hardness
			for y in range (8):
				for x in range (12):
					bmp, tx, ty = self.room[s].tiles[y][x]
					mdat.write (make_lsb ((bmp - 1) * 128 + ty * 12 + tx, 4))
					mdat.write ('\0' * 4)
					mdat.write (make_lsb (self.parent.tile.find_hard (self.room[s].hard, x, y, bmp, tx, ty), 4))
					mdat.write ('\0' * 68)
			mdat.write ('\0' * 320)
			# sprites
			# sprite 0 is never used...
			mdat.write ('\0' * 220)
			editcode = 1
			for sp in self.room[s].sprite:
				spr = self.room[s].sprite[sp]
				spr.editcode = editcode
				editcode += 1
				self.write_sprite (spr, mdat, spr.x, spr.y)
			n = len (self.room[s].sprite)
			extra = [(x, y) for (x, y) in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)) if 0 <= (s - 1) % 32 + x < 32 and 0 <= (s - 1) / 32 + y < 24]
			for ex, ey in extra:
				eroom = ((s - 1) / 32 + ey) * 32 + (s - 1) % 32 + ex + 1
				if eroom not in self.room:
					continue
				for sp in self.room[eroom].sprite:
					spr = self.room[eroom].sprite[sp]
					sq = self.parent.seq.find_seq (spr.seq)
					tx = spr.x + ex * 12 * 50 - 20
					ty = spr.y + ey * 8 * 50
					if tx + sq.boundingbox[2] >= 0 and tx + sq.boundingbox[0] < 12 * 50 and ty + sq.boundingbox[3] >= 0 and ty + sq.boundingbox[1] < 8 * 50:
						self.write_sprite (spr, mdat, spr.x + ex * 12 * 50, spr.y + ey * 8 * 50)
						n += 1
			mdat.write ('\0' * 220 * (100 - n))
			# base script
			mdat.write (make_string (self.room[s].script, 21))
			mdat.write ('\0' * 1019)
	def set_codes (self, per_screen):
		editcode = 1
		for room in self.room:
			if per_screen:
				editcode = 1
			for sp in self.room[room].sprite:
				self.room[room].sprite[sp].editcode = editcode
				editcode += 1

class Tile:
	# self.tile is a dict of num:(tiles, hardness, code). Code means:
	# 0: hardness from original, image from original
	# 1: hardness from original, image from dmod
	# 2: hardness from dmod, image from original
	# 3: hardness from dmod, image from dmod
	def __init__ (self, parent):
		self.parent = parent
		self.hard = {}
		self.tile = {}
		ext = os.extsep + 'png'
		d = os.path.join (parent.root, 'hard')
		if os.path.exists (d):
			for t in os.listdir (d):
				if not t.endswith (ext):
					continue
				base = t[:-len (ext)]
				f = os.path.join (d, t)
				self.hard[base] = (f, 0, os.stat (f).st_size)
		d = os.path.join (parent.root, 'tile')
		if os.path.exists (d):
			for t in os.listdir (d):
				h = '-hard' + ext
				if not t.endswith (h):
					continue
				base = t[:-len (h)]
				nice_assert (re.match ('^\d+$', base), 'tile hardness must have a numeric filename with -hard appended')
				f = os.path.join (d, t)
				hardfile = (f, 0, os.stat (f).st_size)
				n = int (base)
				t = os.path.join (d, base + ext)
				if os.path.exists (t):
					self.tile[n] = ((t, 0, os.stat (t).st_size), hardfile, 3)
				else:
					self.tile[n] = (tilefiles[n - 1], hardfile, 2)
		ext = os.extsep + 'bmp'
		for n in range (1, 41):
			if n not in self.tile:
				t = os.path.join (d, str (n) + ext)
				if os.path.exists (t):
					tilefile = ((t, 0, os.stat (t).st_size), 1)
				else:
					tilefile = (tilefiles[n - 1], 0)
				hardfile = os.path.join (cachedir, 'hard-%02d' % n + os.extsep + 'png')
				self.tile[n] = (tilefile[0], (hardfile, 0, os.stat (hardfile).st_size), tilefile[1])
	def find_hard (self, hard, x, y, bmp, tx, ty):
		if hard != '':
			nice_assert (hard in self.hard, 'reference to undefined hardness screen %s' % hard)
			ret = self.hardmap[hard][y][x]
			if ret != self.tilemap[bmp][ty][tx]:
				return ret
		return 0
	def save (self):
		hfiles = []
		for n in self.parent.world.room:
			h = self.parent.world.room[n].hard
			if h:
				nice_assert (h in self.hard, "room %d references hardness %s which isn't defined" % (n, h))
				hfiles += (h,)
		for h in self.hard:
			nice_assert (h in hfiles, 'not saving unused hardness %s' % h)
		if len (hfiles) > 0:
			d = os.path.join (self.parent.root, 'hard')
			os.mkdir (d)
			for h in hfiles:
				Image.open (filepart (*self.hard[h])).save (os.path.join (d, h + os.extsep + 'png'))
		# Check if any tiles need to be written.
		for i in self.tile:
			if self.tile[i] != 0:
				break
		else:
			return
		d = os.path.join (self.parent.root, 'tile')
		os.mkdir (d)
		for n in self.tile:
			if self.tile[n][2] == 1 or self.tile[n][2] == 3:
				convert_image (Image.open (filepart (*self.tile[n][0]))).save (os.path.join (d, '%02d' % n + os.extsep + 'png'))
			if self.tile[n][2] == 2 or self.tile[n][2] == 3:
				convert_image (Image.open (filepart (*self.tile[n][1]))).save (os.path.join (d, '%02d-hard' % n + os.extsep + 'png'))
	def rename (self, old, new):
		for i in self.hard:
			if self.hard[i][0].startswith (old):
				self.hard[i] = (new + self.hard[i][0][len (old):], self.hard[i][1], self.hard[i][2])
		for i in self.tile:
			if self.tile[i][0][0].startswith (old):
				self.tile[i] = ((new + self.tile[i][0][0][len (old):], self.tile[i][0][1], self.tile[i][0][2]), self.tile[i][1], self.tile[i][2])
			if self.tile[i][1][0].startswith (old):
				self.tile[i] = (self.tile[i][0], (new + self.tile[i][1][0][len (old):], self.tile[i][1][1], self.tile[i][1][2]), self.tile[i][2])
	def write_hard (self, image, h):
		'''Write hardness of all tiles in a given screen to hard.dat (opened as h). Return map of indices used.'''
		ret = [None] * 8
		for y in range (8):
			ret[y] = [None] * 12
			for x in range (12):
				if image.size[0] < (x + 1) * 50 or image.size[1] < (y + 1) * 50:
					# Don't try to read out of bounds.
					continue
				# Get the tile.
				tile = image.crop ((x * 50, y * 50, (x + 1) * 50, (y + 1) * 50))
				s = tile.tostring ()
				try:
					# Check if it's already in the file.
					m = self.hmap.index (s)
				except ValueError:
					# Not in map yet; add new tile to file and map.
					m = len (self.hmap)
					# Note that x and y are reversed. Why? Because Seth liked it that way...
					for tx in range (50):
						for ty in range (50):
							p = tile.getpixel ((tx, ty))
							if p[2] < 150:
								h.write ('\0')
							elif p[1] >= 150:
								h.write ('\1')
							else:
								h.write ('\2')
						h.write ('\0')	# junk
					h.write ('\0' * 58)	# junk
					self.hmap += (s,)
				ret[y][x] = m
		return ret
	def build (self, root):
		# Write tiles/*
		# Write hard.dat
		for i in self.tile:
			nice_assert (1 <= int (i) <= 41, 'invalid tile number %s for building dmod' % i)
		d = os.path.join (root, 'tiles')
		if not os.path.exists (d):
			os.mkdir (d)
		h = open (os.path.join (root, 'hard.dat'), "wb")
		# TODO: fill first hardness tile with junk.
		self.hmap = []
		self.hardmap = {}
		self.tilemap = [None] * 41
		for t in self.hard:
			# Write hardness for custom hard screens.
			self.hardmap[t] = self.write_hard (Image.open (filepart (*self.hard[t])), h)
		for n in range (1, 41):
			if self.tile[n][2] == 1 or self.tile[n][2] == 3:
				# Write custom tile screens.
				convert_image (Image.open (filepart (*self.tile[n][0]))).save (os.path.join (d, str (t) + os.extsep + 'bmp'))
			# Write hardness for standard tiles.
			self.tilemap[n] = self.write_hard (Image.open (filepart (*self.tile[n][1])), h)
		nice_assert (len (self.hmap) <= 800, 'More than 800 hardness tiles defined (%d)' % len (self.hmap))
		h.write ('\0' * (51 * 51 + 1 + 6) * (800 - len (self.hmap)))
		# Write hardness index for tile screens.
		for t in range (1, 41):
			m = self.tilemap[t]
			for y in range (8):
				for x in range (12):
					if m[y][x] != None:
						h.write (make_lsb (m[y][x], 4))
					else:
						# fill it with junk.
						h.write (make_lsb (0, 4))
			# Fill up with junk.
			h.write ('\0' * 32 * 4)
		# Fill the rest with junk.
		h.write ('\0' * (8000 - len (self.tile) * 8 * 12 * 4))
	def get_file (self, num):
		if num not in self.tile:
			return None
		return self.tile[num][0] + (None,)
	def get_hard_file (self, name):
		if type (name) == int:
			if name not in self.tile:
				return None
			return self.tile[name][1] + ((0, 0, 0),)
		else:
			if name not in self.hard:
				return None
			return self.hard[name] + ((0, 0, 0),)

# A sequence has members:
#	frames, list with members:
#		position	Hotspot position.
#		hardbox		Hardbox: left, top, right, bottom.
#		boundingbox	Bounding box: left, top, right, bottom.
#		delay		Delay value for this frame.
#		source		For copied frames, source; None otherwise.
#		cache		Tuple of filename, offset, length of location of file
#	boundingbox	Bounding box: left, top, right, bottom.
#	delay		default delay.
#	hardbox		default hardbox
#	position	default position
#	filepath	name for use in dink.ini
#	repeat		bool, whether the sequence is set for repeating
#	special		int, special frame
#	now		bool, whether to load now
#	code		int
#	preload		string, name of sequence to preload into this code
#	type		normal, notanim, black, or leftalign
class Seq:
	def __init__ (self, parent):
		"""Load all sequence and collection declarations from dink.ini, seq-names.txt (both internal) and seq/info.txt"""
		# General setup
		self.parent = parent
		self.seq = sequences
		self.collection = collections
		self.current_collection = None
		if self.parent.root == None:
			return
		d = os.path.join (parent.root, "seq")
		# Read info specific to this dmod.
		global filename
		filename = os.path.join (d, 'info' + os.extsep + 'txt')
		if not os.path.exists (filename):
			return
		infofile = open (filename)
		while True:
			info = readlines (infofile)
			if info == {}:
				break
			if 'collection' in info:
				# The next blocks with a direction are a collection.
				info, self.current_collection = get (info, "collection")
				nice_assert (info == {}, 'unused data in %s' % infofile)
				if self.current_collection not in self.collection:
					self.collection[self.current_collection] = {code: -1}
				continue
			elif 'append' in info:
				# This block is about a sequence which was declared in dink.ini.
				self.current_collection = None
				info, base = get (info, 'append')
				nice_assert (base in self.seq, 'append to undefined sequence %s' % base)
			else:
				if 'name' in info:
					# This block defines a new sequence.
					self.current_collection = None
					info, base = get (info, 'name')
					nice_assert (base not in self.seq, 'sequence %s already exists' % base)
					self.seq[base] = dinkconfig.Sequence ()
					is_new = True
				else:
					# This block is part of a collection.
					nice_assert (self.current_collection != None, 'collection definition required')
					base = None
					self.seq[None] = dinkconfig.Sequence ()
					info, self.direction = get (info, 'direction', int)
					nice_assert (self.direction >= 1 and self.direction <= 9 and self.direction != 5, 'invalid direction %d' % self.direction)
					info, is_new = get (info, 'new', True)
				if is_new:
					self.seq[base].code = -1
					self.seq[base].frames = []
					self.seq[base].repeat = False
					if base == None:
						name = '%s-%d' % (self.current_collection, self.seq[None].direction)
					else:
						name = base
					self.seq[base].filepath = 'graphics\\custom\\%s-' % name
					self.seq[base].type = 'normal'
					self.seq[base].special = None
					self.seq[base].preload = ''
					self.seq[base].delay = 1
					self.seq[base].hardbox = (0, 0, 0, 0)
					self.seq[base].position = (0, 0)
					self.seq[base].now = False
				else:
					# The collection part should be changed. Remove it now, reinsert it at the end.
					self.seq[base] = self.collections[self.current_collection].seq[self.seq[base].direction]
					del self.collections[self.current_collection].seq[self.seq[base].direction]
			info, self.seq[base].repeat = get (info, 'repeat', self.seq[base].repeat)
			info, self.seq[base].special = get (info, 'special', self.seq[base].special)
			info, self.seq[base].now = get (info, 'load-now', self.seq[base].now)
			info, self.seq[base].preload = get (info, 'preload', self.seq[base].preload)
			info, self.seq[base].type = get (info, 'type', self.seq[base].type)
			nice_assert (self.seq[base].type in ('normal', 'black', 'leftalign', 'notanim'), 'invalid special type %s' % self.seq[base].type)
			info, num = get (info, 'frames', len (self.seq[base].frames))
			if len (self.seq[base].frames) < num:
				self.seq[base].frames += [None] * (num - len (self.seq[base].frames))
			else:
				self.seq[base].frames = self.seq[base].frames[:num]
			for f in range (num):
				info, seq = get (info, 'seq-%d', '')
				if seq != '':
					if self.seq[base].frames[f] == None:
						self.seq[base].frames[f] = dinkconfig.Frame ()
					info, frame = get (info, 'frame-%d', int)
					self.seq[base].frames[f].source = (seq, frame)
				else:
					nice_assert (self.seq[base].frames[f] != None, 'frame %d of sequence %s not defined' % (f, base))
				# TODO: fill frame members.
			info, box = get (info, 'hardbox', '')
			if box != '':
				box = [int (x) for x in box.split ()]
				nice_assert (len (box) == 4, 'hardbox must have 4 members')
				self.seq[base].hardbox = box
				for f in range (1, len (self.seq[base].frames)):
					self.seq[base].frames[f].hardbox = box
			info, delay = get (info, 'delay', 0)
			if delay > 0:
				self.seq[base].delay = delay
				for f in range (1, len (self.seq[base].frames)):
					self.seq[base].frames[f].delay = delay
			nice_assert (info == {}, 'unused data in %s' % infofile)
			if self.current_collection != None:
				nice_assert (base == None, 'cannot define name (%s) for collection member (%s)' % (base, self.current_collection))
				nice_assert (self.direction not in self.collection[self.current_collection], 'duplicate definition of direction %d for collection %s' % (self.direction, self.current_collection))
				self.collection[self.current_collection].seq[self.direction] = self.seq[base]
				del self.seq[base]
		# Give codes to all unassigned collections and sequences.
		nextseq = 1
		for s in self.seq:
			if self.seq[s].code == -1:
				while nextseq in codes:
					nextseq += 1
				self.seq[s].code = nextseq
				codes += (nextseq,)
				nextseq += 1
	def get_dir_seq (self, collection, dir):
		c = self.find_collection (collection)
		order = {	1: (1, 4, 2, 9),
				2: (2, 3, 1, 8),
				3: (3, 6, 2, 7),
				4: (4, 1, 7, 6),
				6: (6, 3, 9, 4),
				7: (7, 4, 8, 3),
				8: (8, 7, 9, 2),
				9: (9, 6, 8, 1)
			}
		for option in order[dir]:
			if option in c:
				return c[option]
		# There's nothing usable. Get whatever exists.
		return c[[x for x in c if type (x) == int][0]]
	def find_seq (self, name):
		if not name:
			return None
		if type (name) == int:
			for i in self.seq:
				if self.seq[i].code == name:
					return self.seq[i]
			for c in self.collection:
				for i in self.collection[c]:
					if i not in (1,2,3,4,6,7,8,9):
						continue
					if self.collection[c][i].code == name:
						return self.collection[c][i]
			print (name)
			raise AssertionError ('undefined numerical code for find_seq')
		elif type (name) == str:
			parts = name.split ()
			if len (parts) == 1:
				if parts[0] not in self.seq:
					return None
				return self.seq[parts[0]]
			else:
				if len (parts) != 2 or parts[0] not in self.collection or int (parts[1]) not in self.collection[parts[0]]:
					return None
				return self.collection[parts[0]][int (parts[1])]
		else:
			if name[0] not in self.collection or int (name[1]) not in self.collection[name[0]]:
				return None
			return self.collection[name[0]][int (name[1])]
	def find_collection (self, name):
		if name not in self.collection:
			return None
		return self.collection[name]
	def collection_code (self, name):
		if type (name) == str and name.startswith ('*'):
			seq = self.find_seq (name[1:])
			if seq == None:
				return -1
			return seq.code
		coll = self.find_collection (name)
		if coll == None:
			return -1
		return coll['code']
	def save (self):
		if True:	# TODO: This should be a check if anything is added to the defaults.
			return
		d = os.path.join (self.parent.root, 'seq')
		os.mkdir (d)
		f = open (os.path.join (d, 'info' + os.extsep + 'txt'), 'w')
		# TODO
	def build_seq (self, ini, seq):
		if seq.preload:
			ini.write ('// Preload\r\n')
			ini.write ('load_sequence_now %s %d\r\n' % (seq.preload, seq.code))
		if seq.now:
			now = '_now'
		else:
			now = ''
		if seq.type == 'normal':
			if seq.position == None:
				if seq.delay != None:
					ini.write ('load_sequence%s %s %d %d\r\n' % (now, seq.filepath, seq.code, seq.delay))
				else:
					ini.write ('load_sequence%s %s %d\r\n' % (now, seq.filepath, seq.code))
			else:
				if seq.delay != None:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d %d\r\n' % (now, seq.filepath, seq.code, seq.delay, seq.position[0], seq.position[1], seq.hardbox[0], seq.hardbox[1], seq.hardbox[2], seq.hardbox[3]))
				else:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d\r\n' % (now, seq.filepath, seq.code, seq.position[0], seq.position[1], seq.hardbox[0], seq.hardbox[1], seq.hardbox[2], seq.hardbox[3]))
		else:
			ini.write ('load_sequence%s %s %d %s\r\n' % (now, seq.filepath, seq.code, seq.type.upper ()))
		for f in range (1, len (seq.frames)):
			# TODO: save images.
			if seq.frames[f].source != None:
				ini.write ('set_frame_frame %d %d %d %d\r\n' % (seq.code, f, self.find_seq (seq.frames[f].source[0]).code, seq.frames[f].source[1]))
			if (len (seq.frames[f].hardbox) == 4 and seq.frames[f].hardbox != seq.hardbox) or (len (seq.frames[f].position) == 2 and seq.frames[f].position != seq.position):
				ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\r\n' % (seq.code, f, seq.frames[f].position[0], seq.frames[f].position[1], seq.frames[f].hardbox[0], seq.frames[f].hardbox[1], seq.frames[f].hardbox[2], seq.frames[f].hardbox[3]))
			if seq.frames[f].source != None or seq.frames[f].delay != seq.delay:
				ini.write ('set_frame_delay %d %d %d\r\n' % (seq.code, f, int (seq.frames[f].delay)))
			if seq.special == f:
				ini.write ('set_frame_special %d %d 1\r\n' % (seq.code, f))
		if seq.repeat:
			ini.write ('set_frame_frame %d %d -1\r\n' % (seq.code, len (seq.frames)))
	def build (self, root):
		# Write graphics/*
		# Write dink.ini
		d = os.path.join (root, 'graphics')
		if not os.path.exists (d):
			os.mkdir (d)
		ini = open (os.path.join (root, 'dink' + os.extsep + 'ini'), 'w')
		for c in self.collection:
			for s in self.collection[c]:
				if s not in (1,2,3,4,6,7,8,9):
					continue
				self.build_seq (ini, self.collection[c][s])
		for g in self.seq:
			self.build_seq (ini, self.seq[g])
	def get_file (self, seq, frame):
		return seq.frames[frame].cache + ((0, 0, 0) if seq.type == 'black' else (255, 255, 255),)

class Sound:
	def __init__ (self, parent):
		global filename
		self.parent = parent
		self.sound = {}
		self.music = {}
		if self.parent.root == None:
			return
		d = os.path.join (parent.root, "sound")
		if os.path.exists (d):
			ext = os.extsep + 'wav'
			other = []
			codes = []
			for s in os.listdir (d):
				if not s.endswith (ext):
					continue
				filename = os.path.join (d, s)
				data = (filename, 0, os.stat (filename).st_size)
				r = re.match ('(\d+)-', s)
				if not r:
					other += ((s[:-len (ext)], data),)
				else:
					code = int (r.group (1))
					self.sound[s[len (r.group (0)):]] = (code, data)
					nice_assert (code not in codes, 'duplicate definition of sound %d' % code)
					codes += (code,)
			i = 1
			for s in other:
				while i in codes:
					i += 1
				self.sound[s[0]] = (i, s[1])
				i += 1
		d = os.path.join (parent.root, "music")
		if os.path.exists (d):
			code = 1
			ext = os.extsep + 'mid'
			for s in os.listdir (d):
				if not s.endswith (ext):
					continue
				filename = os.path.join (d, s)
				self.music[s[:-len (ext)]] = (code, (filename, 0, os.stat (filename).st_size))
				code += 1
	def find_sound (self, name):
		"""Find wav file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		return self.sound[name][0]
	def find_music (self, name):
		"""Find midi file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		nice_assert (name in self.music, 'reference to undefined music %s' % name)
		return self.music[name][0]
	def save (self):
		if len (self.sound) > 0:
			d = os.path.join (self.parent.root, "sound")
			os.mkdir (d)
			for i in self.sound:
				data = filepart (*self.sound[i][1]).read ()
				open (os.path.join (d, '%s-%d' % (i, self.sound[i][0]) + os.extsep + 'wav'), 'w').write (data)
		if len (self.music) > 0:
			d = os.path.join (self.parent.root, "music")
			os.mkdir (d)
			for i in self.music:
				data = filepart (*self.music[i][1]).read ()
				open (os.path.join (d, i + os.extsep + 'mid'), 'w').write (data)
	def rename (self, old, new):
		for i in self.sound:
			if self.sound[i][1][0].startswith (old):
				self.sound[i] = (self.sound[i][0], (new + self.sound[i][1][len (old):], self.sound[i][1][1], self.sound[i][1][2]))
		for i in self.music:
			if self.music[i][1][0].startswith (old):
				self.music[i] = (self.music[i][0], (new + self.music[i][1][len (old):], self.music[i][1][1], self.music[i][1][2]))
	def build (self, root):
		# Write sound/*
		dst = os.path.join (root, 'sound')
		if not os.path.exists (dst):
			os.mkdir (dst)
		src = os.path.join (self.parent.root, 'sound')
		for s in self.sound:
			if self.sound[s][1] == '':
				continue
			open (os.join (dst, s + os.extsep + 'wav'), 'w').write (self.sound[s][1])
		for s in self.music:
			if self.music[s][1] == '':
				continue
			open (os.join (dst, str (self.music[s][0]) + os.extsep + 'mid'), 'w').write (self.music[s][1])

class Script:
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		if self.parent.root == None:
			self.title_music = ''
			self.title_color = 0
			self.title_bg = ''
			self.start_map = 400
			self.start_x = 320
			self.start_y = 200
			self.title_pointer_seq = 'special'
			self.title_pointer_frame = 8
			self.title_script = ''
			self.intro_script = ''
			self.start_script = ''
			self.title_sprite = []
			self.title_button = []
			return
		d = os.path.join (parent.root, "script")
		for s in os.listdir (d):
			ext = os.extsep + 'c'
			if not s.endswith (ext):
				continue
			base = s[:-len (ext)]
			nice_assert (base not in self.data, 'duplicate definition of script %s' % base)
			self.data[base] = open (os.path.join (d, s)).read ()
		global filename
		filename = os.path.join (parent.root, "title" + os.extsep + "txt")
		f = open (filename)
		info = readlines (f)
		info, self.title_music = get (info, 'music', '')
		info, self.title_color = get (info, 'color', 0)
		info, self.title_bg = get (info, 'background', '')
		# These settings belong to Image, but are in the title config file.
		info, self.parent.image.preview = get (info, 'preview', '')
		info, self.parent.image.splash = get (info, 'splash', '')
		info, s = get (info, 'start')
		self.start_map, self.start_x, self.start_y = [int (x) for x in s.split ()]
		info, p = get (info, 'pointer', 'special 8')
		p = p.split ()
		self.title_pointer_seq, self.title_pointer_frame = p[0], int (p[1])
		info, self.title_script = get (info, 'title-script', '')
		info, self.intro_script = get (info, 'intro-script', '')
		info, self.start_script = get (info, 'start-script', '')
		info, n = get (info, 'sprites', 0)
		self.title_sprite = []
		for s in range (n):
			info, spr = get (info, 'sprite-%d' % (s + 1))
			spr = spr.split ()
			if len (spr) == 4:
				spr += ('repeat',)
			if len (spr) == 5:
				spr += ('',)
			nice_assert (len (spr) == 6, 'sprite-* must have 4, 5 or 6 arguments (%d given)' % len (spr))
			self.title_sprite += ((spr[0], int (spr[1]), int (spr[2]), int (spr[3]), spr[4], spr[5]),)
		info, n = get (info, 'buttons', int)
		for s in range (n):
			info, b = get (info, 'button-%d' % (s + 1))
			b = b.split ()
			nice_assert (len (b) == 5, 'button-* must have 5 arguments (%d given)' % len (b))
			self.title_sprite += ((b[0], int (b[1]), int (b[2]), int (b[3]), 'button', b[4]),)
		nice_assert (info == {}, 'unused data in title definition')
	def save (self):
		d = os.path.join (self.parent.root, "script")
		os.mkdir (d)
		for s in self.data:
			open (os.path.join (d, s + os.extsep + 'c'), 'w').write (self.data[s])
		f = open (os.path.join (self.parent.root, "title" + os.extsep + "txt"), 'w')
		put (f, 'music', self.title_music, '')
		put (f, 'color', self.title_color, 0)
		put (f, 'background', self.title_bg, '')
		put (f, 'start', '%d %d %d' % (self.start_map, self.start_x, self.start_y))
		put (f, 'pointer', '%s %d' % (self.title_pointer_seq, self.title_pointer_frame), 'special 8')
		# These settings belong to Image, but are in the title config file.
		put (f, 'preview', self.parent.image.preview, '')
		put (f, 'splash', self.parent.image.splash, '')
		buttons = [x for x in self.title_sprite if x[4] == 'button']
		sprites = [x for x in self.title_sprite if x[4] != 'button']
		put (f, 'buttons', len (buttons))
		for i in range (len (buttons)):
			buttons[i] = buttons[i][:4] + buttons[i][5:]
			put (f, 'button-%d' % (i + 1), ' '.join ([str (x) for x in buttons[i]]))
		put (f, 'sprites', len (sprites))
		for i in range (len (sprites)):
			if sprites[i][5] == '':
				sprites[i][5:] = []
				if sprites[i][4] == 'repeat':
					sprites[i][4:] = []
			put (f, 'sprite-%d' % (i + 1), ' '.join (sprites[i]))
		put (f, 'title-script', self.title_script, '')
		put (f, 'intro-script', self.intro_script, '')
		put (f, 'start-script', self.start_script, '')
	def find_functions (self, script, funcs):
		global max_args
		the_statics = []
		while True:
			t, script, isname = token (script)
			if t == None:
				break
			if t in ('static', 'extern'):
				is_static = t == 'static'
				t, script, isname = token (script)
				nice_assert (t == 'int', 'missing "int" for global variable declaration')
				name, script, isname = token (script)
				nice_assert (isname, 'missing variable name for global variable declaration')
				t, script, isname = token (script)
				nice_assert (t == ';', 'missing semicolon after global variable declaration');
				if is_static:
					nice_assert (name not in the_statics, "duplicate declaration of static variable")
					the_statics += (name,)
				continue
			nice_assert (t == 'int' or t == 'void', 'syntax error while searching for function (found %s): ' % t + script)
			rettype = t
			t, script, isname = token (script)
			nice_assert (isname, 'missing function name')
			name = t
			t, script, isname = token (script)
			nice_assert (t == '(', 'missing function name')
			# Read argument names
			args = []
			t, script, isname = token (script)
			while True:
				if t == ')':
					break
				nice_assert (t == 'int', 'missing argument type')
				t, script, isname = token (script)
				nice_assert (isname, 'missing argument name')
				args += (t,)
				t, script, isname = token (script)
				nice_assert (t in (')', ','), 'syntax error in argument list')
			t, script, isname = token (script)
			nice_assert (t == '{', 'missing function body')
			depth = 1
			while depth > 0:
				t, script, isname = token (script)
				if t == None:
					nice_assert (False, 'function %s is not finished at end of file' % name)
					break
				elif t == '{':
					depth += 1
				elif t == '}':
					depth -= 1
			funcs[name] = [rettype, args]
			if max_args < len (args):
				max_args = len (args)
		funcs[''] = the_statics
	def compile (self):
		'''Compile all scripts. Return a dictionary of files, each value in it is a dictionary of functions, each value is a sequence of statements.
		It also fills the functions dictionary, which has fnames as keys and a dict of name:(retval, args) as values, plus '':[statics].
		Statics is a list of names.'''
		global functions
		functions = {}
		ret = {}
		for name in self.data:
			ret[name.lower ()] = {}
			functions[name.lower ()] = {}
			self.find_functions (self.data[name], functions[name.lower ()])
		for name in self.data:
			for f in tokenize (self.data[name.lower ()], self.parent, name.lower ()):
				ret[name.lower ()][f[0]] = f[2]
		return ret
	def build (self, root):
		# Write Story/*
		global filename
		global functions
		functions = {}
		d = os.path.join (root, 'story')
		if not os.path.exists (d):
			os.mkdir (d)
		for name in self.data:
			functions[name.lower ()] = {}
			filename = name
			self.find_functions (self.data[name], functions[name.lower ()])
		for name in self.data:
			filename = name
			f = open (os.path.join (d, name + os.extsep + 'c'), 'w')
			f.write (preprocess (self.data[name], self.parent, name))
		# Write start.c
		s = open (os.path.join (d, 'start' + os.extsep + 'c'), 'w')
		s.write ('void main ()\r\n{\r\n')
		for n, snd in zip (range (len (self.parent.sound.sound)), self.parent.sound.sound):
			s.write ('\tload_sound ("%s.wav", %d);\r\n' % (snd, n))
		s.write ('\tset_dink_speed (3);\r\n\tsp_frame_delay (1,0);\r\n')
		if self.title_bg != '':
			s.write ('\tcopy_bmp_to_screen ("%s");\r\n' % self.title_bg)
		else:
			s.write ('\tfill_screen (%d);\r\n' % self.title_color)
		s.write ('''\
	load_sound("QUACK.WAV", 1);\r
	load_sound("PIG1.WAV", 2);\r
	load_sound("PIG2.WAV", 3);\r
	load_sound("PIG3.WAV", 4);\r
	load_sound("PIG4.WAV", 5);\r
	load_sound("BURN.WAV", 6);\r
	load_sound("OPEN.WAV", 7);\r
	load_sound("SWING.WAV", 8);\r
	load_sound("PUNCH.WAV", 9);\r
	load_sound("SWORD2.WAV", 10);\r
	load_sound("SELECT.WAV", 11);\r
	load_sound("WSCREAM.WAV", 12);\r
	load_sound("PICKER.WAV", 13);\r
	load_sound("GOLD.WAV", 14);\r
	load_sound("GRUNT1.WAV", 15);\r
	load_sound("GRUNT2.WAV", 16);\r
	load_sound("SEL1.WAV", 17);\r
	load_sound("ESCAPE.WAV", 18);\r
	load_sound("NONO.WAV", 19);\r
	load_sound("SEL2.WAV", 20);\r
	load_sound("SEL3.WAV", 21);\r
	load_sound("HIGH2.WAV", 22);\r
	load_sound("FIRE.WAV", 23);\r
	load_sound("SPELL1.WAV", 24);\r
	load_sound("CAVEENT.WAV", 25);\r
	load_sound("SNARL1.WAV", 26);\r
	load_sound("SNARL2.WAV", 27);\r
	load_sound("SNARL3.WAV", 28);\r
	load_sound("HURT1.WAV", 29);\r
	load_sound("HURT2.WAV", 30);\r
	load_sound("ATTACK1.WAV", 31);\r
	load_sound("CAVEENT.WAV", 32);\r
	load_sound("LEVEL.WAV", 33);\r
	load_sound("SAVE.WAV", 34);\r
	load_sound("SPLASH.WAV", 35);\r
	load_sound("SWORD1.WAV", 36);\r
	load_sound("BHIT.WAV", 37);\r
	load_sound("SQUISH.WAV", 38);\r
	load_sound("STAIRS.WAV", 39);\r
	load_sound("STEPS.WAV", 40);\r
	load_sound("ARROW.WAV", 41);\r
	load_sound("FLYBY.WAV", 42);\r
	load_sound("SECRET.WAV", 43);\r
	load_sound("BOW1.WAV", 44);\r
	load_sound("KNOCK.WAV", 45);\r
	load_sound("DRAG1.WAV", 46);\r
	load_sound("DRAG2.WAV", 47);\r
	load_sound("AXE.WAV", 48);\r
	load_sound("BIRD1.WAV", 49);\r
	sp_seq (1, 0);\r
	sp_brain (1, 13);\r
	sp_pseq (1, %d);\r
	sp_pframe (1, %d);\r
	sp_que (1, 20000);\r
	sp_noclip (1, 1);\r
	int &crap;\r
''' % (self.parent.seq.find_seq (self.title_pointer_seq).code, self.title_pointer_frame))
		for t in self.title_sprite:
			s.write ('\t&crap = create_sprite (%d, %d, %d, %d, %d);\r\n' % (t[2], t[3], make_brain (t[4]), self.parent.seq.find_seq (t[0]).code, t[1]))
			if t[5] != '':
				s.write ('\tsp_script(&crap, "%s");\r\n' % t[5])
				s.write ('\tsp_touch_damage (&crap, -1);\r\n')
			s.write ('\tsp_noclip (&crap, 1);\r\n')
		if self.title_music != '':
			s.write ('\tplaymidi ("%s.mid");\r\n' % self.title_music)
		if self.title_script != '':
			s.write ('\tspawn ("%s");\r\n' % self.title_script)
		s.write ('\tkill_this_task ();\r\n}\r\n')
		# Write main.c
		s = open (os.path.join (d, 'main' + os.extsep + 'c'), 'w')
		s.write ('void main ()\r\n{\r\n')
		nice_assert (len (the_globals) + max_args <= 200, 'too many global variables (%d, max is 200)' % (len (the_globals) + max_args))
		for v in the_globals:
			s.write ('\tmake_global_int ("%s", %d);\r\n' % (mangle (v), the_globals[v]))
		for a in range (max_args):
			s.write ('\tmake_global_int ("&args%d", 0);\r\n' % a)
		s.write ('\tkill_this_task ();\r\n}\r\n')
		# Write start_game.c
		s = open (os.path.join (d, 'start_game' + os.extsep + 'c'), 'wb')
		s.write ('''\
void main ()\r
{\r
	script_attach (1000);\r
	wait (1);\r
	&player_map = %d;\r
	sp_x (1, %d);\r
	sp_y (1, %d);\r
	sp_base_walk (1, %d);\r
	sp_base_attack (1, %d);\r
	set_dink_speed (3);\r
	set_mode (2);\r
	reset_timer ();\r
	sp_dir (1, 4);\r
	sp_brain (1, %d);\r
	sp_que (1, 0);\r
	sp_noclip (1, 0);\r
%s	dink_can_walk_off_screen (0);\r
	&player_map = %d;\r
	sp_x (1, %d);\r
	sp_y (1, %d);\r
%s	load_screen ();\r
	draw_screen ();\r
	&update_status = 1;\r
	draw_status ();\r
	fade_up ();\r
	kill_this_task ();\r
}\r
''' % (self.start_map, self.start_x, self.start_y, self.parent.seq.collection_code ('walk'), self.parent.seq.collection_code ('hit'), make_brain ('dink'), ('\texternal ("' + self.intro_script + '", "main");\r\n' if self.intro_script != '' else ''), self.start_map, self.start_x, self.start_y, ('\texternal ("' + self.start_script + '", "main");\r\n' if self.start_script != '' else '')))

class Images:
	def __init__ (self, parent):
		self.parent = parent
		im = os.path.join (self.parent.root, 'image')
		self.images = {}
		if not os.path.exists (im):
			return
		for i in os.listdir (im):
			if i.endswith (os.extsep + 'png'):
				name = os.path.join (im, i)
				self.images[i[:-4]] = (os.path.join (im, i), 0, os.stat (name).st_size)
	def save (self):
		im = os.path.join (self.parent.root, 'image')
		if self.images != {}:
			os.mkdir (im)
			for i in self.images:
				convert_image (Image.open (filepart (*self.images[i]))).save (os.path.join (im, i + os.extsep + 'png'))
	def build (self, root):
		for i in self.images:
			if self.preview != i and self.splash != i:
				convert_image (Image.open (filepart (*self.images[i]))).save (os.path.join (root, 'graphics', i + os.extsep + 'bmp'))
		if self.preview != '':
			convert_image (Image.open (filepart (*self.images[self.preview]))).save (os.path.join (root, 'preview' + os.extsep + 'bmp'))
		if self.splash != '':
			convert_image (Image.open (filepart (*self.images[self.splash]))).save (os.path.join (root, 'tiles', 'splash' + os.extsep + 'bmp'))
	def get_file (self, name):
		return self.images[name] + (None,)
	def rename (self, old, new):
		for i in self.images:
			if self.images[i][0].startswith (old):
				self.images[i] = (new + self.images[i][0][len (old):], self.images[i][1], self.images[i][2])

class Dink:
	def __init__ (self, root):
		if root == None:
			self.root = None
		else:
			self.root = os.path.abspath (os.path.normpath (root))
		self.image = Images (self)
		self.tile = Tile (self)
		self.world = World (self)
		self.seq = Seq (self)
		self.sound = Sound (self)
		self.script = Script (self)
		if root == None:
			self.info = ''
			return
		global filename
		filename = os.path.join (self.root, 'info' + os.extsep + 'txt')
		self.info = open (filename).read ()
	def save (self, root = None):
		if root != None:
			self.root = os.path.abspath (os.path.normpath (root))
		backup = None
		if os.path.exists (self.root):
			d = os.path.dirname (self.root)
			b = os.path.basename (self.root)
			l = os.listdir (d)
			src = [x for x in l if x.startswith (b + '.') and re.match ('^\d+$', x[len (b) + 1:])]
			if src == []:
				backup = self.root + '.0'
			else:
				src.sort (key = lambda x: int (x[len (b) + 1:]))
				backup = self.root + ('.%d' % (int (src[-1][len (b) + 1:]) + 1))
			os.mkdir (backup)
			for f in os.listdir (self.root):
				if not f.startswith ('.'):
					os.rename (os.path.join (self.root, f), os.path.join (backup, f))
			self.rename (self.root, backup)
		else:
			os.mkdir (self.root)
		self.image.save ()
		self.tile.save ()
		self.world.save ()
		self.seq.save ()
		self.sound.save ()
		self.script.save ()
		open (os.path.join (self.root, 'info' + os.extsep + 'txt'), 'w').write (self.info)
		if backup != None:
			self.rename (backup, self.root)
	def rename (self, old, new):
		self.image.rename (old, new)
		self.tile.rename (old, new)
		self.sound.rename (old, new)
	def build (self, root):
		if not os.path.exists (root):
			os.mkdir (root)
		# Assign sprite codes
		self.world.set_codes (True)
		# Write tiles/*
		self.tile.build (root)
		# Write images.
		self.image.build (root)
		# Write dink.dat
		# Write hard.dat
		# Write map.dat
		self.world.build (root)
		# Write dink.ini
		# Write graphics/*
		self.seq.build (root)
		# Write sound/*
		self.sound.build (root)
		# Write story/* This must be last, because preprocess needs all kinds of things to be initialized.
		self.script.build (root)
		# Write the rest
		open (os.path.join (root, 'dmod' + os.extsep + 'diz'), 'w').write (self.info)
	def play (self, map = None, x = None, y = None):
		if y != None:
			tmp = self.script.start_map, self.script.start_x, self.script.start_y, self.script.title_script, self.script.intro_script
			self.script.start_map = map
			self.script.start_x = x
			self.script.start_y = y
			self.script.title_script = 'start_game'
			self.script.intro_script = ''
		builddir = tempfile.mkdtemp ()
		try:
			self.build (builddir)
			os.spawnl (os.P_WAIT, dinkconfig.dinkprog, dinkconfig.dinkprog, '-g', builddir, '-r', dinkconfig.dinkdir, '-w')
		finally:
			shutil.rmtree (builddir)
			if y != None:
				self.script.start_map, self.script.start_x, self.script.start_y, self.script.title_script, self.script.intro_script = tmp
