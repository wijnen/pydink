# readdmod - read dmod files for pydink programs.
# vim: set fileencoding=utf-8 foldmethod=marker :

# Copyright 2011-2012 Bas Wijnen {{{
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

# {{{ Documentation.
# This code is called by makecache to parse all stuff from the original game,
# and by decompile to parse a dmod.
# It reads hardness, collections and seqs links from dink.ini, tile maps,
# sounds, music.
# }}}

# {{{ Imports
import sys
import os
import re
import Image
import StringIO
import dink
# }}}

is_setup = False
dinkdir = ''
err = ''

# {{{ Names.
collection_names = [(lambda t:(t[0], int (t[1]), t[2], t[3], t[4], t[5]))(x.split ()) for x in '''\
idle 10 repeat none none none
duck 20 duck none none none
pig 40 pig none none none
walk 70 monster none hit none
hit 100 play none none none
duckbloody 110 monster none none none
duckhead 120 mark none none none
pillbug 130 monster en-pill none pillbugdie
pillbugdie 140 mark none none none
dragon 200 rook en-drag none dragondie
dragondie 210 mark none none none
redmaiden 220 person none none none
oldman 230 person none none none
brownmaiden 240 person none none none
bluemaiden 250 person none none none
fairy 260 person none none none
redknight 270 person none redknightattack none
blueknight 280 person none blueknightattack none
silverknight 290 person none silverknightattack none
goldknight 300 person none goldknightattack none
push 310 repeat none none none
shoot 320 repeat none none none
girl 330 person none none none
merchant 340 person none none none
mom 350 person none none none
brownmom 360 person none none none
bluemerchant 370 person none none none
greenmerchant 380 person none none none
purplemerchant 390 person none none none
soldier 400 person none none none
peasant 410 person none none none
comet 500 missile none none none
fireball 510 missile none none none
seeding 520 mark none none none
bonca 530 monster en-bonc boncaattack boncadie
boncaattack 540 repeat none none none
boncadie 550 mark none none none
purplegnome 560 person none none none
bluegnome 570 person none none none
greengnome 580 person none none none
grayboncaattack 590 repeat none none none
graybonca 600 monster en-bong grayboncaattack boncadie
purplebonca 610 monster en-bonc1 purpleboncaattack boncadie
purpleboncaattack 620 repeat none none none
slayerattack 630 repeat none none none
slayer 640 monster en-slay slayerattack none
bluepuddle 650 monster en-slimb none bluepuddledie
bluepuddledie 660 mark none none none
greenpuddle 670 monster en-slimg none greenpuddledie
greenpuddledie 680 mark none none none
redpuddle 690 monster en-slim none redpuddledie
redpuddledie 700 mark none none none
redknightattack 710 repeat none none none
silverknightattack 720 repeat none none none
blueknightattack 730 repeat none none none
goldknightattack 740 repeat none none none
hammergoblinattack 750 repeat none none none
hammergoblin 760 person none hammergoblinattack none
horngoblinattack 770 repeat none none none
horngoblin 780 person none horngoblinattack none
goblinattack 790 repeat none none none
goblin 800 person none goblinattack none
giantattack 810 repeat none none none
giant 820 monster en-gh giantattack none
spikeidle 830 monster en-bonc none none
spike 840 monster en-bonc none none'''.split ('\n')]

