#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

#world
#	nnn-xx-yy
#		info.txt		script, tiles, hardness
#		sprite
#			id.txt		script, x, y, etc.
#tile
#	name-tile.png			tile map (00-41)
#	name-hard.png			hardness for tile map, or for screen
#seq
#	name.gif			sequence
#	name.txt			info about name.gif if it exists, generated sequence otherwise
#sound.txt				list of name filename (number)?
#music.txt				list of name filename (number)?
#script
#	name.c				script to be preprocessed (sound and music names, possibly spacing)

import os
import re
import Image

# brain 0: no brain -- sprite will not do anything automatically
# brain 1: Human [that is, sprite 1 / Dink] brain.
# brain 2: ["Dumb Sprite Bouncer", per DinkEdit.  See below.]
# brain 3: Duck brain.
# brain 4: Pig brain.
# brain 5: When seq is done, kills but leaves last frame drawn to the
# background
# brain 6: Repeat brain - does the active SEQ over and over.
# brain 7: Same as brain 5 but does not draw last frame to the background.
# [brain 8: text sprite brain]
# brain 9: Person/monster ([Only] diagonals)
# brain 10: Person/monster ([No] diagonals)
# brain 11: Missile brain - repeats SEQ [compare brain 17].
# brain 12: Will shrink/grow to match size in sp_brain_parm(), then die
# [WITHOUT giving any experience...]
# brain 13: Mouse brain (for intro, the pointer)
# (do a set_keep_mouse() to use inside game as well)
# brain 14: Button brain.  (intro buttons, can be used in game as well)
# brain 15: Shadow brain.  Shadows for fireballs, etc.
# brain 16: Smart People brain.  They can walk around, stop and look.
# brain 17: Missile brain, [like 11] but kills itself when SEQ is done.

brains = ['none', 'human', 'bounce', 'duck', 'pig', 'mark', 'repeat', 'play', 'text', 'bisshop', 'rook', 'missile', 'resize', 'pointer', 'button', 'shadow', 'person', 'spark']

the_globals = {
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
		"missle_source": 0
	}

