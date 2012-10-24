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
# It reads hardness, collections and seqs links from dink.ini, tile screens,
# sounds, music.
# }}}

# {{{ Imports
import sys
import os
import re
import Image
import StringIO
import glib
p = os.path.join (glib.get_user_config_dir (), 'pydink')
sys.path += (p,)
import dinkconfig
# }}}

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
dinktree = buildtree (dinkconfig.dinkdir)
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
		paths = ((dmoddir, dmodtree), (dinkconfig.dinkdir, dinktree))
	else:
		paths = ((dinkconfig.dinkdir, dinktree),)
	for p, walk in paths:
		for i in f[:-1]:
			branch = walk[i]
			p = os.path.join (p, branch[0])
			if not os.path.exists (p):
				break
			walk = branch[1]
		else:
			return p, walk, f
	raise AssertionError ('path %s not found in dmod or dinkdir' % '\\'.join (f))
# }}}

def read_lsb (f): # {{{
	ret = 0
	for i in range (4):
		ret += ord (f.read (1)) << (i << 3)
	return ret
# }}}

def loaddinkfile (f): # {{{
	'''Load a file from dinkdir.'''
	p, walk, f = makedinkpath (f)
	if f[-1] in walk:
		path = os.path.join (p, walk[f[-1]][0])
		ret = open (os.path.join (p, walk[f[-1]][0]), 'rb')
		ret.seek (0, 2)
		l = ret.tell ()
		ret.seek (0)
		return ret, (path, 0, l)
	if 'dir.ff' not in walk:
		return None, None
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
		return None, None
	end = read_lsb (dirfile)
	dirfile.seek (offset)
	data = dirfile.read (end - offset)
	return StringIO.StringIO (data), (path, offset, end - offset)
# }}}

