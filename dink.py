#!/usr/bin/env python
# vim: set fileencoding=utf-8 foldmethod=marker:
# {{{ Copyright header
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
# }}}

# {{{ Directory setup specification
#world
#	nnn-xx-yy.txt			script, tiles, hardness
#	nnn-xx-yy-sprite		sprites which are locked to this map
#		[0-9]			layer
#			name.txt	sprite info
#	sprite				sprites which are not locked to a map
#		[0-9]			layer
#			name.txt	sprite info
#tile
#	nn.png				tile map
#	nn-hard.png			hardness for tile map
#hard
#	name.png			hardness for map
#image
#	name.png			splash, map, or similar image
#seq
#	name-code
#		nn.png			frame
#		info.txt		delay settings, etc.
#collection
#	name-code
#		dir
#			nn.png		frame
#			info.txt	delay settings, etc.
#sound
#	name-code.wav			sound file
#music
#	name-code.mid			music file
#script
#	name.c				script to be preprocessed
#info.txt				info about this dmod
# }}}

# {{{ Imports
import sys
import os
import re
import Image
import tempfile
import shutil
import StringIO
import pickle
import glib
# }}}
# {{{ Error handling
error_message = ''
def error (message):
	global error_message
	msg = '%s: Error: %s\n' % (filename, message)
	sys.stderr.write (msg)
	error_message += msg

def nice_assert (test, message):
	if test:
		return True
	error (message)
	return False
# }}}
# {{{ Global variables and utility functions
cachedir = os.path.join (glib.get_user_cache_dir (), 'pydink')
filename = ''
read_cache = False

class Sequence:
	pass
class Frame:
	pass

def read_config ():
	config = {}
	for x in open (os.path.join (glib.get_user_config_dir (), 'pydink', 'config.txt')).readlines ():
		if x.strip () == '' or x.strip ().startswith ('#'):
			continue
		k, v = x.strip ().split (None, 1)
		config[k] = v
	return config

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
	f = open (name, 'rb')
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

brains = ['none', 'dink', 'headless', 'duck', 'pig', 'mark', 'repeat', 'play', 'text', 'monster', 'rook', 'missile', 'resize', 'pointer', 'button', 'shadow', 'person', 'flare']

colornames = '\x001234567890!@#$%'

def make_brain (name):
	if name in brains:
		return brains.index (name)
	try:
		ret = int (name)
	except:
		error ('unknown and non-numeric brain %s' % name)
		ret = 0
	if ret < len (brains):
		error ('accessing named brain %s by number (%d)' % (brains[ret], ret))
	return ret

predefined_statics = ['current_sprite']
predefined = ['savegameinfo']
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
		"missile_source": 0
	}
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
		nice_assert (r is not None, 'invalid line in input file: %s' % l)
		nice_assert (r.group (1) not in ret, 'duplicate definition of %s' % r.group (1))
		ret[r.group (1).strip ()] = r.group (2).strip ()
	return ret

def get (d, member, default = None):
	if member not in d:
		nice_assert (default is not None and default != int, 'member %s has no default, but is missing in file' % member)
		return d, default
	if default is None:
		ret = d[member]
	elif isinstance (default, bool):
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
	nice_assert (value is not None, "Writing %s without a value" % member)
	if value == default:
		return
	if isinstance (value, bool):
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
	if r is None:
		is_name = False
		r = re.match ('[0-9]+', s)
		nice_assert (r is not None, 'unrecognized token %s' % s.split ()[0])
	key = r.group (0)
	return key, s[len (key):].lstrip (), is_name

def push (ret, operators):
	args = operators[-1][1]
	r = ret[-args:]
	ret = ret[:-args]
	op = operators.pop ()[0]
	# Precompute constant expressions.
	if all ([x[0] == 'const' for x in r]):
		if len (r) == 1:
			ret += (('const', int (eval ('%s%d' % (op, r[0][1])))),)
		else:
			ret += (('const', int (eval ('%d %s %d' % (r[0][1], op, r[1][1])))),)
	else:
		ret += ([op, r],)
	return ret, operators

def pathsearch (dink, dirname):
	ret = []
	p = os.path.join (dink.root, dirname)
	if os.path.exists (p):
		ret.append (('', p))
	for d in dink.depends:
		p = os.path.join (dink.config['editdir'], d, dirname)
		if os.path.exists (p):
			ret.append ((d + '.', p))
	return ret
# }}}
# {{{ Global variables and functions for building dmod files
functions = {}
max_args = 0
current_tmp = 0
next_mangled = 0
mangled_names = {}

def mangle (name):
	nice_assert (name != 'missle_source', 'misspelling of missile_source must not be used.')
	if name in default_globals or name in predefined or name in predefined_statics:
		# Fix spelling mistake in original source (by inserting it in generated expressions).
		if name == 'missile_source':
			return '&missle_source'
		return '&' + name
	if not nice_assert (name in mangled_names, 'trying to mangle unknown name %s' % name):
		print 'known names:', mangled_names
		raise AssertionError ('yo!')
		return '<<broken>>'
	return '&m%d%s' % (mangled_names[name], name)

def newmangle (name):
	global next_mangled
	if name in default_globals or name in predefined or name in predefined_statics:
		return
	if nice_assert (name not in mangled_names, 'duplicate mangling request for %s' % name):
		mangled_names[name] = next_mangled
		next_mangled += 1

def clear_mangled (which):
	for name in which:
		if name in default_globals or name in predefined or name in predefined_statics:
			continue
		if not nice_assert (name in mangled_names, "trying to clear mangled %s, which isn't in mangled_names" % name):
			continue
		del mangled_names[name]

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
		a += (('const', -1),)
	nice_assert (name != 'sp_hard', 'use sp_nohard instead of sp_hard, to match its meaning')
	if name == 'start_game':
		# Start_game is a generated function (not internal) when a dmod is built.
		name = 'spawn'
		a = [('"', ['_start_game'])]
	elif name == 'load_game':
		# Set up everything for loading a game.
		tmp = current_tmp
		current_tmp = tmp + 1
		b, e = build_expr (dink, fname, a[0], indent, as_bool = False)
		return b + indent + 'int &tmp%d = game_exist(%s);\r\n' % (tmp, e) + indent + 'if (&tmp%d != 0)\r\n' % tmp + indent + '{\r\n' + indent + '\tstopmidi();\r\n' + indent + '\tstopcd();\r\n' + indent + '\tsp_brain(1, 1);\r\n' + indent + '\tsp_que(1, 0);\r\n' + indent + '\tsp_noclip(1, 0);\r\n' + indent + '\tset_mode(2);\r\n' + indent + '\twait(1);\r\n' + indent + '\tload_game(%s);\r\n' % e + indent + '}\r\n', ''
	elif name == 'add_item' or name == 'add_magic':
		s = dink.seq.find_seq (a[1][1][0])
		if not nice_assert (s is not None, 'undefined seq %s' % a[1][1][0]):
			return '', ''
		a[1] = ('const', dink.seq.find_seq (a[1][1][0]).code)
	elif name == 'create_sprite':
		a[2] = ('const', make_brain (a[2][1][0]))
		if a[3][0] == '"':
			s = dink.seq.find_seq (a[3][1][0])
			if not nice_assert (s is not None, 'invalid sequence in create_sprite: %s' % a[3][1][0]):
				return '', ''
			a[3] = ('const', s.code)
	elif name == 'get_rand_sprite_with_this_brain' or name == 'get_sprite_with_this_brain':
		a[0] = ('const', make_brain (a[0][1][0]))
	elif name == 'playmidi':
		a[0] = ('const', dink.sound.find_music (a[0][1][0]))
	elif name == 'playsound':
		a[0] = ('const', dink.sound.find_sound (a[0][1][0]))
	elif name == 'preload_seq':
		s = dink.seq.find_seq (a[0][1][0])
		if not nice_assert (s is not None, 'seq %s not found' % s):
			return '', ''
		a[0] = ('const', dink.seq.find_seq (a[0][1][0]).code)
	elif name == 'sp':
		nm = a[0][1][0]
		sprites = [s for s in dink.world.sprite if s.name == nm]
		if not nice_assert (len (sprites) == 1, 'referenced sprite %s not found' % nm):
			return '', ''
		sprite = sprites[0]
		# Sprite names used with sp () must be locked to their map, because the script doesn't know from which map it's called.
		if not nice_assert (sprite.map is not None, 'referenced sprite %s is not locked to a map' % nm):
			return '', ''
		a[0] = ('const', sprite.editcode)
	elif name == 'sp_base_attack' or name == 'sp_base_death' or name == 'sp_base_idle' or name == 'sp_base_walk':
		if a[1][0] == '"':
			a[1] = ('const', dink.seq.collection_code (a[1][1][0]))
	elif name == 'sp_brain':
		if a[1][0] == '"':
			a[1] = ('const', make_brain (a[1][1][0]))
	elif name == 'sp_sound':
		if a[1][0] == '"':
			a[1] = ('const', dink.sound.find_sound (a[1][1][0]))
	elif name == 'sp_seq' or name == 'sp_pseq':
		if a[1][0] == '"':
			if a[1][1][0] == '':
				a[1] = ('const', 0)
			else:
				s = dink.seq.find_seq (a[1][1][0])
				if not nice_assert (s is not None, 'sequence %s not found' % a[1][1][0]):
					a[1] = ('const', 0)
				else:
					a[1] = ('const', s.code)
	elif name == 'sp_nohard':
		name = 'sp_hard'
	bt = ''
	at = []
	for i in a:
		b, e = build_expr (dink, fname, i, indent, as_bool = False)
		bt += b
		at += (e,)
	if use_retval:
		t = current_tmp
		current_tmp += 1
		return bt + indent + 'int &tmp%d = ' % t + name + '(' + ', '.join (at) + ');\r\n', '&tmp%d' % t
	else:
		return bt + indent + name + '(' + ', '.join (at) + ');\r\n', ''

def read_args (dink, script, used, current_vars):
	args = []
	b = ''
	if script[0] == ')':
		t, script, isname = token (script)
	else:
		while True:
			if script[0] == '"':
				p = script.find ('"', 1)
				nice_assert (p >= 0, 'unterminated string')
				# encode variable references.
				s = script[1:p]
				pos = 0
				sp = ['']
				while True:
					pos = s.find ('&')
					if pos < 0:
						sp[-1] += s
						break
					sp[-1] += s[:pos]
					s = s[pos + 1:]
					e = s.find (';')
					if not nice_assert (e >= 0, 'incomplete reference in string %s' % s):
						break
					var = s[:e]
					s = s[e + 1:]
					if var == '':
						# empty variable is escape for & itself.
						sp[-1] += '&'
					else:
						# variable found: add it.
						sp += (var, '')
				args += (('"', sp),)
				script = script[p + 1:]
			else:
				script, a = tokenize_expr (dink, script, used, current_vars)
				args += (a,)
			t, script, isname = token (script)
			if t != ',':
				break
	nice_assert (t == ')', 'unterminated argument list')
	return script, args