seq_names = r'''
idle 10
duck 20
pig 40
walk 70
hit 100
duckbloody 110
duckhead 120
pillbug 130
pillbugdie 140
dragon 200
dragondie 210
redmaiden 220
oldman 230
brownmaiden 240
bluemaiden 250
fairy 260
redknight 270
blueknight 280
silverknight 290
goldknight 300
push 310
shoot 320
girl 330
merchant 340
mom 350
brownmom 360
bluemerchant 370
greenmerchant 380
purplemerchant 390
soldier 400
peasant 410
comet 500
fireball 510
seeding 520
bonca 530
boncaattack 540
boncadie 550
purplegnome 560
bluegnome 570
greengnome 580
grayboncaattack 590
graybonca 600
purplebonca 610
purpleboncaattack 620
slayerattack 630
slayer 640
bluepuddle 650
bluepuddledie 660
greenpuddle 670
greenpuddledie 680
redpuddle 690
redpuddledie 700
redknightattack 710
silverknightattack 720
blueknightattack 730
goldknightattack 740
hammergoblinattack 750
hammergoblin 760
horngoblinattack 770
horngoblin 780
goblinattack 790
goblin 800
giantattack 810
giant 820
spikeidle 830
spike 840

special 10
treefire 20
arrow 25
textbox 30
innwalls 31
tree 32
outinn 33
doorleft 50
doorright 51
heart 52
goldheart 53
smallheart 54
bluebottle 55
redbottle 56
purplebottle 57
bridge 58
cabin 59
church 60
doorout1 61
doorout2 62
home 63
inacc 64
grass 65
garden 66
castle 67
doorcastle 68
gatecastle 69
explode 70
crazybottle 75
wallstone 80
snakeb 81
snakec 82
snakem 83
teleport 84
axe 85
fire 86
table 87
crack 89
grave 90
forest 91
beach 92
fence 93
spray 94
rock 95
building 96
rocks 97
castle-l 150
castle-la 151
castle-r 152
castle-ra 153
damage 154
fire2 155
fire3 156
fire4 157
hole 158
monument 159
atomc 161
circle 162
star2 163
magic1 164
shiny 165
spark 166
shock 167
whirl 168
star2-slow 169
star1 170
blast 171
barrel 173
redbarrel 174
chest1 175
chest2 176
chest3 177
coin 178
bush 179
status 180
nums 181
numr 182
numb 183
nump 184
numy 185
landmark 186
spurt 187
spurtl 188
spurtr 189
health-w 190
health-g 191
button-ordering 192
button-quit 193
button-start 194
button-continue 195
title 196
startme1 197
startme3 198
startme7 199
startme9 200
redmaidendie 225
brownmaidendie 245
bluemaidendie 255
redknightdie 275
blueknightdie 285
silverknightdie 295
goldknightdie 305
girldie 335
merchantdie 345
momdie 355
brownmomdie 365
bluemerchantdie 375
greenmerchantdie 385
purplemerchantdie 395
soldierdie 405
peasantdie 415
bomb 420
food 421
paper 422
menu 423
island 424
torch 425
boatman3 426
fire1 427
stairs 428
catapult 429
seed4 430
seed6 431
shadow 432
splash 433
fish1 434
fish2 435
die 436
item-m 437
item-w 438
fishx 439
flop1 440
flop2 441
level 442
box1 443
box3 444
box 445
tomb 446
tool 447
cup 448
save 449
health-br 450
health-r 451
crawl 452
arrow-l 456
arrow-r 457
sign 458
shelf 459
lab 460
chair 461
poster 462
grain 463
horngoblinattackswing 780
slayerdie 645
hammergoblindie 765
horngoblindie 785
goblindie 805
giantdie 825
'''.split ('\n')
tile_names = r'''
out1
out2
out3
out4
out5
wall1
wall2
water
water2
water3
water4
water5
dry
beach1
beach2
beach3
mud
spike
fire1
fire2
fire3
fire4
fire5
cave1
cave2
cave3
cave4
cave5
ice1
ice2
ice3
ice4
ice5
housel
houser
bfloor1
bfloor2
rfloor1
rfloor2
cave6
grass
'''.split ('\n')
dink_ini = r'''
;dink .ini file, be sure to back it up before you change it!
;NOTE:  This file is rarely directly editted - the DINKEDIT.EXE program can make changes to
;it directly, allowing you to graphically set 'depth dots' and hardboxes. 


//outdated starting commands, not used anymore (scripts couldn't do as much then)
starting_dink_x 334
starting_dink_y 161
starting_dink_map 1

//load dink

load_sequence_now tiles\s 10 BLACK

//dinks idle


load_sequence_now graphics\lands\trees\treefire\tree-f 20 35 81 196 -14 -4 16 17

//special moves to make the idle play backwards

set_frame_frame 12 5 12 3
set_frame_frame 12 6 12 2
set_frame_delay 12 5 250
set_frame_delay 12 6 250

set_frame_frame 14 5 14 3
set_frame_frame 14 6 14 2
set_frame_delay 14 5 250
set_frame_delay 14 6 250

set_frame_frame 16 5 16 3
set_frame_frame 16 6 16 2
set_frame_delay 16 5 250
set_frame_delay 16 6 250

set_frame_frame 18 5 18 3
set_frame_frame 18 6 18 2
set_frame_delay 18 5 250
set_frame_delay 18 6 250


//dink hit

load_sequence_now graphics\dink\walk\ds-w1- 71 43 38 72 -14 -9 14 9
load_sequence_now graphics\dink\walk\ds-w2- 72 43 37 69 -13 -9 13 9
load_sequence_now graphics\dink\walk\ds-w3- 73 43 38 72 -14 -9 14 9
load_sequence_now graphics\dink\walk\ds-w4- 74 43 38 72 -12 -9 12 9

load_sequence_now graphics\dink\walk\ds-w6- 76 43 38 72 -13 -9 13 9
load_sequence_now graphics\dink\walk\ds-w7- 77 43 38 72 -12 -10 12 10
load_sequence_now graphics\dink\walk\ds-w8- 78 43 37 69 -13 -9 13 9
load_sequence_now graphics\dink\walk\ds-w9- 79 43 38 72 -14 -9 14 9

load_sequence_now graphics\dink\idle\ds-i2- 12 250 33 70 -12 -9 12 9
load_sequence_now graphics\dink\idle\ds-i4- 14 250 30 71 -11 -9 11 9
load_sequence_now graphics\dink\idle\ds-i6- 16 250 36 70 -11 -9 11 9
load_sequence_now graphics\dink\idle\ds-i8- 18 250 32 68 -12 -9 12 9

//this is here for reasons to complex to explain.  j/k!  This sequence
//is one that is going to be replaced, so I'm loading the one with the most
//frames first, because max frame count is initted only the first time we
//load into a certain seq #.

load_sequence_now graphics\dink\sword\hit\d-sa2- 102 75 52 92 -23 -12 24 11
load_sequence_now graphics\dink\sword\hit\d-sa4- 104 75 74 90 -23 -13 23 14
load_sequence_now graphics\dink\sword\hit\d-sa6- 106 75 33 92 -18 -14 18 10
load_sequence_now graphics\dink\sword\hit\d-sa8- 108 75 46 109 -17 -16 17 10

load_sequence_now graphics\dink\hit\normal\ds-h2- 102 75 60 72 -19 -9 19 9
load_sequence_now graphics\dink\hit\normal\ds-h4- 104 75 61 73 -19 -10 19 10
load_sequence_now graphics\dink\hit\normal\ds-h6- 106 75 58 71 -18 -10 18 10
load_sequence_now graphics\dink\hit\normal\ds-h8- 108 75 61 71 -19 -10 19 10

//bow weapon diags

load_sequence_now graphics\dink\bow\hit\d-ba1- 101 75 57 84 -20 -12 20 12
load_sequence_now graphics\dink\bow\hit\d-ba3- 103 75 33 86 -19 -13 19 13
load_sequence_now graphics\dink\bow\hit\d-ba7- 107 75 54 82 -19 -11 19 11
load_sequence_now graphics\dink\bow\hit\d-ba9- 109 75 37 78 -21 -10 21 10



//set which frame can 'hit'

set_frame_special 102 3 1
set_frame_special 104 3 1
set_frame_special 106 3 1
set_frame_special 108 3 1
//make it delay on the third sprite for longer than 75

set_frame_delay 102 2 100
set_frame_delay 104 2 100
set_frame_delay 106 2 100
set_frame_delay 108 2 100

//duck walking

load_sequence graphics\animals\duck\dk1w- 21 75 20 30 -13 -10 12 6
load_sequence graphics\animals\duck\dk3w- 23 75 21 30 -14 -9 14 6
load_sequence graphics\animals\duck\dk4w- 24 75 22 27 -14 -7 14 10
//hey I know, let's squeeze the arrow anim in here!
load_sequence graphics\effects\arrow\arrow- 25 75 NOTANIM
load_sequence graphics\animals\duck\dk6w- 26 75 23 28 -19 -7 11 11
load_sequence graphics\animals\duck\dk7w- 27 75 19 29 -14 -7 16 9
load_sequence graphics\animals\duck\dk9w- 29 75 19 30 -15 -9 14 7

//duck walking all bloody

load_sequence graphics\animals\duck\death\dkb1x- 111 75 22 33 -16 -10 12 9
load_sequence graphics\animals\duck\death\dkb3x- 113 75 22 33 -16 -10 12 9
load_sequence graphics\animals\duck\death\dkb7x- 117 75 18 32 -13 -7 12 9
load_sequence graphics\animals\duck\death\dkb9x- 119 18 32 -14 -7 14 10

//lets modify the duck anim so it repeats by itself
set_frame_frame 111 5 -1
set_frame_frame 113 5 -1
set_frame_frame 117 5 -1
set_frame_frame 119 5 -1

//duck's head animation

load_sequence graphics\animals\duck\death\dkh1x- 121 125
load_sequence graphics\animals\duck\death\dkh3x- 123 125
load_sequence graphics\animals\duck\death\dkh7x- 127 125
load_sequence graphics\animals\duck\death\dkh9x- 129 125

//pig

load_sequence graphics\animals\pig\pg-w1- 41 75 34 34 -26 -24 20 4
load_sequence graphics\animals\pig\pg-w3- 43 75 33 34 -24 -17 25 9
load_sequence graphics\animals\pig\pg-w7- 47 75 33 35 -18 -17 22 11
load_sequence graphics\animals\pig\pg-w9- 49 75 35 33 -25 -17 15 11

//misc sprite animations that are not directionally based


//misc sprites (not animations) having to do with backgrounds

load_sequence_now graphics\inter\text-box\main- 30 NOTANIM
load_sequence graphics\inside\innwalls\walls\inn- 31 NOTANIM
load_sequence graphics\lands\trees\tree- 32 NOTANIM
load_sequence graphics\struct\outinn\oinn- 33 NOTANIM

load_sequence graphics\inside\innwalls\door\dri-l- 50 75
load_sequence graphics\inside\innwalls\door\dri-r- 51 75

load_sequence graphics\bonuses\heart\heart 52 75 18 24 -25 -11 24 11

load_sequence graphics\bonuses\heart\gldhrt 53 75 19 24 -22 -12 24 10
load_sequence graphics\bonuses\heart\smhrt 54 75 9 13 -8 -8 10 4
load_sequence graphics\bonuses\bottles\botl-b 55 75 13 43 -12 -9 9 7
load_sequence graphics\bonuses\bottles\botl-r 56 75 13 43 -12 -9 9 7
load_sequence graphics\bonuses\bottles\botl-p 57 75 13 43 -12 -9 9 7
//for the 'crazy bottle'
load_sequence graphics\bonuses\bottles\botl-b 75 75 13 43 -12 -9 9 7
set_frame_frame 75 2 56 2
set_frame_frame 75 3 57 3
set_frame_frame 75 5 56 5
set_frame_frame 75 6 57 6
set_frame_frame 75 8 56 8
set_frame_frame 75 9 57 9
set_frame_frame 75 11 56 11
set_frame_frame 75 12 57 12
set_frame_frame 75 14 57 14

//fix hearts to play backwards too

set_frame_frame 52 6 52 4
set_frame_delay 52 6 75
set_frame_frame 52 7 52 3
set_frame_delay 52 7 75
set_frame_frame 52 8 52 2
set_frame_delay 52 8 75

set_frame_frame 53 6 53 4
set_frame_delay 53 6 75
set_frame_frame 53 7 53 3
set_frame_delay 53 7 75
set_frame_frame 53 8 53 2
set_frame_delay 53 8 75

set_frame_frame 54 6 54 4
set_frame_delay 54 6 75
set_frame_frame 54 7 54 3
set_frame_delay 54 7 75
set_frame_frame 54 8 54 2
set_frame_delay 54 8 75


//outdoor sprites

load_sequence graphics\struct\bridge\brdge- 58 NOTANIM
load_sequence graphics\struct\cabin\cabin- 59 NOTANIM 
load_sequence graphics\struct\church\chrch- 60 NOTANIM
load_sequence graphics\struct\details\door\odor1- 61 75 22 50 -24 -8 6 23
load_sequence graphics\struct\details\door\odor2- 62 75 28 48 -6 -7 29 23
load_sequence graphics\struct\home\home- 63 NOTANIM
load_sequence graphics\inside\details\inacc- 64 NOTANIM
load_sequence graphics\lands\grass\grass- 65 NOTANIM
load_sequence graphics\lands\garden\gardn- 66 NOTANIM
load_sequence graphics\struct\castle\castl- 67 NOTANIM
load_sequence graphics\struct\castle\cdoor- 68 75
load_sequence graphics\struct\castle\cgate- 69 75

load_sequence graphics\effects\splode\explo- 70 40 44 47 -15 -13 15 16

load_sequence graphics\inside\stnwalls\stonw- 80 NOTANIM

load_sequence graphics\inside\stnwalls\snake\snakb- 81 75 10 43 -11 -1 6 1
set_frame_frame 81 6 81 4
set_frame_frame 81 7 81 3
set_frame_frame 81 8 81 2
set_frame_delay 81 6 100
set_frame_delay 81 7 100
set_frame_delay 81 8 100


load_sequence graphics\inside\stnwalls\snake\snakc- 82 75
load_sequence graphics\inside\stnwalls\snake\snakm- 83 100
//lets make the snake reverse
set_frame_frame 83 9 83 7
set_frame_delay 83 9 100
set_frame_frame 83 10 83 6
set_frame_delay 83 10 100
set_frame_frame 83 11 83 5
set_frame_delay 83 11 100
set_frame_frame 83 12 83 4
set_frame_delay 83 12 100
set_frame_frame 83 13 82 3
set_frame_delay 83 13 100
set_frame_frame 83 14 82 2
set_frame_delay 83 14 100


load_sequence graphics\struct\teleport\telep- 84 75 43 168 -43 -46 45 3
load_sequence graphics\effects\axe\wpn02- 85 30 23 63 -12 -9 17 7
load_sequence graphics\inside\details\fire- 86 75 22 48 -24 -15 25 6
load_sequence graphics\inside\details\table- 87 NOTANIM
load_sequence graphics\lands\details\crack- 89 NOTANIM
load_sequence graphics\lands\details\grave- 90 NOTANIM
load_sequence graphics\lands\details\fores- 91 NOTANIM
load_sequence graphics\lands\details\beach- 92 NOTANIM
load_sequence graphics\lands\fence\fence- 93 NOTANIM
load_sequence graphics\lands\garden\spray- 94 75 39 73 -30 -16 38 8
load_sequence graphics\lands\rocks\rock- 95 NOTANIM
load_sequence graphics\struct\building\build- 96 NOTANIM
load_sequence graphics\lands\rocks\rocks- 97 NOTANIM

//pill bug

load_sequence graphics\foes\pill\f1-w1- 131 75 24 29 -18 -12 19 7
load_sequence graphics\foes\pill\f1-w3- 133 75 24 29 -18 -12 19 7

load_sequence graphics\foes\pill\f1-x3- 143 125 22 27 -20 -14 22 6
load_sequence graphics\foes\pill\f1-x1- 141 125 22 27 -20 -14 22 6




load_sequence graphics\struct\castle\c-sl- 150 NOTANIM
load_sequence graphics\struct\castle\c-sla- 151 75
load_sequence graphics\struct\castle\c-sr- 152 NOTANIM
load_sequence graphics\struct\castle\c-sra- 153 75
load_sequence graphics\struct\details\damage\damag- 154 200

//lets make the fire anim play backwards too

set_frame_frame 154 4 154 2
set_frame_delay 154 4 200

load_sequence graphics\struct\details\damage\fire2- 155 250

set_frame_frame 155 4 155 2
set_frame_delay 155 4 250

load_sequence graphics\struct\details\damage\fire3- 156 200

set_frame_frame 156 4 156 2
set_frame_delay 156 4 250

load_sequence graphics\struct\details\damage\fire4- 157 275

set_frame_frame 157 4 157 2
set_frame_delay 157 4 250

load_sequence graphics\struct\details\damage\hole- 158 NOTANIM
load_sequence graphics\struct\stone\mdink\monum- 159 75
load_sequence graphics\effects\atomic\atomc- 161 50 57 123 -22 -14 22 14
load_sequence graphics\effects\circles\circl- 162 50 29 29 -9 -3 9 3
load_sequence graphics\effects\stars\star2- 163 1 38 98 -19 -18 19 7

//empty slot
load_sequence_now graphics\effects\magic\magc1- 164 50 57 36 -15 -4 15 4

load_sequence_now graphics\effects\shiny\shiny- 165 50

load_sequence graphics\effects\sparks\spark- 166 50
load_sequence graphics\effects\splode\shock- 167 30 87 -26 -17 26 20
load_sequence graphics\effects\splode\whirl- 168 50
load_sequence graphics\effects\stars\star2- 169 150 38 39 -19 -7 19 7

load_sequence graphics\effects\stars\star1- 170 150 38 40 -19 -7 19 7

load_sequence graphics\lands\firemoun\blast- 171 50 60 154 -17 -16 17 16
//load_sequence graphics\lands\firemoun\mound- 172 NOTANIM

load_sequence graphics\bonuses\barrels\barel- 173 75 41 44 -17 -15 20 6
load_sequence graphics\bonuses\barrels\bar- 174 NOTANIM
load_sequence graphics\bonuses\chest\chst1- 175 75 25 50 -20 -14 20 6
load_sequence graphics\bonuses\chest\chst2- 176 75 29 48 -20 -13 18 5
load_sequence graphics\bonuses\chest\chst3- 177 75 40 50 -21 -13 22 6

load_sequence_now graphics\bonuses\coins\coin- 178 75
load_sequence graphics\lands\shrubs\bush- 179 NOTANIM
load_sequence_now graphics\inter\status\stat- 180 BLACK
load_sequence_now graphics\inter\numbers\ns- 181 LEFTALIGN
load_sequence_now graphics\inter\numbers\nr- 182 LEFTALIGN
load_sequence_now graphics\inter\numbers\nb- 183 LEFTALIGN
load_sequence_now graphics\inter\numbers\np- 184 LEFTALIGN
load_sequence_now graphics\inter\numbers\ny- 185 LEFTALIGN
load_sequence graphics\struct\landmark\landm- 186 NOTANIM
load_sequence_now graphics\effects\spurt\spurt- 187 100 16 9 -8 -1 8 1
load_sequence_now graphics\effects\spurt\sprtl- 188 100 50 20 -12 -2 12 2
load_sequence_now graphics\effects\spurt\sprtr- 189 100 0 20 -5 -2 5 2
load_sequence_now graphics\inter\health\hm-w- 190 LEFTALIGN
load_sequence_now graphics\inter\health\hm-g- 191 LEFTALIGN
load_sequence_now graphics\startme\options\but1- 192 BLACK
load_sequence_now graphics\startme\options\but3- 193 BLACK
load_sequence_now graphics\startme\options\but7- 194 BLACK
load_sequence_now graphics\startme\options\but9- 195 BLACK
load_sequence_now graphics\startme\options\dinkL- 196 BLACK
load_sequence_now graphics\startme\vstart\stm1- 197 BLACK
load_sequence_now graphics\startme\vstart\stm3- 198 BLACK
load_sequence_now graphics\startme\vstart\stm7- 199 BLACK
load_sequence_now graphics\startme\vstart\stm9- 200 BLACK


//load dragon

load_sequence graphics\foes\dragon\f2-w2- 202 75 106 120 -41 -18 41 18
load_sequence graphics\foes\dragon\f2-w4- 204 75 103 113 -38 -18 38 18
load_sequence graphics\foes\dragon\f2-w6- 206 75 116 111 -38 -18 38 18
load_sequence graphics\foes\dragon\f2-w8- 208 75 105 100 -43 -18 43 18

load_sequence graphics\foes\dragon\f2-x3- 212 125 42 90 -26 -12 26 12
load_sequence graphics\foes\dragon\f2-x7- 216 125 63 38 -23 -9 23 9

//maiden

load_sequence graphics\people\maiden\red\c4-w1- 221 100 37 61 -20 -17 20 8
load_sequence graphics\people\maiden\red\c4-w3- 223 100 32 59 -16 -12 18 11
load_sequence graphics\people\maiden\red\death- 225 100 32 59 -16 -12 18 11
load_sequence graphics\people\maiden\red\c4-w7- 227 100 32 60 -16 -13 16 8
load_sequence graphics\people\maiden\red\c4-w9- 229 100 31 60 -18 -14 16 8

//old man who dies a lot

load_sequence graphics\people\oldman\c1-w1- 231 100 45 54 -16 -11 23 7
load_sequence graphics\people\oldman\c1-w3- 233 100 46 54 -29 -11 17 7
load_sequence graphics\people\oldman\c1-w7- 237 100 42 49 -20 -8 21 10
load_sequence graphics\people\oldman\c1-w9- 239 100 39 49 -23 -10 18 13

load_sequence graphics\people\maiden\brown\c6-w1- 241 100 37 61 -20 -17 20 8
load_sequence graphics\people\maiden\brown\c6-w3- 243 100 32 59 -16 -12 18 11
load_sequence graphics\people\maiden\red\death- 245 100 32 59 -16 -12 18 11
load_sequence graphics\people\maiden\brown\c6-w7- 247 100 32 60 -16 -13 16 8
load_sequence graphics\people\maiden\brown\c6-w9- 249 100 31 60 -18 -14 16 8

load_sequence graphics\people\maiden\blue\c7-w1- 251 100 37 61 -20 -17 20 8
load_sequence graphics\people\maiden\blue\c7-w3- 253 100 32 59 -16 -12 18 11
load_sequence graphics\people\maiden\red\death- 255 100 32 59 -16 -12 18 11
load_sequence graphics\people\maiden\blue\c7-w7- 257 100 32 60 -16 -13 16 8
load_sequence graphics\people\maiden\blue\c7-w9- 259 100 31 60 -18 -14 16 8

load_sequence graphics\people\fairy\c2-w1- 261 100
load_sequence graphics\people\fairy\c2-w3- 263 100






load_sequence graphics\people\knight\red\c5-w1- 271 100 67 86 -21 -12 21 12
load_sequence graphics\people\knight\red\c5-w3- 273 100 58 84 -27 -11 27 11
load_sequence graphics\people\knight\red\death- 275 100 54 11 -51 -4 27 39
load_sequence graphics\people\knight\red\c5-w7- 277 100 70 86 -22 -12 22 12
load_sequence graphics\people\knight\red\c5-w9- 279 100 66 85 -24 -12 24 12

load_sequence graphics\people\knight\blue\c5-w1- 281 100 67 86 -21 -12 21 12
load_sequence graphics\people\knight\blue\c5-w3- 283 100 58 84 -27 -11 27 11
load_sequence graphics\people\knight\silver\death- 285 100 58 84 -27 -11 27 11
load_sequence graphics\people\knight\blue\c5-w7- 287 100 70 86 -22 -12 22 12
load_sequence graphics\people\knight\blue\c5-w9- 289 100 66 85 -24 -12 24 12
load_sequence graphics\people\knight\silver\c5-w1- 291 100 67 86 -21 -12 21 12
load_sequence graphics\people\knight\silver\c5-w3- 293 100 58 84 -27 -11 27 11
load_sequence graphics\people\knight\silver\death- 295 100 25 11 -22 0 55 42
load_sequence graphics\people\knight\silver\c5-w7- 297 100 70 86 -22 -12 22 12
load_sequence graphics\people\knight\silver\c5-w9- 299 100 66 85 -24 -12 24 12

load_sequence graphics\people\knight\gold\c5-w1- 301 100 67 86 -21 -12 21 12
load_sequence graphics\people\knight\gold\c5-w3- 303 100 58 84 -27 -11 27 11
load_sequence graphics\people\knight\gold\death- 305 100 54 11 -50 1 27 36
load_sequence graphics\people\knight\gold\c5-w7- 307 100 70 86 -22 -12 22 12
load_sequence graphics\people\knight\gold\c5-w9- 309 100 66 85 -24 -12 24 12

//dinks push sprites

load_sequence_now graphics\dink\push\ds-p2- 312 75 45 79 -7 -21 13 -7
load_sequence_now graphics\dink\push\ds-p4- 314 75 36 69 3 -9 45 9
load_sequence_now graphics\dink\push\ds-p6- 316 75 67 71 -21 -12 21
load_sequence_now graphics\dink\push\ds-p8- 318 75 46 59 -9 5 12 24

//dink magic

load_sequence_now graphics\dink\hit\magic\ds-m2- 322 30 60 84 -15 -9 16 7
load_sequence_now graphics\dink\hit\magic\ds-m4- 324 30 61 86 -13 -7 15 8
load_sequence_now graphics\dink\hit\magic\ds-m6- 326 30 60 86 -11 -8 13 9
load_sequence_now graphics\dink\hit\magic\ds-m8- 328 30 61 83 -15 -4 15 14

load_sequence graphics\people\girl\c03w1- 331 100 35 45 -19 -10 13 6
load_sequence graphics\people\girl\c03w3- 333 100 35 48 -14 -13 13 6
load_sequence graphics\people\girl\death- 335 100 44 9 -40 -7 13 26
load_sequence graphics\people\girl\c03w7- 337 100 31 44 -11 -8 18 11
load_sequence graphics\people\girl\c03w9- 339 100 33 46 -16 -12 14 7

load_sequence graphics\people\merchant\c09w1- 341 100 38 71 -18 -9 24 14
load_sequence graphics\people\merchant\c09w3- 343 100 36 69 -22 -14 23 14
load_sequence graphics\people\merchant\death- 345 100 59 11 -58 -7 17 38
load_sequence graphics\people\merchant\c09w7- 347 100 40 67 -24 -14 23 11
load_sequence graphics\people\merchant\c09w9- 349 100 34 69 -18 -13 23 16

load_sequence graphics\people\mom\c08w1- 351 100
load_sequence graphics\people\mom\c08w3- 353 100
load_sequence graphics\people\mom\death- 355 100 54 9 -52 -6 13 34
load_sequence graphics\people\mom\c08w7- 357 100
load_sequence graphics\people\mom\c08w9- 359 100


load_sequence graphics\people\mom\brown\c08w1- 361 100
load_sequence graphics\people\mom\brown\c08w3- 363 100
load_sequence graphics\people\mom\death- 365 100 49 11 -44 -4 17 33
load_sequence graphics\people\mom\brown\c08w7- 367 100
load_sequence graphics\people\mom\brown\c08w9- 369 100

load_sequence graphics\people\merchant\blue\c09w1- 371 100 38 71 -18 -9 24 14
load_sequence graphics\people\merchant\blue\c09w3- 373 100 36 69 -22 -14 23 14
load_sequence graphics\people\merchant\death- 375 100 56 13 -55 -7 17 32

load_sequence graphics\people\merchant\blue\c09w7- 377 100 40 67 -24 -14 23 11
load_sequence graphics\people\merchant\blue\c09w9- 379 100 34 69 -18 -13 23 16

load_sequence graphics\people\merchant\green\c09w1- 381 100 38 71 -18 -9 24 14
load_sequence graphics\people\merchant\green\c09w3- 383 100 36 69 -22 -14 23 14
load_sequence graphics\people\merchant\green\death- 385 100 12 12 -2 -3 58 38
load_sequence graphics\people\merchant\green\c09w7- 387 100 40 67 -24 -14 23 11
load_sequence graphics\people\merchant\green\c09w9- 389 100 34 69 -18 -13 23 16

load_sequence graphics\people\merchant\purple\c09w1- 391 100 38 71 -18 -9 24 14
load_sequence graphics\people\merchant\purple\c09w3- 393 100 36 69 -22 -14 23 14
load_sequence graphics\people\merchant\death- 395 100 61 9 -60 -4 10 36
load_sequence graphics\people\merchant\purple\c09w7- 397 100 40 67 -24 -14 23 11
load_sequence graphics\people\merchant\purple\c09w9- 399 100 34 69 -18 -13 23 16

load_sequence graphics\people\soldier\c10w1- 401 100 50 68 -15 -5 17 18
load_sequence graphics\people\soldier\c10w3- 403 100 43 68 -20 -13 25 13
load_sequence graphics\people\soldier\death- 405 100 49 11 -45 1 16 36
load_sequence graphics\people\soldier\c10w7- 407 100 51 70 -23 -14 21 9
load_sequence graphics\people\soldier\c10w9- 409 100 40 70 -14 -11 19 8

load_sequence graphics\people\peasant2\c11w1- 411 100 55 96 -16 -8 18 15
load_sequence graphics\people\peasant2\c11w3- 413 100 50 94 -20 -11 21 16
load_sequence graphics\people\peasant2\death- 415 100 91 40 -64 -30 19 10
load_sequence graphics\people\peasant2\c11w7- 417 100 56 97 -21 -9 23 15
load_sequence graphics\people\peasant2\c11w9- 419 100 48 100 -13 -8 19 12


load_sequence graphics\items\bomb\bomb- 420 NOTANIM
load_sequence graphics\items\food\food- 421 12 20 -13 -19 21 7
load_sequence graphics\items\paper\paper- 422 12 20 -13 -19 21 7
load_sequence_now graphics\inter\menu\menu- 423 NOTANIM
load_sequence graphics\struct\island\isle- 424 NOTANIN
load_sequence graphics\struct\island\torch- 425 100 71 99 -21 -10 21 10
load_sequence graphics\people\boatman\c12r3- 426 75
load_sequence graphics\effects\fire\fire1- 427 75 71 99 -5 -6 6 1

set_frame_frame 427 7 427 5
set_frame_delay 427 7 75
set_frame_frame 427 8 427 4
set_frame_delay 427 8 75
set_frame_frame 427 9 427 3
set_frame_delay 427 9 75
set_frame_frame 427 10 427 2
set_frame_delay 427 10 75


load_sequence graphics\inside\stairs\stair- 428 NOTANIM
load_sequence graphics\struct\cataplt\arms- 429 NOTANIM
load_sequence graphics\effects\seed\seed4- 430 150
load_sequence graphics\effects\seed\seed6- 431 150
load_sequence_now graphics\effects\shadows\shadw- 432 NOTANIM
load_sequence graphics\effects\splash\splas- 433 75 33 44 -19 -12 23 4
load_sequence graphics\animals\fish\fish1\fish1- 434 75 48 58 -23 -5 27 11
load_sequence graphics\animals\fish\fish2\fish2- 435 75 48 58 -23 -5 27 11
load_sequence_now graphics\dink\die\ds-x3- 436 75 30 67 -10 -9 10 9
load_sequence_now graphics\inter\menu\item-m 437 NOTANIM
load_sequence_now graphics\inter\menu\item-w 438 NOTANIM
load_sequence graphics\animals\fish\flop\fishx- 439 NOTANIM
load_sequence graphics\animals\fish\flop\flop1- 440 75
load_sequence graphics\animals\fish\flop\flop2- 441 75
load_sequence_now graphics\inter\level#\ln- 442 LEFTALIGN
load_sequence graphics\items\boxes\boxb1- 443 75 38 41 -26 -16 33 6
load_sequence graphics\items\boxes\boxb3- 444 75 28 37 -32 -19 28 4
load_sequence graphics\items\boxes\box- 445 NOTANIM
load_sequence graphics\items\tomb\tomb- 446 NOTANIM
load_sequence graphics\items\tools\tool- 447 NOTANIM
load_sequence graphics\items\cup\cup- 448 NOTANIM
load_sequence graphics\inter\save\save- 449 135 60 60 -59 -45 60 26
//save needs to play reversed too
set_frame_frame 449 6 449 4
set_frame_frame 449 7 449 3
set_frame_frame 449 8 449 2
set_frame_delay 449 6 135
set_frame_delay 449 7 135
set_frame_delay 449 8 135
set_frame_delay 449 9 135
load_sequence_now graphics\inter\health\hm-br- 450 LEFTALIGN
load_sequence_now graphics\inter\health\hm-r- 451 LEFTALIGN
load_sequence graphics\dink\crawl\ds-cr- 452 100
load_sequence_now graphics\inter\arrow\arowl- 456 100
load_sequence_now graphics\inter\arrow\arowr- 457 100
load_sequence_now graphics\inside\details\sign- 458 NOTANIM

load_sequence graphics\inner\shelf- 459 NOTANIM
load_sequence graphics\inner\lab- 460 NOTANIM
load_sequence graphics\inner\chair- 461 NOTANIM
load_sequence graphics\inner\poster 462 50 27 56 -30 -57 21 6
load_sequence graphics\items\grain\bag- 463 100 28 41 -28 -28 30 4


load_sequence graphics\effects\comets\sm-comt1\comt2- 502 30 14 118 -8 -5 11 13
load_sequence graphics\effects\comets\sm-comt1\comt4- 504 30 9 57 -6 -6 9 8
load_sequence graphics\effects\comets\sm-comt1\comt6- 506 30 77 57 -7 -8 9 8
load_sequence graphics\effects\comets\sm-comt1\comt8- 508 30 15 48 -9 -8 10 8

load_sequence graphics\effects\comets\sm-comt2\fbal2- 512 0 15 94 -17 -47 18 -17
load_sequence graphics\effects\comets\sm-comt2\fbal4- 514 0 14 51 -11 -11 16 12
load_sequence graphics\effects\comets\sm-comt2\fbal6- 516 0 59 51 -12 -12 15 12
load_sequence graphics\effects\comets\sm-comt2\fbal8- 518 0 13 49 -11 -11 16 11


load_sequence graphics\dink\seed\ds-s2- 522 150 49 74 -14 -9 16 10
load_sequence graphics\dink\seed\ds-s4- 524 150 47 73 -16 -10 14 10
load_sequence graphics\dink\seed\ds-s6- 526 150 53 71 -16 -10 16 10
load_sequence graphics\dink\seed\ds-s8- 528 150 50 70 -16 -9 16 9


load_sequence graphics\foes\bonca\walk\f03w1- 531 75 55 67 -29 -9 24 18
load_sequence graphics\foes\bonca\walk\f03w3- 533 75 57 68 -18 -13 25 11
load_sequence graphics\foes\bonca\walk\f03w7- 537 75 56 71 -27 -13 27 13
load_sequence graphics\foes\bonca\walk\f03w9- 539 75 58 67 -23 -8 25 20


load_sequence graphics\foes\bonca\attack\f03a2- 544 75 70 65 -21 -11 21 14
load_sequence graphics\foes\bonca\attack\f03a4- 548 75 70 64 -32 -8 32 17
load_sequence graphics\foes\bonca\attack\f03a6- 542 75 65 66 -24 -12 24 16
load_sequence graphics\foes\bonca\attack\f03a8- 546 75 68 65 -21 -11 21 11

set_frame_special 544 5 1
set_frame_special 548 5 1
set_frame_special 542 5 1
set_frame_special 546 5 1


load_sequence graphics\foes\bonca\death\f03x1- 551 75
load_sequence graphics\foes\bonca\death\f03x3- 553 75
load_sequence graphics\foes\bonca\death\f03x7- 557 75
load_sequence graphics\foes\bonca\death\f03x9- 559 75

load_sequence graphics\people\gnome\purple\c13w1- 561 75 29 55 -15 -7 17 17
load_sequence graphics\people\gnome\purple\c13w3- 563 75 31 57 -19 -12 18 12
load_sequence graphics\people\gnome\purple\c13w7- 567 75 30 57 -16 -9 16 10
load_sequence graphics\people\gnome\purple\c13w9- 569 75 28 54 -17 -10 17 13

load_sequence graphics\people\gnome\blue\c13w1- 571 75 29 55 -15 -7 17 17
load_sequence graphics\people\gnome\blue\c13w3- 573 75 31 57 -19 -12 18 12
load_sequence graphics\people\gnome\blue\c13w7- 577 75 30 57 -16 -9 16 10
load_sequence graphics\people\gnome\blue\c13w9- 579 75 28 54 -17 -10 17 13

load_sequence graphics\people\gnome\green\c13w1- 581 75 29 55 -15 -7 17 17
load_sequence graphics\people\gnome\green\c13w3- 583 75 31 57 -19 -12 18 12
load_sequence graphics\people\gnome\green\c13w7- 587 75 30 57 -16 -9 16 10
load_sequence graphics\people\gnome\green\c13w9- 589 75 28 54 -17 -10 17 13

load_sequence graphics\foes\bonca\gray\attack\f03a2- 594 75 70 65 -21 -11 21 14
load_sequence graphics\foes\bonca\gray\attack\f03a4- 598 75 70 64 -32 -8 32 17
load_sequence graphics\foes\bonca\gray\attack\f03a6- 592 75 65 66 -24 -12 24 16
load_sequence graphics\foes\bonca\gray\attack\f03a8- 596 75 68 65 -21 -11 21 11

set_frame_special 594 5 1
set_frame_special 598 5 1
set_frame_special 592 5 1
set_frame_special 596 5 1

load_sequence graphics\foes\bonca\gray\walk\f03w1- 601 75 55 67 -29 -9 24 18
load_sequence graphics\foes\bonca\gray\walk\f03w3- 603 75 57 68 -18 -13 25 11
load_sequence graphics\foes\bonca\gray\walk\f03w7- 607 75 56 71 -27 -13 27 13
load_sequence graphics\foes\bonca\gray\walk\f03w9- 609 75 58 67 -23 -8 25 20

load_sequence graphics\foes\bonca\purple\walk\f03w1- 611 75 55 67 -29 -9 24 18
load_sequence graphics\foes\bonca\purple\walk\f03w3- 613 75 57 68 -18 -13 25 11
load_sequence graphics\foes\bonca\purple\walk\f03w7- 617 75 56 71 -27 -13 27 13
load_sequence graphics\foes\bonca\purple\walk\f03w9- 619 75 58 67 -23 -8 25 20

load_sequence graphics\foes\bonca\purple\attack\f03a2- 624 75 70 65 -21 -11 21 14
load_sequence graphics\foes\bonca\purple\attack\f03a4- 628 75 70 64 -32 -8 32 17
load_sequence graphics\foes\bonca\purple\attack\f03a6- 622 75 65 66 -24 -12 24 16
load_sequence graphics\foes\bonca\purple\attack\f03a8- 626 75 68 65 -21 -11 21 11

load_sequence graphics\foes\slayers\attack\f04a2- 632 75 89 78 -28 -13 28 16
load_sequence graphics\foes\slayers\attack\f04a4- 634 75 81 75 -22 -13 30 19
load_sequence graphics\foes\slayers\attack\f04a6- 636 75 95 75 -22 -13 25 15
load_sequence graphics\foes\slayers\attack\f04a8- 638 75 92 75 -25 -18 22 17

SET_FRAME_SPECIAL 632 5 1
SET_FRAME_SPECIAL 634 5 1
SET_FRAME_SPECIAL 636 5 1
SET_FRAME_SPECIAL 638 5 1

SET_SPRITE_INFO 632 5 89 78 -23 -19 14 27
SET_SPRITE_INFO 634 5 81 75 -59 -17 30 19
SET_SPRITE_INFO 636 5 95 75 -22 -8 59 26

load_sequence graphics\foes\slayers\walk\f04w1- 641 75 92 67 -28 -15 24 14
load_sequence graphics\foes\slayers\walk\f04w3- 643 75 97 66 -28 -13 25 23
load_sequence graphics\foes\slayers\walk\death- 645 75 62 28 -62 -16 23 28
load_sequence graphics\foes\slayers\walk\f04w7- 647 75 85 62 -21 -17 33 21
load_sequence graphics\foes\slayers\walk\f04w9- 649 75 91 67 -20 -17 40 12

load_sequence graphics\foes\puddle\blue\walk\f06w1- 651 75 11 11 -9 -8 14 11
load_sequence graphics\foes\puddle\blue\walk\f06w3- 653 75 15 10 -13 -10 13 12

load_sequence graphics\foes\puddle\blue\death\f06x1- 661 75 
load_sequence graphics\foes\puddle\blue\death\f06x3- 663 75

load_sequence graphics\foes\puddle\green\walk\f06w1- 671 75 11 11 -9 -8 14 11
load_sequence graphics\foes\puddle\green\walk\f06w3- 673 75 15 10 -13 -10 13 12

load_sequence graphics\foes\puddle\green\death\f06x1- 681 75
load_sequence graphics\foes\puddle\green\death\f06x3- 683 75

load_sequence graphics\foes\puddle\red\walk\f06w1- 691 75 11 11 -9 -8 14 11
load_sequence graphics\foes\puddle\red\walk\f06w3- 693 75 15 10 -13 -10 13 12

load_sequence graphics\foes\puddle\red\death\f06x1- 701 75
load_sequence graphics\foes\puddle\red\death\f06x3- 703 75

load_sequence graphics\people\knight\red\attack\c05a2- 712 75 92 98 -16 -12 16 16
load_sequence graphics\people\knight\red\attack\c05a4- 714 75 94 98 -17 -10 13 15
load_sequence graphics\people\knight\red\attack\c05a6- 716 75 87 96 -12 -11 23 16
load_sequence graphics\people\knight\red\attack\c05a8- 718 75 92 97 -20 -9 18 19


//frame they can hurt on

set_frame_special 712 6 1
set_frame_special 714 5 1
set_frame_special 716 6 1
set_frame_special 718 6 1

load_sequence graphics\people\knight\silver\attack\c05a2- 722 75 92 98 -16 -12 16 16
load_sequence graphics\people\knight\silver\attack\c05a4- 724 75 94 98 -17 -10 13 15
load_sequence graphics\people\knight\silver\attack\c05a6- 726 75 87 96 -12 -11 23 16
load_sequence graphics\people\knight\silver\attack\c05a8- 728 75 92 97 -20 -9 18 19

set_frame_special 722 6 1
set_frame_special 724 5 1
set_frame_special 726 6 1
set_frame_special 728 6 1

load_sequence graphics\people\knight\blue\attack\c05a2- 732 75 92 98 -16 -12 16 16
load_sequence graphics\people\knight\blue\attack\c05a4- 734 75 94 98 -17 -10 13 15
load_sequence graphics\people\knight\blue\attack\c05a6- 736 75 87 96 -12 -11 23 16
load_sequence graphics\people\knight\blue\attack\c05a8- 738 75 92 97 -20 -9 18 19

set_frame_special 732 6 1
set_frame_special 734 5 1
set_frame_special 736 6 1
set_frame_special 738 6 1

load_sequence graphics\people\knight\gold\attack\c05a2- 742 75 92 98 -16 -12 16 16
load_sequence graphics\people\knight\gold\attack\c05a4- 744 75 94 98 -17 -10 13 15
load_sequence graphics\people\knight\gold\attack\c05a6- 746 75 87 96 -12 -11 23 16
load_sequence graphics\people\knight\gold\attack\c05a8- 748 75 92 97 -20 -9 18 19

set_frame_special 742 6 1
set_frame_special 744 5 1
set_frame_special 746 6 1
set_frame_special 748 6 1


//goblin sprites

load_sequence graphics\foes\goblin\hammer\attack\f01a2- 752 75 53 87 -20 -11 20 13
load_sequence graphics\foes\goblin\hammer\attack\f01a4- 754 75 73 88 -26 -11 26 11
load_sequence graphics\foes\goblin\hammer\attack\f01a6- 756 75 46 69 -17 -11 30 13
load_sequence graphics\foes\goblin\hammer\attack\f01a8- 758 75 34 91 -16 -12 16 12

set_frame_special 752 6 1
set_frame_special 754 6 1
set_frame_special 756 6 1
set_frame_special 758 6 1

load_sequence graphics\foes\goblin\hammer\walk\f01w1- 761 75 50 72 -19 -12 19 10
load_sequence graphics\foes\goblin\hammer\walk\f01w3- 763 75 26 68 -21 -9 28 13
load_sequence graphics\foes\goblin\hammer\walk\death- 765 75 17 16 -10 -2 57 37
load_sequence graphics\foes\goblin\hammer\walk\f01w7- 767 75 44 74 -24 -10 24 10
load_sequence graphics\foes\goblin\hammer\walk\f01w9- 769 75 27 72 -16 -10 24 12

load_sequence graphics\foes\goblin\horns\attack\f01a2- 772 75 69 93 -23 -10 27 15
load_sequence graphics\foes\goblin\horns\attack\f01a4- 774 75 80 105 -30 -11 30 15
load_sequence graphics\foes\goblin\horns\attack\f01a6- 776 75 53 94 -22 -10 24 15
load_sequence graphics\foes\goblin\horns\attack\f01a8- 778 75 60 91 -25 -13 25 13

set_frame_special 772 6 1
set_frame_special 774 6 1
set_frame_special 776 6 1
set_frame_special 778 6 1


//spinning special attack, only need 1 seq

load_sequence graphics\foes\goblin\horns\attack2\f01sa- 780 75 101 100 -40 -25 45 33

load_sequence graphics\foes\goblin\horns\walk\f01w1- 781 75 82 83 -25 -13 27 13
load_sequence graphics\foes\goblin\horns\walk\f01w3- 783 75 38 76 -19 -14 27 14
load_sequence graphics\foes\goblin\horns\walk\death- 785 75 60 16 -59 -4 19 37
load_sequence graphics\foes\goblin\horns\walk\f01w7- 787 75 72 99 -31 -13 24 13
load_sequence graphics\foes\goblin\horns\walk\f01w9- 789 75 37 91 -19 -11 28 18

load_sequence graphics\foes\goblin\soldier\attack\f01a2- 792 75 87 111 -27 -14 32 18
load_sequence graphics\foes\goblin\soldier\attack\f01a4- 794 75 101 115 -19 -8 27 21
load_sequence graphics\foes\goblin\soldier\attack\f01a6- 796 75 78 102 -23 -11 29 23
load_sequence graphics\foes\goblin\soldier\attack\f01a8- 798 75 64 105 -21 -15 25 17

set_frame_special 792 6 1
set_frame_special 794 6 1
set_frame_special 796 6 1
set_frame_special 798 6 1

load_sequence graphics\foes\goblin\soldier\walk\f01w1- 801 75 82 91 -23 -10 26 17
load_sequence graphics\foes\goblin\soldier\walk\f01w3- 803 75 33 74 -19 -11 29 14
load_sequence graphics\foes\goblin\soldier\walk\death- 805 75 97 19 -95 -6 29 36
load_sequence graphics\foes\goblin\soldier\walk\f01w7- 807 75 53 100 -26 -10 20 15
load_sequence graphics\foes\goblin\soldier\walk\f01w9- 809 75 30 88 -19 -12 25 15

//stone giant

load_sequence graphics\foes\stonegnt\attack\f01a2- 812 75 47 119 -21 -13 21 18
load_sequence graphics\foes\stonegnt\attack\f01a4- 814 75 90 105 -26 -11 27 17
load_sequence graphics\foes\stonegnt\attack\f01a6- 816 75 72 97 -23 -9 20 15
load_sequence graphics\foes\stonegnt\attack\f01a8- 818 75 44 111 -19 -7 19 16

set_frame_special 812 5 1
set_frame_special 814 5 1
set_frame_special 816 5 1
set_frame_special 818 5 1


load_sequence graphics\foes\stonegnt\walk\f01w1- 821 75 78 41 -55 -12 26 38
load_sequence graphics\foes\stonegnt\walk\f01w3- 823 75 25 39 -21 -14 64 33
load_sequence graphics\foes\stonegnt\walk\death- 825 75 25 36 -14 -15 76 22
load_sequence graphics\foes\stonegnt\walk\f01w7- 827 75 59 72 -60 -26 21 18
load_sequence graphics\foes\stonegnt\walk\f01w9- 829 75 23 71 -19 -29 59 14

//spike

load_sequence graphics\foes\spike\idle\f07i1- 831 75 26 57 -20 -12 23 7
load_sequence graphics\foes\spike\idle\f07i3- 833 75 25 54 -20 -12 24 9

load_sequence graphics\foes\spike\walk\f07w1- 841 75 25 53 -21 -14 24 7
load_sequence graphics\foes\spike\walk\f07w3- 843 75 26 51 -22 -14 26 7

//lines added by dinkedit

//tree alignments
SET_SPRITE_INFO 32 11 30 24 -32 -22 20 3
SET_SPRITE_INFO 32 3 88 187 -14 -8 17 15
SET_SPRITE_INFO 32 4 126 227 -19 -7 19 15
SET_SPRITE_INFO 32 5 131 181 -25 -13 28 13                
SET_SPRITE_INFO 32 6 110 221 -19 -9 20 13
SET_SPRITE_INFO 32 7 104 134 -14 -6 12 13
SET_SPRITE_INFO 32 2 116 190 -16 -3 17 18
SET_SPRITE_INFO 32 1 81 158 -48 -13 46 23
SET_SPRITE_INFO 32 11 30 24 -32 -16 20 16
SET_SPRITE_INFO 32 12 30 25 -32 -13 41 12
SET_SPRITE_INFO 32 13 31 23 -29 -15 28 13


//wall alignments

SET_SPRITE_INFO 31 26 49 99 -49 -10 51
SET_SPRITE_INFO 31 19 5 88 -5 0 95 12
SET_SPRITE_INFO 31 20 16 88 -16 0 83 12
SET_SPRITE_INFO 31 21 4 88 -4 1 93 12
SET_SPRITE_INFO 31 22 79 88 -75 1 21 12
SET_SPRITE_INFO 31 23 8 53 -13 -53 19 47
SET_SPRITE_INFO 31 24 52 88 -52 0 148 12
SET_SPRITE_INFO 31 26 49 90 -49 -1 51 10
SET_SPRITE_INFO 31 27 2 88 -2 0 98 12
SET_SPRITE_INFO 31 28 5 88 -5 0 95 12
SET_SPRITE_INFO 31 29 5 88 -5 1 95 12
SET_SPRITE_INFO 31 30 5 88 -5 1 95 12
SET_SPRITE_INFO 31 33 16 88 -14 2 93 12
SET_SPRITE_INFO 31 34 4 88 -4 1 100 12
SET_SPRITE_INFO 31 35 5 88 -4 0 13 12
SET_SPRITE_INFO 31 36 5 88 -5 1 9 12
SET_SPRITE_INFO 67 1 107 342 -93 -5 86 59
SET_SPRITE_INFO 67 2 98 368 -98 -7 95 51
SET_SPRITE_INFO 64 4 67 117 -67 -17 67 3
SET_SPRITE_INFO 31 28 5 88 -5 -36 95 12
SET_SPRITE_INFO 31 27 2 88 -2 -36 98 12
SET_SPRITE_INFO 64 1 81 115 -92 -51 82 1
SET_SPRITE_INFO 64 2 79 70 -88 -42 88 9
SET_SPRITE_INFO 64 3 81 67 -81 -32 40 11
SET_SPRITE_INFO 64 4 67 117 -78 -52 78 7
SET_SPRITE_INFO 64 5 47 113 -46 -21 49 4
SET_SPRITE_INFO 63 1 145 156 -129 -85 188 -1
SET_SPRITE_INFO 63 2 37 65 -36 1 5 18
SET_SPRITE_INFO 61 1 22 50 -24 -4 6 14
SET_SPRITE_INFO 31 31 98 90 -25 -20 25 20
SET_SPRITE_INFO 31 32 98 180 -25 -20 25 20
SET_SPRITE_INFO 51 1 36 52 -5 -35 21 24


SET_SPRITE_INFO 31 22 54 87 -66 -35 59 20
SET_SPRITE_INFO 31 20 16 88 -26 -36 83 12
SET_SPRITE_INFO 31 19 5 88 -5 -36 106 12
SET_SPRITE_INFO 63 3 38 65 -30 -14 3 23
SET_SPRITE_INFO 31 36 5 88 -5 -32 9 12
SET_SPRITE_INFO 31 29 5 88 -5 -36 95 12
SET_SPRITE_INFO 31 36 5 88 -5 -36 9 12
SET_SPRITE_INFO 31 35 5 88 -4 -36 13 12
SET_SPRITE_INFO 31 23 8 53 -21 -53 25 47
SET_SPRITE_INFO 31 35 5 88 -1 -36 13 12
SET_SPRITE_INFO 31 26 49 90 -49 -1 51 17
SET_SPRITE_INFO 31 30 5 88 -5 -36 95 19
SET_SPRITE_INFO 31 35 5 88 -19 -36 13 12
SET_SPRITE_INFO 31 36 5 88 -5 -36 27 12
SET_SPRITE_INFO 31 22 79 88 -75 -36 21 19
SET_SPRITE_INFO 31 26 49 90 -49 -38 51 17
SET_SPRITE_INFO 31 21 4 88 -4 -36 93 19
SET_SPRITE_INFO 66 13 50 61 -61 -35 64 25
SET_SPRITE_INFO 95 5 51 46 -49 -36 37 6
SET_SPRITE_INFO 95 6 72 35 -75 -39 43 9
SET_SPRITE_INFO 95 3 66 58 -63 -52 39 4
SET_SPRITE_INFO 93 1 98 41 -89 -6 86 9
SET_SPRITE_INFO 93 3 77 68 -65 -26 11 5
SET_SPRITE_INFO 93 2 68 67 -64 -25 9 3


SET_SPRITE_INFO 95 4 48 46 -49 -41 30 9
SET_SPRITE_INFO 95 9 53 43 -56 -36 30 12
SET_SPRITE_INFO 93 4 17 98 -18 -65 19 24
SET_SPRITE_INFO 93 1 98 41 -89 -6 86 17
SET_SPRITE_INFO 179 4 57 47 -53 -25 28 13
SET_SPRITE_INFO 179 3 96 61 -83 -29 55 16
SET_SPRITE_INFO 87 9 30 55 -39 -33 43 7
SET_SPRITE_INFO 10 5 0 0 -12 -5 12 5
SET_SPRITE_INFO 10 4 0 0 -5 -2 5 2
SET_SPRITE_INFO 10 2 0 0 -2 0 2 0
SET_SPRITE_INFO 10 1 0 0 -2 0 2 0
SET_SPRITE_INFO 82 1 9 52 -12 -9 16 22
SET_SPRITE_INFO 31 22 79 88 -76 -36 21 19
SET_SPRITE_INFO 61 1 22 50 -24 -9 6 14
SET_SPRITE_INFO 90 5 10 15 -15 -21 10 8
SET_SPRITE_INFO 64 5 47 113 -54 -21 57 8
SET_SPRITE_INFO 178 1 1 3 -4 -7 6 3
SET_SPRITE_INFO 186 1 65 95 -31 -18 32 22
SET_SPRITE_INFO 63 4 130 164 -64 -31 64 31
SET_SPRITE_INFO 31 23 8 53 -23 -53 25 47

SET_SPRITE_INFO 196 1 329 139 -163 -99 156 76
SET_SPRITE_INFO 192 1 92 19 -92 -19 92 16
SET_SPRITE_INFO 192 2 102 31 -94 -23 97 17
SET_SPRITE_INFO 193 1 50 16 -50 -16 43 13
SET_SPRITE_INFO 193 2 59 27 -47 -16 43 14
SET_SPRITE_INFO 194 1 60 18 -60 -18 55 11
SET_SPRITE_INFO 194 2 70 29 -60 -19 55 13
SET_SPRITE_INFO 195 1 102 17 -101 -16 86 12
SET_SPRITE_INFO 195 2 105 28 -92 -15 95 14
SET_SPRITE_INFO 31 28 5 88 -6 -36 95 12
SET_SPRITE_INFO 87 1 48 29 -62 -16 59 28
SET_SPRITE_INFO 31 22 79 88 -94 -36 21 19
SET_SPRITE_INFO 31 20 16 88 -26 -36 84 12
SET_SPRITE_INFO 31 35 5 88 -19 -36 28 12
SET_SPRITE_INFO 87 7 26 76 -36 -40 39 12
SET_SPRITE_INFO 31 36 5 88 -5 -36 27 19
SET_SPRITE_INFO 10 8 0 2 0 0 13 15
SET_SPRITE_INFO 192 1 90 20 -92 -19 92 16
SET_SPRITE_INFO 195 2 112 28 -92 -15 95 14
SET_SPRITE_INFO 87 9 30 55 -39 -33 43 9
SET_SPRITE_INFO 192 2 101 31 -94 -23 97 17
SET_SPRITE_INFO 58 10 57 63 -62 -16 32 26
SET_SPRITE_INFO 421 11 12 17 -15 -19 16 6
SET_SPRITE_INFO 131 1 24 29 -18 -23 19 7
SET_SPRITE_INFO 133 1 24 29 -18 -24 19 7
SET_SPRITE_INFO 93 5 41 63 -49 -15 20 11
SET_SPRITE_INFO 93 6 44 65 -54 -23 20 6
SET_SPRITE_INFO 193 2 59 27 -51 -17 43 15
SET_SPRITE_INFO 195 2 112 28 -105 -17 95 16
SET_SPRITE_INFO 428 3 68 11 -45 -8 21 61
SET_SPRITE_INFO 428 1 4 2 -4 -3 52 74
SET_SPRITE_INFO 428 2 41 74 -41 -75 37 -7
SET_SPRITE_INFO 67 7 189 225 -87 -46 87 46
SET_SPRITE_INFO 87 10 23 108 -16 -25 16 9
SET_SPRITE_INFO 32 8 133 69 -135 -23 70 9
SET_SPRITE_INFO 58 9 85 90 -48 -9 48 9
SET_SPRITE_INFO 58 7 64 93 -25 -9 25 9
SET_SPRITE_INFO 58 8 86 36 -48 -8 48 8
SET_SPRITE_INFO 58 6 61 36 -25 -8 25 8
SET_SPRITE_INFO 186 9 37 69 -14 -15 14 9
SET_SPRITE_INFO 89 9 29 90 -15 -10 15 14
SET_SPRITE_INFO 95 10 52 69 -50 -9 52 15
SET_SPRITE_INFO 422 12 19 36 -17 -14 18 4
SET_SPRITE_INFO 422 11 19 37 -19 -10 15 9
SET_SPRITE_INFO 422 10 18 37 -19 -11 19 7
SET_SPRITE_INFO 424 18 13 100 -13 -19 14 10

SET_SPRITE_INFO 87 2 45 20 -49 -8 54 5
SET_SPRITE_INFO 89 9 29 69 -15 -10 15 14
SET_SPRITE_INFO 159 7 74 133 -79 -47 76 15
SET_SPRITE_INFO 422 7 21 19 -25 -15 26 2
SET_SPRITE_INFO 87 4 33 49 -30 -32 40 5
SET_SPRITE_INFO 87 3 49 49 -37 -30 57 1
SET_SPRITE_INFO 447 4 25 71 -23 -22 32 3
SET_SPRITE_INFO 178 4 16 9 -20 -14 27 14
SET_SPRITE_INFO 87 3 47 80 -47 -42 61 6
SET_SPRITE_INFO 66 24 51 87 -59 -53 59 9
SET_SPRITE_INFO 428 4 41 74 -36 -74 41 -7
SET_SPRITE_INFO 87 5 70 61 -63 -45 31 8
SET_SPRITE_INFO 445 2 66 80 -85 -28 49 21
SET_SPRITE_INFO 447 11 1 96 -13 -17 19 17
SET_SPRITE_INFO 447 3 19 87 -21 -20 26 9
SET_SPRITE_INFO 447 12 28 62 -15 -14 12 8
SET_SPRITE_INFO 446 3 17 40 -18 -14 22 9
SET_SPRITE_INFO 179 2 42 42 -47 -20 46 14
SET_SPRITE_INFO 179 1 65 54 -64 -25 58 12
SET_SPRITE_INFO 445 1 38 95 -44 -48 68 10
SET_SPRITE_INFO 445 3 26 58 -38 -27 50 7
SET_SPRITE_INFO 445 4 34 57 -38 -26 38 9
SET_SPRITE_INFO 445 5 30 56 -36 -23 43 9
SET_SPRITE_INFO 445 6 26 57 -36 -24 47 6
SET_SPRITE_INFO 89 10 37 23 -33 -23 13 3
SET_SPRITE_INFO 95 1 29 60 -21 -35 23 9
SET_SPRITE_INFO 80 10 66 108 -66 -32 34 42
SET_SPRITE_INFO 80 7 48 100 -57 -54 59 50
SET_SPRITE_INFO 80 1 48 79 -60 -36 64 25
SET_SPRITE_INFO 80 9 66 101 -72 -8 43 53
SET_SPRITE_INFO 80 5 14 37 -23 -41 25 66
SET_SPRITE_INFO 80 2 49 63 -62 -20 65 41
SET_SPRITE_INFO 80 3 49 62 -57 -19 59 42
SET_SPRITE_INFO 80 4 50 64 -56 -21 56 40
SET_SPRITE_INFO 80 14 66 72 -72 -29 39 32
SET_SPRITE_INFO 80 15 52 65 -59 -22 53 39
SET_SPRITE_INFO 80 20 49 75 -55 -29 57 32
SET_SPRITE_INFO 80 25 41 91 -40 -10 40 30
SET_SPRITE_INFO 80 23 42 18 -28 -5 28 9
SET_SPRITE_INFO 80 24 23 35 -26 -33 25 17

SET_SPRITE_INFO 80 27 20 69 -22 -9 22 29
SET_SPRITE_INFO 80 28 18 70 -22 -13 26 26
SET_SPRITE_INFO 428 5 18 25 -21 -14 20 33
SET_SPRITE_INFO 66 24 51 46 -59 -9 59 45
SET_SPRITE_INFO 446 1 22 32 -20 -18 13 6


SET_SPRITE_INFO 459 1 58 105 -66 -29 68 5
SET_SPRITE_INFO 459 2 61 122 -67 -22 49 22
SET_SPRITE_INFO 459 3 40 121 -44 -29 72 26
SET_SPRITE_INFO 459 4 62 102 -72 -26 67 10
SET_SPRITE_INFO 460 1 35 122 -38 -19 51 20
SET_SPRITE_INFO 460 2 35 111 -43 -13 42 17
SET_SPRITE_INFO 460 3 35 112 -43 -22 40 23
SET_SPRITE_INFO 461 1 18 41 -17 -15 17 6
SET_SPRITE_INFO 461 2 18 48 -20 -15 20 5
SET_SPRITE_INFO 461 3 11 45 -15 -14 18 7
SET_SPRITE_INFO 461 4 16 42 -24 -15 23 7
SET_SPRITE_INFO 461 5 15 35 -17 -11 20 9
SET_SPRITE_INFO 461 6 15 42 -22 -16 24 4
SET_SPRITE_INFO 461 7 16 48 -22 -16 22 6
SET_SPRITE_INFO 461 8 11 46 -19 -15 19 7
SET_SPRITE_INFO 461 9 16 46 -22 -17 24 4
SET_SPRITE_INFO 461 10 19 45 -27 -20 25 4
SET_SPRITE_INFO 461 11 13 43 -23 -16 26 4
SET_SPRITE_INFO 461 12 11 21 -18 -12 19 7
SET_SPRITE_INFO 461 13 15 26 -17 -13 16 6
SET_SPRITE_INFO 461 14 8 25 -16 -15 20 8
SET_SPRITE_INFO 461 15 15 27 -17 -10 17 5

SET_SPRITE_INFO 25 6 33 55 -7 -3 11 17
SET_SPRITE_INFO 25 2 2 62 -1 -4 1 4
SET_SPRITE_INFO 25 5 24 49 -11 -3 11 3
SET_SPRITE_INFO 25 7 21 53 -11 -3 11 3
SET_SPRITE_INFO 25 8 3 63 -1 -4 1 4
SET_SPRITE_INFO 25 1 30 63 -11 -3 11 3
SET_SPRITE_INFO 25 3 14 63 -11 -3 11 3
SET_SPRITE_INFO 25 4 30 50 -15 0 15 1
SET_SPRITE_INFO 429 1 146 184 -65 -26 65 26
SET_SPRITE_INFO 424 7 142 59 -125 -11 129 6
SET_SPRITE_INFO 159 8 50 144 -53 -54 59 10
SET_SPRITE_INFO 95 2 31 63 -27 -21 31 7
SET_SPRITE_INFO 95 3 66 58 -63 -31 39 5
SET_SPRITE_INFO 95 4 48 46 -49 -27 30 9
SET_SPRITE_INFO 95 5 51 46 -49 -29 37 6
SET_SPRITE_INFO 95 7 52 62 -57 -43 59 7
SET_SPRITE_INFO 95 8 29 22 -30 -12 19 2
SET_SPRITE_INFO 95 9 53 43 -56 -26 30 9
SET_SPRITE_INFO 89 3 58 24 -48 -18 22 3
SET_SPRITE_INFO 166 1 12 14 -5 -6 7 7
SET_SPRITE_INFO 90 10 38 30 -39 -11 34 5
SET_SPRITE_INFO 90 9 61 44 -61 -24 32 -4
SET_SPRITE_INFO 90 8 68 58 -69 -24 34 8
SET_SPRITE_INFO 90 7 68 50 -69 -33 33 7
SET_SPRITE_INFO 178 2 15 10 -22 -13 19 6
SET_SPRITE_INFO 178 3 15 9 -20 -12 22 7
SET_SPRITE_INFO 429 4 89 90 -68 -37 65 10
SET_SPRITE_INFO 448 16 11 26 -13 -7 15 6
SET_SPRITE_INFO 424 1 138 128 -149 -29 83 40
SET_SPRITE_INFO 91 3 54 49 -48 -30 24 6
SET_SPRITE_INFO 91 4 56 59 -48 -30 21 8
SET_SPRITE_INFO 174 1 43 39 -17 -8 17 12
SET_SPRITE_INFO 159 4 85 155 -77 -55 112 15
SET_SPRITE_INFO 446 2 21 35 -21 -12 15 9
SET_SPRITE_INFO 421 23 3 11 -5 -9 6 1
SET_SPRITE_INFO 66 23 51 55 -56 -14 55 36
SET_SPRITE_INFO 87 6 41 41 -42 -20 36 17
SET_SPRITE_INFO 87 8 6 42 -11 -28 12 28
SET_SPRITE_INFO 421 31 70 109 -54 -36 55 11

SET_SPRITE_INFO 89 4 77 58 -69 -38 29 7
SET_SPRITE_INFO 89 2 51 31 -40 -22 19 4
SET_SPRITE_INFO 89 1 31 21 -23 -16 11 2
SET_SPRITE_INFO 159 5 74 130 -33 -31 33 3
SET_SPRITE_INFO 424 16 22 107 -6 -11 6 11
SET_SPRITE_INFO 424 13 2 92 -6 -9 6 9
SET_SPRITE_INFO 424 13 2 92 -6 -9 6 9
SET_SPRITE_INFO 424 3 138 128 -147 -32 77 39
SET_SPRITE_INFO 424 4 121 191 -124 -35 124 64
SET_SPRITE_INFO 424 8 25 148 -7 -104 7 25

'''.split ('\n')

