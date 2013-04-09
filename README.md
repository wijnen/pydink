# Introduction
This is PyDink, an alternative engine and editor for Dink Smallwood.  It
requires the (free) artwork of the original game (or new artwork, of course).

The engine is currently not entirely functional and will not be entirely
bug-compatible.  Several choices have been made which make things work
differently from the original game.

The editor creates games for both the original as well as this new engine.
DMods which were not made with this editor cannot be played on this engine.

## Setting up the system
First make sure you have Python, PyGtk, the Python Imaging Library and FreeDink
installed.  If you want decompile to work, you also need numpy.  You can get
them here:

http://python.org/download
http://pygtk.org/downloads.html
http://www.pythonware.com/products/pil/
http://www.dinknetwork.com/file/gnu_freedink
http://sourceforge.net/projects/numpy/files/NumPy/

(They're all free software, which means that if you're not using Windows, you
can most likely save yourself some trouble and install them with your package
manager.)

PyGtk has two version numbers: its own version, and the Python version that it
should work with.  Make sure that this second version matches the Python
version that you are installing.  (Check that matching versions exist before
downloading.)  At this moment, the highest Python version that PyGtk supports
is 2.7.

Install Python before installing PyGtk, PIL, or NumPy.

You will need to edit scripts during DMod making.  Don't use a lousy editor like
notepad if you want to keep your sanity.  For beginners, I recommend gedit:
http://gedit.en.softonic.com/.  If you want real power and don't mind having
to learn how to use it first, I recommend vim: http://www.vim.org/download.php
(and feel free to ask for help learning)

## Setting up PyDink
Edit pde.gui.  It is an xml file which can be edited with your text editor.  The
Settings at the top should be changed to match you system and preferences.  What
they mean:
script_editor:
	The command to run for editing a script.  The default value starts a new
	terminal with vi in the directory of the script on a unix system.  It
	will not work on Windows.  Change it for example to "gedit '$SCRIPT'".
	Note that in Windows you normally need to specify full paths, so
	something like "'C:\Program Files\gedit\gedit.exe' '$SCRIPT'".  Don't
	forget the single quotes.
hardness_editor:
	The command to run for editing hardness.  The default value starts the
	gimp, which should work if you have installed it (unless you are on
	Windows, where you need a full path again).  Change it to your
	preferred image editor if you don't.
*_gc:
	Colours of many elements in the gui.  Feel free to change them.  Values
	can be certain names, or an rgb-code, such as "#f0c" (very red, no
	green, quite some blue: reddish purple)
nobackingstore:
	On slow systems, draw directly to the screen instead of an off-screen
	window, which is then copied to the screen.  Setting this to True will
	make the program fast and ugly.  Unless you are experiencing slowness
	in the screen drawing, leave this to False.

The first time you start the PyDink Editor (pde), it will notice that there is
no cache, and generate it.  For this, it will ask you a few questions.  Set up
all the paths, then make it generate the cache.  It will give some errors when
generating the cache; these are errors in Dink's source code.  They can be
safely ignored.

If you want to change these settings, either change config.txt in your
configuration directory (~/.config/pydink/ on unix), or run makecache.py again.

# Running the editor

## IMPORTANT NOTE
    For those who are used to writing DinkC scripts: I know you are used to
    writing workarounds for all sorts of bugs.  Please do not do this with
    PyDink.

    If something doesn't work as it should, or some functionality is not
    available, but would be very useful, instead of hacking around it, please
    file a bug report or feature request.

    If you encounter a bug and decide you can use it as a feature, expect your
    DMod to break on it in the next version of PyDink.  Future PyDink versions
    will not be backwards compatible when it comes to bugs.