def build_expr (dink, fname, expr, indent, invert = False, as_bool = None):
	assert as_bool in (False, True)
	global current_tmp
	eq = ('>', '<=', '>=', '<', '==', '!=')
	if expr[0] == 'const':
		if as_bool:
			if invert:
				return '', '%d == 0' % expr[1]
			else:
				return '', '%d != 0' % expr[1]
		else:
			if invert:
				tmp = current_tmp
				current_tmp = tmp + 1
				return indent + 'int &tmp%d;\r\n' % tmp + indent + 'if (%d == 0)\r\n' % expr[1] + indent + '{\r\n' + indent + '\t&tmp%d = 1;\r\n' % tmp + indent + '} else\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 0;\r\n' % tmp + indent + '}\r\n', '&tmp%d' % tmp
			else:
				return '', str (expr[1])
	elif expr[0] == '"':
		nice_assert (not as_bool and not invert, 'string (%s) cannot be inverted or used as boolean expression' % expr[0])
		ret = ''
		for i in range (0, len (expr[1]) - 1, 2):
			ret += expr[1][i] + '&' + mangle (expr[1][i + 1])
		return '', '"' + ret + expr[1][-1] + '"'
	elif expr[0] in ('local', 'static', 'global'):
		if as_bool:
			if invert:
				return '', '%s == 0' % mangle (expr[1])
			else:
				return '', '%s != 0' % mangle (expr[1])
		else:
			if invert:
				tmp = current_tmp
				current_tmp = tmp + 1
				return indent + 'int &tmp%d;' % tmp + indent + 'if (%s != 0)\r\n' % mangle (expr[1]) + indent + '{\r\n' + indent + '\t&tmp%d = 1;\r\n' % tmp + indent + '} else\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 0;\r\n' % tmp + indent + '}\r\n', '&tmp%d' % tmp
			else:
				return '', mangle (expr[1])
	elif expr[0] in eq:
		if invert:
			op = eq[eq.index (expr[0]) ^ 1]
		else:
			op = expr[0]
		b1, e1 = build_expr (dink, fname, expr[1][0], indent, as_bool = False)
		b2, e2 = build_expr (dink, fname, expr[1][1], indent, as_bool = False)
		e = e1 + ' ' + op + ' ' + e2
		if as_bool:
			return b1 + b2, e
		else:
			tmp = current_tmp
			current_tmp = tmp + 1
			return b1 + b2 + indent + 'int &tmp%d;\r\n' % tmp + indent + 'if (%s)\r\n' % e + indent + '{\r\n' + indent + '\t&tmp%d = 1;\r\n' % tmp + indent + '} else\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 0;\r\n' % tmp + indent + '}\r\n', '&tmp%d' % tmp
	elif expr[0] in ('+', '-', '*', '/'):
		if len (expr[1]) == 1:
			if invert:
				return build_expr (dink, fname, ['==', expr[1][0], 0], indent, as_bool = as_bool)
			return build_expr (dink, fname, [expr[0], 0, expr[1][0]], indent, as_bool = as_bool)
		else:
			if invert:
				return build_expr (dink, fname, ['==', expr, 0], indent, as_bool = as_bool)
			tmp = current_tmp
			b1, e1 = build_expr (dink, fname, expr[1][0], indent, as_bool = False)
			current_tmp = tmp + 1
			if e1 == '&tmp%d' % tmp:
				b = b1
			else:
				b = b1 + indent + 'int &tmp%d = ' % tmp + e1 + ';\r\n'
			b2, e2 = build_expr (dink, fname, expr[1][1], indent, as_bool = False)
			current_tmp = tmp + 1
			extra = '' if expr[0] in ('*', '/') else '='
			b += b2 + indent + '&tmp%d ' % tmp + expr[0] + extra + ' ' + e2 + ';\r\n'
			if as_bool:
				return b, '&tmp%d != 0' % tmp
			else:
				return b, '&tmp%d' % tmp
	elif expr[0] in ('&&', '||'):
		# Turn everything into &&.
		# a && b == a && b
		# a || b == !(!a && !b)
		# !(a && b) == !(a && b)
		# !(a || b) == !a && !b
		b1, e1 = build_expr (dink, fname, expr[1][0], indent, expr[0] == '||', as_bool = True)
		b2, e2 = build_expr (dink, fname, expr[1][1], indent + '\t', expr[0] == '||', as_bool = True)
		tmp = current_tmp
		current_tmp = tmp + 1
		if as_bool:
			b = b1 + indent + 'int &tmp%d = 0;\r\n' % tmp + indent + 'if (' + e1 + ')\r\n' + indent + '{\r\n'
			b += b2 + indent + '\tif (' + e2 + ')\r\n' + indent + '\t{\r\n' + indent + '\t\t&tmp%d = 1;\r\n' % tmp + indent + '\t}\r\n' + indent + '}\r\n'
			if invert ^ (expr[0] == '||'):
				return b, '&tmp%d == 0' % tmp
			else:
				return b, '&tmp%d != 0' % tmp
		else:
			if invert ^ (expr[0] == '||'):
				b = b1 + indent + 'int &tmp%d = 1;\r\n' % tmp + indent + 'if (' + e1 + ')\r\n' + indent + '{\r\n'
				b += b2 + indent + '\tif (' + e2 + ')\r\n' + indent + '\t{\r\n' + indent + '\t\t&tmp%d = 0;\r\n' % tmp + indent + '\t}\r\n' + indent + '}\r\n'
			else:
				b = b1 + indent + 'int &tmp%d = 0;\r\n' % tmp + indent + 'if (' + e1 + ')\r\n' + indent + '{\r\n'
				b += b2 + indent + '\tif (' + e2 + ')\r\n' + indent + '\t{\r\n' + indent + '\t\t&tmp%d = 1;\r\n' % tmp + indent + '\t}\r\n' + indent + '}\r\n'
			return b, '&tmp%d' % tmp
	elif expr[0] == '!':
		return build_expr (dink, fname, ['==', [('const', 0), expr[1][0]]], indent, invert, as_bool = as_bool)
	elif expr[0] == 'choice':
		tmp = current_tmp
		current_tmp += 1
		return build_choice (dink, fname, expr[1], expr[2], indent) + indent + 'int &tmp%d = &result;\r\n' % tmp, '&tmp%d' % tmp
	elif expr[0] == 'internal':	# internal function call
		b, e = build_internal_function (expr[1], expr[2], indent, dink, fname, True)
		if as_bool:
			tmp = current_tmp
			current_tmp = tmp + 1
			b += indent + 'int &tmp%d;\r\n' % tmp + indent + 'if (%s != 0)\r\n' % e + indent + '{\r\n' + indent + '\t&tmp%d = 1;\r\n' % tmp + indent + '} else\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 0;\r\n' % tmp + indent + '}\r\n'
			if invert:
				return b, '&tmp%d == 0' % tmp
			else:
				return b, '&tmp%d != 0' % tmp
		else:
			return b, e
	else:
		if not nice_assert (expr[0] == '()', 'unknown thing %s' % expr[0]):
			return '', ''
		if len (expr[1]) == 1:	# function call in same file
			tmp = current_tmp
			current_tmp = tmp + 1
			b = build_function (expr[1][0], expr[2], indent, dink, fname)
			if as_bool:
				b += indent + 'int &tmp%d;\r\n' % tmp + indent + 'if (&result != 0)\r\n' % e + indent + '{\r\n' + indent + '\t&tmp%d = 1;\r\n' % tmp + indent + '} else\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 0;\r\n' % tmp + indent + '}\r\n'
				if invert:
					return b, '&tmp%d == 0' % tmp
				else:
					return b, '&tmp%d != 0' % tmp
			else:
				return b + indent + 'int &tmp%d;\r\n' % tmp + indent + '&tmp%d = &result;\r\n' % tmp, '&tmp%d' % tmp
		else:				# remote function call
			tmp = current_tmp
			current_tmp = tmp + 1
			b = build_function (expr[1][1], expr[2], indent, dink, expr[1][0])
			if as_bool:
				b += indent + 'int &tmp%d;\r\n' % tmp + indent + 'if (&result != 0)\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 1;\r\n' % tmp + indent + '} else\r\n' + indent + '{\r\n' + indent + '\t&tmp%d = 0;\r\n' % tmp + indent + '}\r\n'
				if invert:
					return b, '&tmp%d == 0' % tmp
				else:
					return b, '&tmp%d != 0' % tmp
			else:
				return b + indent + 'int &tmp%d;\r\n' % tmp + indent + '&tmp%d = &result;\r\n' % tmp, '&tmp%d' % tmp

internal_functions = {
		'activate_bow': '',
		'add_exp': 'ii',
		'add_item': 'sqi',
		'add_magic': 'sqi',
		'arm_magic': '',
		'arm_weapon': '',
		'busy': 'i',
		'compare_sprite_script': 'is',
		'compare_weapon': 's',
		'copy_bmp_to_screen': 'b',
		'count_item': 's',
		'count_magic': 's',
		'create_sprite': 'ii*qi',
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
		'preload_seq': 'q',
		'push_active': 'i',
		'random': 'ii',
		'reset_timer': '',
		'restart_game': '',
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
		'show_bmp': 'bii',
		'sound_set_kill': 'i',
		'sound_set_survive': 'ii',
		'sound_set_vol': 'ii',
		'sp': 's',
		'sp_active': 'iI',
		'sp_attack_hit_sound': 'ii',
		'sp_attack_hit_sound_speed': 'ii',
		'sp_attack_wait': 'ii',
		'sp_base_attack': 'ic',
		'sp_base_death': 'ic',
		'sp_base_idle': 'ic',
		'sp_base_walk': 'ic',
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
		'sp_pseq': 'iQ',
		'sp_que': 'iI',
		'sp_range': 'iI',
		'sp_reverse': 'iI',
		'sp_script': 'is',
		'sp_seq': 'iQ',
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
		'seq_code': 'q',
		'brain_code': 's',
		'collection_code': 'c',
		'sound_code': 's',
		'music_code': 's'
		}

def make_direct (dink, name, args, used):
	# Check validity of name and arguments.
	nice_assert (name in internal_functions, 'use of undefined function %s' % name)
	ia = internal_functions[name]
	a = list (args)
	if len (a) < len (ia) and (ia.endswith ('I') or ia.endswith ('S') or ia.endswith ('Q')):
		a += ((None,),)
	if not nice_assert (len (a) == len (ia), 'incorrect number of arguments for %s (must be %d; is %d)' % (name, len (ia), len (a))):
		return None
	for i in range (len (ia)):
		if ia[i] in ('i', 'I'):
			if not nice_assert (a[i][0] != '"', 'argument %d of %s must not be a string' % (i, name)):
				return None
		elif ia[i] == 's':
			if not nice_assert (a[i][0] == '"', 'argument %d of %s must be a string' % (i, name)):
				return None
		elif ia[i] in ('*', 'S'):
			pass
		elif ia[i] == 'b':
			if not nice_assert (a[i][0] == '"', 'argument %d of %s must be a bitmap filename' % (i, name)):
				return None
		elif ia[i] == 'c':
			if used is not None and a[i][0] == '"' and a[i][1] != ['']:
				used[0].add (a[i][1][0])
		elif ia[i] in ('q', 'Q'):
			if a[i] is not None:
				if used is not None and a[i][0] == '"' and a[i][1] != ['']:
					used[1].add (a[i][1][0])
		else:
			raise AssertionError ('invalid character in internal_functions %s' % ia)
	# Find direct functions.
	if name == 'brain_code':
		return 'const', make_brain (args[0][1][0])
	elif name == 'seq_code':
		seq = dink.seq.find_seq (args[0][1][0])
		if not nice_assert (seq is not None, 'invalid sequence name %s' % args[0][1][0]):
			return None
		return 'const', seq.code
	elif name == 'collection_code':
		coll = dink.seq.find_collection (args[0][1][0])
		if not nice_assert (coll is not None, 'invalid collection name %s' % args[0][1][0]):
			return None
		return 'const', coll['code']
	elif name == 'sound_code':
		s = dink.sound.find_sound (args[0][1][0])
		if not nice_assert (s != 0, 'invalid sound name %s' % args[0][1][0]):
			return None
		return 'const', s
	elif name == 'music_code':
		m = dink.sound.find_music (args[0][1][0])
		if not nice_assert (s != 0, 'invalid music name %s' % args[0][1][0]):
			return None
		return 'const', m
	elif name == 'sp_code':
		nm = args[0][1][0]
		sprites = [s for s in dink.world.sprite if s.name == nm]
		if not nice_assert (len (sprites) == 1, "referenced sprite %s doesn't exist" % nm):
			return None
		if not nice_assert (sprites[0].map is not None, "referenced sprite %s is not locked to a map" % nm):
			return None
		if used is not None:
			# When looking for used sequences, editcodes are not initialized yet. This is no problem, because that part isn't used anyway.
			return 'const', 1
		if not nice_assert (hasattr (sprites[0], 'editcode'), 'sprite %s has no editcode' % nm):
			return None
		return 'const', sprites[0].editcode
	else:
		# Nothing special.
		return None

def choice_args (args):
	i = 0
	ret = []
	while i < len (args):
		if args[i][0] != '"':
			expr = args[i]
			i += 1
			nice_assert (args[i][0] == '"', 'Only one expression is allowed per choice option (got %s)' % str (args[i]))
		else:
			expr = None
		ret += ((expr, args[i]),)
		i += 1
	nice_assert (ret != [], 'A choice must have at least one option.')
	return ret

def tokenize_expr (parent, script, used, current_vars):
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
				nice_assert (len (ret) == 1, 'expression does not resolve to one value: %s' % repr (ret))
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
						if not nice_assert (name[0] in functions and name[1] in functions[name[0]], 'function %s not found in file %s' % (name[1], name[0])):
							print functions
						nice_assert (script.startswith ('('), 'external function %s.%s is not called' % (name[0], name[1]))
					if script.startswith ('('):
						# Read away the opening parenthesis.
						t, script, isname = token (script)
						script, args = read_args (parent, script, used, current_vars)
						if isinstance (name, str):
							if filename.lower () in functions and name in functions[filename.lower ()]:
								# local function.
								nice_assert (len (args) == len (functions[filename.lower ()][name][1]), 'incorrect number of arguments when calling %s (%d, needs %d)' % (name, len (args), len (functions[filename.lower ()][name][1])))
								ret += (['()', (filename.lower (), name), args],)
							else:
								# internal function.
								if name == 'choice':
									ret += (['choice', choice_args (args), choice_title[0]],)
									choice_title[:] = [None, False]
								else:
									direct = make_direct (parent, name, args, used)
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
					if t in current_vars[0]:
						ret += (('local', t),)
					elif t in predefined_statics or t in current_vars[1]:
						ret += (('static', t),)
					elif t in default_globals or t in predefined or t in current_vars[2]:
						ret += (('global', t),)
					else:
						error ('using undefined variable %s. locals: %s, statics: %s, globals: %s' % ((t,) + tuple ([str (x) for x in current_vars])))
				else:
					# numerical constant.
					ret += (('const', int (t)),)
				need_operator = True