def convert_image (im):
	k = Image.eval (im.convert ('RGBA'), lambda (v): [v, 254][v == 255])
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
		assert r != None
		assert r.group (1) not in ret
		ret[r.group (1).strip ()] = r.group (2).strip ()
	return ret

def get (d, member, default = None):
	if member not in d:
		assert default != None and default != int
		return d, default
	if default == None:
		ret = d[member]
	elif type (default) == bool:
		if d[member].lower () in ['true', 'yes', '1']:
			ret = True
		else:
			assert d[member].lower () in ['false', 'no', '0']
			ret = False
	elif default == int:
		ret = int (d[member])
	else:
		ret = type (default)(d[member])
	del d[member]
	return d, ret

def make_lsb (num, size):
	ret = ''
	for i in range (size):
		ret += '%c' % (num & 0xff)
		num >>= 8
	return ret

def make_string (s, size):
	assert len (s) < size
	return s + '\0' * (size - len (s))

def token (script, allow_comment = False):
	s = script.lstrip ()
	if s == '':
		return None, None, False
	while True:
		if s.startswith ('//'):
			p = s.find ('\n', 2)
			if p < 0:
				if not allow_comment:
					continue
				return s, '', False
		if s.startswith ('/*'):
			p = s.find ('*/', 2)
			assert p >= 0
			if not allow_comment:
				continue
			return s[:p + 2], s[p + 2:].lstrip (), False
		break
	l = ['//', '/*', '&&', '||', '==', '!=', '>=', '<=', '>', '<', '!', '+=', '-=', '/=', '*=', '=', '+', '-', '*', '/', ',', ';', '{', '}', '?', ':', '(', ')']
	for i in l:
		if s.startswith (i):
			return i, s[len (i):].lstrip (), False
	if s[0] == '"':
		p = s.find ('"', 1)
		assert p >= 0
		n = s.find ('\n', 1)
		assert n == -1 or n > p
		return s[:p + 1], s[p + 1:].lstrip (), False
	is_name = True
	r = re.match ('[a-zA-Z_][a-zA-Z_0-9]*', s)
	if r == None:
		is_name = False
		r = re.match ('[0-9]+', s)
		assert r != None
	key = r.group (0)
	return key, s[len (key):].lstrip (), is_name