sequence_names = [(x.split ()[0], int (x.split ()[1]), x.split ()[2], x.split ()[3], (x.split ()[4] == 'hard')) for x in '''\
special 10 none none nohard
treefire 20 play none hard
arrow 25 repeat none nohard
textbox 30 none none nohard
innwalls 31 none none hard
tree 32 none none hard
outinn 33 none none hard
doorleft 50 none none hard
doorright 51 none none hard
heart 52 repeat heart hard
goldheart 53 repeat gheart hard
smallheart 54 repeat sheart hard
bluebottle 55 repeat bpotion hard
redbottle 56 repeat rpotion hard
purplebottle 57 repeat ppotion hard
bridge 58 none none nohard
cabin 59 none none hard
church 60 none none hard
doorout1 61 none none hard
doorout2 62 none none hard
home 63 none none hard
inacc 64 none none hard
grass 65 none none nohard
garden 66 none none nohard
castle 67 none none hard
doorcastle 68 none none hard
gatecastle 69 none none hard
explode 70 play none hard
crazybottle 75 repeat apotion hard
wallstone 80 none none hard
snakeb 81 repeat none nohard
snakec 82 repeat none nohard
snakem 83 repeat none nohard
teleport 84 repeat none hard
axe 85 repeat none nohard
fire 86 repeat fire hard
table 87 none none hard
crack 89 none none nohard
grave 90 none none hard
forest 91 none none hard
beach 92 none none nohard
fence 93 none none hard
spray 94 repeat none nohard
rock 95 none none hard
building 96 none none hard
rocks 97 none none hard
castle-l 150 none none hard
castle-la 151 none none hard
castle-r 152 none none hard
castle-ra 153 none none hard
damage 154 none none nohard
fire2 155 repeat fire hard
fire3 156 repeat fire hard
fire4 157 repeat fire hard
hole 158 none none nohard
monument 159 none none hard
atomc 161 none none nohard
circle 162 none none nohard
bluestar-fast 163 repeat none hard
magic1 164 repeat none nohard
shiny 165 repeat none nohard
spark 166 repeat none nohard
shock 167 repeat none hard
whirl 168 repeat none hard
bluestar 169 repeat none hard
redstar 170 repeat none hard
blast 171 repeat none hard
barrel 173 none none hard
redbarrel 174 none none hard
chest1 175 none none hard
chest2 176 none none hard
chest3 177 none none hard
coin 178 none none hard
bush 179 none none hard
status 180 none none nohard
nums 181 none none nohard
numr 182 none none nohard
numb 183 none none nohard
nump 184 none none nohard
numy 185 none none nohard
landmark 186 none none hard
spurt 187 none none nohard
spurtl 188 none none nohard
spurtr 189 none none nohard
health-w 190 none none nohard
health-g 191 none none nohard
button-ordering 192 none none nohard
button-quit 193 none none nohard
button-start 194 none none nohard
button-continue 195 none none nohard
title 196 none none nohard
startme1 197 none none nohard
startme3 198 none none nohard
startme7 199 none none nohard
startme9 200 none none nohard
bomb 420 none none nohard
food 421 none none hard
paper 422 none none hard
menu 423 none none hard
island 424 none none nohard
torch 425 none none hard
boatman3 426 repeat none hard
fire1 427 repeat fire hard
stairs 428 none none hard
catapult 429 none none hard
seed4 430 mark none nohard
seed6 431 mark none nohard
shadow 432 shadow none nohard
splash 433 repeat none nohard
bluefish 434 repeat none nohard
yellowfish 435 repeat none nohard
die 436 play none nohard
item-m 437 none none nohard
item-w 438 none none nohard
fishx 439 none none nohard
blueflop 440 repeat none nohard
yellowflop 441 repeat none nohard
level 442 none none nohard
box1 443 none none hard
box3 444 none none hard
box 445 none none hard
tomb 446 none none hard
tool 447 none none hard
cup 448 none none hard
save 449 repeat savebot hard
health-br 450 none none nohard
health-r 451 none none nohard
crawl 452 play none nohard
arrow-l 456 none none nohard
arrow-r 457 none none nohard
sign 458 none none hard
shelf 459 none none hard
lab 460 none none hard
chair 461 none none hard
poster 462 none none hard
grain 463 none none hard
horngoblinattackswing 780 repeat none nohard'''.split ('\n')]

soundnames = '''
quack
pig1
pig2
pig3
pig4
burn
open
swing
punch
sword2
select
wscream
picker
gold
grunt1
grunt2
sel1
escape
nono
sel2
sel3
high2
fire
spell1
-
snarl1
snarl2
snarl3
hurt1
hurt2
attack1
caveent
level
save
splash
sword1
bhit
squish
stairs
steps
arrow
flyby
secret
bow1
knock
drag1
drag2
axe
bird1
'''.split ()
# }}}

def buildtree (d): # {{{
	'''Create lowercase tree of all files in dinkdir.'''
	ret = {}
	for l in os.listdir (d):
		p = os.path.join (d, l)
		if os.path.isdir (p):
			ret[l.lower ()] = (l, buildtree (p))
		else:
			ret[l.lower ()] = (l,)
	return ret
# }}}

def setup (dir): # {{{
	global dinkdir, dinktree, is_setup
	dinkdir = dir
	dinktree = buildtree (dinkdir)
	is_setup = True
# }}}

def set_dmoddir (d): # {{{
	global dmoddir, dmodtree
	dmoddir = d
	dmodtree = buildtree (dmoddir)
dmoddir = None
dmodtree = None
# }}}