def check_exists (current_vars, name):
	if name in predefined or name in default_globals or name in predefined_statics:
		return True
	return any ([name in x for x in current_vars])

def tokenize (script, dink, fname, used):
	'''Tokenize a script completely. Return a list of functions (name, (rettype, args), definition-statement).'''
	my_locals = set ()	# Local variables currently in scope.
	my_statics = set ()
	my_globals = set ()
	ret = []
	indent = []
	numlabels = 0
	while True:
		choice_title[1] = False
		t, script, isname = token (script)
		if not t:
			break
		if t in ('extern', 'static'):
			is_static = t == 'static'
			t, script, isname = token (script)
			if nice_assert (t == 'int', 'extern or static must be followed by int'):
				t, script, isname = token (script)
			nice_assert (isname, 'invalid argument for extern or static')
			name = t
			t, script, isname = token (script)
			nice_assert (t == ';', 'junk after extern')
			nice_assert (not check_exists ((my_locals, my_statics, my_globals), name), 'duplicate definition of static or global variable %s' % name)
			if not is_static:
				if name not in the_globals:
					the_globals[name] = 0
				my_globals.add (name)
			else:
				my_statics.add (name)
			continue
		if not nice_assert (t in ('void', 'int'), 'invalid token at top level; only extern, static, void or int allowed (not %s)' % t):
			continue
		t, script, isname = token (script)
		nice_assert (isname, 'function name required after top level void or int (not %s)' % t)
		name = t
		t, script, isname = token (script)
		nice_assert (t == '(', '(possibly empty) argument list required for function definition (not %s)' % t)
		while True:
			# find_functions parsed the arguments already.
			t, script, isname = token (script)
			if t == ')':
				break
		for i in functions[fname][name][1]:
			my_locals.add (i)
		t, script, isname = token (script)
		nice_assert (t == '{', 'function body not defined')
		script, s = tokenize_statement ('{ ' + script, dink, fname, name, used, (my_locals, my_statics, my_globals))
		ret += ((name, functions[fname][name], s),)
		my_locals.clear ()
	return ret

def tokenize_statement (script, dink, fname, own_name, used, current_vars):
	t, script, isname = token (script, False)
	nice_assert (t is not None, 'missing statement')
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
			script, s = tokenize_statement (t + ' ' + script, dink, fname, own_name, used, current_vars)
			statements += (s,)
	elif t == ';':
		ret = None
		need_semicolon = False
	elif t == 'return':
		if functions[fname][own_name][0] == 'int':
			script, e = tokenize_expr (dink, script, used, current_vars)
			ret = 'return', e
		else:
			ret = 'return', None
	elif t == 'break':
		ret = ('break',)
	elif t == 'continue':
		ret = ('continue',)
	elif t == 'while':
		t, script, isname = token (script)
		nice_assert (t == '(', 'parenthesis required after while')
		script, e = tokenize_expr (dink, script, used, current_vars)
		t, script, isname = token (script)
		nice_assert (t == ')', 'parenthesis for while not closed')
		script, s = tokenize_statement (script, dink, fname, own_name, used, current_vars)
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
			script, e = tokenize_expr (dink, script, used, current_vars)
			f1 = (a, n, e)
			nice_assert (check_exists (current_vars, n), 'use of undefined variable %s in for loop' % n)
		else:
			f1 = None
		t, script, isname = token (script)
		nice_assert (t == ';', 'two semicolons required in for argument')
		script, f2 = tokenize_expr (dink, script, used, current_vars)
		t, script, isname = token (script)
		nice_assert (t == ';', 'two semicolons required in for argument')
		if script[0] != ')':
			n, script, isname = token (script)
			nice_assert (isname, 'third for-expression must be empty or assignment (not %s)' % n)
			a, script, isname = token (script)
			nice_assert (a in ('=', '+=', '-=', '*=', '/='), 'third for-expression must be empty or assignment (not %s)' % a)
			script, e = tokenize_expr (dink, script, used, current_vars)
			nice_assert (check_exists (current_vars, n), 'use of undefined variable %s in for loop' % n)
			f3 = (a, n, e)
		else:
			f3 = None
		t, script, isname = token (script)
		nice_assert (t == ')', 'parenthesis for for not closed')
		script, s = tokenize_statement (script, dink, fname, own_name, used, current_vars)
		need_semicolon = False
		ret = 'for', f1, f2, f3, s
	elif t == 'if':
		t, script, isname = token (script)
		nice_assert (t == '(', 'parenthesis required after if')
		script, e = tokenize_expr (dink, script, used, current_vars)
		t, script, isname = token (script)
		nice_assert (t == ')', 'parenthesis not closed for if')
		script, s1 = tokenize_statement (script, dink, fname, own_name, used, current_vars)
		t, script, isname = token (script)
		if t == 'else':
			script, s2 = tokenize_statement (script, dink, fname, own_name, used, current_vars)
		else:
			script = t + ' ' + script
			s2 = None
		need_semicolon = False
		ret = 'if', e, s1, s2
	elif t == 'int':
		ret = []
		while True:
			t, script, isname = token (script)
			if not nice_assert (isname, 'local definition without name'):
				script = t + ' ' + script
				continue
			name = t
			if nice_assert (not check_exists (current_vars, name), 'duplicate definition of local variable %s' % name):
				current_vars[0].add (name)
			t, script, isname = token (script)
			if t == '=':
				script, e = tokenize_expr (dink, script, used, current_vars)
				t, script, isname = token (script)
			else:
				e = None
			ret.append ((name, e))
			if t != ',':
				script = t + ' ' + script
				break
		ret = 'int', ret
	else:
		nice_assert (isname, 'syntax error')
		name = t
		t, script, isname = token (script)
		if t in ['=', '+=', '-=', '*=', '/=']:
			nice_assert (check_exists (current_vars, name), 'use of undefined variable %s' % name)
			op = t
			script, e = tokenize_expr (dink, script, used, current_vars)
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
				script, args = read_args (dink, script, used, current_vars)
				nice_assert (len (args) >= 1 and len (args) <= 3 and args[0][0] == '"', 'invalid argument list for %s' % name)
				choice_title[0] = args
				ret = None
			elif name == 'choice':
				choices = []
				script, args = read_args (dink, script, used, current_vars)
				choices = choice_args (args)
				ret = 'choice', choice_args (args), choice_title[0]
				choice_title[:] = [None, False]
			else:
				script, args = read_args (dink, script, used, current_vars)
				if isinstance (name, str):
					if name in functions[fname]:
						nice_assert (len (args) == len (functions[fname][name][1]), 'incorrect number of arguments when calling %s (%d, needs %d)' % (name, len (args), len (functions[fname][name][1])))
						ret = '()', (fname, name), args
					else:
						direct = make_direct (dink, name, args, used)
						if direct is not None:
							ret = direct
						else:
							ret = 'internal', name, args
				else:
					if not nice_assert (name[0] in functions and name[1] in functions[name[0]], 'function %s not found in file %s' % (name[1], name[0])):
						print functions[name[0]]
					nice_assert (len (args) == len (functions[name[0]][name[1]][1]), 'incorrect number of arguments when calling %s.%s (%d, needs %d)' % (name[0], name[1], len (args), len (functions[name[0]][name[1]][1])))
					ret = '()', name, args
	nice_assert (choice_title[1] == False or choice_title[0] is None, 'unused choice_title')
	if need_semicolon:
		t, script, isname = token (script)
		if not nice_assert ((t == ';'), 'missing semicolon'):
			print token, script
	return script, ret

def preprocess (script, dink, fname):
	if script.split ('\n', 1)[0].strip () == '#no preprocessing':
		return data.split ('\n', 1)[1]
	global numlabels
	numlabels = 0
	fs = tokenize (script, dink, fname, used = None)
	my_statics, my_globals = functions[fname.lower ()]['']
	for i in my_statics:
		newmangle (i)
	if 'main' not in functions[fname.lower ()] and len (my_statics) > 0:
		fs.append (('main', ('void', ()), ('{', ())))
	ret = '\r\n'.join ([build_function_def (x, fname, dink, my_statics, my_globals) for x in fs])
	clear_mangled (my_statics)
	return ret

def build_function_def (data, fname, dink, my_statics, my_globals):
	'''Build a function definition.'''
	name, ra, impl = data
	ret = 'void %s (void)\r\n{\r\n' % name
	my_locals = set ()
	for a in range (len (ra[1])):
		newmangle (ra[1][a])
		my_locals.add (ra[1][a])
		ret += '\tint %s = &arg%d;\r\n' % (mangle (ra[1][a]), a)
	assert impl[0] == '{'
	if name == 'main':
		for i in my_statics:
			ret += '\tint %s;\n' % mangle (i)
		# It would be so much nicer if this could be generated in main.c, but that doesn't work.
		if fname == 'start':
			ret += '''\
	set_dink_speed (3);\r
	sp_frame_delay (1, 0);\r
	sp_seq (1, 0);\r
	sp_brain (1, %d);\r
	sp_pseq (1, %d);\r
	sp_pframe (1, 8);\r
	sp_que (1, 20000);\r
	sp_noclip (1, 1);\r
''' % (make_brain ('pointer'), dink.seq.find_seq ('special').code)
	for s in impl[1]:
		ret += build_statement (s, ra[0], '\t', fname, dink, None, None, (my_locals, my_statics, my_globals))
	clear_mangled (my_locals)
	return ret + '}\r\n'

def build_function (name, args, indent, dink, fname):
	'''Build a function call. Return (before, expression).'''
	global current_tmp
	if isinstance (name, str):
		f = functions[fname][name]
	else:
		f = functions[name[0]][name[1]]
	tb = ''
	old_current_tmp = current_tmp
	for i in range (len (f[1])):
		b, e = build_expr (dink, fname, args[i], indent, as_bool = False)
		tb += b + indent + '&arg%d = ' % i + e + ';\r\n'
		current_tmp = old_current_tmp
	if isinstance (name, str):
		return tb + indent + name + '();\r\n'
	else:
		return tb + indent + 'external("%s", "%s");\r\n' % name

def build_choice (dink, fname, choices, title, indent):
	# choices[i][0] = expr or None
	# choices[i][1] = Choice string
	# title = None or title (sequence of 1, 2 or 3 arguments)
	tb = ''
	ret = indent + 'choice_start()\r\n'
	if title is not None:
		if len (title) == 3:
			b, e = build_expr (dink, fname, title[2], as_bool = False)
			tb += b
			ret += indent + 'set_y %d\r\n' % e
		if len (title) >= 2:
			b, e = build_expr (dink, fname, title[1], as_bool = False)
			tb += b
			ret += indent + 'set_title_color %d\r\n' % e
		ret += indent + 'title_start()\r\n' + title[0] + indent + 'title_end()\r\n'
	for i in choices:
		ret += indent
		if i[0] is not None:
			b, e = build_expr (dink, fname, i[0], indent, as_bool = True)
			tb += b
			ret += '(%s) ' % e
		b, e = build_expr (dink, fname, i[1], indent, as_bool = False)
		tb += b
		ret += e + '\r\n'
	return tb + ret + indent + 'choice_end()\r\n'