If everything is correctly set up (see above), a window should open when you
run pde.py.  This window has a map on the left and a side bar on the right
(unless you've changed the interface in pde.gui ;-) ).  It starts in world
view; click on a map position to go to normal editing view.

Every command is a single key or key combination.  For many keys, the pointer
position while pressing it matters.  So move your pointer to the right place,
then press the key.  You can cancel an editing action by pressing the right
mouse button or the Escape key, or confirm it using the left mouse button or
Enter key.  Undo is not implemented, nor is auto-save, so be careful.
Auto-backup is implemented, so to simulate undo, just save a lot.

## Very fast introduction

The editor starts in world overview mode; the rectangles are the map screens.
Click on the map to start editing at that location.

The first thing you'll want to do in a new dmod is create a map screen: Press
ctrl-insert while the pointer is hovering over the map screen you want to
create.  If you want to remove it again, you can press ctrl-delete while
hovering over it.

To do mapping, use t to go to the tile screens.  Select tiles there by clicking
or dragging the left mouse button while holding the shift key.  Press t again
to go back.  Use the middle mouse button to paste the selected tiles.  Once
there are some tiles on the map, the same method can be used to reorganise
tiles in the real world (copying from map screen instead of from tile screen).

Alternatively, press the y button (or ctrl-c) after selecting for yanking them
into the buffer (this will also take you back to the map screen), then select a
new region and press f there to fill it with the selection, or press r for
random fill with tiles from the selection (useful for fields of grass, for
example).

Now add a sprite: press 0 on the numpad to select from a list of non-collection
(see below) sequences.  Select a sequence by clicking and holding the middle
mouse button.  Its frames appear and you can select one.  The first frame can
also be selected from the position where the sequence was, so just clicking and
not holding will select the first frame.  The sprite will appear where your
pointer was when you pressed 0.  If it isn't at the right place, press m to
move it, then move your pointer.  Note that it moves with, not to, the pointer.
This makes more sense for multi-sprite select.  Left-click to finish the move
action.  Similarly, use s to scale and q to set the depth que.  In all cases,
for fine tuning you can also move with the cursor keys.  Pressing enter will
also confirm the operation; right mouse button and escape both cancel the
operation and make the object return to its original position (or size, or
whatever you were editing).

Instead of 0, you can also use other keys on the numpad to create collection
sprites.  A collection is several sequences which represent different
directions of the same thing.  For example, Dink has 8 directions where he can
walk; the "walk" collection is a combination of those 8 sequences.  The
directions can be read directly from the numpad.  For example, 1 is pointing to
bottom left, 6 to the right.  5 is special, it is the death sequence of a
collection.  The death sequence of the sprite's walk collection will be used
when a monster dies (unless base_death is set; in that case a sequence from
that collection will be used).

When using collection sequence select, all collections are shown, even those
without a sequence for that direction.  For those collections, a different
direction is used instead.

If you have sprites selected and use the left mouse button in the sequence
selection screen, the sequence of the selected sprites is changed and no new
sprites are added.  When using the left mouse button in the sequence selection
screen while a warp target is selected, the sprite's touch sequence (which will
be played when warping) is changed (the frame is ignored in that case).  When
viewing collections, pressing the w, a, i, or d button while hovering over a
collection will set the selected sprites' walk, attack, idle and death
collection respectively.

To give your sprite a warp, press ctrl-w while it is selected.  It will now be
warping to the pointer position.  You see the hardbox of the sprite drawn in
pink to reflect that it has an active warp target.  When any warping sprites or
warp targets are selected, pressing w will toggle the selection between the
warp target and the sprite itself.  The j key is particularly useful in
combination with this; that will make the view jump to the current selection.
So to see where a warp is going or coming from, select the sprite or warp
target by clicking on it, then press w to select the other one and press j to
see where it is.

When multiple sprites are selected, the n key (n for next) has a similar
function; it will jump to all selected sprites in turn (j jumps to a point in
their center).

Standard pointer actions:
left-click: select single sprite or tile (with shift).
ctrl-left-click: add or remove single sprite or tile (with shift) to or from
	selection.
left-drag: select multiple sprites or tiles (with shift).
ctrl-left-drag: add or remove multiple sprites or tiles (with shift) to or from
	selection.
middle-click: paste selected sprites or tiles around current pointer position.
middle-drag: pan view.
right-click: cancel current operation.

There are 10 layers available to sort the sprites.  By default, layer 9 is for
invisible background sprites and layer 0 for visible (normal) background
sprites.  You can change these settings in the layer edit tab.  Pressing a
number key (not on the numpad) changes the active layer.  Using ctrl and a
number key moves the selected sprites to a new layer.  Sprites which are not in
the active layer cannot be selected, so this can be used to temporarily ignore
a group of sprites.  However, selected sprites remain selected when the active
layer is changed, so it is possible to multi-select several sprites from
different layers.