def makedinkpath (f): # {{{
	'''Get real path from dinkdir.'''
	f = f.split ('\\')
	if dmodtree != None:
		paths = ((dmoddir, dmodtree, True), (dinkdir, dinktree, False))
	else:
		paths = ((dinkdir, dinktree, False),)
	for p, walk, from_dmod in paths:
		for i in f[:-1]:
			if i not in walk:
				break
			branch = walk[i]
			p = os.path.join (p, branch[0])
			if not os.path.exists (p):
				break
			walk = branch[1]
		else:
			return p, walk, f, from_dmod
	print ('Warning: path %s not found in dmod or dinkdir' % '\\'.join (f))
	return None, None, None, None
# }}}

def parse_lsb (s): # {{{
	ret = 0
	for i in range (4):
		ret += ord (s[i]) << (i << 3)
	return ret
# }}}

def read_lsb (f): # {{{
	ret = 0
	for i in range (4):
		ret += ord (f.read (1)) << (i << 3)
	return ret
# }}}

def loaddinkfile (f): # {{{
	'''Load a file from dinkdir.'''
	if not is_setup:
		setup (dink.read_config ()['dinkdir'])
	p, walk, f, from_dmod = makedinkpath (f)
	if p is None:
		return None, None, False
	if f[-1] in walk:
		path = os.path.join (p, walk[f[-1]][0])
		ret = open (os.path.join (p, walk[f[-1]][0]), 'rb')
		ret.seek (0, 2)
		l = ret.tell ()
		ret.seek (0)
		return ret, (path, 0, l), from_dmod
	if 'dir.ff' not in walk:
		return None, None, False
	path = os.path.join (p, walk['dir.ff'][0])
	dirfile = open (path, 'rb')
	n = read_lsb (dirfile) - 1
	for i in range (n):
		offset = read_lsb (dirfile)
		name = dirfile.read (13).rstrip ('\0').lower ()
		if name == f[-1]:
			break
		offset = None
	if offset == None:
		return None, None, False
	end = read_lsb (dirfile)
	dirfile.seek (offset)
	data = dirfile.read (end - offset)
	return StringIO.StringIO (data), (path, offset, end - offset), from_dmod
# }}}

def read_hard (): # {{{
	'''read hardness into usable format.'''
	f, junk, junk = loaddinkfile ('hard.dat')
	data = [None] * 800
	for t in range (800):
		dat = f.read (2608)
		data[t] = Image.new ('RGBA', (50, 50), None)
		pixels = data[t].load ()
		for y in range (50):
			for x in range (50):
				# Watch out! The x and y are reversed. Why, Seth???
				p = ord (dat[x * 51 + y])
				if p == 0:
					pixels[x, y] = (0, 0, 0, 0)
				elif p in (1, 3):
					pixels[x, y] = (255, 255, 255, 255)
				elif p == 2:
					pixels[x, y] = (0, 0, 255, 255)
				else:
					global err
					err += 'Warning: invalid hardness in default hard.dat: %d:%d,%d = %d\n' % (t, x, y, p)
					pixels[x, y] = (0, 0, 0, 0)
	dat = f.read ((8 * 12 + 32) * 41 * 4)
	defaults = [None] * 41
	for s in range (41):
		ps = (8 * 12 + 32) * s
		defaults[s] = [0] * (8 * 12 + 32)
		for x in range (8 * 12 + 32):
			px = (ps + x) * 4
			if len (dat) < px + 4:
				break
			defaults[s][x] = parse_lsb (dat[px:px + 4])
	tilefiles = [None] * 41
	for n in range (41):
		junk, tilefiles[n], from_dmod = loaddinkfile ('tiles\\ts%02d.bmp' % (n + 1))
		tilefiles[n] = (tilefiles[n], from_dmod)
	return data, defaults, tilefiles
# }}}

sequence_codes = {}

def set_custom (cols, seqs): # {{{
	for c in cols:
		#TODO
		pass
# }}}