def build_statement (data, retval, indent, fname, dink, continue_label, break_label, vars):
	global numlabels
	global current_tmp
	current_tmp = 0
	if data[0] == '{':
		ret = ''
		for s in data[1]:
			ret += build_statement (s, retval, indent + '\t', fname, dink, continue_label, break_label, vars)
		return ret
	elif data[0] == 'break':
		nice_assert (break_label is not None, 'break not inside loop')
		return indent + 'goto ' + break_label + ';\r\n'
	elif data[0] == 'continue':
		nice_assert (continue_label is not None, 'continue not inside loop')
		return indent + 'goto ' + continue_label + ';\r\n'
	elif data[0] == 'return':
		if data[1] is None:
			return indent + 'return;\r\n'
		else:
			b, e = build_expr (dink, fname, data[1], indent, as_bool = False)
			return b + indent + '&result = ' + e + ';\r\n' + indent + 'return;\r\n'
	elif data[0] == 'while':
		start = 'while%d' % numlabels
		end = 'endwhile%d' % numlabels
		numlabels += 1
		b, e = build_expr (dink, fname, data[1], indent, invert = True, as_bool = True)
		ret = start + ':\r\n'
		ret += b + indent + 'if (' + e + ')\r\n' + indent + '{\r\n' + indent + '\tgoto ' + end + ';\r\n' + indent + '}\r\n'
		ret += build_statement (data[2], retval, indent, fname, dink, start, end, vars)
		ret += indent + 'goto ' + start + ';\r\n' + end + ':\r\n'
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
		continueend = 'continuefor%d' % numlabels
		end = 'endfor%d' % numlabels
		numlabels += 1
		ret = ''
		if data[1] is not None:
			a, n, te = data[1]
			if a[0] in ('*', '/'):
				a = a[0]
			b, e = build_expr (dink, fname, te, indent, as_bool = False)
			ret += b + indent + mangle (n) + ' ' + a + ' ' + e + ';\r\n'
		ret += start + ':\r\n'
		b, e = build_expr (dink, fname, data[2], indent, invert = True, as_bool = True)
		ret += b + indent + 'if (' + e + ')\r\n' + indent + '{\r\n' + indent + '\tgoto ' + end + ';\r\n' + indent + '}\r\n'
		ret += build_statement (data[4], retval, indent, fname, dink, start, continueend, vars)
		ret += continueend + ':\r\n'
		if data[3] is not None:
			a, n, te = data[3]
			if a[0] in ('*', '/'):
				a = a[0]
			b, e = build_expr (dink, fname, te, indent, as_bool = False)
			ret += b + indent + mangle (n) + ' ' + a + ' ' + e + ';\r\n'
		ret += indent + 'goto ' + start + ';\r\n' + end + ':\r\n'
		return ret
	elif data[0] == 'if':
		ret = ''
		b, e = build_expr (dink, fname, data[1], indent, as_bool = True)
		ret += b + indent + 'if (' + e + ')\r\n' + indent + '{\r\n'
		ret += build_statement (data[2], retval, indent + '\t', fname, dink, continue_label, break_label, vars)
		if data[3] is None:
			ret += indent + '}\r\n'
		else:
			ret += indent + '} else\r\n' + indent + '{\r\n'
			ret += build_statement (data[3], retval, indent + '\t', fname, dink, continue_label, break_label, vars)
			ret += indent + '}\r\n'
		return ret
	elif data[0] == 'int':
		tb = ''
		ret = ''
		for v in data[1]:
			newmangle (v[0])
			vars[0].add (v[0])
			if v[1] is not None:
				b, e = build_expr (dink, fname, v[1], indent, as_bool = False)
				tb += b
				ret += indent + 'int ' + mangle (v[0]) + ' = ' + e + ';\r\n'
			else:
				ret += indent + 'int ' + mangle (v[0]) + ';\r\n'
		return tb + ret
	elif data[0] == 'choice':
		b, e = build_choice (dink, fname, data[1], data[2], indent)
		# discard return value
		return b
	elif data[0] == '()':
		return build_function (data[1], data[2], indent, dink, fname)
	elif data[0] == 'internal':
		b, e = build_internal_function (data[1], data[2], indent, dink, fname, False)
		# discard return value.
		return b
	else:
		a, n, te = data
		if a[0] in ('*', '/'):
			a = a[0]
		b, e = build_expr (dink, fname, te, indent, as_bool = False)
		return b + indent + mangle (n) + ' ' + a + ' ' + e + ';\r\n'
# }}}

class Sprite: #{{{
	def __init__ (self, parent, seq = None, frame = 1, world = None, name = None):
		self.parent = parent
		if world is None:
			world = parent.world
		if seq is None:
			the_seq = None
			s = 'none'
		elif isinstance (seq, str):
			s = seq
			the_seq = self.parent.seq.find_seq (s)
			if the_seq is None:
				print ('seq %s not found' % s)
			else:
				brain = the_seq.brain
				script = the_seq.script
				hard = the_seq.hard
			walk = ''
			attack = ''
			death = ''
		else:
			s = seq[0]
			the_collection = self.parent.seq.find_collection (s)
			if the_collection is None:
				print ('collection %s not found' % s)
				the_seq = None
			elif seq[1] not in the_collection:
				print ('direction %d not in collection %s' % (seq[1], seq[0]))
				the_seq = None
			else:
				the_seq = the_collection[seq[1]]
				brain = the_collection['brain']
				script = the_collection['script']
				walk = seq[0]
				attack = the_collection['attack']
				death = the_collection['death']
				hard = False
		if the_seq is None:
			brain = 'none'
			script = ''
			hard = False
			walk = ''
			attack = ''
			death = ''
		self.name = None
		self.rename (name if name is not None else s, world)
		self.map = None
		self.layer = 1
		self.x = None
		self.y = None
		self.seq = seq
		self.frame = frame
		self.size = 100
		self.brain = brain
		self.script = script
		self.speed = 1
		self.base_walk = walk
		self.base_idle = ''
		self.base_attack = attack
		self.timing = 33
		self.que = 0
		self.hard = hard
		self.left = 0
		self.top = 0
		self.right = 0
		self.bottom = 0
		self.warp = None
		self.touch_seq = ''
		self.base_death = death
		self.gold = 0
		self.hitpoints = 0
		self.strength = 0
		self.defense = 0
		self.experience = 0
		self.sound = ''
		self.vision = 0
		self.nohit = False
		self.touch_damage = 0
	def rename (self, name, world = None):
		if world is None:
			world = self.parent.world
		if self.name is not None:
			world.spritenames.remove (self.name)
		if name in world.spritenames:
			r = re.match ('(.*)-(\d+)', name)
			if r:
				name = r.group (1)
			i = 0
			n = name
			while n in world.spritenames:
				n = name + '-%03d' % i
				i += 1
		else:
			n = name
		assert n not in world.spritenames
		world.spritenames.add (n)
		self.name = n
	def get_maps (self, world):
		ret = []
		if self.x is None or self.y is None:
			return ret
		if self.map is not None:
			if self.map in world.map:
				ret.append (self.map)
		else:
			# Compute bounding box; add sprite wherever it is visible.
			s = self.parent.seq.find_seq (self.seq)
			if s is None or self.frame >= len (s.frames):
				# Sequence not found: no maps.
				return ret
			boundingbox = s.frames[self.frame].boundingbox
			minx = (self.x - 20 + boundingbox[0]) / (50 * 12)
			miny = (self.y + boundingbox[1]) / (50 * 8)
			maxx = (self.x - 20 + boundingbox[2]) / (50 * 12)
			maxy = (self.y + boundingbox[3]) / (50 * 8)
			ret += [r for r in (y * 32 + x + 1 for y in range (miny, maxy + 1) for x in range (minx, maxx + 1)) if r in world.map]
		return ret
	def register (self, world = None):
		if world is None:
			world = self.parent.world
		for i in self.get_maps (world):
			world.map[i].sprite.add (self)
	def unregister (self, world = None):
		if world is None:
			world = self.parent.world
		for i in self.get_maps (world):
			world.map[i].sprite.remove (self)
	def read (self, info, name, base, map = None, world = None):
		'''Read sprite info from info. Optionally lock sprite to map.'''
		self.unregister (world)
		self.map = map
		info, self.x = get (info, 'x', int)
		info, self.y = get (info, 'y', int)
		info, seq = get (info, 'seq', base)
		seq = seq.split ()
		if len (seq) == 1:
			self.seq = seq[0]
		elif len (seq) == 2:
			self.seq = (seq[0], int (seq[1]))
		else:
			print 'Warning: strange seq:', seq
			self.seq = None
		self.rename (name, world)
		info, self.frame = get (info, 'frame', 1)
		info, self.size = get (info, 'size', 100)
		info, self.brain = get (info, 'brain', 'none')
		info, self.script = get (info, 'script', '')
		info, self.speed = get (info, 'speed', 1)
		info, self.base_walk = get (info, 'base_walk', '')
		info, self.base_idle = get (info, 'base_idle', '')
		info, self.base_attack = get (info, 'base_attack', '')
		info, self.timing = get (info, 'timing', 33)
		info, self.que = get (info, 'que', 0)
		info, self.hard = get (info, 'hard', True)
		info, self.left = get (info, 'left', 0)
		info, self.top = get (info, 'top', 0)
		info, self.right = get (info, 'right', 0)
		info, self.bottom = get (info, 'bottom', 0)
		info, w = get (info, 'warp', '')
		if w == '':
			self.warp = None
		else:
			self.warp = [int (x) for x in w.split ()]
		info, self.touch_seq = get (info, 'touch_seq', '')
		info, self.base_death = get (info, 'base_death', '')
		info, self.gold = get (info, 'gold', 0)
		info, self.hitpoints = get (info, 'hitpoints', 0)
		info, self.strength = get (info, 'strength', 0)
		info, self.defense = get (info, 'defense', 0)
		info, self.experience = get (info, 'exp', 0)
		info, self.sound = get (info, 'sound', '')
		info, self.vision = get (info, 'vision', 0)
		info, self.nohit = get (info, 'nohit', False)
		info, self.touch_damage = get (info, 'touch_damage', 0)
		self.register (world)
		return info
	def save (self):
		if self.map is not None:
			n = self.map
			x = (n - 1) % 32
			y = (n - 1) / 32
			d = os.path.join (self.parent.root, 'world', '%03d-%02d-%02d-sprite' % (n, x, y), '%d' % self.layer)
		else:
			d = os.path.join (self.parent.root, 'world', 'sprite', '%d' % self.layer)
		if not os.path.exists (d):
			os.makedirs (d)
		n = os.path.join (d, self.name + os.extsep + 'txt')
		nice_assert (not os.path.exists (n), 'duplicate sprite name')
		f = open (n, 'w')
		put (f, 'x', self.x)
		put (f, 'y', self.y)
		if isinstance (self.seq, str):
			seq = self.seq
		else:
			seq = '%s %s' % (self.seq[0], str (self.seq[1]))
		r = re.match ('(.*)-\d*$', self.name)
		if r is not None:
			base = r.group (1)
		else:
			base = self.name
		put (f, 'seq', seq, base)
		put (f, 'frame', self.frame, 1)
		put (f, 'size', self.size, 100)
		put (f, 'brain', self.brain, 'none')
		put (f, 'script', self.script, '')
		put (f, 'speed', self.speed, 1)
		put (f, 'base_walk', self.base_walk, '')
		put (f, 'base_idle', self.base_idle, '')
		put (f, 'base_attack', self.base_attack, '')
		put (f, 'timing', self.timing, 33)
		put (f, 'que', self.que, 0)
		put (f, 'hard', self.hard, True)
		put (f, 'left', self.left, 0)
		put (f, 'top', self.top, 0)
		put (f, 'right', self.right, 0)
		put (f, 'bottom', self.bottom, 0)
		if self.warp is not None:
			put (f, 'warp', ' '.join ([str (x) for x in self.warp]))
		put (f, 'touch_seq', self.touch_seq, '')
		put (f, 'base_death', self.base_death, '')
		put (f, 'gold', self.gold, 0)
		put (f, 'hitpoints', self.hitpoints, 0)
		put (f, 'strength', self.strength, 0)
		put (f, 'defense', self.defense, 0)
		put (f, 'exp', self.experience, 0)
		put (f, 'sound', self.sound, '')
		put (f, 'vision', self.vision, 0)
		put (f, 'nohit', self.nohit, False)
		put (f, 'touch_damage', self.touch_damage, 0)
# }}}

class Map: #{{{
	def __init__ (self, parent, path = None):
		self.parent = parent
		self.sprite = set ()
		if path is None:
			self.tiles = [[[1, 0, 0] for x in range (12)] for y in range (8)]
			self.hard = ''
			self.script = ''
			self.music = ''
			self.indoor = False
			return
		global filename
		filename = path
		f = open (path)
		self.tiles = []
		for ty in range (8):
			ln = f.readline ()
			self.tiles += ([[int (z) for z in y.split (',')] for y in ln.split ()],)
			nice_assert (len (self.tiles[-1]) == 12, 'invalid line in %s: not 12 tiles on a line' % path)
		info = readlines (f)
		info, self.hard = get (info, 'hard', '')
		info, self.script = get (info, 'script', '')
		info, self.music = get (info, 'music', '')
		info, self.indoor = get (info, 'indoor', False)
		nice_assert (info == {}, 'unused data in %s' % path)
	def save (self, n):
		y = (n - 1) / 32
		x = n - y * 32 - 1
		path = os.path.join (self.parent.root, 'world', '%03d-%02d-%02d' % (n, x, y) + os.extsep + 'txt')
		f = open (path, 'w')
		for y in range (8):
			f.write (' '.join ([','.join ([str (z) for z in self.tiles[y][x]]) for x in range (12)]) + '\n')
		put (f, 'hard', self.hard, '')
		put (f, 'script', self.script, '')
		put (f, 'music', self.music, '')
		put (f, 'indoor', self.indoor, False)