def push (ret, operators):
	args = operators[-1][1]
	r = ret[:-args]
	ret = ret[:-args]
	ret += ([operators[-1][0], r],)
	operators = operators[:-1]
	return ret, operators

max_tmp = 0
current_tmp = 0
def build (expr, as_bool):
	"""Build an expression or subexpression. Return before, expr"""
	global current_tmp
	if type (expr) == str:
		assert not as_bool
		if as_bool:
			return expr + ' != 0'
		else:
			return expr, ''
	if len (expr) == 3:
		# function call: name, args, before
		assert not as_bool
		return expr[0] + ' (' + ', '.join (expr[1]) + ')', expr[2]
	if expr[0] in ['==', '!=', '<=', '>=', '<', '>']:
		assert as_bool
		e0, b0 = build (expr[1][0], False)
		e1, b1 = build (expr[1][1], False)
		return e0 + ' ' + expr[0] + ' ' + e1, b0 + b1
	if expr[0] in ['&&', '||']:
		assert as_bool
		e0, b0 = build (expr[1][0], True)
		e1, b1 = build (expr[1][1], True)
		tmp = '&tmp%d' % current_tmp
		current_tmp += 1
		if expr[0] == '&&':
			return tmp + ' == 1', b0 + b1 + tmp + ' = 0;\nif (' + e0 + ')\n{\nif (' + e1 + ')\n' + tmp + ' = 1;\n}\n'
		else:
			return tmp + ' == 1', b0 + b1 + tmp + ' = 0;\nif (' + e0 + ')\n' + tmp + ' = 1;\nif (' + e1 + ')\n' + tmp + ' = 1;\n'
	assert expr[0] in ['*', '/', '+', '-', '!']
	assert not as_bool
	tmp = '&tmp%d' % current_tmp
	current_tmp += 1
	if len (expr[1]) == 2:
		e0, b0 = build (expr[1][0], False)
		e1, b1 = build (expr[1][1], False)
	else:
		e0, b0 = '0', ''
		e1, b1 = build (expr[1][0], False)
	if expr[0] == '+' or expr[0] == '-':
		op = expr[0] + '='
	else:
		op = expr[0]
	return tmp, b0 + b1 + '%s = %s;\n%s %s %s;\n' % (tmp, e0, tmp, op, e1)