def read_ini (): # {{{
	'''read dink.ini; make a list of sequences and sequence collections using the name list at the start.
	Result is a list of collections and a list of sequences.
	A collection has members 1-9\\5 and 'die', which can be None or a sequence.
	Graphics from the dmod ignore the namelist and are never collections.
	Sequence and Frame members are described below.'''
	global err
	dinkini, junk, junk = loaddinkfile ('dink.ini')

	def fill_frame (s, f, im): # {{{
		if not hasattr (sequence_codes[s].frames[f], 'position'):
			if sequence_codes[s].position != None:
				sequence_codes[s].frames[f].position = sequence_codes[s].position
			elif im != None:
				# Why is this how the default position is computed? Beats me, blame Seth...
				sequence_codes[s].frames[f].position = (im.size[0] - im.size[0] / 2 + im.size[0] / 6, im.size[1] - im.size[1] / 4 - im.size[1] / 30)
			elif hasattr (sequence_codes[s].frames[f], 'source'):
				src = sequence_codes[s].frames[f].source
				sequence_codes[s].frames[f].position = sequence_codes[src[0]].frames[src[1]].position
			else:
				if hasattr (sequence_codes[s], 'filepath'):
					# If it doesn't a warning has already been printed.
					print ('Warning: seq %d %d has no image and no source' % (s, f))
				sequence_codes[s].frames[f].position = (0, 0)
		if not hasattr (sequence_codes[s].frames[f], 'hardbox'):
			if sequence_codes[s].hardbox != None:
				sequence_codes[s].frames[f].hardbox = sequence_codes[s].hardbox
			elif im != None:
				# Why is this how the default hardbox is computed? Beats me, blame Seth...
				sequence_codes[s].frames[f].hardbox = [-im.size[0] / 4, -im.size[1] / 10, im.size[0] / 4, im.size[1] / 10]
			elif hasattr (sequence_codes[s].frames[f], 'source'):
				src = sequence_codes[s].frames[f].source
				sequence_codes[s].frames[f].hardbox = sequence_codes[src[0]].frames[src[1]].hardbox
			else:
				# Warning is already printed for 'position'.
				sequence_codes[s].frames[f].hardbox = [0, 0, 0, 0]
		if not hasattr (sequence_codes[s].frames[f], 'delay'):
			sequence_codes[s].frames[f].delay = sequence_codes[s].delay
		if not hasattr (sequence_codes[s].frames[f], 'source'):
			sequence_codes[s].frames[f].source = None
	# }}}

	def use (seq, f): # {{{
		if len (seq.frames) == 0:
			seq.frames += (None,)
		while len (seq.frames) <= f:
			seq.frames += (dink.Frame (),)
	# }}}

	for l in [y.lower ().split () for y in dinkini.readlines ()]:
		if l == [] or l[0].startswith ('//') or l[0].startswith (';') or l[0] == 'starting_dink_x' or l[0] == 'starting_dink_y' or l[0] == 'starting_dink_map':
			pass
		elif l[0] == 'load_sequence' or l[0] == 'load_sequence_now':
			if l == ['load_sequence_now', 'graphics\dink\push\ds-p6-', '316', '75', '67', '71', '-21', '-12', '21']:
				# Bug in original dink.ini.
				err += '(ignore) warning: setting sprite info for 316 with extra number, because the source is missing it.\n'
				l += ('6',)
			s = int (l[2])
			if s in sequence_codes:
				if hasattr (sequence_codes[s], 'filepath'):
					assert not hasattr (sequence_codes[s], 'preload')
					preload = sequence_codes[s].filepath
					sequence_codes[s] = dink.Sequence ()
					sequence_codes[s].frames = []
					sequence_codes[s].preload = preload
			else:
				sequence_codes[s] = dink.Sequence ()
				sequence_codes[s].frames = []
			sequence_codes[s].filepath = l[1]
			sequence_codes[s].now = l[0] == 'load_sequence_now'
			if len (l) == 3:
				pass
			elif len (l) == 4:
				# Ignore bug in original source.
				if l[3] == 'notanin':
					err += '(ignore) warning: changing "notanin" into "notanim".\n'
					l[3] = 'notanim'
				if l[3] == 'black' or l[3] == 'notanim' or l[3] == 'leftalign':
					sequence_codes[s].type = l[3]
				else:
					sequence_codes[s].delay = int (l[3])
			elif len (l) == 5:
				sequence_codes[s].delay = int (l[3])
				assert l[4] == 'black' or l[4] == 'notanim' or l[4] == 'leftalign'
				sequence_codes[s].type = l[4]
			elif len (l) == 9:
				err += '(ignore) warning: no delay in %s.\n' % l
				sequence_codes[s].position = [int (x) for x in l[3:5]]
				sequence_codes[s].hardbox = [int (x) for x in l[5:9]]
			elif len (l) == 10:
				sequence_codes[s].delay = int (l[3])
				sequence_codes[s].position = [int (x) for x in l[4:6]]
				sequence_codes[s].hardbox = [int (x) for x in l[6:10]]
			else:
				raise AssertionError ('invalid line for load_sequence')
		elif l[0] == 'set_sprite_info':
			if l == ['set_sprite_info', '31', '26', '49', '99', '-49', '-10', '51']:
				# Bug in original dink.ini.
				err += '(ignore) warning: setting sprite info for 31 18, because the source is missing the frame.\n'
				l = ['set_sprite_info', '31', '18', '26', '49', '99', '-49', '-10', '51']
			assert len (l) == 9
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dink.Sequence ()
				sequence_codes[s].frames = []
			use (sequence_codes[s], f)
			sequence_codes[s].frames[f].position = [int (x) for x in l[3:5]]
			sequence_codes[s].frames[f].hardbox = [int (x) for x in l[5:9]]
		elif l[0] == 'set_frame_delay':
			assert len (l) == 4
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dink.Sequence ()
				sequence_codes[s].frames = []
			#use (sequence_codes[s], f)
			if len (sequence_codes[s].frames) <= f:
				err += '(ignore) warning: not using frame delay, because %d %d was not defined yet.\n' % (s, f)
			else:
				sequence_codes[s].frames[f].delay =  int (l[3])
		elif l[0] == 'set_frame_frame':
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dink.Sequence ()
				sequence_codes[s].frames = []
			if len (l) == 5:
				use (sequence_codes[s], f)
				sequence_codes[s].frames[f].source = (int (l[3]), int (l[4]))
				# Fix yet another bug in original dink.ini
				if sequence_codes[s].frames[f].source == (82, 3):
					err += '(ignore) warning: using 83 3 instead of 82 3 because of bug in original source.\n'
					sequence_codes[s].frames[f].source = (83, 3)
				if sequence_codes[s].frames[f].source == (82, 2):
					err += '(ignore) warning: using 83 2 instead of 82 2 because of bug in original source.\n'
					sequence_codes[s].frames[f].source = (83, 2)
			else:
				assert len (l) == 4 and int (l[3]) == -1
				sequence_codes[s].repeat = True
		elif l[0] == 'set_frame_special':
			assert len (l) == 4
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dink.Sequence ()
				sequence_codes[s].frames = []
			use (sequence_codes[s], f)
			sequence_codes[s].frames[f].special = True
		else:
			print ('Warning: ignoring invalid line in dink.ini: %s' % l)

	# A sequence has members:
	#	frames, list with members:
	#		position	Hotspot position. If len (position) == 3, this is a default generated position.
	#		hardbox		Hardbox: left, top, right, bottom. If len (hardbox) == 5, this is a default generated position.
	#		special		bool, special frame
	#		boudingbox	Bounding box: left, top, right, bottom.
	#		delay		Delay value for this frame.
	#		source		For copied frames, source; None otherwise.
	#		cache		Tuple of filename, offset, length of location of file
	#	name		name of the seq (copy of the dictionary key or tuple of collection name, dir)
	#	boudingbox	bounding box: left, top, right, bottom.
	#	delay		default delay.
	#	hardbox		default hardbox
	#	position	default position
	#	filepath	name for use in dink.ini
	#	repeat		bool, whether the sequence is set for repeating
	#	now		bool, whether to load now
	#	code		int
	#	preload		string, name of sequence to preload into this code
	#	type		normal, notanim, black, or leftalign

	# Fill all open members of all sequences.
	for s in sequence_codes:
		sequence_codes[s].code = s
		if not hasattr (sequence_codes[s], 'filepath'):
			print ('Warning: no filepath for sequence %d' % s)
		if not hasattr (sequence_codes[s], 'type'):
			sequence_codes[s].type = 'normal'
		if not hasattr (sequence_codes[s], 'preload'):
			sequence_codes[s].preload = ''
		if not hasattr (sequence_codes[s], 'now'):
			sequence_codes[s].now = False
		if not hasattr (sequence_codes[s], 'repeat'):
			sequence_codes[s].repeat = False
		if not hasattr (sequence_codes[s], 'position'):
			sequence_codes[s].position = None
		if not hasattr (sequence_codes[s], 'hardbox'):
			sequence_codes[s].hardbox = None
		if not hasattr (sequence_codes[s], 'delay'):
			sequence_codes[s].delay = 1
		if not hasattr (sequence_codes[s], 'brain'):
			sequence_codes[s].brain = 'none'
		if not hasattr (sequence_codes[s], 'script'):
			sequence_codes[s].script = ''
		if not hasattr (sequence_codes[s], 'hard'):
			sequence_codes[s].hard = True
		# Read frame information from images.
		f = 1
		boundingbox = [None] * 4
		sequence_codes[s].from_dmod = False
		while True:
			if not hasattr (sequence_codes[s], 'filepath'):
				break
			fr, c, from_dmod = loaddinkfile ('%s%02d.bmp' % (sequence_codes[s].filepath, f))
			if fr == None:
				break
			use (sequence_codes[s], f)
			im = Image.open (fr)
			fill_frame (s, f, im)
			if from_dmod:
				sequence_codes[s].from_dmod = True
			sequence_codes[s].frames[f].cache = c
			sequence_codes[s].frames[f].boundingbox = (-sequence_codes[s].frames[f].position[0], -sequence_codes[s].frames[f].position[1], im.size[0] - sequence_codes[s].frames[f].position[0], im.size[1] - sequence_codes[s].frames[f].position[1])
			if boundingbox[0] == None or sequence_codes[s].frames[f].boundingbox[0] < boundingbox[0]:
				boundingbox[0] = sequence_codes[s].frames[f].boundingbox[0]
			if boundingbox[1] == None or sequence_codes[s].frames[f].boundingbox[1] < boundingbox[1]:
				boundingbox[1] = sequence_codes[s].frames[f].boundingbox[1]
			if boundingbox[2] == None or sequence_codes[s].frames[f].boundingbox[2] > boundingbox[2]:
				boundingbox[2] = sequence_codes[s].frames[f].boundingbox[2]
			if boundingbox[3] == None or sequence_codes[s].frames[f].boundingbox[3] > boundingbox[3]:
				boundingbox[3] = sequence_codes[s].frames[f].boundingbox[3]
			f += 1
		sequence_codes[s].boundingbox = boundingbox
		for f in range (1, len (sequence_codes[s].frames)):
			fill_frame (s, f, None)
		for f in range (1, len (sequence_codes[s].frames)):
			if not hasattr (sequence_codes[s].frames[f], 'special'):
				sequence_codes[s].frames[f].special = False
			if not hasattr (sequence_codes[s].frames[f], 'cache'):
				if sequence_codes[s].frames[f].source is not None:
					sequence_codes[s].frames[f].cache = sequence_codes[sequence_codes[s].frames[f].source[0]].frames[sequence_codes[s].frames[f].source[1]].cache
				else:
					sequence_codes[s].frames[f].cache = None
			if not hasattr (sequence_codes[s].frames[f], 'boundingbox'):
				if sequence_codes[s].frames[f].source is not None:
					sequence_codes[s].frames[f].boundingbox = sequence_codes[sequence_codes[s].frames[f].source[0]].frames[sequence_codes[s].frames[f].source[1]].boundingbox
				else:
					sequence_codes[s].frames[f].boundingbox = (0, 0, 0, 0)

	codes = set ()

	# Create the collections.
	collections = {}
	for c in collection_names:
		collections[c[0]] = {}
		for d in (1,2,3,4,5,6,7,8,9):
			# Seth decided that it would be a good idea to use the death position of duck and walk for other things. :-(
			if d is 5 and c[1] in (20, 70):
				continue
			codes.add (c[1] + d)
			if c[1] + d not in sequence_codes:
				continue
			name = d if d != 5 else 'die'
			collections[c[0]][name] = sequence_codes[c[1] + d]
			collections[c[0]][name].name = (c[0], name)
			del sequence_codes[c[1] + d]
		if collections[c[0]] == {}:
			del collections[c[0]]
			continue
		collections[c[0]]['name'] = c[0]
		collections[c[0]]['code'] = c[1]
		collections[c[0]]['brain'] = c[2]
		collections[c[0]]['script'] = '' if c[3] == 'none' else c[3]
		collections[c[0]]['attack'] = '' if c[4] == 'none' else c[4]
		collections[c[0]]['death'] = '' if c[5] == 'none' else c[5]

	# Create the sequences.
	sequences = {}
	for s in sequence_names:
		if s[1] not in sequence_codes:
			codes.add (s[1])
			name = 'seq%03d' % s[1]
			sequences[name] = dink.Seq.makeseq (name)
			sequences[name].code = s[1]
			sequences[name].from_dmod = False
			continue
		codes.add (s[1])
		sequences[s[0]] = sequence_codes[s[1]]
		sequences[s[0]].name = s[0]
		sequences[s[0]].brain = s[2]
		sequences[s[0]].script = '' if s[3] == 'none' else s[3]
		sequences[s[0]].hard = s[4]
		sequences[s[0]].from_dmod = sequence_codes[s[1]].from_dmod
		del sequence_codes[s[1]]

	for s in sequence_codes:
		codes.add (s)
		name = 'seq%03d' % s
		sequences[name] = sequence_codes[s]
		sequences[name].name = name
		sequences[name].code = s
		sequences[name].from_dmod = sequence_codes[s].from_dmod

	def seq_name (code):
		for s in sequences:
			if sequences[s].code == code:
				return sequences[s].name
		for c in collections:
			for s in collections[c]:
				if s not in (1, 2, 3, 4, 'die', 6, 7, 8, 9):
					continue
				n = 5 if s == 'die' else s
				if collections[c]['code'] + n == code:
					return collections[c][s].name
		print ('Warning: sequence name not found for code %d' % code)
	# Fix source references.
	for s in sequences:
		for f in sequences[s].frames[1:]:
			if f.source is not None:
				f.source = (seq_name (f.source[0]), f.source[1])
	for c in collections:
		for s in collections[c]:
			if s not in (1, 2, 3, 4, 'die', 6, 7, 8, 9):
				continue
			for f in collections[c][s].frames[1:]:
				if f.source is not None:
					f.source = (seq_name (f.source[0]), f.source[1])

	return collections, sequences, codes