# }}}

class World: #{{{
	def __init__ (self, parent):
		self.parent = parent
		self.map = {}
		self.spritenames = set ()
		self.sprite = set ()
		if self.parent.root is None:
			return
		d = os.path.join (parent.root, 'world')
		for y in range (24):
			for x in range (32):
				n = y * 32 + x + 1
				path = os.path.join (d, '%03d-%02d-%02d' % (n, x, y))
				infopath = path + os.extsep + 'txt'
				if not os.path.exists (infopath):
					continue
				self.map[n] = Map (parent, infopath)
				self.read_sprites (path + '-sprite', n)
		self.read_sprites ('sprite')
		if not os.path.exists (d):
			return
		for f in os.listdir (d):
			if os.path.isdir (os.path.join (d, f)):
				pass # TODO: check some more stuff.
			else:
				r = re.match ('(\d{3})-(\d{2})-(\d{2})' + os.extsep + 'txt$', f)
				if r is None:
					if re.match ('\d+-', f) is not None:
						sys.stderr.write ("Warning: not using %s as map\n" % f)
					continue
				n, x, y = [int (k) for k in r.groups ()]
				if x >= 32 or y >= 24 or n != y * 32 + x + 1:
					sys.stderr.write ("Warning: not using %s as map (%d != %d * 32 + %d + 1)\n" % (f, n, y, x))
	def add_sprite (self, name, pos, seq, frame):
		spr = Sprite (self.parent, seq, frame, name = name)
		self.sprite.add (spr)
		spr.x, spr.y = pos
		spr.register ()
		return spr
	def read_sprites (self, dirname, map = None):
		global filename
		sdir = os.path.join (self.parent.root, 'world', dirname)
		if not os.path.exists (sdir):
			return
		for layer in range (10):
			layerdir = os.path.join (sdir, '%d' % layer)
			if not os.path.exists (layerdir):
				continue
			for s in os.listdir (layerdir):
				r = re.match ('(([^.].+?)(-\d+)?)\.txt$', s)
				nice_assert (r, 'sprite has incorrect filename')
				filename = os.path.join (layerdir, s)
				info = readlines (open (filename))
				s = r.group (1)
				base = r.group (2)
				nice_assert (s not in self.spritenames, 'duplicate definition of sprite name %s' % s)
				spr = Sprite (self.parent, world = self, name = s)
				self.sprite.add (spr)
				spr.layer = layer
				info = spr.read (info, s, base, map, world = self)
				nice_assert (info == {}, 'unused data for sprite %s: %s' % (s, str (info.keys ())))
	def save (self):
		os.mkdir (os.path.join (self.parent.root, 'world'))
		for r in self.map:
			self.map[r].save (r)
		for s in self.sprite:
			s.save ()
	def write_sprite (self, spr, mdat, s):
		sx = (s - 1) % 32
		sy = (s - 1) / 32
		x = spr.x - sx * 50 * 12
		y = spr.y - sy * 50 * 8
		mdat.write (make_lsb (x, 4))
		mdat.write (make_lsb (y, 4))
		sq = self.parent.seq.find_seq (spr.seq)
		if sq is None:
			mdat.write (make_lsb (-1, 4))
		else:
			mdat.write (make_lsb (sq.code, 4))
		mdat.write (make_lsb (spr.frame, 4))
		# Invisible foreground is ignored, and this function is not even called for it.
		if not self.parent.layer_background[spr.layer]:
			mdat.write (make_lsb (1, 4))
		elif self.parent.layer_visible[spr.layer]:
			mdat.write (make_lsb (0, 4))
		else:
			mdat.write (make_lsb (2, 4))
		mdat.write (make_lsb (spr.size, 4))
		mdat.write (make_lsb (1, 4))	# active
		mdat.write (make_lsb (0, 4))	# rotation
		mdat.write (make_lsb (0, 4))	# special
		if not nice_assert (spr.warp is None or spr.brain != 'repeat' or self.parent.layer_background[spr.layer], 'sprite %s has repeat brain and warp; resetting brain to none to avoid bug in engine' % spr.name):
			mdat.write (make_lsb (make_brain ('none'), 4))
		else:
			mdat.write (make_lsb (make_brain (spr.brain), 4))
		mdat.write (make_string (spr.script, 14))
		mdat.write ('\0' * 38)
		mdat.write (make_lsb (spr.speed, 4))
		def coll (which):
			if which == '':
				return -1
			return self.parent.seq.collection_code (which)
		mdat.write (make_lsb (coll (spr.base_walk), 4))
		mdat.write (make_lsb (coll (spr.base_idle), 4))
		mdat.write (make_lsb (coll (spr.base_attack), 4))
		mdat.write (make_lsb (0, 4))	# hit
		mdat.write (make_lsb (spr.timing, 4))
		mdat.write (make_lsb (0 if spr.que == 0 else max (1, y - spr.que), 4))
		mdat.write (make_lsb (not spr.hard, 4))
		mdat.write (make_lsb (spr.left, 4))
		mdat.write (make_lsb (spr.top, 4))
		mdat.write (make_lsb (spr.right, 4))
		mdat.write (make_lsb (spr.bottom, 4))
		if spr.warp is not None:
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
		mdat.write (make_lsb (spr.experience, 4))
		# Ok, so Seth doesn't like 0. He adds an empty element to every
		# array to make sure 0 is never used. That's annoying, but I've
		# learned to live with it. BUT WHAT IS THIS?! While the sounds
		# in scripts are 1-based, like the rest of the code, he thought
		# it would be a good idea to drop this idea for sounds and make
		# them 0-based. Seth, STOP BEING SO TERRIBLY INCONSISTENT!!!
		mdat.write (make_lsb (self.parent.sound.find_sound (spr.sound) - 1, 4))
		mdat.write (make_lsb (spr.vision, 4))
		mdat.write (make_lsb (int (spr.nohit), 4))
		mdat.write (make_lsb (spr.touch_damage, 4))
		mdat.write ('\0' * 20)
	def find_used_sprites (self):
		# Initial values are all which are used by the engine.
		cols = set (('idle', 'walk', 'hit', 'push', 'duckbloody', 'duckhead'))
		seqs = set (('status', 'nums', 'numr', 'numb', 'nump', 'numy', 'special', 'textbox', 'spurt', 'spurtl', 'spurtr', 'health-w', 'health-g', 'health-br', 'health-r', 'level', 'title', 'arrow-l', 'arrow-r', 'shiny', 'menu'))
		self.parent.seq.clear_used ()
		for spr in self.sprite:
			c = self.parent.seq.as_collection (spr.seq)
			if c:
				cols.add (c)
				col = self.parent.seq.find_collection (c)
				for d in (1,2,3,4,'die',6,7,8,9):
					if d in col:
						col[d].used = True
			else:
				seqs.add (spr.seq)
				seq = self.parent.seq.find_seq (spr.seq)
				if nice_assert (seq, "undefined sequence %s" % str (spr.seq)):
					seq.used = True
			for i in (spr.base_idle, spr.base_walk, spr.base_attack, spr.base_death):
				if i:
					cols.add (i)
		# Fill with values from scripts.
		used = self.parent.script.find_used_sprites ()
		cols.update (used[0])
		seqs.update (used[1])
		# Some collections and seqs which are often used from default scripts.
		cols.update (('pig', 'duck', 'duckbloody', 'duckhead', 'shoot', 'comet', 'fireball', 'seeding'))
		seqs.update (('treefire', 'explode', 'smallheart', 'heart', 'spray', 'blast', 'coin', 'button-ordering', 'button-quit', 'button-start', 'button-continue', 'startme1', 'startme3', 'startme7', 'startme9', 'food', 'seed4', 'seed6', 'shadow', 'die', 'item-m', 'item-w', 'fishx', 'crawl', 'horngoblinattackswing'))
		for c in cols:
			col = self.parent.seq.find_collection (c)
			if col is None:
				continue
			for d in (1,2,3,4,'die',6,7,8,9):
				if d in col:
					col[d].used = True
		for s in seqs:
			seq = self.parent.seq.find_seq (s)
			if not nice_assert (seq is not None, "used sequence %s doesn't exist" % str (s)):
				continue
			seq.used = True
		return cols, seqs
	def build (self, root):
		used_cols, used_seqs = self.find_used_sprites ()
		used_codes = set ()
		remove = set ()
		for i in used_cols:
			collection = self.parent.seq.find_collection (i)
			if collection is not None and collection['code'] is not None:
				for c in (1,2,3,4,'die',6,7,8,9):
					used_codes.add (collection['code'] + (5 if c == 'die' else c))
				remove.add (i)
		used_cols.difference_update (remove)
		remove.clear ()
		for i in used_seqs:
			seq = self.parent.seq.find_seq (i)
			if seq is not None and seq.code:
				used_codes.add (seq.code)
				remove.add (i)
		used_seqs.difference_update (remove)
		next_code = 0
		for i in used_cols:
			collection = self.parent.seq.find_collection (i)
			if collection is None:
				continue
			while True:
				for d in (1,2,3,4,'die',6,7,8,9):
					if (next_code + (5 if d == 'die' else d)) in used_codes:
						break
				else:
					collection['code'] = next_code
					for d in collection:
						if d in (1,2,3,4,'die',6,7,8,9):
							collection[d].code = next_code + (5 if d == 'die' else d)
					break
				next_code += 10
		nice_assert (next_code < 1000, 'more than 1000 sequences required for collections')
		next_code = 1
		for i in used_seqs:
			seq = self.parent.seq.find_seq (i)
			if seq is None:
				continue
			while next_code in used_codes:
				next_code += 1
			seq.code = next_code
		nice_assert (next_code < 1000, 'more than 1000 sequences used')
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink' + os.extsep + 'dat'), "wb")
		ddat.write ('Smallwood' + '\0' * 15)
		maps = []
		for i in range (1, 32 * 24 + 1):
			if not i in self.map:
				ddat.write (make_lsb (0, 4))
				continue
			maps.append (i)
			# Note that the write is after the append, because the index must start at 1.
			ddat.write (make_lsb (len (maps), 4))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.map:
				ddat.write (make_lsb (0, 4))
				continue
			ddat.write (make_lsb (self.parent.sound.find_music (self.map[i].music), 4))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.map or not self.map[i].indoor:
				ddat.write (make_lsb (0, 4))
			else:
				ddat.write (make_lsb (1, 4))
		# Write map.dat
		mdat = open (os.path.join (root, 'map' + os.extsep + 'dat'), "wb")
		for s in maps:
			mdat.write ('\0' * 20)
			# tiles and hardness
			for y in range (8):
				for x in range (12):
					bmp, tx, ty = self.map[s].tiles[y][x]
					mdat.write (make_lsb ((bmp - 1) * 128 + ty * 12 + tx, 4))
					mdat.write ('\0' * 4)
					mdat.write (make_lsb (self.parent.tile.find_hard (self.map[s].hard, x, y, bmp, tx, ty), 4))
					mdat.write ('\0' * 68)
			mdat.write ('\0' * 320)
			# sprites
			# sprite 0 is never used...
			mdat.write ('\0' * 220)
			editcode = 1
			ignored = 0
			for spr in self.map[s].sprite:
				if not self.parent.layer_visible[spr.layer] and not self.parent.layer_background[spr.layer]:
					ignored += 1
					continue
				if spr.map is not None:
					spr.editcode = editcode
				editcode += 1
				self.write_sprite (spr, mdat, s)
			n = len (self.map[s].sprite) - ignored
			mdat.write ('\0' * 220 * (100 - n))
			# base script
			mdat.write (make_string (self.map[s].script, 21))
			mdat.write ('\0' * 1019)
# }}}