def mangle_function (name, args, dink):
	'''\
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
	sp_base_attack
	sp_base_death
	sp_base_idle
	sp_base_walk
	sp_brain
	sp_sound

	return name, args, before.'''
	if name == 'add_item' or name == 'add_magic':
		assert len (args) == 3
		assert args[1][0] == '"'
		return name, [args[0], str (dink.seq.find_seq (args[1][1:-1])), args[2]], ''
	elif name == 'create_sprite':
		assert len (args) == 5
		assert args[2][0] == '"'
		return name, [args[0], args[1], str (brains.index[args[2]]), str (dink.seq.find_seq (args[3][1:-1])), args[4]], ''
	elif name == 'get_rand_sprite_with_this_brain' or name == 'get_sprite_with_this_brain':
		assert len (args) == 2
		assert args[0][0] == '"'
		return name, [str (brains.index[args[0][1:-1]]), args[1]], ''
	elif name == 'playmidi':
		assert len (args) == 1
		assert args[0][0] == '"'
		return name, [str (dink.sound.find_music (args[0][1:-1]))], ''
	elif name == 'playsound':
		assert len (args) == 4 or len (args) == 5
		assert args[0][0] == '"'
		return name, [str (dink.sound.find_sound (args[0][1:-1]))] + args[1:], ''
	elif name == 'preload_seq':
		assert len (args) == 1
		assert args[0][0] == '"'
		return name, [str (dink.seq.find_seq (args[0][1:-1]))], ''
	elif name == 'sp_base_attack' or name == 'sp_base_death' or name == 'sp_base_idle' or name == 'sp_base_walk':
		assert len (args) == 2
		assert args[1][0] == '"'
		return name, [args[0], str (dink.seq.find_collection (args[1][1:-1]))], ''
	elif name == 'sp_brain':
		assert len (args) == 1 or len (args) == 2
		if len (args) == 2:
			v = brains.index (args[1][1:-1])
		else:
			v = -1
		return name, [args[0], str (v)], ''
	elif name == 'sp_sound':
		assert len (args) == 2
		assert args[1][0] == '"'
		return name, [args[0], str (dink.sound.find_sound (args[1][1:-1]))], ''
	else:
		return name, args, ''

