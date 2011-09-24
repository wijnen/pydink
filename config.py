# Set this to True if you have 512 MB or less real RAM memory.
lowmem = False
# Maximum number of pixbufs in cache. This setting is only used if lowmem == True.
# Indication: there are 224 built-in sequences.
maxcache = 500
# Disable backing store for windows. This makes the X server use less memory, but it causes flicker.
nobackingstore = False
# Directory where cache is located.
cachedir = '~/.cache/dink'
# Directory where dink is installed.
dinkdir = '/usr/share/games/dink'
# Program to run when pressing 'p'.
# Note: if this is not freedink, you will need to change the arguments in dink.py.
dinkprog = '/usr/games/dink'
# Number of pixels per tile in the sequence selection widgets.
tilesize = 30
# Number of tiles per line in the sequence selection widgets.
seqwidth = 20

class Sequence:
	pass
class Frame:
	pass
