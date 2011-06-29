# Set this to true if you have 512 MB or less real RAM memory.
lowmem = True
# Directory where cache is located.
cachedir = '~/.cache/dink'
# Directory where dink is installed.
dinkdir = '/usr/share/games/dink'
# Program to run when pressing 'p'.
# Note: if this is not freedink, you will need to change the arguments in dink.py.
dinkprog = '/usr/games/dink'
# Maximum number of pixbufs in cache. This setting is only used if lowmem == True.
# Indication: there are 224 built-in sequences.
maxcache = 500

class Sequence:
	pass
class Frame:
	pass