# }}}

def read_sound (): # {{{
	p = makedinkpath ('sound\\')[0]
	musics = {}
	musiccodes = set ()
	other = []
	for i in os.listdir (p):
		root, ext = os.path.splitext (i)
		if ext.startswith (os.extsep):
			ext = ext[len (os.extsep):]
		if ext.lower () not in ('ogg', 'mid'):
			continue
		f, c, from_dmod = loaddinkfile ('sound\\' + root + '.' + ext)
		r = re.match (r'\d+$', root)
		if r:
			r = int (r.group (0))
			musics[root] = (r, c, ext, from_dmod)
			musiccodes.add (r)
		else:
			other.append ((root, c, ext, from_dmod))
	nextcode = 1
	for i in other:
		while nextcode in musiccodes:
			nextcode += 1
		musics[i[0]] = (nextcode, i[1], i[2], i[3])
		musiccodes.add (nextcode)
	nextcode += 1

	sounds = {}
	for i in range (len (soundnames)):
		if soundnames[i] != '-':
			f, c, from_dmod = loaddinkfile ('sound\\' + soundnames[i] + '.wav')
			if c == None:
				global err
				err += "(ignore) warning: sound file %s doesn't exist.\n" % soundnames[i]
			sounds[soundnames[i]] = (i + 1, c, 'wav', from_dmod)

	return musics, sounds