class Tile: #{{{
	# TODO: allow external tiles somehow.
	# self.tile is a dict of num:(tiles, hardness, code). Code means:
	# 0: hardness from original, image from original
	# 1: hardness from original, image from dmod
	# 2: hardness from dmod, image from original
	# 3: hardness from dmod, image from dmod
	def __init__ (self, parent):
		self.parent = parent
		self.hard = {}
		self.tile = {}
		if self.parent.root is not None:
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
		for n in range (1, 42):
			if n not in self.tile:
				if self.parent.root is not None:
					t = os.path.join (d, str (n) + ext)
				if self.parent.root is not None and os.path.exists (t):
					tilefile = ((t, 0, os.stat (t).st_size), 1)
				else:
					tilefile = (tilefiles[n - 1], 0)
				hardfile = os.path.join (cachedir, 'hard-%02d' % n + os.extsep + 'png')
				self.tile[n] = (tilefile[0], (hardfile, 0, os.stat (hardfile).st_size), tilefile[1])
	def find_hard (self, hard, x, y, bmp, tx, ty):
		if hard != '':
			nice_assert (hard in self.hard, 'reference to undefined hardness map %s' % hard)
			ret = self.hardmap[hard][y][x]
			if ret != self.tilemap[bmp][ty][tx]:
				return ret
		return 0
	def save (self):
		hfiles = []
		for n in self.parent.world.map:
			h = self.parent.world.map[n].hard
			if h:
				nice_assert (h in self.hard, "map %d references hardness %s which isn't defined" % (n, h))
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
		'''Write hardness of all tiles in a given map to hard.dat (opened as h). Return map of indices used.'''
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
		# First hardness tile cannot be used (because 0 means "use default"), so skip it.
		self.hmap = [None]
		# Write it in the file as well.
		h.write ('\0' * (51 * 50 + 58))
		self.hardmap = {}
		self.tilemap = [None] * 41
		for t in self.hard:
			# Write hardness for custom hard maps.
			self.hardmap[t] = self.write_hard (Image.open (filepart (*self.hard[t])), h)
		for n in range (1, 41):
			if self.tile[n][2] == 1 or self.tile[n][2] == 3:
				# Write custom tile maps.
				convert_image (Image.open (filepart (*self.tile[n][0]))).save (os.path.join (d, str (t) + os.extsep + 'bmp'))
			# Write hardness for standard tiles.
			self.tilemap[n] = self.write_hard (Image.open (filepart (*self.tile[n][1])), h)
		nice_assert (len (self.hmap) <= 800, 'More than 800 hardness tiles defined (%d)' % len (self.hmap))
		h.write ('\0' * (51 * 51 + 1 + 6) * (800 - len (self.hmap)))
		# Write hardness index for tile maps.
		for t in range (1, 41):
			m = self.tilemap[t]
			for y in range (8):
				for x in range (12):
					if m[y][x] is not None:
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
		if isinstance (name, int):
			if name not in self.tile:
				return None
			return self.tile[name][1] + ((0, 0, 0),)
		else:
			if name not in self.hard:
				return None
			return self.hard[name] + ((0, 0, 0),)
# }}}

class Seq: #{{{
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
	#	type		normal, notanim, black, or leftalign, or foreign
	def __init__ (self, parent):
		"""Load all sequence and collection declarations from cache (generated from dink.ini) and seq/info.txt"""
		global filename
		global codes
		# General setup
		self.parent = parent
		self.seq = sequences
		self.collection = collections
		self.current_collection = None
		self.custom_seqs = []
		self.custom_collections = []
		if self.parent.root is None:
			return
		for prefix, d in pathsearch (parent, 'seq'):
			for s in os.listdir (d):
				filename = os.path.join (d, s)
				if not os.path.isdir (filename):
					continue
				r = re.match (r'([^.].*?)(?:-(\d+))?$', s)
				if not r:
					continue
				base = prefix + r.group (1)
				if base not in self.seq:
					self.seq[base] = self.makeseq (base)
				if prefix == '' and r.group (2):
					self.seq[base].code = int (r.group (2))
				else:
					self.seq[base].code = None
				self.fill_seq (self.seq[base], filename)
				self.custom_seqs += (self.seq[base],)
		for prefix, d in pathsearch (parent, 'collection'):
			for s in os.listdir (d):
				filename = os.path.join (d, s)
				if not os.path.isdir (filename):
					r = re.match (r'([^.].*)-(die|\d).txt$', s)
					if not r:
						continue
					base = prefix + r.group (1)
					if not nice_assert (base in self.collection, '%s is not a known collection' % base):
						continue
					d = r.group (2)
					if d != 'die':
						d = int (d)
						nice_assert (d in (1,2,3,4,6,7,8,9), 'invalid direction %d' % d)
					if not nice_assert (d in self.collection[base], 'trying to override undefined direction %s for %s' % (str (d), base)):
						continue
					self.fill_seq (self.collection[base][d], filename, self.collection[base])
					continue
				r = re.match (r'([^.].*?)(?:-(\d+))?$', s)
				if not r:
					continue
				base = r.group (1)
				if base not in self.collection:
					self.collection[base] = self.makecollection (base)
				if prefix == '' and r.group (2):
					self.collection[base]['code'] = int (r.group (2))
				else:
					self.collection[base]['code'] = None
				fname = filename
				filename = os.path.join (fname, 'info' + os.extsep + 'txt')
				if os.path.exists (filename):
					info = readlines (open (filename))
					info, self.collection[base]['brain'] = get (info, 'brain', self.collection[base]['brain'])
					info, self.collection[base]['script'] = get (info, 'script', self.collection[base]['script'])
					info, self.collection[base]['attack'] = get (info, 'attack', self.collection[base]['attack'])
					info, self.collection[base]['death'] = get (info, 'death', self.collection[base]['death'])
					nice_assert (info == {}, 'unused data in collection definition')
				for direction in (1, 2, 3, 4, 'die', 6, 7, 8, 9):
					filename = os.path.join (fname, str (direction))
					if not os.path.isdir (filename):
						continue
					self.collection[base][direction] = self.makeseq (base + str (direction))
					self.fill_seq (self.collection[base][direction], filename, self.collection[base])
				self.custom_collections += (self.collection[base],)
	def makecollection (self, base):
		ret = {}
		ret['name'] = base
		ret['code'] = None
		ret['brain'] = 'none'
		ret['script'] = ''
		ret['attack'] = ''
		ret['death'] = ''
		return ret
	def makeseq (self, base):
		ret = Sequence ()
		ret.name = base
		ret.brain = 'none'
		ret.script = ''
		ret.hard = True
		ret.frames = []
		ret.repeat = False
		ret.filepath = 'graphics\\custom\\%s-' % base
		ret.type = 'foreign'
		ret.special = 0
		ret.preload = ''
		ret.delay = 75
		ret.hardbox = None
		ret.position = None
		ret.now = False
		ret.code = None
		return ret
	def makeframe (self):
		ret = Frame ()
		ret.position = None
		ret.hardbox = None
		ret.boundingbox = None
		ret.delay = 75
		ret.source = None
		ret.cache = None
		return ret
	def fill_seq (self, seq, sd, collection = None):
		global filename
		imgext = os.extsep + 'png'
		for f in os.listdir (sd):
			if not f.endswith (imgext):
				continue
			filename = os.path.join (sd, f)
			r = re.match (r'\d+$', f[:-len (imgext)])
			nice_assert (r, 'unexpected filename for frame image')
			frame = int (r.group (0))
			if frame >= len (seq.frames):
				seq.frames += [None] * (frame + 1 - len (seq.frames))
			if seq.frames[frame] is None:
				seq.frames[frame] = self.makeframe ()
			seq.frames[frame].cache = (filename, 0, os.stat (filename).st_size)
			seq.frames[frame].size = Image.open (filename).size
		filename = os.path.join (sd, 'info' + os.extsep + 'txt')
		if os.path.exists (filename):
			infofile = open (filename)
			info = readlines (infofile)
		else:
			infofile = None
			info = {}
		if collection is None:
			info, seq.brain = get (info, 'brain', seq.brain)
			info, seq.script = get (info, 'script', seq.script)
			info, seq.hard = get (info, 'hard', seq.hard)
		info, seq.repeat = get (info, 'repeat', seq.repeat)
		info, seq.special = get (info, 'special', seq.special)
		info, seq.now = get (info, 'load-now', seq.now)
		info, seq.preload = get (info, 'preload', seq.preload)
		info, seq.type = get (info, 'type', seq.type)
		if seq.special == 0:
			seq.special = None
		info, seq.delay = get (info, 'delay', seq.delay)
		if seq.delay == -1:
			seq.delay = None
		info, pos = get (info, 'position', '')
		if pos != '':
			pos = [int (x) for x in pos.split ()]
			nice_assert (len (pos) == 2, 'position must be 2 numbers')
			seq.position = pos
		info, box = get (info, 'hardbox', '')
		if box != '':
			box = [int (x) for x in box.split ()]
			nice_assert (len (box) == 4, 'hardbox must be 4 numbers')
			seq.hardbox = box
		info, frames = get (info, 'frames', 0)
		if frames == 0:
			frames = len (seq.frames)
		elif frames < len (seq.frames):
			seq,frames[frames:] = []
		else:
			seq.frames += [None] * (frames - len (seq.frames))
		for f in range (1, frames):
			if seq.frames[f] is None:
				seq.frames[f] = self.makeframe ()
			info, pos = get (info, 'position-%d' % f, '')
			if pos != '':
				seq.frames[f].position = [int (x) for x in pos.split ()]
				nice_assert (len (seq.frames[f].position) == 2, 'frame position must be two numbers')
			info, hardbox = get (info, 'hardbox-%d' % f, '')
			if hardbox != '':
				seq.frames[f].hardbox = [int (x) for x in hardbox.split ()]
				nice_assert (len (seq.frames[f].hardbox) == 4, 'frame hardbox must be four numbers')
			info, seq.frames[f].delay = get (info, 'delay-%d' % f, 75)
			if seq.frames[f].delay == -1:
				seq.frames[f].delay = None
			if seq.frames[f].cache is None:
				info, source = get (info, 'source-%d' % f, str)
				source = source.split ()
				seq.frames[f].source = [source[0], int (source[1])]
				nice_assert (len (seq.frames[f].source) == 2, 'frame source must be two numbers')
		if seq.position is None or seq.hardbox is None:
			bb = None
			for f in range (1, frames):
				w, h = seq.frames[f].size
				if bb is None:
					bb = w, h
				else:
					if w > bb[0]:
						bb = w, bb[1]
					if h > bb[1]:
						bb = bb[0], h
			if seq.position is None:
				seq.position = bb[0] / 2, bb[1] / 2
			if seq.hardbox is None:
				x, y = seq.position
				seq.hardbox = -x / 2, -y / 2, (bb[0] - x) / 2, (bb[1] - y) / 2
		# Fill in the gaps, if any, and compute actual bounding box.
		seq.boundingbox = None
		for f in range (1, frames):
			w, h = seq.frames[f].size
			del seq.frames[f].size
			if seq.frames[f].position is None:
				seq.frames[f].position = seq.position
			x, y = seq.frames[f].position
			seq.frames[f].boundingbox = -x, -y, w - x, h - y
			if seq.frames[f].hardbox is None:
				seq.frames[f].hardbox = seq.hardbox
			if seq.boundingbox is None:
				seq.boundingbox = list (seq.frames[f].boundingbox)
			else:
				if seq.frames[f].boundingbox[0] < seq.boundingbox[0]:
					seq.boundingbox[0] = seq.frames[f].boundingbox[0]
				if seq.frames[f].boundingbox[1] < seq.boundingbox[1]:
					seq.boundingbox[1] = seq.frames[f].boundingbox[1]
				if seq.frames[f].boundingbox[2] > seq.boundingbox[2]:
					seq.boundingbox[2] = seq.frames[f].boundingbox[2]
				if seq.frames[f].boundingbox[3] > seq.boundingbox[3]:
					seq.boundingbox[3] = seq.frames[f].boundingbox[3]
		nice_assert (info == {}, 'unused data in %s' % infofile)
	def get_dir_seq (self, collection, dir, num = False):
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
		if dir in order:
			for option in order[dir]:
				if option in c:
					return option if num else c[option]
		# There's nothing usable. Get whatever exists.
		n = [x for x in c if isinstance (x, int)][0]
		return n if num else c[n]
	def as_collection (self, name):
		if not name:
			return None
		if isinstance (name, int):
			for i in self.seq:
				if self.seq[i].code == name:
					return None
			for c in self.collection:
				for i in self.collection[c]:
					if i not in (1,2,3,4,'die',6,7,8,9):
						continue
					if self.collection[c][i].code == name:
						return c
			raise AssertionError ('undefined numerical code %d for is_collection' % name)
		elif isinstance (name, str):
			parts = name.split ()
			if len (parts) == 1:
				return None
			else:
				if len (parts) != 2 or parts[0] not in self.collection or int (parts[1]) not in self.collection[parts[0]]:
					return None
				return parts[0]
		else:
			if name[0] not in self.collection or int (name[1]) not in self.collection[name[0]]:
				return None
			return name[0]
	def find_seq (self, name):
		if not name:
			return None
		if isinstance (name, int):
			for i in self.seq:
				if self.seq[i].code == name:
					return self.seq[i]
			for c in self.collection:
				for i in self.collection[c]:
					if i not in (1,2,3,4,'die',6,7,8,9):
						continue
					if self.collection[c][i].code == name:
						return self.collection[c][i]
			raise AssertionError ('undefined numerical code %d for find_seq' % name)
		elif isinstance (name, str):
			parts = name.split ()
			if len (parts) == 1:
				if parts[0] not in self.seq:
					return None
				return self.seq[parts[0]]
			else:
				if len (parts) != 2 or parts[0] not in self.collection:
					return None
				if parts[1] != 'die':
					p = int (parts[1])
				else:
					p = parts[1]
				if p not in self.collection[parts[0]]:
					return None
				return self.collection[parts[0]][p]
		else:
			if name[0] not in self.collection or int (name[1]) not in self.collection[name[0]]:
				return None
			return self.collection[name[0]][int (name[1])]
	def find_collection (self, name):
		if isinstance (name, int):
			for c in self.collection:
				if self.collection[c]['code'] == name:
					return self.collection[c]
			return None
		if name not in self.collection:
			return None
		return self.collection[name]
	def clear_used (self):
		for s in self.seq:
			self.seq[s].used = False
		for c in self.collection:
			for d in (1,2,3,4,'die',6,7,8,9):
				if d in self.collection[c]:
					self.collection[c][d].used = False
	def collection_code (self, name):
		if isinstance (name, str) and name.startswith ('*'):
			seq = self.find_seq (name[1:])
			if seq is None:
				return -1
			return seq.code
		coll = self.find_collection (name)
		if coll is None:
			return -1
		return coll['code']
	def save_seq (self, d, f, seq):
		put (f, 'repeat', seq.repeat, False)
		put (f, 'special', 0 if seq.special is None else seq.special, 0)
		put (f, 'load-now', seq.now, False)
		put (f, 'preload', seq.preload, '')
		put (f, 'type', seq.type, 'foreign')
		put (f, 'delay', -1 if seq.delay is None else seq.delay, 75)
		put (f, 'position', '%d %d' % tuple (seq.position), str)
		put (f, 'hardbox', '%d %d %d %d' % tuple (seq.hardbox), str)
		put (f, 'frames', 0 if seq.frames[-1].source is None else len (seq.frames), 0)
		for frame in range (1, len (seq.frames)):
			if seq.frames[frame].source is None:
				open (os.path.join (d, '%02d' % frame + os.extsep + 'png'), 'wb').write (open (seq.frames[frame].cache[0], 'rb').read ())
			put (f, 'position-%d' % frame, '' if seq.frames[frame].position == seq.position else '%d %d' % tuple (seq.frames[frame].position), '')
			put (f, 'hardbox-%d' % frame, '' if seq.frames[frame].hardbox == seq.hardbox else '%d %d %d %d' % tuple (seq.frames[frame].hardbox), '')
			put (f, 'delay-%d' % frame, -1 if seq.frames[frame].delay == seq.delay else seq.frames[frame].delay, -1)
			put (f, 'source-%d' % frame, '' if seq.frames[frame].source is None else '%s %d' % tuple (seq.frames[frame].source), '')
	def save (self):
		if len (self.custom_seqs) > 0:
			d = os.path.join (self.parent.root, 'seq')
			os.mkdir (d)
			for s in self.custom_seqs:
				sd = os.path.join (d, s.name)
				os.mkdir (sd)
				f = open (os.path.join (sd, 'info' + os.extsep + 'txt'), 'w')
				put (f, 'brain', s.brain, 'none')
				put (f, 'script', s.script, '')
				put (f, 'hard', s.hard, True)
				self.save_seq (sd, f, s)
		if len (self.custom_collections) > 0:
			d = os.path.join (self.parent.root, 'collection')
			os.mkdir (d)
			for c in self.custom_collections:
				cd = os.path.join (d, c['name'])
				os.mkdir (cd)
				f = open (os.path.join (cd, 'info' + os.extsep + 'txt'), 'w')
				put (f, 'brain', c['brain'], 'none')
				put (f, 'script', c['script'], '')
				put (f, 'attack', c['attack'], '')
				put (f, 'death', c['death'], '')
				for dir in (1,2,3,4,'die',6,7,8,9):
					if dir not in c:
						continue
					cdd = os.path.join (cd, str (dir))
					os.mkdir (cdd)
					f = open (os.path.join (cdd, 'info' + os.extsep + 'txt'), 'w')
					self.save_seq (cdd, f, c[dir])
		# TODO: write changes to standard graphics.
	def build_seq (self, ini, seq):
		if not seq.used:
			return
		if seq.preload:
			ini.write ('// Preload\r\n')
			ini.write ('load_sequence_now %s %d\r\n' % (seq.preload, seq.code))
		if seq.now:
			now = '_now'
		else:
			now = ''
		if seq.type in ('normal', 'foreign'):
			if seq.position is None:
				if seq.delay is not None:
					ini.write ('load_sequence%s %s %d %d\r\n' % (now, seq.filepath, seq.code, seq.delay))
				else:
					ini.write ('load_sequence%s %s %d\r\n' % (now, seq.filepath, seq.code))
			else:
				if seq.delay is not None:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d %d\r\n' % (now, seq.filepath, seq.code, seq.delay, seq.position[0], seq.position[1], seq.hardbox[0], seq.hardbox[1], seq.hardbox[2], seq.hardbox[3]))
				else:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d\r\n' % (now, seq.filepath, seq.code, seq.position[0], seq.position[1], seq.hardbox[0], seq.hardbox[1], seq.hardbox[2], seq.hardbox[3]))
		else:
			ini.write ('load_sequence%s %s %d %s\r\n' % (now, seq.filepath, seq.code, seq.type.upper ()))
		for f in range (1, len (seq.frames)):
			if seq.frames[f].source is not None:
				ini.write ('set_frame_frame %d %d %d %d\r\n' % (seq.code, f, self.find_seq (seq.frames[f].source[0]).code, seq.frames[f].source[1]))
			if (len (seq.frames[f].hardbox) == 4 and seq.frames[f].hardbox != seq.hardbox) or (len (seq.frames[f].position) == 2 and seq.frames[f].position != seq.position):
				ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\r\n' % (seq.code, f, seq.frames[f].position[0], seq.frames[f].position[1], seq.frames[f].hardbox[0], seq.frames[f].hardbox[1], seq.frames[f].hardbox[2], seq.frames[f].hardbox[3]))
			if seq.frames[f].source is not None or seq.frames[f].delay != seq.delay:
				ini.write ('set_frame_delay %d %d %d\r\n' % (seq.code, f, int (seq.frames[f].delay)))
			if seq.special == f:
				ini.write ('set_frame_special %d %d 1\r\n' % (seq.code, f))
		if seq.repeat:
			ini.write ('set_frame_frame %d %d -1\r\n' % (seq.code, len (seq.frames)))
	def build (self, root):
		# Write graphics/*
		if len (self.custom_seqs) != 0 or len (self.custom_collections) != 0:
			d = os.path.join (root, 'graphics')
			if not os.path.exists (d):
				os.mkdir (d)
			cd = os.path.join (d, 'custom')
			if not os.path.exists (cd):
				os.mkdir (cd)
		for i in self.custom_seqs:
			for f in range (1, len (i.frames)):
				convert_image (Image.open (filepart (*i.frames[f].cache))).save (os.path.join (root, 'graphics', 'custom', '%s-%02d' % (i.name, f) + os.extsep + 'bmp'))
		for i in self.custom_collections:
			for d in i:
				if d not in (1,2,3,4,'die',6,7,8,9):
					continue
				for f in range (1, len (i[d].frames)):
					convert_image (Image.open (filepart (*i[d].frames[f].cache))).save (os.path.join (root, 'graphics', 'custom', '%s-%02d' % (i[d].name, f) + os.extsep + 'bmp'))
		# Write dink.ini
		ini = open (os.path.join (root, 'dink' + os.extsep + 'ini'), 'w')
		for c in self.collection:
			for s in self.collection[c]:
				if s not in (1,2,3,4,'die',6,7,8,9):
					continue
				self.build_seq (ini, self.collection[c][s])
		for g in self.seq:
			self.build_seq (ini, self.seq[g])
	def get_file (self, seq, frame):
		if seq.type == 'black':
			alpha = (0, 0, 0)
		elif seq.type == 'foreign':
			alpha = None
		else:
			alpha = (255, 255, 255)
		return seq.frames[frame].cache + (alpha,)
	def rename (self, old, new):
		for i in self.seq:
			for f in range (1, len (self.seq[i].frames)):
				if self.seq[i].frames[f].cache[0].startswith (old):
					self.seq[i].frames[f].cache = (new + self.seq[i].frames[f].cache[0][len (old):], self.seq[i].frames[f].cache[1], self.seq[i].frames[f].cache[2])
		for i in self.collection:
			for d in self.collection[i]:
				if d not in (1,2,3,4,'die',6,7,8,9):
					continue
				for f in range (1, len (self.collection[i][d].frames)):
					if self.collection[i][d].frames[f].cache[0].startswith (old):
						self.collection[i][d].frames[f].cache = (new + self.collection[i][d].frames[f].cache[0][len (old):], self.collection[i][d].frames[f].cache[1], self.collection[i][d].frames[f].cache[2])