To quick-test the dmod, put your pointer on the desired starting position and
press ctrl-p.  The title screen and intro will be skipped, and Dink will start
at the pointer position.  To fully test it (including title screen and intro),
use the "Play" button from the sidebar or menu.  To save it, press ctrl-s.
Save it with a new name with ctrl-shift-s.  To build the dmod for playing
outside the editor, press ctrl-b.  To quit the editor, press ctrl-q or close
the window.  Note that it doesn't ask for confirmation when there are unsaved
changes, so be careful.

You will need to edit info.txt before building a real dmod.  This can be done
from the DMod tab.  If you want to use non-standard graphics, you will also
need to add them manually.  If you want to use graphics from other DMods, the
decompile script can help you converting them.

Making any manual changes (like adding new graphics) must be done while the
editor is not running, because the editor works on an internal copy of the
data.  If you change the data on disk and then save, the changed data is moved
to the backup directory and a new version without the changes is saved in its
place.

## Editing scripts
The primary reason for starting this project was that Dink's script parsing is
too terrible to work with.  Therefore I started a script preprocessor, which
grew out to be this editor.  Obviously, scripts written with this editor are
much easier to write than original DinkC scripts.  But in some cases you will
need to know about some quirks of the engine, because there was no way to hide
them.  I'll try here to describe the system.

In the following, the notation file.function refers to a function in
story/file.c.  In all cases, if a file or function doesn't exist, nothing
happens.  This is not an error unless otherwise noted.

### Special scripts
There are a few special scripts.  Here's a list of them, and their functions.
* start.c: This is run when the game starts.  It should create the title screen.
  If it is missing, a default title screen with buttons for start, continue and
  quit is used.  Scripts for those buttons are also generated, called
  game-start.c, game-continue.c and game-quit.c.  These scripts are not used
  (unless created by the dmod) if the default start.c is not used.  This is
  skipped when doing a quick play-test, so don't use this to set up the game.

* intro.c: This is run after start_game () is executed.  It should play an intro
  sequence, if any.  This is skipped when doing a quick play-test, so don't use
  this to set up the game.  However, it should be used to set Dink's starting
  position.  Since that must be skipped for play-testing, it cannot be done in
  init.

* init.c: This is run after start_game () is executed, after the intro is
  played.  It should set the game up for playing.  However, it must not set
  Dink's starting position (this must be done in intro.c), because this
  function is called when play-testing, and Dink should be moved to the pointer
  position in that case.

### When scripts run
Nothing has changed when it comes to when scripts are started and when they
abort.  Scripts can be started for the following reasons (Note that this list is
not complete):
* When the engine starts, start.main runs.  (For those who know about the
  engine: main.main runs first, but that is generated by the PyDink and cannot
  be changed.) When play-testing, instead of the real start.main, a script
  containing only start_game () is used, so the title screen is skipped.  Note
  that the entire file is changed, so no other functions for external use
  should be created in the start script (they will not work during
  play-testing).

* When start_game () is executed, intro.main runs, and then init.main.  In case
  of play-testing, instead of the real intro.main, a script containing code to
  set the player position is used, so the intro is skipped and Dink is moved to
  the desired position.  As with the start script, the entire intro script is
  replaced while play-testing, so no other functions for external use should be
  defined there.

* When draw_screen() is executed, [screenscript].main runs, and then
  [spritescript].main for each active sprite on the screen (this means
  main functions can change which sprites are active).

* When events happen (talk, use, touch, etc), [spritescript].[event] runs.  But
  there is a complication: if [spritescript] was still doing something else,
  that operation is aborted.  For example, if a sprite responds to talking, and
  the response waits for some time (for example, by using say_stop), and during
  that wait the user talks to it again, the talk function will be started once
  again, and the one that was started first is _NOT_ finished.  This is a
  problem of the original Dink engine.  The PyDink engine is not compatible with
  this behavior, and _DOES_ run both script instances in parallel.

* Some scripts can be started in case of special events, such as talking to
  nothing (dnotalk.main), magic without armed magic (dnomagic.main), pressing a
  key (key[num].main), or dying (dinfo.die).

### How scripts look
At top level, scripts can contain three things:
* extern int variables
	A variable which is declared as extern can be used without defining it
	inside a function.  It will be a global variable, so its value is shared
	between all functions in all scripts.  The Dink engine has a limit to
	the number of global variables (the PyDink engine does not), so don't
	use them if you don't need to.  Global variables are always initialized
	to 0.