def read_args (script):
	args = []
	b = ''
	if script[0] == ')':
		t, script, isname = token (script)
	else:
		while True:
			if script[0] == '"':
				p = script.find ('"', 1)
				assert p >= 0
				args += (script[:p + 1],)
				script = script[p + 1:]
			else:
				a, bp, script = parse_expr (script, restart = False, as_bool = False)
				args += (a,)
				b += bp
			t, script, isname = token (script, True)
			if t != ',':
				break
	assert t == ')'
	return b, args, script

def parse_expr (script, allow_cmd = False, restart = True, as_bool = None):
	assert as_bool != None
	global current_tmp, max_tmp
	if restart:
		if current_tmp > max_tmp:
			max_tmp = current_tmp
		current_tmp = 0
	need_operator = False
	ret = []
	operators = []
	while True:
		t, script, isname = token (script, True)
		if need_operator:
			if t == ')' and '(' in operators:
				while operators[-1] != ['(', 0, 100]:
					ret, operators = push (ret, operators)
				continue
			if t == ',' or t == ';' or t == ')':
				assert ['(', 0, 100] not in operators
				while operators != []:
					ret, operators = push (ret, operators)
				assert len (ret) == 1
				if allow_cmd:
					assert ret[0][0] == '='
					e, b = build (ret[0][1][1], as_bool = False)
					return ret[0][1][0] + ' = ' + e, b, t + ' ' + script
				e, b = build (ret[0], as_bool)
				return e, b, t + ' ' + script
			if allow_cmd and t == '=':
				# assignments are almost never allowed in an expression.
				assert operators == [] and len (ret) == 1 and ret[0] == '&'
				while operators != [] and operators[-1][2] < 6:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 6])
			elif t in ['==', '!=', '>=', '<=', '>', '<']:
				while operators != [] and operators[-1][2] < 5:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 5])
			elif t == '||':
				while operators != [] and operators[-1][2] < 4:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 4])
			elif t == '&&':
				while operators != [] and operators[-1][2] < 3:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 3])
			elif t in ['+', '-']:
				while operators != [] and operators[-1][2] < 2:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 2])
			elif t in ['*', '/']:
				while operators != [] and operators[-1][2] < 1:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 1])
		else:
			if t == '(':
				operators += (['(', 0, 100],)
			elif t in ['+', '-', '!']:
				operators += ([t, 1, 0],)
			else:
				assert t and (isname or (t[0] >= '0' and t[0] <= '9'))
				if isname:
					if script.startswith ('('):
						# Read away the opening parenthesis.
						t, script, isname = token (script)
						b, args, script = read_args (script)
						f, a, bf = mangle_function (name, args, parent)
						ret += ([f, a, b + bf],)
						need_operator = True
						continue
					ret += ('&' + t,)
				else:
					ret += (t,)
				need_operator = True

def preprocess (script, dink):
	the_locals = []
	ret = ''
	indent = []
	numlabels = 0
	atend = ''
	realatend = ''
	while True:
		i = '\t' * len (indent)
		t, script, isname = token (script, True)
		if t == 'else':
			ret += i + 'else\n'
			# don't do the atend code just yet.
			continue
		if not t:
			break
		if t.startswith ('//'):
			comment = script.split ('\n', 1)[0]
			ret += i + t + comment + '\n'
			script = script[len (comment) + 1:]
			continue
		if t.startswith ('/*'):
			comment = script.split ('*/', 1)[0]
			ret += i + t + comment + '*/\n'
			script = script[len (comment) + 2:]
			continue
		if len (indent) == 0:
			assert t == 'void'
			t, script, isname = token (script)
			assert isname
			name = t
			t, script, isname = token (script)
			assert t == '('
			t, script, isname = token (script)
			assert t == ')'
			t, script, isname = token (script)
			assert t == '{'
			indent += ('',)
			ret += 'void %s ()\n{\n' % name
			continue
		ret += realatend
		realatend = ''
		if t == '{':
			indent += (atend,)
			atend = ''
			continue
		if t == '}':
			assert atend == ''
			ret += i[:-1] + '}\n'
			realatend = indent[-1]
			indent = indent[:-1]
			continue
		if t == 'while':
			t, script, isname = token (script)
			assert t == '('
			e, before, script = parse_expr (script, as_bool = True)
			t, script, isname = token (script)
			assert t == ')'
			start = 'while%d' % numlabels
			numlabels += 1
			end = 'while%d' % numlabels
			numlabels += 1
			ret += i + start + ':\n' + before + i + 'if (' + e + ') goto ' + end + '\n'
			atend = i + 'goto ' + start + '\n' + i + end + ':\n' + atend
			continue
		elif t == 'for':
			# for (i = 0; i < 4; ++i) foo;
			# i = 0;
			# loop:
			# 	if (!(i < 4))
			#		goto end
			# 	foo;
			#	++i;
			# 	goto loop
			# end:
			t, script, isname = token (script)
			assert t == '('
			if script[0] != ';':
				e1, b1, script = parse_expr (script, allow_cmd = True, as_bool = False)
			else:
				e1, b1 = '', ''
			t, script, isname = token (script)
			assert t == ';'
			e2, b2, script = parse_expr (script, as_bool = True)
			t, script, isname = token (script)
			assert t == ';'
			if script[0] != ')':
				e3, b3, script = parse_expr (script, allow_cmd = True, as_bool = False)
			else:
				e3, b3 = '', ''
			t, script, isname = token (script)
			assert t == ')'
			start = 'for%d' % numlabels
			numlabels += 1
			end = 'for%d' % numlabels
			numlabels += 1
			ret += b1 + i + e1 + ';\n' + i + start + ':\n' + b2 + i + 'if (' + e2 + ') goto ' + end + '\n'
			atend = b3 + i + e3 + ';\n' + i + 'goto ' + start + '\n' + i + end + ':\n' + atend
			continue
		elif t == 'if':
			t, script, isname = token (script)
			assert t == '('
			e, before, script = parse_expr (script, as_bool = True)
			t, script, isname = token (script)
			assert t == ')'
			ret += before + i + 'if (' + e + ')\n'
			# Don't add the atend code here.
			continue
		elif t == 'int':
			t, script, isname = token (script)
			assert isname
			name = t
			if name not in the_locals:
				the_locals += (name,)
			t, script, isname = token (script)
			if t == '=':
				e, before, script = parse_expr (script, as_bool = False)
				ret += before + i + 'int &' + name + ' = ' + e + ';\n'
			else:
				ret += i + 'int &' + name + ';\n'
			t, script, isname = token (script)
			assert t == ';'
		else:
			assert isname
			name = t
			t, script, isname = token (script)
			if t in ['=', '+=', '-=']:
				if name not in the_locals:
					global the_globals
					the_globals[name] = 0
				op = t
				e, before, script = parse_expr (script, as_bool = False)
				ret += before + i + '&' + name + ' ' + op + ' ' + e + ';\n'
			elif t in ['*=', '/=']:
				# Really, the target language is too broken for words...
				op = t[0]
				e, before, script = parse_expr (script, as_bool = False)
				ret += before + i + '&' + name + ' ' + op + ' ' + e + ';\n'
			else:
				assert t == '('
				global current_tmp, max_tmp
				if current_tmp > max_tmp:
					max_tmp = current_tmp
				current_tmp = 0
				if name == 'choice':
					# TODO: title and settings.
					b = ''
					c = i + 'choice_start ();\n'
					while True:
						t, script, isname = token (script)
						if t[0] != '"':
							e, before, script = parse_expr (t + script, restart = False, as_bool = True)
							t, script, isname = token (script)
							assert t[0] == '"'
							b += before
							t = e + ' ' + t
						c += i + t + '\n'
						t, script, isname = token (script)
						if t == ')':
							break
						assert t == ','
					ret += b + c + i + 'choice_end ();\n'
				else:
					b, args, script = read_args (script)
					f, a, bf = mangle_function (name, args, dink)
					ret += b + bf + i + f + '(' + ', '.join (a) + ');\n'
		realatend = atend
		atend = ''
		t, script, isname = token (script)
		assert (t == ';')
	return ret

class Sprite:
	pass

class Room:
	def __init__ (self, parent, root):
		self.parent = parent
		f = open (os.path.join (root, 'info' + os.extsep + 'txt'))
		self.tiles = []
		for ty in range (8):
			ln = f.readline ()
			self.tiles += ([(x[0], int (x[1]), int (x[2])) for x in [y.split (',') for y in ln.split ()]],)
			assert len (self.tiles[-1]) == 12
		info = readlines (f)
		info, self.hard = get (info, 'hard', '')
		info, self.script = get (info, 'script', '')
		info, self.music = get (info, 'music', '')
		info, self.indoor = get (info, 'indoor', False)
		assert info == {}
		self.sprite = {}
		sdir = os.path.join (root, "sprite")
		for s in os.listdir (sdir):
			info = readlines (open (os.path.join (sdir, s)))
			base = re.match ('(.+?)(-\d*?)?(\..*)?$', s).group (1)
			self.sprite[s] = Sprite ()
			info, self.sprite[s].x = get (info, 'x', int)
			info, self.sprite[s].y = get (info, 'y', int)
			info, self.sprite[s].seq = get (info, 'seq', base)
			info, self.sprite[s].frame = get (info, 'frame', 1)
			info, self.sprite[s].type = get (info, 'type', 1)	# 0 for background, 1 for person or sprite, 3 for invisible
			info, self.sprite[s].size = get (info, 'size', 100)
			info, self.sprite[s].active = get (info, 'active', True)
			info, self.sprite[s].brain = get (info, 'brain', 'bisshop')
			info, self.sprite[s].script = get (info, 'script', '')
			info, self.sprite[s].speed = get (info, 'speed', 1)
			info, self.sprite[s].base_walk = get (info, 'base_walk', '')
			info, self.sprite[s].base_idle = get (info, 'base_idle', '')
			info, self.sprite[s].base_attack = get (info, 'base_attack', '')
			info, self.sprite[s].timer = get (info, 'timer', 33)
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
			info, self.sprite[s].base_die = get (info, 'base_die', '')
			info, self.sprite[s].gold = get (info, 'gold', 0)
			info, self.sprite[s].hitpoints = get (info, 'hitpoints', 0)
			info, self.sprite[s].strength = get (info, 'strength', 0)
			info, self.sprite[s].defense = get (info, 'defense', 0)
			info, self.sprite[s].exp = get (info, 'exp', 0)
			info, self.sprite[s].sound = get (info, 'sound', '')
			info, self.sprite[s].vision = get (info, 'vision', 0)
			info, self.sprite[s].nohit = get (info, 'nohit', False)
			info, self.sprite[s].touch_damage = get (info, 'touch_damage', 0)
			assert info == {}