def read_hard (): # {{{
	'''read hardness into usable format.'''
	f, junk = loaddinkfile ('hard.dat')
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
					sys.stderr.write ('Warning: invalid hardness in default hard.dat: %d:%d,%d = %d\n' % (t, x, y, p))
					pixels[x, y] = (0, 0, 0, 0)
	defaults = [[read_lsb (f) for x in range (8 * 12 + 32)] for s in range (41)]
	tilefiles = [None] * 41
	for n in range (41):
		junk, tilefiles[n] = loaddinkfile ('tiles\\ts%02d.bmp' % (n + 1))
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
	A collection has 10 members, which can be None or a sequence. (0 is always None.)
	Sequence and Frame members are described below.'''
	dinkini, junk = loaddinkfile ('dink.ini')

	def fill_frame (s, f, im): # {{{
		if 'position' not in dir (sequence_codes[s].frames[f]):
			if sequence_codes[s].position != None:
				sequence_codes[s].frames[f].position = sequence_codes[s].position
			elif im != None:
				# Why is this how the default position is computed? Beats me, blame Seth...
				sequence_codes[s].frames[f].position = (im.size[0] - im.size[0] / 2 + im.size[0] / 6, im.size[1] - im.size[1] / 4 - im.size[1] / 30)
			else:
				src = sequence_codes[s].frames[f].source
				sequence_codes[s].frames[f].position = sequence_codes[src[0]].frames[src[1]].position
		if 'hardbox' not in dir (sequence_codes[s].frames[f]):
			if sequence_codes[s].hardbox != None:
				sequence_codes[s].frames[f].hardbox = sequence_codes[s].hardbox
			elif im != None:
				# Why is this how the default hardbox is computed? Beats me, blame Seth...
				sequence_codes[s].frames[f].hardbox = (-im.size[0] / 4, -im.size[1] / 10, im.size[0] / 4, im.size[1] / 10, False)
			else:
				sequence_codes[s].frames[f].hardbox = sequence_codes[src[0]].frames[src[1]].hardbox
		if 'delay' not in dir (sequence_codes[s].frames[f]):
			sequence_codes[s].frames[f].delay = sequence_codes[s].delay
		if 'source' not in dir (sequence_codes[s].frames[f]):
			sequence_codes[s].frames[f].source = None
	# }}}

	def use (seq, f): # {{{
		if len (seq.frames) == 0:
			seq.frames += (None,)
		while len (seq.frames) <= f:
			seq.frames += (dinkconfig.Frame (),)
	# }}}

	for l in [y.lower ().split () for y in dinkini.readlines ()]:
		if l == [] or l[0].startswith ('//') or l[0].startswith (';') or l[0] == 'starting_dink_x' or l[0] == 'starting_dink_y' or l[0] == 'starting_dink_map':
			pass
		elif l[0] == 'load_sequence' or l[0] == 'load_sequence_now':
			if l == ['load_sequence_now', 'graphics\dink\push\ds-p6-', '316', '75', '67', '71', '-21', '-12', '21']:
				# Bug in original dink.ini.
				sys.stderr.write ('(ignore) warning: setting sprite info for 316 with extra number, because the source is missing it.\n')
				l += ('6',)
			s = int (l[2])
			if s in sequence_codes:
				if 'filepath' in dir (sequence_codes[s]):
					assert 'preload' not in dir (sequence_codes[s])
					preload = sequence_codes[s].filepath
					sequence_codes[s] = dinkconfig.Sequence ()
					sequence_codes[s].frames = []
					sequence_codes[s].preload = preload
			else:
				sequence_codes[s] = dinkconfig.Sequence ()
				sequence_codes[s].frames = []
			sequence_codes[s].filepath = l[1]
			sequence_codes[s].now = l[0] == 'load_sequence_now'
			if len (l) == 3:
				pass
			elif len (l) == 4:
				# Ignore bug in original source.
				if l[3] == 'notanin':
					sys.stderr.write ('(ignore) warning: changing "notanin" into "notanim".\n')
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
				sys.stderr.write ('(ignore) warning: no delay in %s.\n' % l)
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
				sys.stderr.write ('(ignore) warning: setting sprite info for 31 18, because the source is missing the frame.\n')
				l = ['set_sprite_info', '31', '18', '26', '49', '99', '-49', '-10', '51']
			assert len (l) == 9
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dinkconfig.Sequence ()
				sequence_codes[s].frames = []
			use (sequence_codes[s], f)
			sequence_codes[s].frames[f].position = [int (x) for x in l[3:5]]
			sequence_codes[s].frames[f].hardbox = [int (x) for x in l[5:9]]
		elif l[0] == 'set_frame_delay':
			assert len (l) == 4
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dinkconfig.Sequence ()
				sequence_codes[s].frames = []
			#use (sequence_codes[s], f)
			if len (sequence_codes[s].frames) <= f:
				sys.stderr.write ('(ignore) warning: not using frame delay, because %d %d was not defined yet.\n' % (s, f))
			else:
				sequence_codes[s].frames[f].delay =  int (l[3])
		elif l[0] == 'set_frame_frame':
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dinkconfig.Sequence ()
				sequence_codes[s].frames = []
			if len (l) == 5:
				use (sequence_codes[s], f)
				sequence_codes[s].frames[f].source = (int (l[3]), int (l[4]))
				# Fix yet another bug in original dink.ini
				if sequence_codes[s].frames[f].source == (82, 3):
					sys.stderr.write ('(ignore) warning: using 83 3 instead of 82 3 because of bug in original source.\n')
					sequence_codes[s].frames[f].source = (83, 3)
				if sequence_codes[s].frames[f].source == (82, 2):
					sys.stderr.write ('(ignore) warning: using 83 2 instead of 82 2 because of bug in original source.\n')
					sequence_codes[s].frames[f].source = (83, 2)
			else:
				assert len (l) == 4 and int (l[3]) == -1
				sequence_codes[s].repeat = True
		elif l[0] == 'set_frame_special':
			assert len (l) == 4
			s = int (l[1])
			f = int (l[2])
			if s not in sequence_codes:
				sequence_codes[s] = dinkconfig.Sequence ()
				sequence_codes[s].frames = []
			use (sequence_codes[s], f)
			sequence_codes[s].special = f
		else:
			raise AssertionError ('Error: invalid line in dink.ini: %s' % l)

	# A sequence has members:
	#	frames, list with members:
	#		position	Hotspot position. If len (position) == 3, this is a default generated position.
	#		hardbox		Hardbox: left, top, right, bottom. If len (hardbox) == 5, this is a default generated position.
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
	#	special		int, special frame
	#	now		bool, whether to load now
	#	code		int
	#	preload		string, name of sequence to preload into this code
	#	type		normal, notanim, black, or leftalign

	# Fill all open members of all sequences.
	for s in sequence_codes:
		sequence_codes[s].code = s
		assert 'filepath' in dir (sequence_codes[s])
		if 'type' not in dir (sequence_codes[s]):
			sequence_codes[s].type = 'normal'
		if 'preload' not in dir (sequence_codes[s]):
			sequence_codes[s].preload = ''
		if 'now' not in dir (sequence_codes[s]):
			sequence_codes[s].now = False
		if 'special' not in dir (sequence_codes[s]):
			sequence_codes[s].special = None
		if 'repeat' not in dir (sequence_codes[s]):
			sequence_codes[s].repeat = False
		if 'position' not in dir (sequence_codes[s]):
			sequence_codes[s].position = None
		if 'hardbox' not in dir (sequence_codes[s]):
			sequence_codes[s].hardbox = None
		if 'delay' not in dir (sequence_codes[s]):
			sequence_codes[s].delay = 1
		# Read frame information from images.
		f = 1
		boundingbox = [None] * 4
		while True:
			fr, c = loaddinkfile ('%s%02d.bmp' % (sequence_codes[s].filepath, f))
			if fr == None:
				break
			use (sequence_codes[s], f)
			im = Image.open (fr)
			fill_frame (s, f, im)
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
			if 'cache' not in dir (sequence_codes[s].frames[f]):
				sequence_codes[s].frames[f].cache = sequence_codes[sequence_codes[s].frames[f].source[0]].frames[sequence_codes[s].frames[f].source[1]].cache
			if 'boundingbox' not in dir (sequence_codes[s].frames[f]):
				sequence_codes[s].frames[f].boundingbox = sequence_codes[sequence_codes[s].frames[f].source[0]].frames[sequence_codes[s].frames[f].source[1]].boundingbox

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
		assert collections[c[0]] != {}
		collections[c[0]]['name'] = c[0]
		collections[c[0]]['code'] = c[1]
		collections[c[0]]['brain'] = c[2]
		collections[c[0]]['script'] = '' if c[3] == 'none' else c[3]
		collections[c[0]]['attack'] = '' if c[4] == 'none' else c[4]
		collections[c[0]]['death'] = '' if c[5] == 'none' else c[5]

	# Create the sequences.
	sequences = {}
	for s in sequence_names:
		codes.add (s[1])
		sequences[s[0]] = sequence_codes[s[1]]
		sequences[s[0]].name = s[0]
		sequences[s[0]].brain = s[2]
		sequences[s[0]].script = '' if s[3] == 'none' else s[3]
		sequences[s[0]].hard = s[4]
		del sequence_codes[s[1]]

	assert sequence_codes == {}

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
		f, c = loaddinkfile ('sound\\' + root + '.' + ext)
		r = re.match (r'\d+$', root)
		if r:
			r = int (r.group (0))
			musics[root] = (r, c, ext)
			musiccodes.add (r)
		else:
			other.append ((root, c, ext))
	nextcode = 1
	for i in other:
		while nextcode in musiccodes:
			nextcode += 1
		musics[i[0]] = (nextcode, i[1], i[2])
		musiccodes.add (nextcode)
	nextcode += 1

	sounds = {}
	for i in range (len (soundnames)):
		if soundnames[i] != '-':
			f, c = loaddinkfile ('sound\\' + soundnames[i] + '.wav')
			if c == None:
				sys.stderr.write ("(ignore) warning: sound file %s doesn't exist.\n" % soundnames[i])
			sounds[soundnames[i]] = (i + 1, c, 'wav')

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
		for s in data.sound.music:
			if data.sound.music[s][0] == code:
				return s
		return ''
	# }}}
	def read_sprite (f, data, room): # {{{
		"""Read a sprite from map.dat"""
		ret = data.Sprite (data)
		ret.room = room
		ret.x = read_lsb (f) + ((room - 1) % 32) * 50 * 12
		ret.y = read_lsb (f) + ((room - 1) / 32) * 50 * 8
		ret.seq = get_seq (read_lsb (f), data).name
		ret.frame = read_lsb (f)
		t = read_lsb (f)
		if t == 0:
			ret.bg = True
			ret.visible = True
		elif t == 1:
			ret.bg = False
			ret.visible = True
		elif t == 2:
			ret.bg = False
			ret.visible = False
		else:
			sys.stderr.write ('invalid sprite type %d' % t)
			ret.bg = True
			ret.visible = False
		ret.size = read_lsb (f)
		active = read_lsb (f) & 0xff
		read_lsb (f)
		read_lsb (f)
		ret.brain = get_brain (read_lsb (f))
		ret.script = clean (f.read (14))
		f.seek (38, 1)
		ret.speed = read_lsb (f)
		ret.base_walk = get_collection (read_lsb (f), target)['name']
		ret.base_idle = get_collection (read_lsb (f), target)['name']
		ret.base_attack = get_collection (read_lsb (f), target)['name']
		read_lsb (f)
		timer = read_lsb (f)
		ret.que = read_lsb (f)
		ret.hard = read_lsb (f) == 0    # Note: the meaning is inverted, "== 0" is correct!
		ret.left = read_lsb (f)
		ret.top = read_lsb (f)
		ret.right = read_lsb (f)
		ret.bottom = read_lsb (f)
		prop = read_lsb (f)
		warp_map = read_lsb (f)
		warp_x = read_lsb (f)
		warp_y = read_lsb (f)
		if prop:
			ret.warp = [warp_map, warp_x, warp_y]
		else:
			ret.warp = None
		ret.touch_seq = get_seq (read_lsb (f), target).name
		ret.base_die = get_collection (read_lsb (f), target)['name']
		ret.gold = read_lsb (f)
		ret.hitpoints = read_lsb (f)
		ret.strength = read_lsb (f)
		ret.defense = read_lsb (f)
		ret.exp = read_lsb (f)
		ret.sound = get_sound (read_lsb (f), target)
		ret.vision = read_lsb (f)
		ret.nohit = read_lsb (f) != 0
		ret.touch_damage = read_lsb (f)
		for k in range (5):
			read_lsb (f)
		if not active:
			return None
		data.world.sprite.add (ret)
		ret.register ()
		return ret
	# }}}
	def read_tile (f): # {{{
		"""Read a tile from map.dat"""
		ret = [0, 0, 0]
		n = read_lsb (f)
		ret[0] = n / 128
		n %= 128
		ret[1] = n % 12
		ret[2] = n / 12
		f.seek (4, 1)
		althard = read_lsb (f)
		f.seek (68, 1)
		return ret, althard
	# }}}
	def read_screen (f, data, roomnum, hard, defaulthard): # {{{
		"""Read a screen, including tiles and sprites, from map.dat"""
		room = dink.Room (data)
		f.seek (20, 1)
		hard = [None] * 8 * 12
		for y in range (8):
			for x in range (12):
				room.tiles[y][x], hard[y * 12 + x] = read_tile (f)
		# TODO: build hard image and keep it if it's not default.
		# end marker: ignore.
		read_tile (f)
		# junk to ignore.
		f.seek (160 + 80, 1)
		for s in range (100):
			spr = read_sprite (f, data, roomnum)
			if spr:
				if type (spr.seq) == str:
					name = spr.seq
				else:
					name = '%s-%d' % spr.seq
		# end marker: ignore.
		read_sprite (f, target, None)
		room.script = clean (f.read (21))
		f.seek (1019, 1)
		return room
	# }}}
	screens = [[0, 0, 0] for i in range (768)]
	f = loaddinkfile ('dink.dat')[0]
	f.seek (20)
	for a in range (3):
		for s in range (768):
			screens[s][a] = read_lsb (f)
	f.close ()
	f = loaddinkfile ('map.dat')[0]
	for s in range (len (screens)):
		if screens[s][0] == 0:
			continue
		f.seek (31280 * (screens[s][0] - 1))
		room = read_screen (f, data, s, hard, defaulthard)
		room.music = get_music (screens[s][1], data)
		room.indoor = screens[s][2] != 0
		data.world.room[s] = room
# }}}