* static int variables
	These are variables which are meant to be stored on a per-sprite basis.
	You should use them for storing things which are private for the
	sprite.  For example, if you have two monsters and both have to keep a
	separate value, you can use a static variable to store it.  (For those
	who are used to DinkC scripting: the variable will be defined inside
	the main function and can be used by other functions in the same script
	instance.  Please do not do dirty tricks with this: the per-sprite use
	will be strictly enforced by PyDink's engine, and you don't want your
	DMod to break on that, now do you?) Like extern variables, static
	variables cannot be defined with an initializer.  They can of course be
	initialized inside the main function.
* function definitions.
	This is the bulk of any script.  A function's return type can be void or
	int.  It can have any number of arguments, all of them must be of type
	int.

Inside functions, there are some differences to DinkC:
* Functions which accept a brain, sequence, collection, sound, music, or editor
  sprite number as argument can (and should, unless it's computed) instead be
  given a string argument.  Brain names can be found in dink.py; all other names
  in readini.py.  Custom artwork is named by the directory it is put in.  All
  names are also shown in the editor.  Note that editor sprites must be locked
  to a map screen, otherwise using their name is not allowed.  (The PyDink
  engine does allow using them without locking, but if you want your DMod to be
  buildable for the original Dink engine, you shouldn't use this feature.)

* There are new functions brain_code, seq_code, collection_code, sound_code,
  music_code and sp_code to get the numbers which correspond to the names.  This
  way they can be passed into other functions, or used in computations.

* A new function start_game does everything needed to start a new game.  It
  calls set_mode (2), runs intro.main and init.main.  set_mode is not recognized
  as a function.

* Variables are named without &, just like in normal C.

* Expressions can be combined (1 + (3 * 5)), like in normal C.

* Function calls to local functions can be made by calling their name and
  arguments; calling functions from other script files can be done by
  prepending the script name and a period: scriptfile.function (arg1, arg2).

* Function calls can be part of expressions.

* The operators &&, || and ! work as you would expect in C.

* The variable missile_source must not be misspelled.

* Variable names in string constants work the same way as they do in DinkC, but
  must be followed by a semicolon to mark their end, for example:
  "That will cost you &amount; gold."
  If you want to insert a literal & in a string, write it as an empty variable:
  "This is cool &; great."

* The choice statement has been changed to look more like a normal C statement.
  It is a function which takes any number of string arguments.  Before any
  string argument, there may be a single int argument condition.  The return
  value is the chosen value.  A simple use case is:
	if (choice ("Yes", "No") == 1) say_stop ("Yes!", 1);
  A more complete example:
	choice_title ("What is your answer?");
	int answer = choice ("Yes", "No", clearance > 3, "Shutdown");
	if (answer == 1)
		say_stop ("Yes!", 1);
	else if (answer == 3)
	{
		say_stop ("Shutting down.", 1);
		stop = 1;
	}

- When using choice_stop instead of choice, stop_entire_game (1) is called
  before choice.  The function stop_entire_game is not recognized as a function.

Last but not least: Spaces, tabs and newlines are all considered whitespace and
are mostly ignored, just like in C.  This is true at top level and inside
functions.

# The PyDink engine
The engine is a script called play.py.  You can run it from the commandline:
python play.py path/to/dmod
Note that it wants a path to the PyDink files, not the built DMod.

The engine is not finished yet, and probably buggy.  But feel free to test it.

# Decompile
This is a script which tries to decompile any dmod into a format which pydink
can understand.  It is particularly useful for examining the dmod in ways that
dinkedit doesn't support (for example, jumping from warp target to the warping
object location), and for using custom artwork from other dmods.  It may also
find some bugs in dink.ini.  It does not attempt to convert the DinkC scripts,
nor does it find bugs in them.  This also means that a decompiled dmod cannot be
recompiled and played.

Using it is not Windows-friendly: you need to run it from the commandline and
it requires exactly two arguments: the path to the dmod directory which should
be decompiled, and the path to the new pydink dmod directory, which must not
exist yet.  If you are using Windows, you must run Python explicitly:
C:\path\to\python path\to\decompile path\to\dmod path\to\new_dmod

# Bugs
There are no known bugs.  Which doesn't mean there aren't any bugs.  Please
report them if you find any (see next section).

# Finally
Feedback is very welcome.  Contact me at wijnen@debian.org, or by posting on the
dink network (http://dinknetwork.com/forum.cgi).