class World:
	def __init__ (self, parent):
		self.parent = parent
		d = os.path.join (parent.root, 'world')
		self.room = {}
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
	def write (self, root):
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink' + os.extsep + 'dat'), "wb")
		ddat.write ('Smallwood' + '\0' * 15)
		rooms = []
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 4))
				continue
			rooms += (self.room[i],)
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
					bmp, tx, ty = s.tiles[y][x]
					mdat.write (make_lsb (self.parent.tile.find_bmp (bmp) * 128 + ty * 12 + tx, 4))
					mdat.write ('\0' * 4)
					mdat.write (make_lsb (self.parent.tile.find_hard (s.hard, x, y, bmp, tx, ty), 4))
					mdat.write ('\0' * 68)
			mdat.write ('\0' * 320)
			# sprites
			# sprite 0 is never used...
			mdat.write ('\0' * 220)
			for sp in s.sprite:
				spr = s.sprite[sp]
				mdat.write (make_lsb (spr.x, 4))
				mdat.write (make_lsb (spr.y, 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.seq), 4))
				mdat.write (make_lsb (spr.frame, 4))
				mdat.write (make_lsb (spr.type, 4))
				mdat.write (make_lsb (spr.size, 4))
				mdat.write (make_lsb (int (spr.active), 4))
				mdat.write (make_lsb (0, 4))	# rotation
				mdat.write (make_lsb (0, 4))	# special
				mdat.write (make_lsb (brains.index (spr.brain), 4))
				mdat.write (make_string (spr.script, 14))
				mdat.write ('\0' * 38)
				mdat.write (make_lsb (spr.speed, 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_walk), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_idle), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_attack), 4))
				mdat.write (make_lsb (0, 4))	# hit
				mdat.write (make_lsb (spr.timer, 4))
				mdat.write (make_lsb (spr.que, 4))
				mdat.write (make_lsb (spr.hard, 4))
				mdat.write (make_lsb (spr.left, 4))
				mdat.write (make_lsb (spr.top, 4))
				mdat.write (make_lsb (spr.right, 4))
				mdat.write (make_lsb (spr.bottom, 4))
				if spr.warp != None:
					mdat.write (make_lsb (0, 4))
					mdat.write (make_lsb (spr.warp[0], 4))
					mdat.write (make_lsb (spr.warp[1], 4))
					mdat.write (make_lsb (spr.warp[2], 4))
				else:
					mdat.write ('\0' * 16)
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.touch_seq), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_die), 4))
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
			mdat.write ('\0' * 220 * (100 - len (s.sprite)))
			# base script
			mdat.write (make_string (s.script, 21))
			mdat.write ('\0' * 1019)

class Tile:
	def __init__ (self, parent):
		self.parent = parent
		self.internal = [x.strip () for x in tile_names if x.strip () != '' and x.strip ()[0] != '#']
		assert len (self.internal) == 41
		self.hard = {}
		self.tile = {}
		d = os.path.join (parent.root, "tile")
		for t in os.listdir (d):
			ext = os.extsep + 'png'
			h = '-hard' + ext
			if not t.endswith (h):
				continue
			base = t[:-len (h)]
			self.hard[base] = convert_image (Image.open (os.path.join (d, t)))
			t = os.path.join (d, base + '-tile' + os.extsep + 'png')
			if os.path.exists (t):
				self.tile[base] = convert_image (Image.open (t))
	def find_bmp (self, name):
		if name in self.internal:
			return self.internal.index (name)
		assert name in self.tile
		return self.tile.keys ().index (name)
	def find_hard (self, hard, x, y, bmp, tx, ty):
		if hard != '':
			assert hard in self.hard
			return self.map[hard][y][x]
		if bmp in self.internal:
			return 0	# TODO
		assert bmp in self.hard
		return self.map[bmp][ty][tx]
	def write (self, root):
		# Write tiles/*
		# Write hard.dat
		d = os.path.join (root, 'tiles')
		if not os.path.exists (d):
			os.mkdir (d)
		h = open (os.path.join (root, 'hard.dat'), "wb")
		hmap = []
		self.map = {}
		for t in self.hard:
			if t in self.tile:
				self.tile[t].save (os.path.join (d, t + os.extsep + 'bmp'))
			self.map[t] = [None] * 8
			for y in range (8):
				self.map[t][y] = [None] * 12
				for x in range (12):
					if self.hard[t].size[0] < (x + 1) * 50 or self.hard[t].size[1] < (y + 1) * 50:
						continue
					tile = self.hard[t].crop ((x * 50, y * 50, (x + 1) * 50, (y + 1) * 50))
					s = tile.tostring ()
					try:
						m = hmap.index (s)
					except ValueError:
						# Not in map yet; add new tile to file and map.
						m = len (hmap)
						for ty in range (50):
							for tx in range (50):
								p = tile.getpixel ((tx, ty))
								if p == (0, 0, 0):
									h.write ('\0')
								elif p == (255, 255, 255):
									h.write ('\1')
								elif p == (0, 0, 255):
									h.write ('\2')
								else:
									raise ValueError ('invalid pixel in hard tile')
							h.write ('\0')	# junk
						h.write ('\0' * 58)	# junk
						hmap += (s,)
					self.map[t][y][x] = m
		assert len (hmap) <= 800
		h.write ('\0' * (51 * 51 + 1 + 6) * (800 - len (hmap)))
		for t in self.tile:
			m = self.map[t]
			for y in range (8):
				for x in range (12):
					if m[y][x] != None:
						h.write (make_lsb (m[y][x], 4))
					else:
						# fill it with junk
						h.write (make_lsb (0, 4))
		h.write ('\0' * (8000 - len (self.tile) * 8 * 12 * 4))

class Oneseq:
	'''\
A sequence is either an animation (optionally single-frame, so not animated).  It has the following members:
	frames		- list of frames, for local images. These frames are created from a gif file.
	filename	- name of the file to write to dink.ini, including dos-style directory separators (\\)
	num		- total number of frames in the sequence.
	repeat		- whether this sequence should be marked as repeating.
	special		- which frame hits during an attack.
	now		- boolean value. When true, use load_sequence_now to load it.
	code		- Sequence code. If 0, auto-generate.
	preload		- Name of file to preload into this sequence number before the real one.
	desc		- Information about the frames. List of size num, each element is a 7-value list: x, y, left, top, right, bottom, delay.
	type		- normal, notanim, black, or leftalign.
'''
	def __init__ (self):
		self.internal = False
class Oneframe:
	pass
class Collection:
	pass
class Dinkframe:
	'''\
This class contains information about one frame from dink.ini. Members:
	target: [seq,frame] for copied frame
	info: box for non-copied frame
	delay: int
'''
	def __init__ (self):
		self.target = None
		self.info = None
		self.delay = None
	def mkbox (self):
		if self.target:
			return self.target + [self.delay]
		elif self.info:
			return self.info + [self.delay]
		else:
			return [None] * 6 + [self.delay]

class Dinkseq:
	'''\
This class holds a sequence as defined in dink.ini. Its members are:
	file: filename
	special: int special frame
	now = bool load_now
	type = str
	repeat = bool
	frames = list of Dinkframe
	defaults = Dinkframe
	num = int max frame (only certainly valid if used)
	preload = None or str (filename)
'''
	def __init__ (self):
		self.file = None
		self.special = 1
		self.now = False
		self.type = 'normal'
		self.repeat = False
		self.preload = ''
		self.num = 1
		self.frames = {}
		self.defaults = Dinkframe ()
	def use (self, s):
		if s in self.frames:
			return
		self.frames[s] = Dinkframe ()
		if s > self.num:
			self.num = s
	def mkseq (self, code):
		ret = Oneseq ()
		ret.internal = True
		ret.code = code
		ret.frames = []
		ret.filename = self.file
		ret.num = self.num
		ret.repeat = self.repeat
		ret.special = self.special
		ret.now = self.now
		ret.type = self.type
		ret.preload = self.preload
		ret.box = []
		for f in range (self.num):
			if f + 1 in self.frames:
				ret.box += (self.frames[f + 1].mkbox (),)
			else:
				ret.box += (Dinkframe ().mkbox (),)
		ret.box += (self.defaults.mkbox (),)
		return ret