# }}}

class Sound: #{{{
	def __init__ (self, parent):
		global filename
		self.parent = parent
		self.sound = {}
		self.music = {}
		if self.parent.root is None:
			return
		self.sound = self.detect ('sound', ('wav',), sounds)
		self.music = self.detect ('music', ('mid', 'ogg'), musics)
	def detect (self, dirname, exts, initial):
		ret = {}
		codes = set ()
		other = []
		for prefix, d in pathsearch (self.parent, dirname):
			for s in os.listdir (d):
				for e in exts:
					if s.endswith (os.extsep + e):
						break
				else:
					continue
				r = re.match ('(.*?)(-(\d+))?' + os.extsep + e + '$', s)
				nice_assert (r, 'file %s has wrong name, must be from %s' % (s, str (exts)))
				filename = os.path.join (d, s)
				data = (filename, 0, os.stat (filename).st_size)
				code = r.group (3)
				if not code:
					other += ((prefix + r.group (1), data, e),)
				else:
					code = int (code)
					ret[prefix + r.group (1)] = (code, data, True, e)
					nice_assert (code not in codes, 'duplicate definition of sound %d' % code)
					codes.add (code)
		for i in initial:
			if initial[i][0] not in codes:
				ret[i] = (initial[i][0], initial[i][1], False, initial[i][2])
				codes.add (initial[i][0])
		i = 1
		for s in other:
			while i in codes:
				i += 1
			ret[s[0]] = (i, s[1], True, s[2])
			i += 1
		return ret
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
		if len ([1 for x in self.sound if self.sound[x][2]]) > 0:
			d = os.path.join (self.parent.root, "sound")
			os.mkdir (d)
			for i in self.sound:
				if not self.sound[i][2]:
					continue
				data = filepart (*self.sound[i][1]).read ()
				open (os.path.join (d, '%s-%d' % (i, self.sound[i][0]) + os.extsep + self.sound[i][3]), 'wb').write (data)
		if len ([x for x in self.music if self.music[x][2]]) > 0:
			d = os.path.join (self.parent.root, "music")
			os.mkdir (d)
			for i in self.music:
				if not self.music[i][2]:
					continue
				data = filepart (*self.music[i][1]).read ()
				open (os.path.join (d, '%s-%d' % (i, self.music[i][0]) + os.extsep + self.music[i][3]), 'wb').write (data)
	def rename (self, old, new):
		for i in self.sound:
			if self.sound[i][2] and self.sound[i][1][0].startswith (old):
				self.sound[i] = (self.sound[i][0], (new + self.sound[i][1][0][len (old):], self.sound[i][1][1], self.sound[i][1][2]), self.sound[i][2], self.sound[i][3])
		for i in self.music:
			if self.music[i][2] and self.music[i][1][0].startswith (old):
				self.music[i] = (self.music[i][0], (new + self.music[i][1][0][len (old):], self.music[i][1][1], self.music[i][1][2]), self.music[i][2], self.music[i][3])
	def build (self, root):
		# Write sound/*
		dst = os.path.join (root, 'sound')
		if not os.path.exists (dst):
			os.mkdir (dst)
		src = os.path.join (self.parent.root, 'sound')
		for s in self.sound:
			if not self.sound[s][2]:
				continue
			data = filepart (*self.sound[s][1]).read ()
			open (os.path.join (dst, s + os.extsep + self.sound[s][3]), 'wb').write (data)
		for s in self.music:
			if not self.music[s][2]:
				continue
			data = filepart (*self.music[s][1]).read ()
			open (os.path.join (dst, str (self.music[s][0]) + os.extsep + self.music[s][3]), 'wb').write (data)
# }}}