# }}}

def read_map (data, hard, defaulthard): # {{{
	def clean (s): # {{{
		"""Clean a string by removing all '\0's from the end."""
		return s[:s.find ('\0')]
	# }}}
	def get_seq (code, data): # {{{
		return data.seq.find_seq (code)
	# }}}
	def get_collection (code, data): # {{{
		return data.seq.find_collection (code)
	# }}}
	def get_brain (code): # {{{
		return dink.brains[code] if 0 <= code < len (dink.brains) else str (code)
	# }}}
	def get_sound (code, data): # {{{
		for s in data.sound.sound:
			if data.sound.sound[s][0] == code:
				return s
		return ''
	# }}}
	def get_music (code, data): # {{{
		if code == 0:
			return ''
		for s in data.sound.music:
			if data.sound.music[s][0] == code:
				return s
		print ('Warning: music not found: %d' % code)
		return ''
	# }}}
	def read_sprite (f, data, map): # {{{
		"""Read a sprite from map.dat"""
		sdata = f.read (220)
		active = parse_lsb (sdata[24:28])
		if not active:
			return None
		ret = dink.Sprite (data)
		ret.map = map
		ret.x = parse_lsb (sdata[0:4]) + ((map - 1) % 32) * 50 * 12	# 4	  0
		ret.y = parse_lsb (sdata[4:8]) + ((map - 1) / 32) * 50 * 8	# 4	  4
		s = get_seq (parse_lsb (sdata[8:12]), data)			# 4	  8
		ret.seq = s.name if s is not None else ''
		ret.rename (ret.seq if isinstance (ret.seq, str) else '%s-%s' % (ret.seq[0], str (ret.seq[1])))
		ret.frame = parse_lsb (sdata[12:16])				# 4	 12
		t = parse_lsb (sdata[16:20])					# 4	 16
		if t == 0:
			ret.layer = 0
		elif t == 1:
			ret.layer = 1
		elif t == 2:
			ret.layer = 9
		else:
			global err
			err += 'invalid sprite type %d' % t
			ret.bg = True
			ret.visible = False
		ret.size = parse_lsb (sdata[20:24])				# 4	 20
		active = parse_lsb (sdata[24:28]) & 0xff			# 4	 24
		# 2 words junk.							# 8      28
		ret.brain = get_brain (parse_lsb (sdata[36:40]))		# 4	 36
		ret.script = clean (sdata[40:54])				# 14	 40
		# 38 bytes junk.						# 38	 54
		ret.speed = parse_lsb (sdata[92:96])				# 4	 92
		c = get_collection (parse_lsb (sdata[96:100]), data)		# 4	 96
		ret.base_walk = c['name'] if c is not None else ''
		c = get_collection (parse_lsb (sdata[100:104]), data)		# 4	100
		ret.base_idle = c['name'] if c is not None else ''
		c = get_collection (parse_lsb (sdata[104:108]), data)		# 4	104
		ret.base_attack = c['name'] if c is not None else ''
		# 1 word junk.							# 4	108
		timer = parse_lsb (sdata[112:116])				# 4	112
		ret.que = parse_lsb (sdata[116:120])				# 4	116
		ret.hard = parse_lsb (sdata[120:124]) == 0			# 4	120 Note: the meaning is inverted, "== 0" is correct!
		ret.left = parse_lsb (sdata[124:128])				# 4	124
		ret.top = parse_lsb (sdata[128:132])				# 4	128
		ret.right = parse_lsb (sdata[132:136])				# 4	132
		ret.bottom = parse_lsb (sdata[136:140])				# 4	136
		prop = parse_lsb (sdata[140:144])				# 4	140
		if prop:
			warp_map = parse_lsb (sdata[144:148])			# 4	144
			warp_x = parse_lsb (sdata[148:152])			# 4	148
			warp_y = parse_lsb (sdata[152:156])			# 4	152
			ret.warp = [warp_map, warp_x, warp_y]
		else:
			ret.warp = None
		s = get_seq (parse_lsb (sdata[156:160]), data)			# 4	156
		ret.touch_seq = s.name if s is not None else ''
		c = get_collection (parse_lsb (sdata[160:164]), data)		# 4	160
		ret.base_death = c['name'] if c is not None else ''
		ret.gold = parse_lsb (sdata[164:168])				# 4	164
		ret.hitpoints = parse_lsb (sdata[168:172])			# 4	168
		ret.strength = parse_lsb (sdata[172:176])			# 4	172
		ret.defense = parse_lsb (sdata[176:180])			# 4	176
		ret.exp = parse_lsb (sdata[180:184])				# 4	180
		ret.sound = get_sound (parse_lsb (sdata[184:188]), data)	# 4	184
		ret.vision = parse_lsb (sdata[188:192])				# 4	188
		ret.nohit = parse_lsb (sdata[192:196]) != 0			# 4	192
		ret.touch_damage = parse_lsb (sdata[196:200])			# 4	196
		# 5 words junk.							# 20	216
		data.world.sprite.add (ret)
		ret.register ()
		return ret
	# }}}
	def read_tile (f): # {{{
		"""Read a tile from map.dat"""
		ret = [0, 0, 0]
		n = read_lsb (f)
		ret[0] = n / 128 + 1
		n %= 128
		ret[1] = n % 12
		ret[2] = n / 12
		f.seek (4, 1)
		althard = read_lsb (f)
		f.seek (68, 1)
		return ret, althard
	# }}}
	def read_map (f, data, mapnum, hard, defaulthard): # {{{
		"""Read a map screen, including tiles and sprites, from map.dat"""
		map = dink.Map (data)
		f.seek (20, 1)
		hard = [None] * 8 * 12
		for y in range (8):
			for x in range (12):
				map.tiles[y][x], hard[y * 12 + x] = read_tile (f)
		# TODO: build hard image and keep it if it's not default.
		# end marker: ignore.
		read_tile (f)
		# junk to ignore.
		f.seek (160 + 80, 1)
		for s in range (100):
			spr = read_sprite (f, data, mapnum)
		# end marker: ignore.
		read_sprite (f, data, 1)
		map.script = clean (f.read (21))
		f.seek (1019, 1)
		return map
	# }}}
	maps = [[0, 0, 0, i] for i in range (769)]
	f = loaddinkfile ('dink.dat')[0]
	f.seek (20)
	for a in range (3):
		for s in range (769):
			maps[s][a] = read_lsb (f)
	f.close ()
	f = loaddinkfile ('map.dat')[0]
	print ('reading %d maps' % len ([0 for m in maps if m[0] != 0]))
	maps.sort (key = lambda x: x[0])
	for m, music, indoor, s in maps:
		if m == 0:
			continue
		sys.stdout.write ('\rreading map %d' % m)
		sys.stdout.flush ()
		f.seek (31280 * (m - 1))
		map = read_map (f, data, s, hard, defaulthard)
		map.music = get_music (music, data)
		map.indoor = indoor != 0
		data.world.map[s] = map
	print ('')
# }}}