class Seq:
	def use (self, s):
		if s in self.seqs:
			return
		self.seqs[s] = Dinkseq ()
	def prepare (self, info, base, box):
		info, self.seq[base].num = get (info, 'frames', self.seq[base].num)
		info, self.seq[base].repeat = get (info, 'repeat', self.seq[base].repeat)
		info, self.seq[base].special = get (info, 'special', self.seq[base].special)
		info, self.seq[base].now = get (info, 'load-now', False)
		if self.current_collection == None:
			info, self.seq[base].code = get (info, 'code', self.seq[base].code)
			assert self.seq[base].code not in self.codes
			if self.seq[base].code >= 0:
				self.codes += (self.seq[base].code,)
		info, self.seq[base].preload = get (info, 'preload', self.seq[base].preload)
		info, defbox = get (info, 'box', '')
		if defbox == '':
			defbox = [None] * 6
		else:
			defbox = defbox.split ()
		assert len (defbox) == 6
		info, delay = get (info, 'delay', 0)
		defbox += [delay]
		self.seq[base].desc = []
		for f in range (self.seq[base].num):
			self.seq[base].desc += (Oneframe (),)
			if len (box[f]) == 3:
				# These are internal frames with a target. Num is not valid, so just use the target without checking.
				info, self.seq[base].desc[-1].seq = get (info, 'seq-%d' % (f + 1), box[f][0])
				info, self.seq[base].desc[-1].frame = get (info, 'frame-%d' % (f + 1), box[f][1])
			elif not self.seq[base].internal and f >= len (self.seq[base].frames):
				# these are generated frames. They need a target.
				info, self.seq[base].desc[-1].seq = get (info, 'seq-%d' % (f + 1))
				info, self.seq[base].desc[-1].frame = get (info, 'frame-%d' % (f + 1), 1)
			info, curbox = get (info, 'box-%d' % (f + 1), '')
			if curbox == '':
				curbox = box[f][:6]
				if len (curbox) != 6 or curbox[0] == None:
					curbox = defbox[:6]
					if curbox[0] == None:
						curbox = box[-1][:6]
			else:
				curbox = [int (x) for x in curbox.split ()]
			assert len (curbox) == 6
			if curbox[0] != None:
				self.seq[base].desc[-1].x = curbox[0]
				self.seq[base].desc[-1].y = curbox[1]
				self.seq[base].desc[-1].left = curbox[2]
				self.seq[base].desc[-1].top = curbox[3]
				self.seq[base].desc[-1].right = curbox[4]
				self.seq[base].desc[-1].bottom = curbox[5]
			info, dl = get (info, 'delay-%d' % (f + 1), 0)
			if not dl:
				dl = box[f][-1]
				if not dl:
					dl = defbox[-1]
					if not dl:
						dl = box[-1][-1]
						if not dl:
							dl = None
			self.seq[base].desc[-1].delay = dl
		info, self.seq[base].type = get (info, 'type', self.seq[base].type)
		assert self.seq[base].type in ('normal', 'black', 'leftalign', 'notanim')
		assert info == {}
		if self.current_collection != None:
			assert base == None
			assert self.collection[self.current_collection].seq[self.direction] == None
			self.collection[self.current_collection].seq[self.direction] = self.seq[base]
			del self.seq[base]
		return info
	def __init__ (self, parent):
		"""Load all sequence and collection declarations from dink.ini, seq-names.txt (both internal) and seq/info.txt"""
		# General setup
		self.parent = parent
		self.seq = {}
		self.codes = []
		self.seq = {}
		self.collection = {}
		self.seqs = {}
		d = os.path.join (parent.root, "seq")
		# Read dink.ini.
		for l in [y.lower ().split () for y in dink_ini]:
			if l == [] or l[0].startswith ('//') or l[0].startswith (';') or l[0] == 'starting_dink_x' or l[0] == 'starting_dink_y' or l[0] == 'starting_dink_map':
				pass
			elif l[0] == 'load_sequence' or l[0] == 'load_sequence_now':
				s = int (l[2])
				self.use (s)
				if self.seqs[s].file:
					assert not self.seqs[s].preload
					assert self.seqs[s].file
					preload = self.seqs[s].file
					self.seqs[s] = Dinkseq ()
					self.seqs[s].preload = preload
				self.seqs[s].file = l[1]
				self.seqs[s].now = l[0] == 'load_sequence_now'
				if len (l) == 3:
					pass
				elif len (l) == 4:
					# Ignore bug in original source.
					if l[3] == 'notanin':
						l[3] = 'notanim'
					if l[3] == 'black' or l[3] == 'notanim' or l[3] == 'leftalign':
						self.seqs[s].type = l[3]
					else:
						self.seqs[s].defaults.delay = int (l[3])
				elif len (l) == 5:
					self.seqs[s].defaults.delay = int (l[3])
					self.seqs[s].type = l[4]
				elif len (l) == 9:
					self.seqs[s].defaults.info = [int (x) for x in l[3:]]
				elif len (l) == 10:
					self.seqs[s].defaults.delay = int (l[3])
					self.seqs[s].defaults.info = [int (x) for x in l[4:]]
				else:
					raise AssertionError ('invalid line for load_sequence')
			elif l[0] == 'set_sprite_info':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				self.seqs[s].use (f)
				self.seqs[s].frames[f].info =  [int (x) for x in l[3:]]
			elif l[0] == 'set_frame_delay':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				self.seqs[s].use (f)
				self.seqs[s].frames[f].delay =  int (l[3])
			elif l[0] == 'set_frame_frame':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				if len (l) == 5:
					self.seqs[s].use (f)
					self.seqs[s].frames[f].target =  [int (l[3]), int (l[4])]
				else:
					self.seqs[s].repeat = True
			elif l[0] == 'set_frame_special':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				self.seqs[s].special = int (l[3])
			else:
				print l
				raise AssertionError ('invalid line in dink.ini')
		# Link names to sequences from dink.ini. Start at 1, because the first character is a newline.
		n = 1
		# Read collections.
		while n < len (seq_names):
			l = seq_names[n].strip ()
			n += 1
			if not l:
				break
			if l[0] == '#':
				continue
			nm, c = l.split ()
			c = int (c)
			assert nm not in self.collection
			self.collection[nm] = Collection ()
			self.collection[nm].code = c
			self.collection[nm].seq = [None] * 10
			for i in range (1, 10):
				if i == 5:
					continue
				if c + i in self.seqs:
					self.collection[nm].seq[i] = self.seqs[c + i].mkseq (c + i)
					del self.seqs[c + i]
			assert self.collection[nm].seq != [None] * 10
		# Read sequences.
		while n < len (seq_names):
			l = seq_names[n].strip ()
			n += 1
			if not l:
				break
			if l[0] == '#':
				continue
			nm, c = l.split ()
			c = int (c)
			assert nm not in self.seq
			assert c in self.seqs
			self.seq[nm] = self.seqs[c].mkseq (c)
			del self.seqs[c]
		assert self.seqs == {}
		del self.seqs
		# Read info specific to this dmod.
		infofile = open (os.path.join (d, 'info' + os.extsep + 'txt'))
		self.current_collection = None
		while True:
			info = readlines (infofile)
			if info == {}:
				break
			if 'collection' in info:
				# The next blocks with a direction are a collection.
				info, self.current_collection = get (info, "collection")
				assert info == {}
				continue
			elif 'append' in info:
				# This block is about a sequence which was declared in dink.ini.
				self.current_collection = None
				info, base = get (info, 'append')
				assert base in self.seq
				assert self.seq[base].internal
				box = self.seq[base].box
				del self.seq[base].box
			else:
				if 'name' in info:
					# This block defines a new sequence.
					self.current_collection = None
					info, base = get (info, 'name')
					assert base not in self.seq
					self.seq[base] = Oneseq ()
					is_new = True
				else:
					# This block is part of a collection.
					assert self.current_collection != None
					base = None
					self.seq[None] = Oneseq ()
					info, self.seq[None].direction = get (info, 'direction', int)
					assert self.seq[None].direction >= 1 and self.seq[None].direction <= 9 and self.seq[None].direction != 5
					info, is_new = get (info, 'new', True)
				if is_new:
					self.seq[base].code = -1
					self.seq[base].frames = []
					self.seq[base].repeat = False
					gif = os.path.join (d, base + os.extsep + 'gif')
					assert os.path.exists (gif)
					f = Image.open (gif)
					while True:
						self.seq[base].frames += ((f.info['duration'], convert_image (f)),)
						try:
							f.seek (len (self.seq[base].frames))
						except EOFError:
							break
					w = self.seq[base].frames[0][1].size[0]
					h = self.seq[base].frames[0][1].size[1]
					box = [[None] * 7] * len (self.seq[base].frames) + [w / 2, h * 8 / 10, -w * 4 / 10, -h / 10, w * 4 / 10, h / 10, self.seq[base].frames[0][0]]
					info, self.seq[base].filename = 'graphics\\%s-' % base
					self.seq[base].type = 'normal'
					self.seq[base].special = 1
					self.seq[base].preload = ''
					self.seq[base].num = len (self.seq[base].frames)
				else:
					self.seq[base] = self.collections[self.current_collection].seq[self.seq[base].direction]
					del self.collections[self.current_collection].seq[self.seq[base].direction]
					box = self.seq[base].box
					del self.seq[base].box
			# Now the sequence is prepared for use. The box is created from info if present, from box[f] otherwise, or from default_box otherwise.
			info = self.prepare (info, base, box)
		# Also prepare all sequences which have not been changed by info.txt.
		for base in self.seq:
			if 'box' in dir (self.seq[base]):
				box = self.seq[base].box
				del self.seq[base].box
				self.prepare ({}, base, box)
		# Reserve all codes which fit in a collection.
		for c in self.collection:
			for s in range (len (self.collection[c].seq)):
				if not self.collection[c].seq[s]:
					continue
				if 'box' in dir (self.collection[c].seq[s]):
					self.seq[None] = self.collection[c].seq[s]
					box = self.seq[None].box
					del self.seq[None].box
					self.prepare ({}, None, box)
					self.collection[c].seq[s] = self.seq[None]
					del self.seq[None]
			for s in [1, 2, 3, 4, 6, 7, 8, 9]:
				if self.collection[c].code + s not in self.codes:
					self.codes += [self.collection[c].code + s]
		nextseq = 1
		for s in self.seq:
			if self.seq[s].code == -1:
				self.seq[s].code = nextseq
				nextseq += 1
				while nextseq in self.codes:
					nextseq += 1
	def find_seq (self, name):
		if not name:
			return 0
		if type (name) == int:
			return name
		return self.seq[name].code
	def find_collection (self, name):
		return self.collection[name].code
	def write_seq (self, ini, seq):
		if seq.preload:
			ini.write ('// Preload\n')
			ini.write ('load_sequence_now %s %d\n' % (seq.preload, seq.code))
		if len (seq.desc) > 0:
			delay = seq.desc[0].delay
		else:
			delay = None
		if seq.now:
			now = '_now'
		else:
			now = ''
		if seq.type == 'normal':
			if len (seq.desc) == 0 or 'x' not in dir (seq.desc[0]):
				if delay != None:
					ini.write ('load_sequence%s %s %d %d\n' % (now, seq.filename, seq.code, delay))
				else:
					ini.write ('load_sequence%s %s %d\n' % (now, seq.filename, seq.code))
			else:
				if delay != None:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d %d\n' % (now, seq.filename, seq.code, delay, seq.desc[0].x, seq.desc[0].y, seq.desc[0].left, seq.desc[0].top, seq.desc[0].right, seq.desc[0].bottom))
				else:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d\n' % (now, seq.filename, seq.code, seq.desc[0].x, seq.desc[0].y, seq.desc[0].left, seq.desc[0].top, seq.desc[0].right, seq.desc[0].bottom))
		else:
			ini.write ('load_sequence%s %s %d %s\n' % (now, seq.filename, seq.code, seq.type.upper ()))
		for n, f in zip (range (len (seq.frames)), seq.frames):
			if f != None:
				f[1].save (os.path.join (d, (g + '-%02d' + os.extsep + 'bmp') % (n + 1)))
		for f in range (len (seq.desc)):
			if 'seq' in dir (seq.desc[f]):
				ini.write ('set_frame_frame %d %d %d %d\n' % (seq.code, f + 1, self.find_seq (seq.desc[f].seq), seq.desc[f].frame))
			if 'x' in dir (seq.desc[f]):
				if 'x' not in dir (seq.desc[0]) or (((seq.type != 'normal' or seq.desc[0].x, seq.desc[0].y, seq.desc[0].left, seq.desc[0].top, seq.desc[0].right, seq.desc[0].bottom) != (seq.desc[f].x, seq.desc[f].y, seq.desc[f].left, seq.desc[f].top, seq.desc[f].right, seq.desc[f].bottom)) and seq.desc[f].right != None and seq.desc[f].right - seq.desc[f].left != 0):
					ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\n' % (seq.code, f + 1, seq.desc[f].x, seq.desc[f].y, seq.desc[f].left, seq.desc[f].top, seq.desc[f].right, seq.desc[f].bottom))
			if 'seq' in dir (seq.desc[f]) or (f > 0 and seq.desc[f].delay != seq.desc[0].delay):
				ini.write ('set_frame_delay %d %d %d\n' % (seq.code, f + 1, int (seq.desc[f].delay)))
			if f != 0 and seq.special == f + 1:
				ini.write ('set_frame_special %d %d\n' % (seq.code, f + 1))
		if seq.repeat:
			ini.write ('set_frame_frame %d %d -1\n' % (seq.code, len (seq.desc) + 1))
	def write (self, root):
		# Write graphics/*
		# Write dink.ini
		d = os.path.join (root, 'graphics')
		if not os.path.exists (d):
			os.mkdir (d)
		ini = open (os.path.join (root, 'dink.ini'), 'w')
		for c in self.collection:
			for s in self.collection[c].seq:
				if s:
					self.write_seq (ini, s)
		for g in self.seq:
			self.write_seq (ini, self.seq[g])

class Sound:
	def __init__ (self, parent):
		self.parent = parent
		ext = os.extsep + 'wav'
		self.sound = {}
		other = []
		codes = []
		for s in os.listdir (os.path.join (parent.root, "sound")):
			if not s.endswith (ext):
				continue
			r = re.match ('(\d+)-', s)
			if not r:
				other += (s[:-len (ext)],)
			else:
				code = int (r.group (1))
				self.sound[s[len (r.group (0)):]] = code
				assert code not in codes
				codes += (code,)
		i = 1
		for s in other:
			while i in codes:
				i += 1
			self.sound[s] = i
			i += 1
		ext = os.extsep + 'mid'
		self.music = [s[:-len (ext)] for s in os.listdir (os.path.join (parent.root, "music")) if s.endswith (ext)]
	def find_sound (self, name):
		"""Find wav file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		return self.sound[name]
	def find_music (self, name):
		"""Find midi file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		assert name in self.music
		return self.music.index (name) + 1
	def write (self, root):
		# Write sound/*
		dst = os.path.join (root, 'sound')
		if not os.path.exists (dst):
			os.mkdir (dst)
		src = os.path.join (self.parent.root, 'sound')
		for s in self.sound:
			f = s + os.extsep + 'wav'
			open (os.join (dst, f), 'w').write (open (os.join (src, f)).read ())
		for s in range (len (self.music)):
			f = self.music[s] + os.extsep + 'mid'
			open (os.join (dst, str (s + 1) + os.extsep + 'mid'), 'w').write (open (os.join (src, f)).read ())

class Script:
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		d = os.path.join (parent.root, "script")
		for s in os.listdir (d):
			ext = os.extsep + 'c'
			if not s.endswith (ext):
				continue
			base = s[:-len (ext)]
			assert base not in self.data
			self.data[base] = open (os.path.join (d, s)).read ()
		f = open (os.path.join (parent.root, "title" + os.extsep + "txt"))
		info = readlines (f)
		info, self.title_music = get (info, 'music', '')
		info, self.title_color = get (info, 'color', 0)
		info, self.title_bg = get (info, 'background', '')
		info, p = get (info, 'pointer', 'special 8')
		p = p.split ()
		self.title_pointer_seq, self.title_pointer_frame = p[0], int (p[1])
		info, self.title_run = get (info, 'run', '')
		info, n = get (info, 'sprites', 0)
		self.title_sprite = []
		for s in range (n):
			info, spr = get (info, 'sprite-%d' % (s + 1))
			spr = spr.split ()
			if len (spr) == 4:
				spr += ('repeat',)
			if len (spr) == 5:
				spr += ('',)
			assert len (spr) == 6
			self.title_sprite += ((spr[0], int (spr[1]), int (spr[2]), int (spr[3]), spr[4], spr[5]),)
		info, n = get (info, 'buttons', int)
		self.title_button = []
		for s in range (n):
			info, b = get (info, 'button-%d' % (s + 1))
			b = b.split ()
			assert len (b) == 5
			self.title_sprite += ((b[0], int (b[1]), int (b[2]), int (b[3]), 'button', b[4]),)
		assert info == {}
	def write (self, root):
		# Write Story/*
		d = os.path.join (root, 'story')
		if not os.path.exists (d):
			os.mkdir (d)
		for name in self.data:
			f = open (os.path.join (d, name + os.extsep + 'c'), 'w')
			f.write (preprocess (self.data[name], self.parent))
		# Write start.c
		s = open (os.path.join (d, 'start' + os.extsep + 'c'), 'w')
		s.write ('void main ()\n{\n')
		for n, snd in zip (range (len (self.parent.sound.sound)), self.parent.sound.sound):
			s.write ('\tload_sound ("%s.wav", %d);\n' % (snd, n))
		s.write ('set_dink_speed (3);\nsp_frame_delay (1,0);\n')
		if self.title_bg != '':
			s.write ('copy_bmp_to_screen ("%s");\n' % self.title_bg)
		else:
			s.write ('fill_screen (%d);\n' % self.title_color)
		s.write ('''\
sp_seq (1, 0);
sp_brain (1, 13);
sp_pseq (1, %d);
sp_pframe (1, %d);
sp_que (1, 20000);
sp_noclip (1, 1);
int &crap;
''' % (self.parent.seq.find_seq (self.title_pointer_seq), self.title_pointer_frame))
		for t in self.title_sprite:
			s.write ('&crap = create_sprite (%d, %d, %d, %d, %d);\n' % (t[2], t[3], brains.index (t[4]), self.parent.seq.find_seq (t[0]), t[1]))
			if t[5] != '':
				s.write ('sp_script(&crap, "%s");\n' % t[5])
				s.write ('sp_touch_damage (&crap, -1);\n')
			s.write ('sp_noclip (&crap, 1);\n')
		if self.title_music != '':
			s.write ('playmidi ("%s.mid");\n' % self.title_music)
		if self.title_run != '':
			s.write ('spawn ("%s");\n' % self.title_run)
		s.write ('kill_this_task ();\n}\n')
		# Write main.c
		s = open (os.path.join (d, 'main' + os.extsep + 'c'), 'w')
		s.write ('void main ()\n{')
		global the_globals
		for v in the_globals:
			s.write ('\tmake_global_int ("&%s", %d);\n' % (v, the_globals[v]))
		for t in range (max_tmp):
			s.write ('\tmake_global_int ("&tmp%s", %d);\n' % (t, 0))
		s.write ('\tkill_this_task ();\n}\n')

class Dink:
	def __init__ (self, root):
		self.root = root
		self.tile = Tile (self)
		self.world = World (self)
		self.seq = Seq (self)
		self.sound = Sound (self)
		self.script = Script (self)
		self.info = open (os.path.join (root, 'info' + os.extsep + 'txt')).read ()
		im = os.path.join (root, 'image')
		p = os.path.join (im, 'preview' + os.extsep + 'png')
		if os.path.exists (p):
			self.preview = convert_image (Image.open (p))
		p = os.path.join (im, 'splash' + os.extsep + 'png')
		if os.path.exists (p):
			self.splash = convert_image (Image.open (p))
	def write (self, root):
		if not os.path.exists (root):
			os.mkdir (root)
		# Write tiles/*
		self.tile.write (root)
		# Write dink.dat
		# Write hard.dat
		# Write map.dat
		self.world.write (root)
		# Write dink.ini
		# Write graphics/*
		self.seq.write (root)
		# Write sound/*
		self.sound.write (root)
		# Write story/*
		self.script.write (root)
		# Write the rest
		if 'preview' in dir (self):
			self.preview.save (os.path.join (root, 'preview' + os.extsep + 'bmp'))
		if 'splash' in dir (self):
			self.splash.save (os.path.join (os.path.join (root, 'tiles'), 'splash' + os.extsep + 'bmp'))
		open (os.path.join (root, 'dmod' + os.extsep + 'diz'), 'w').write (self.info)