class Script: #{{{
	def create_defaults (self):
		if 'intro' not in self.data:
			self.data['intro'] = '''\
void main ()
{
	// The intro script must put Dink at his starting position.
	player_map = 400;
	sp_x (1, 320);
	sp_y (1, 200);
}
'''
		if 'start' not in self.data:
			self.data['start'] = '''\
int make_button (int button)
{
	sp_noclip (button, 1);
	sp_touch_damage (button, -1);
	return button;
}

void main ()
{
	fill_screen (0);
	sp_script (make_button (create_sprite (76, 40, "button", "button-start", 1)), "game-start");
	sp_script (make_button (create_sprite (524, 40, "button", "button-continue", 1)), "game-continue");
	sp_script (make_button (create_sprite (560, 440, "button", "button-quit", 1)), "game-quit");
}
'''
			if 'game-start' not in self.data:
				self.data['game-start'] = '''\
void buttonon ()
{
	sp_pframe (current_sprite, 2);
}

void buttonoff ()
{
	sp_pframe (current_sprite, 1);
}

void click ()
{
	start_game ();
	kill_this_task ();
}
'''
			if 'game-continue' not in self.data:
				self.data['game-continue'] = '''\
void buttonon ()
{
	sp_pframe (current_sprite, 2);
}

void buttonoff ()
{
	sp_pframe (current_sprite, 1);
}

void click ()
{
	int game = choice ("&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"Nevermind");
	if (game == 11 || !game_exist (game))
		return;
	stopmidi ();
	stopcd ();
	load_game (game);
	kill_this_task ();
}
'''
			if 'game-quit' not in self.data:
				self.data['game-quit'] = '''\
void buttonon ()
{
	sp_pframe (current_sprite, 2);
}

void buttonoff ()
{
	sp_pframe (current_sprite, 1);
}

void click ()
{
	kill_game ();
}
'''
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		if self.parent.root is None:
			self.create_defaults ()
			return
		d = os.path.join (parent.root, "script")
		if os.path.exists (d):
			for s in os.listdir (d):
				ext = os.extsep + 'c'
				if not s.endswith (ext):
					continue
				base = s[:-len (ext)]
				nice_assert (base not in self.data, 'duplicate definition of script %s' % base)
				self.data[base] = open (os.path.join (d, s)).read ()
		self.create_defaults ()
	def save (self):
		d = os.path.join (self.parent.root, "script")
		k = set (self.data.keys ())
		if len (k) > 0:
			os.mkdir (d)
			for s in k:
				open (os.path.join (d, s + os.extsep + 'c'), 'w').write (self.data[s])
	def find_functions (self, script, funcs):
		global max_args
		my_statics = []
		my_globals = []
		while True:
			t, script, isname = token (script)
			if t is None:
				break
			if t in ('static', 'extern'):
				is_static = t == 'static'
				t, script, isname = token (script)
				if nice_assert (t == 'int', 'missing "int" for global variable declaration'):
					name, script, isname = token (script)
				nice_assert (isname, 'missing variable name for global variable declaration')
				t, script, isname = token (script)
				if not nice_assert (t == ';', 'missing semicolon after global variable declaration'):
					script = t + ' ' + script
				if is_static:
					if nice_assert (name not in my_statics, "duplicate declaration of static variable"):
						my_statics += (name,)
				else:
					if nice_assert (name not in my_globals, "duplicate declaration of global variable"):
						my_globals += (name,)
				continue
			if not nice_assert (t == 'int' or t == 'void', 'syntax error while searching for function (found %s): ' % t + script):
				continue
			rettype = t
			t, script, isname = token (script)
			nice_assert (isname, 'missing function name')
			name = t
			t, script, isname = token (script)
			nice_assert (t == '(', 'missing function name')
			# Read argument names
			args = []
			t, script, isname = token (script)
			while t != ')':
				if nice_assert (t == 'int', 'missing argument type'):
					t, script, isname = token (script)
				if nice_assert (isname, 'missing argument name'):
					args += (t,)
				t, script, isname = token (script)
				nice_assert (t in (')', ','), 'syntax error in argument list')
				if t == ',':
					t, script, isname = token (script)
			t, script, isname = token (script)
			nice_assert (t == '{', 'missing function body')
			depth = 1
			while depth > 0:
				t, script, isname = token (script)
				if t is None:
					nice_assert (False, 'function %s is not finished at end of file' % name)
					break
				elif t == '{':
					depth += 1
				elif t == '}':
					depth -= 1
			funcs[name] = [rettype, args]
			if max_args < len (args):
				max_args = len (args)
		funcs[''] = my_statics, my_globals
	def compile (self, used = None):
		'''Compile all scripts. Return a dictionary of files, each value in it is a dictionary of functions, each value is a sequence of statements.
		It also fills the functions dictionary, which has fnames as keys and a dict of name:(retval, args) as values, plus '':[statics].
		Statics is a list of names.'''
		global functions
		global filename
		functions = {}
		ret = {}
		for name in self.data:
			ret[name.lower ()] = {}
			functions[name.lower ()] = {}
			filename = name
			self.find_functions (self.data[name], functions[name.lower ()])
		for name in self.data:
			filename = name
			for f in tokenize (self.data[name.lower ()], self.parent, name.lower (), used = used):
				ret[name.lower ()][f[0]] = f[2]
		return ret
	def find_used_sprites (self):
		ret = [set (), set ()]
		self.compile (used = ret)
		return ret
	def build (self, root):
		# Write story/*
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
		if error_message != '':
			return
		for i in the_globals:
			newmangle (i)
		for name in self.data:
			filename = name
			f = open (os.path.join (d, name + os.extsep + 'c'), 'w')
			f.write (preprocess (self.data[name], self.parent, name))
		# Write main.c
		s = open (os.path.join (d, 'main' + os.extsep + 'c'), 'w')
		s.write ('void main ()\r\n{\r\n')
		nice_assert (len (the_globals) + max_args <= 248, 'too many global variables (%d, max is 248)' % (len (the_globals) + max_args))
		for v in the_globals:
			s.write ('\tmake_global_int ("%s", %d);\r\n' % (mangle (v), the_globals[v]))
		clear_mangled (the_globals)
		nice_assert (len (mangled_names) == 0, 'mangled names remaining: %s' % repr (mangled_names))
		for a in range (max_args):
			s.write ('\tmake_global_int ("&arg%d", 0);\r\n' % a)
		for snd in self.parent.sound.sound:
			s.write ('\tload_sound("%s.wav", %d);\r\n' % (snd, self.parent.sound.sound[snd][0]))
		s.write ('\tkill_this_task ();\r\n}\r\n')
		# Write _start_game.c
		s = open (os.path.join (d, '_start_game' + os.extsep + 'c'), 'wb')
		s.write ('''\
void main ()\r
{\r
	script_attach (1000);\r
	wait (1);\r
	sp_base_walk (1, %d);\r
	sp_base_attack (1, %d);\r
	set_dink_speed (3);\r
	set_mode (2);\r
	wait (1);\r
	reset_timer ();\r
	sp_dir (1, 4);\r
	sp_brain (1, %d);\r
	sp_que (1, 0);\r
	sp_noclip (1, 0);\r
%s	dink_can_walk_off_screen (0);\r
%s	load_screen ();\r
	draw_screen ();\r
	&update_status = 1;\r
	draw_status ();\r
	fade_up ();\r
	kill_this_task ();\r
}\r
''' % (self.parent.seq.collection_code ('walk'), self.parent.seq.collection_code ('hit'), make_brain ('dink'), ('\texternal ("intro", "main");\r\n' if 'intro' in self.data else ''), ('\texternal ("init", "main");\r\n' if 'init' in self.data else '')))
# }}}

class Images: #{{{
	def __init__ (self, parent):
		self.parent = parent
		self.images = {}
		if self.parent.root is None:
			return
		for prefix, im in pathsearch (parent, 'image'):
			for i in os.listdir (im):
				ext = os.extsep + 'png'
				if i.endswith (ext):
					name = os.path.join (im, i)
					self.images[prefix + i[:-len (ext)]] = (name, 0, os.stat (name).st_size)
	def save (self):
		im = os.path.join (self.parent.root, 'image')
		imgs = [x for x in self.images.keys () if not '.' in x]
		if len (imgs) > 0:
			os.mkdir (im)
			for i in imgs:
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
# }}}

class Dink: #{{{
	def __init__ (self, root):
		global filename, read_cache
		if not read_cache:
			global tilefiles, collections, sequences, codes, musics, sounds
			tilefiles, collections, sequences, codes, musics, sounds = pickle.load (open (os.path.join (cachedir, 'data'), 'rb'))
			read_cache = True
		self.config = read_config ()
		assert 'dinkdir' in self.config and 'dmoddir' in self.config and 'editdir' in self.config and 'dinkprog' in self.config
		if root is None:
			self.root = None
		else:
			self.root = os.path.abspath (os.path.normpath (root))
			filename = os.path.join (self.root, 'info' + os.extsep + 'txt')
		if root is not None and os.path.exists (filename):
			f = open (filename)
			info = readlines (f)
			self.info = f.read ()
			info, preview = get (info, 'preview', '')
			info, splash = get (info, 'splash', '')
			self.layer_visible = [None] * 10
			self.layer_background = [None] * 10
			for i in range (10):
				info, self.layer_visible[i] = get (info, 'visible-%d' % i, i != 9)
				info, self.layer_background[i] = get (info, 'background-%d' % i, i in (0, 9))
			info, d = get (info, 'depends', '')
			self.depends = d.split ()
			nice_assert (info == {}, 'unused data')
		else:
			preview = ''
			splash = ''
			self.layer_visible = [i != 9 for i in range (10)]
			self.layer_background = [i in (0, 9) for i in range (10)]
			self.depends = []
			self.info = '''\
%s

This file should describe the game. If this text is still here and you are not
the author of the game, please inform the author that they should update this
file (info.txt).
''' % ('dmodname' if root is None else os.path.basename (root))
		self.image = Images (self)
		self.image.preview = preview
		self.image.splash = splash
		self.tile = Tile (self)
		self.seq = Seq (self)
		self.sound = Sound (self)
		self.world = World (self)
		self.script = Script (self)
	def save (self, root = None):
		if root is not None:
			self.root = os.path.abspath (os.path.normpath (root))
		if self.root is None:
			return False
		backup = None
		if os.path.exists (self.root):
			d = os.path.dirname (self.root)
			backupdir = os.path.join (d, 'backup')
			if not os.path.exists (backupdir):
				os.mkdir (backupdir)
			b = os.path.basename (self.root)
			l = os.listdir (backupdir)
			src = [x for x in l if x.startswith (b + '.') and re.match ('^\d+$', x[len (b) + 1:])]
			if src == []:
				backup = os.path.join (backupdir, b + '.0')
			else:
				src.sort (key = lambda x: int (x[len (b) + 1:]))
				backup = os.path.join (backupdir, b + ('.%d' % (int (src[-1][len (b) + 1:]) + 1)))
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
		f = open (os.path.join (self.root, 'info' + os.extsep + 'txt'), 'w')
		put (f, 'preview', self.image.preview, '')
		put (f, 'splash', self.image.splash, '')
		for i in range (10):
			put (f, 'visible-%d' % i, self.layer_visible[i], i != 9)
			put (f, 'background-%d' % i, self.layer_background[i], i in (0, 9))
		f.write ('\r\n' + self.info)
		if backup is not None:
			self.rename (backup, self.root)
		return True
	def rename (self, old, new):
		self.image.rename (old, new)
		self.tile.rename (old, new)
		self.sound.rename (old, new)
		self.seq.rename (old, new)
	def build (self, root = None):
		global error_message
		error_message = ''
		if root is None:
			if self.root is None:
				return
			root = os.path.join (self.config['dmoddir'], os.path.basename (self.root))
		if os.path.exists (root):
			shutil.rmtree (root)
		os.mkdir (root)
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
		return error_message
	def play (self, map = None, x = None, y = None):
		global error_message
		error_message = ''
		if y is not None:
			tmp = (None if 'intro' not in self.script.data else self.script.data['intro']), self.script.data['start']
			if 'intro' in self.script.data:
				del self.script.data['intro']
			self.script.data['start'] = 'void main ()\n{\n\tstart_game ();\n\t\tplayer_map = %d;\n\tsp_x (1, %d);\n\tsp_y (1, %d);\n\tkill_this_task ();\n}\n' % (map, x, y)
		builddir = tempfile.mkdtemp (prefix = 'pydink-test-')
		oldroot = self.root
		self.root = 'playtest'
		try:
			self.build (builddir)
			if os.path.basename (self.config['dinkdir']) == '':
				d = os.path.dirname (os.path.dirname (self.config['dinkdir']))
			else:
				d = os.path.dirname (self.config['dinkdir'])
			if error_message == '':
				os.spawnl (os.P_WAIT, self.config['dinkprog'], self.config['dinkprog'], '-g', builddir, '-r', d, '-w')
		finally:
			self.root = oldroot
			shutil.rmtree (builddir)
			if y is not None:
				intro, self.script.data['start'] = tmp
				if intro is not None:
					self.script.data['intro'] = intro
		return error_message
# }}}
