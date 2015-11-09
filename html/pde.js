// vim: set fileencoding=utf-8 foldmethod=marker:
// {{{ Copyright header
// pde - pydink editor: editor for pydink games.
// Copyright 2011-2015 Bas Wijnen
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
/// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
// }}}

// Variables. {{{
var map = [];
var tilemaps = [];
var sequences = {};
var seqnames = [];
var collections = {};
var collectionnames = [];
var pos = [32 * 600 / 2 - 300, 24 * 400 / 2 - 200];
var canvas, context, canvasdiv;
var canvascache = {};
var ref_pos = null;
var orig_pos = null;
var action = null;
var moved;
var action_shift;
var action_ctrl;
var info, game;
var dirs = [1, 2, 3, 4, 'die', 6, 7, 8, 9];
var gui = {};
var current_map = 0;
var current_frame = 1;
var selection = [], sprite_selection = null;
var music = {};
var sound = {};
var current_audio = null;
// }}}

// Initialization. {{{
function get_file(file, cb) { // {{{
	var xhr = new XMLHttpRequest();
	xhr.open('GET', file);
	xhr.AddEvent('loadend', function() { cb(xhr.responseText); });
	xhr.send();
} // }}}

AddEvent('load', function() { // {{{
	canvasdiv = document.getElementById('content');
	canvas = document.getElementById('map');
	context = canvas.getContext('2d');
	get_file('info.txt', function(reply) {
		info = JSON.parse(reply);
		get_file('game.txt', function(reply) {
			game = JSON.parse(reply);
			data_init();
			maps_init();
			sprite_init();
			window.AddEvent('resize', redraw_all);
			redraw_all(true);
		});
	});
}); // }}}

function data_init() { // {{{
	if (game.locations === undefined)
		game.locations = {};
	// Layers. {{{
	gui.active_layer = document.getElementById('active_layer');
	gui.layer = [];
	game.layer.push([]);
	for (var i = 0; i < game.layer[0].length; ++i) {
		gui.layer.push([document.getElementById('layer' + i), document.getElementById('visible' + i), document.getElementById('background' + i)]);
		gui.layer[i][1].checked = game.layer[0][i];
		gui.layer[i][2].checked = game.layer[1][i];
		var type;
		if (!game.layer[0][i] && !game.layer[1][i])
			type = 3;
		else if (!game.layer[0][i] && game.layer[1][i])
			type = 1;
		else
			type = 0;
		gui.layer[i][0].selectedIndex = type;
	} // }}}
	// Tiles. {{{
	gui.tiles_canvas = document.getElementById('tiles');
	for (var i = 0; i < info.tiles.length; ++i) {
		var img, hard;
		if (info.tiles[i][0]) {
			img = Create('img');
			img.src = 'tiles/' + i + '.png';
		}
		else {
			img = null;
		}
		if (info.tiles[i][1]) {
			hard = Create('img');
			hard.src = 'tiles/' + i + '-hard.png';
		}
		else {
			hard = null;
		}
		tilemaps.push([img, hard]);
	} // }}}
	// Sequences. {{{
	gui.seq_canvas = document.getElementById('sequences');
	gui.seq_ctx = gui.seq_canvas.getContext('2d');
	for (var s in info.seq) {
		if (typeof(info.seq[s]) != 'object') {
			continue;
		}
		seqnames.push(s);
		sequences[s] = [];
		for (var f = 0; f < info.seq[s].length; ++f) {
			if (!info.seq[s][f]) {
				sequences[s].push([null, null]);
				continue;
			}
			var img = Create('img');
			img.src = 'seq/' + s + '-' + f + '.png';
			var hard;
			if (info.seq[s][f].hard) {
				hard = Create('img');
				hard.src = 'seq/' + s + '-' + f + '-hard.png';
			}
			else {
				hard = null;
			}
			sequences[s].push([img, hard]);
		}
	}
	seqnames.sort();
	// }}}
	// Collections. {{{
	gui.collection_canvas = document.getElementById('collections');
	gui.collection_ctx = gui.collection_canvas.getContext('2d');
	for (var c in info.collections) {
		if (typeof(info.collections[c]) != 'object')
			continue;
		collections[c] = {};
		collectionnames.push(c);
		for (d = 0; d < dirs.length; ++d) {
			if (info.collections[c][dirs[d]] === null) {
				collections[c][dirs[d]] = null;
				continue;
			}
			collections[c][dirs[d]] = [];
			for (var f = 0; f < info.collections[c][dirs[d]].length; ++f) {
				if (!info.collections[c][dirs[d]][f]) {
					collections[c][dirs[d]].push([null, null]);
					continue;
				}
				var img = Create('img');
				img.src = 'collection/' + c + '-' + f + '-' + dirs[d] + '.png';
				var hard;
				if (info.collections[c][dirs[d]][f].hard) {
					hard = Create('img');
					hard.src = 'collection/' + c + '-' + f + '-' + dirs[d] + '-hard.png';
				}
				else {
					hard = null;
				}
				collections[c][dirs[d]].push([img, hard]);
			}
		}
	}
	collectionnames.sort();
	// }}}
	// Images. {{{
	gui.preview = document.getElementById('preview');
	gui.splash = document.getElementById('splash');
	var add_img = function(name, title) {
		if (title === undefined)
			title = name;
		gui.preview.AddElement('option').AddText(title).value = name;
		if (game.preview == name) {
			gui.preview.selectedIndex = gui.preview.options.length - 1;
		}
		gui.splash.AddElement('option').AddText(title).value = name;
		if (game.splash == name) {
			gui.splash.selectedIndex = gui.splash.options.length - 1;
		}
	};
	add_img('', '-');
	for (var i = 0; i < info.image.length; ++i) {
		add_img(info.image[i]);
	}
	// }}}
	// Music. {{{
	for (var m = 0; m < info.music.length; ++m) {
		if (info.music[m][1] != 'mid') {
			music[info.music[m][0]] = Create('audio');
			music[info.music[m][0]].src = 'music/' + info.music[m][0] + '.' + info.music[m][1];
		}
	}
	// }}}
	// Sound. {{{
	for (var s = 0; s < info.sound.length; ++s) {
		sound[info.sound[s][0]] = Create('audio');
		sound[info.sound[s][0]].src = 'sound/' + info.sound[s][0] + '.' + info.sound[s][1];
	}
	// }}}
	gui.world_canvas = document.getElementById('world');
	gui.settings = document.getElementById('settings');
} // }}}

function redraw_all(flush) {
	gui.redraw_impl(flush);
}
// }}}

// Load and save. {{{
function sync() {
	for (var i = 0; i < game.layer[0].length; ++i) {
		game.layer[0][i] = gui.layer[i][1].checked;
		game.layer[1][i] = gui.layer[i][2].checked;
	}
	game.preview = gui.preview.options[gui.preview.selectedIndex].value;
	game.splash = gui.splash.options[gui.splash.selectedIndex].value;
}

function dmod_export() {
	sync();
	var a = document.getElementById('dmod_export');
	if (a.href != '#')
		URL.revokeObjectURL(a.href);
	var blob = new Blob([JSON.stringify(game)], {type: 'octet/stream'});
	a.href = URL.createObjectURL(blob);
	a.download = 'dmod.json';
}

function dmod_save() {
	sync();
	localStorage.dmod = JSON.stringify(game);
}

function load(data) {
	game = JSON.parse(data);
	redraw_all(true);
}

function dmod_load() {
	load(localStorage.dmod);
}

function dmod_import() {
	var input = document.getElementById('dmod_import');
	if (input.files.length < 1) {
		return;
	}
	var reader = new FileReader();
	reader.onloadend = function() {
		load(reader.result);
	};
	reader.readAsText(input.files[0]);
}
// }}}

// UI updates. {{{
function get_selected(item) {
	if (selection.length == 0) {
		return '';
	}
	var sprites = game.world.sprite;
	if (gui.single.checked) {
		var s = gui.sprite_select.options[gui.sprite_select.selectedIndex].value;
		return sprites[s][item];
	}
	else {
		var ret = sprites[selection[0]][item];
		for (var s = 1; s < selection.length; ++s) {
			if (sprites[selection[s]][item] != ret) {
				return '';
			}
		}
		return ret;
	}
}

function set_select(select, value) {
	for (var s = 0; s < select.options.length; ++s) {
		if (select.options[s].value == value) {
			select.selectedIndex = s;
			return;
		}
	}
	select.selectedIndex = 0;
}

function update_ui() {
	var old_selected = gui.sprite_select.options[gui.sprite_select.selectedIndex] === undefined ? '' : gui.sprite_select.options[gui.sprite_select.selectedIndex].value;
	gui.sprite_select.ClearAll();
	for (var s = 0; s < selection.length; ++s) {
		gui.sprite_select.AddElement('option').AddText(selection[s]).value = selection[s];
		if (selection[s] == old_selected)
			gui.sprite_select.selectedIndex = s;
	}
	//gui.sprite_name = document.getElementById('sprite_name');
	set_select(gui.sprite_brain, get_selected('brain'));
	gui.sprite_script.value = get_selected('script');
	gui.sprite_use_hard.checked = get_selected('use_hard');
	gui.sprite_vision.value = get_selected('vision');
	gui.sprite_speed.value = get_selected('speed');
	gui.sprite_timing.value = get_selected('timing');
	set_select(gui.sprite_sound, get_selected('sound'));
	gui.sprite_strength.value = get_selected('strength');
	gui.sprite_defense.value = get_selected('defense');
	gui.sprite_hp.value = get_selected('hitpoints');
	gui.sprite_exp.value = get_selected('experience');
	gui.sprite_touch.value = get_selected('touch_damage');
	gui.sprite_gold.value = get_selected('gold');

	gui.sprite_x.value = get_selected('x');
	gui.sprite_y.value = get_selected('y');
	var seq = get_selected('seq');
	if (seq) {
		gui.sprite_seq.ClearAll().AddText(seq);
		var frame = get_selected('frame');
		gui.sprite_frame.ClearAll().AddElement('option').AddText('-').value = '';
		var s;
		if (typeof(seq) == 'string') {
			s = info.seq[seq];
		}
		else {
			s = info.collections[seq[0]][seq[1]];
		}
		if (s !== undefined) {
			for (f = 1; f < s.length; ++f) {
				gui.sprite_frame.AddElement('option').AddText(f).value = f;
			}
		}
		if (frame != '')
			gui.sprite_frame.selectedIndex = frame;
		else
			gui.sprite_frame.selectedIndex = 0;
	}
	else {
		gui.sprite_seq.ClearAll().AddText('-');
		var frame = get_selected('frame');
		if (frame != '')
			gui.sprite_frame.selectedIndex = frame + 1;
	}
	gui.sprite_size.value = get_selected('size');
	gui.sprite_que.value = get_selected('que');
	var c = get_selected('base_walk');
	gui.sprite_walk.ClearAll().AddText(c ? c : '-');
	c = get_selected('base_idle');
	gui.sprite_idle.ClearAll().AddText(c ? c : '-');
	c = get_selected('base_attack');
	gui.sprite_attack.ClearAll().AddText(c ? c : '-');
	c = get_selected('base_death');
	gui.sprite_die.ClearAll().AddText(c ? c : '-');
	gui.sprite_nohit.checked = get_selected('nohit');
	gui.sprite_map.value = get_selected('map');

	var warp = get_selected('warp');
	if (warp == '' || warp == null) {
		gui.sprite_warp.checked = false;
		gui.sprite_warp_map.value = '';
		gui.sprite_warp_x.value = '';
		gui.sprite_warp_y.value = '';
	}
	else {
		gui.sprite_warp.checked = true;
		gui.sprite_warp_map.value = warp[0];
		gui.sprite_warp_x.value = warp[1];
		gui.sprite_warp_y.value = warp[2];
	}
	var seq = get_selected('touch_seq');
	gui.sprite_touch_seq.ClearAll().AddText(seq ? seq : '-');
	gui.sprite_hard.checked = get_selected('hard') == true;
	gui.sprite_left.value = get_selected('left');
	gui.sprite_top.value = get_selected('top');
	gui.sprite_right.value = get_selected('right');
	gui.sprite_bottom.value = get_selected('bottom');
}
// }}}

// Sprite updates. {{{
function sprite_set_num(value, def) {
	if (value.value == '')
		return def;
	var ret = Number(value.value);
	if (isNaN(ret) || !isFinite(ret))
		return def;
	return Math.round(ret);
}

function sprite_update() {
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		// Name TODO?
		if (gui.sprite_brain.selectedIndex > 0)
			spr.brain = gui.sprite_brain.options[gui.sprite_brain.selectedIndex].value;
		spr.vision = sprite_set_num(gui.sprite_vision, spr.vision);
		spr.speed = sprite_set_num(gui.sprite_speed, spr.speed);
		spr.timing = sprite_set_num(gui.sprite_timing, spr.timing);
		if (gui.sprite_sound.selectedIndex > 0)
			spr.sound = gui.sprite_sound.options[gui.sprite_sound.selectedIndex].value;
		spr.strength = sprite_set_num(gui.sprite_strength, spr.strength);
		spr.defense = sprite_set_num(gui.sprite_defense, spr.defense);
		spr.hitpoints = sprite_set_num(gui.sprite_hp, spr.hitpoints);
		spr.experience = sprite_set_num(gui.sprite_exp, spr.experience);
		spr.touch_damage = sprite_set_num(gui.sprite_touch, spr.touch_damage);
		spr.gold = sprite_set_num(gui.sprite_gold, spr.gold);

		spr.x = sprite_set_num(gui.sprite_x, spr.x);
		spr.y = sprite_set_num(gui.sprite_y, spr.y);
		spr.frame = sprite_set_num(gui.sprite_frame.options[gui.sprite_frame.selectedIndex], spr.frame);
		spr.size = sprite_set_num(gui.sprite_size, spr.size);
		spr.que = sprite_set_num(gui.sprite_que, spr.que);
		spr.map = sprite_set_num(gui.sprite_map, spr.map);

		if (gui.sprite_warp.checked) {
			if (spr.warp !== null) {
				var warp_map = sprite_set_num(gui.sprite_warp_map, spr.warp[0]);
				var warp_x = sprite_set_num(gui.sprite_warp_x, spr.warp[1]);
				var warp_y = sprite_set_num(gui.sprite_warp_y, spr.warp[2]);
				spr.warp = [warp_map, warp_x, warp_y];
			}
			else {
				var warp_map = sprite_set_num(gui.sprite_warp_map, current_map);
				var warp_x = sprite_set_num(gui.sprite_warp_x, pos[0] - Math.floor((current_map - 1) % 32) * 600 + 20);
				var warp_y = sprite_set_num(gui.sprite_warp_y, pos[1] - Math.floor((current_map - 1) / 32) * 400);
				spr.warp = [warp_map, warp_x, warp_y];
			}
		}
		spr.left = sprite_set_num(gui.sprite_left, spr.left);
		spr.top = sprite_set_num(gui.sprite_top, spr.top);
		spr.right = sprite_set_num(gui.sprite_right, spr.right);
		spr.bottom = sprite_set_num(gui.sprite_bottom, spr.bottom);
	}
	redraw_all(true);
}

function sprite_update_script() {
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		spr.script = gui.sprite_script.value;
	}
}

function sprite_update_tile_hardness() {
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		spr.use_hard = gui.sprite_use_hard.checked;
	}
	redraw_all(true);
}

function sprite_update_nohit() {
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		spr.nohit = gui.sprite_nohit.checked;
	}
}

function sprite_update_warp() {
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		if (gui.sprite_warp.checked) {
			var warp_map = sprite_set_num(gui.sprite_warp_map, current_map);
			var warp_x = sprite_set_num(gui.sprite_warp_x, pos[0] - Math.floor((current_map - 1) % 32) * 600 + 20);
			var warp_y = sprite_set_num(gui.sprite_warp_y, pos[1] - Math.floor((current_map - 1) / 32) * 400);
			spr.warp = [warp_map, warp_x, warp_y];
		}
		else {
			spr.warp = null;
		}
	}
	update_ui();
	redraw_all(true);
}

function sprite_update_hard() {
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		spr.hard = gui.sprite_hard.checked;
	}
	redraw_all(true);
}
// }}}

// Pointer events {{{
function get_pos(event, c) {
	var extra = [0, 0];
	if (c === undefined) {
		c = canvas;
		extra = [pos[0] - c.width / 2, pos[1] - c.height / 2];
	}
	var rect = c.getBoundingClientRect();
	var x = event.clientX - rect.left + extra[0];
	var y = event.clientY - rect.top + extra[1];
	return [x, y];
}

function map_down(event) {
	if (enter()) {
		return;
	}
	moved = false;
	action_shift = event.shiftKey;
	action_ctrl = event.ctrlKey;
	ref_pos = get_pos(event);
	orig_pos = [pos[0], pos[1]];
	action = event.button;
}

function get_seq(name) {
	if (typeof(name) == 'string') {
		return info.seq[name];
	}
	return info.collections[name[0]][name[1]];
}

function get_selection_pos(warp) {
	var n = 0, x = 0, y = 0;
	for (var s = 0; s < selection.length; ++s) {
		if (warp) {
			if (game.world.sprite[selection[s]].warp === null)
				continue;
			n += 1;
			var mx = Math.trunc((game.world.sprite[selection[s]].warp[0] - 1) % 32);
			var my = Math.trunc((game.world.sprite[selection[s]].warp[0] - 1) / 32);
			x += game.world.sprite[selection[s]].warp[1] + mx * 600 - 20;
			y += game.world.sprite[selection[s]].warp[2] + my * 400;
		}
		else {
			n += 1;
			x += game.world.sprite[selection[s]].x;
			y += game.world.sprite[selection[s]].y;
		}
	}
	if (n == 0)
		return pos;
	x /= n;
	y /= n;
	return [x, y];
}

function map_up(event) {
	if (ref_pos === null) {
		return;
	}
	var p = get_pos(event);
	if (!moved) {
		if (action == 0) {
			// Left click: select sprite.
			sprite_selection = null;
			if (!action_ctrl)
				selection = [];
			for (var s in game.world.sprite) {
				var spr = game.world.sprite[s];
				if (typeof(spr) != 'object' || spr.layer != gui.active_layer.options[gui.active_layer.selectedIndex].value) {
					continue;
				}
				var seq = get_seq(spr.seq);
				if (!seq)
					continue;
				var frame = get_seq(spr.seq)[spr.frame];
				if (spr.x + frame.hardbox[0] > p[0] || spr.x + frame.hardbox[2] < p[0] || spr.y + frame.hardbox[1] > p[1] || spr.y + frame.hardbox[3] < p[1]) {
					continue;
				}
				if (sprite_selected(s)) {
					selection.splice(selection.indexOf(s), 1);
				}
				else {
					selection.push(s);
				}
			}
			update_ui();
			redraw_all(true);
		}
		else if (action == 1) {
			// Middle click: paste selection.
			var create_sprite = function(name, seq, frame, x, y) {
				var n;
				if (game.world.sprite[name] === undefined) {
					n = name;
				}
				else {
					var i, base;
					var r = name.match(/^(.*)-(\d+)$/);
					if (r === null) {
						base = name;
						i = 0;
					}
					else {
						base = r[1];
						i = Number(r[2]);
					}
					while (true) {
						var num = String(i);
						n = base + '-' + '000'.substr(0, 3 - num.length) + num;
						if (game.world.sprite[n] === undefined)
							break;
						i += 1;
					}
				}
				var spr = game.world.sprite[n] = {};
				spr.seq = seq;
				spr.frame = frame;
				spr.x = x;
				spr.y = y;
				spr.brain = 'none';
				spr.script = '';
				spr.use_hard = true;
				spr.vision = 0;
				spr.speed = 1;
				spr.timing = 33;
				spr.sound = '';
				spr.strength = 0;
				spr.defense = 0;
				spr.hitpoints = 0;
				spr.experience = 0;
				spr.touch_damage = 0;
				spr.gold = 0;
				spr.size = 100;
				spr.que = 0;
				spr.base_walk = '';
				spr.base_idle = '';
				spr.base_attack = '';
				spr.base_death = '';
				spr.nohit = false;
				spr.map = null;
				spr.warp = null;
				spr.touch_seq = '';
				spr.hard = true;
				spr.left = 0;
				spr.top = 0;
				spr.right = 0;
				spr.bottom = 0;
				spr.layer = gui.active_layer;
				selection.push(n);
				return spr;
			};
			if (selection.length > 0) {
				// Copy selected sprites.
				tpos = get_selection_pos();
				var list = selection;
				selection = [];
				sprite_selection = null;
				for (var s = 0; s < list.length; ++s) {
					var ss = game.world.sprite[list[s]];
					var tx = ss.x - tpos[0] + p[0];
					var ty = ss.y - tpos[1] + p[1];
					var spr = create_sprite(list[s], ss.seq, ss.frame, tx, ty);
					spr.brain = ss.brain;
					spr.script = ss.script;
					spr.use_hard = ss.use_hard;
					spr.vision = ss.vision;
					spr.speed = ss.speed;
					spr.timing = ss.timing;
					spr.sound = ss.sound;
					spr.strength = ss.strength;
					spr.defense = ss.defense;
					spr.hitpoints = ss.hitpoints;
					spr.experience = ss.experience;
					spr.touch_damage = ss.touch_damage;
					spr.gold = ss.gold;
					spr.size = ss.size;
					spr.que = ss.que;
					spr.base_walk = ss.base_walk;
					spr.base_idle = ss.base_idle;
					spr.base_attack = ss.base_attack;
					spr.base_death = ss.base_death;
					spr.nohit = ss.nohit;
					spr.map = null;
					spr.warp = ss.warp;
					spr.touch_seq = ss.touch_seq;
					spr.hard = ss.hard;
					spr.left = ss.left;
					spr.top = ss.top;
					spr.right = ss.right;
					spr.bottom = ss.bottom;
					spr.layer = ss.layer;
				}
			}
			else if (sprite_selection !== null) {
				// Create new sprite.
				selection = [];
				create_sprite(sprite_selection, sprite_selection, current_frame, p[0], p[1]);
				sprite_selection = null;
			}
			update_ui();
			redraw_all(true);
		}
	}
	ref_pos = null;
	orig_pos = null;
	action = null;
}

// geom: [tilesize, width, height, offset_x, offset_y];
function seq_down(event) {
	var w = gui.seq_canvas.width;
	var h = gui.seq_canvas.height;
	var geom = get_geom(w, h, seqnames.length);
	var p = get_pos(event, gui.seq_canvas);
	var num = Math.trunc((p[1] - geom[4]) / geom[0] + .5) * geom[1] + Math.trunc((p[0] - geom[3]) / geom[0] + .5);
	if (num < 0 || num > seqnames.length) {
		sprite_selection = null;
	}
	else {
		sprite_selection = seqnames[num];
	}
	redraw_all();
}

function collection_down(event) {
	var w = gui.collection_canvas.width;
	var h = gui.collection_canvas.height;
	var geom = get_geom(w, h, collectionnames.length);
	var p = get_pos(event, gui.collection_canvas);
	var num = Math.trunc((p[1] - geom[4]) / geom[0] + .5) * geom[1] + Math.trunc((p[0] - geom[3]) / geom[0] + .5);
	if (num < 0 || num > collectionnames.length) {
		sprite_selection = null;
	}
	else {
		sprite_selection = [collectionnames[num], find_collection_dir(info.collections[collectionnames[num]])];
	}
	redraw_all();
}



function map_move(event) {
	if (ref_pos === null) {
		return;
	}
	if (isNaN(ref_pos[1])) {
		ref_pos = get_pos(event);
		return;
	}
	if (event.buttons == 4 && action == 1) {
		moved = true;
		pos = orig_pos;	// Use original position for get_pos.
		var p = get_pos(event);
		pos = [orig_pos[0] - p[0] + ref_pos[0], orig_pos[1] - p[1] + ref_pos[1]];
		redraw_all();
	}
	var p = get_pos(event);
	if (action == 'que') {
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].que = orig_pos[s] - p[1] + ref_pos[1];
		}
		update_ui();
		redraw_all(true);
	}
	else if (action == 'move') {
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].x = orig_pos[s][0] + p[0] - ref_pos[0];
			game.world.sprite[selection[s]].y = orig_pos[s][1] + p[1] - ref_pos[1];
		}
		update_ui();
		redraw_all(true);
	}
	else if (action == 'warpmove') {
		for (var s = 0; s < selection.length; ++s) {
			if (game.world.sprite[selection[s]].warp === null)
				continue;
			var tx = orig_pos[s][0] + p[0] - ref_pos[0];
			var ty = orig_pos[s][1] + p[1] - ref_pos[1];
			var mx = Math.floor(tx / 600);
			var my = Math.floor(ty / 400);
			var map = my * 32 + mx + 1;
			game.world.sprite[selection[s]].warp = [map, tx - mx * 600 + 20, ty - my * 400];
		}
		update_ui();
		redraw_all(true);
	}
}
// }}}

// Key events. {{{
function map_insert() {
	var x = Math.floor(pos[0] / 600);
	var y = Math.floor(pos[1] / 400);
	var n = mapnr(x, y);
	if (game.world[n]) {
		return;
	}
	var t = [];
	for (var ty = 0; ty < 8; ++ty) {
		var r = [];
		for (var tx = 0; tx < 12; ++tx) {
			r.push([1, 0, 0]);
		}
		t.push(r);
	}
	game.world[n] = { tiles: t, indoor: false, hard: '', music: '', script: '' };
	if ([x, y] in canvascache) {
		map[y][x] = null;
		delete canvascache[[x, y]];
	}
	update_maps();
	redraw_all();
}

function map_delete() {
	var x = Math.floor(pos[0] / 600);
	var y = Math.floor(pos[1] / 400);
	var n = mapnr(x, y);
	if (!game.world[n]) {
		return;
	}
	delete game.world[n];
	if ([x, y] in canvascache) {
		map[y][x] = null;
		delete canvascache[[x, y]];
	}
	update_maps();
	redraw_all();
}

function sprite_delete() {
	while (selection.length > 0) {
		s = selection.pop();
		delete game.world.sprite[s];
	}
	update_ui();
	redraw_all(true);
}

function set_layer(l, c) {
	if (c) {
		// Move selection to new layer and switch to that layer.
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].layer = l;
		}
	}
	else {
		selection = [];
	}
	gui.active_layer.selectedIndex = (l + 9) % 10;
	redraw_all(true);
}

function cancel() {
	if (ref_pos === null)
		return;
	if (action == 'que') {
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].que = orig_pos[s];
		}
	}
	else if (action == 'move') {
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].x = orig_pos[s][0];
			game.world.sprite[selection[s]].y = orig_pos[s][1];
		}
	}
	else if (action == 'warpmove') {
		for (var s = 0; s < selection.length; ++s) {
			if (game.world.sprite[selection[s]].warp === null)
				continue;
			var tx = orig_pos[s][0];
			var ty = orig_pos[s][1];
			var mx = Math.floor(tx / 600);
			var my = Math.floor(ty / 400);
			var map = my * 32 + mx + 1;
			game.world.sprite[selection[s]].warp = [map, tx - mx * 600 + 20, ty - my * 400];
		}
	}
	ref_pos = null;
	orig_pos = null;
	action = null;
	update_ui();
	redraw_all(true);
}

function enter() {
	if (ref_pos !== null) {
		ref_pos = null;
		orig_pos = null;
		action = null;
		redraw_all(true);
		return true;
	}
	return false;
}

function que() {
	orig_pos = [];
	for (var s = 0; s < selection.length; ++s) {
		orig_pos.push(game.world.sprite[selection[s]].que);
	}
	ref_pos = [NaN, NaN];
	action = 'que';
	redraw_all(true);
}

function move() {
	orig_pos = [];
	for (var s = 0; s < selection.length; ++s) {
		orig_pos.push([game.world.sprite[selection[s]].x, game.world.sprite[selection[s]].y]);
	}
	ref_pos = [NaN, NaN];
	action = 'move';
}

function warpmove() {
	orig_pos = [];
	for (var s = 0; s < selection.length; ++s) {
		var spr = game.world.sprite[selection[s]];
		if (spr.warp === null) {
			orig_pos.push(null);
			continue;
		}
		var mx = Math.floor((spr.warp[0] - 1) % 32);
		var my = Math.floor((spr.warp[0] - 1) / 32);
		var tx = mx * 600 + spr.warp[1] - 20;
		var ty = my * 400 + spr.warp[2];
		orig_pos.push([tx, ty]);
	}
	ref_pos = [NaN, NaN];
	action = 'warpmove';
}

function jump() {
	pos = get_selection_pos();
	redraw_all(true);
}

function jump_warp() {
	pos = get_selection_pos(true);
	redraw_all(true);
}

var chars = {
	48: function(s, c, a) { set_layer(0, c); },
	49: function(s, c, a) { set_layer(1, c); },
	50: function(s, c, a) { set_layer(2, c); },
	51: function(s, c, a) { set_layer(3, c); },
	52: function(s, c, a) { set_layer(4, c); },
	53: function(s, c, a) { set_layer(5, c); },
	54: function(s, c, a) { set_layer(6, c); },
	55: function(s, c, a) { set_layer(7, c); },
	56: function(s, c, a) { set_layer(8, c); },
	57: function(s, c, a) { set_layer(9, c); },
	109: function(s, c, a) { move(); },
	116: function(s, c, a) { warpmove(); },
	113: function(s, c, a) { que(); },
	106: function(s, c, a) { jump(); },
	119: function(s, c, a) { jump_warp(); }
};

var keys = {
	45: function(s, c, a) { if (c) map_insert(); else select_new_seq(); },
	46: function(s, c, a) { if (c) map_delete(); else sprite_delete(); },
	35: function(s, c, a) { select_new_collection(1); },
	40: function(s, c, a) { select_new_collection(2); },
	34: function(s, c, a) { select_new_collection(3); },
	37: function(s, c, a) { select_new_collection(4); },
	12: function(s, c, a) { select_new_collection('die'); },
	39: function(s, c, a) { select_new_collection(6); },
	36: function(s, c, a) { select_new_collection(7); },
	38: function(s, c, a) { select_new_collection(8); },
	33: function(s, c, a) { select_new_collection(9); },
	13: function(s, c, a) { enter(); },
	27: function(s, c, a) { cancel(); }
};

function map_keypress(event) {
	console.info([event.charCode, event.keyCode]);
	if (event.charCode >= 65 && event.charCode <= 90) {
		if (game.locations[event.charCode + 0x20] === undefined)
			return;
		if (event.altKey) {
			// Remove stored location.
			event.preventDefault();
			delete game.locations[event.charCode + 0x20];
		}
		else {
			// Goto stored location.
			event.preventDefault();
			pos = game.locations[event.charCode + 0x20];
			redraw_all();
		}
		return;
	}
	if (event.altKey && event.charCode >= 97 && event.charCode <= 122) {
		// Store location.
		game.locations[event.charCode] = pos;
		event.preventDefault();
		return;
	}
	if (chars[event.charCode]) {
		chars[event.charCode](event.shiftKey, event.ctrlKey, event.altKey);
	}
	else if (keys[event.keyCode]) {
		keys[event.keyCode](event.shiftKey, event.ctrlKey, event.altKey);
	}
}

function seq_keypress(event) {
	//console.info(['seq', event.charCode, event.keyCode]);
	if (event.keyCode == 27) {
		gui.redraw_impl = redraw_map;
		redraw_all();
		canvas.focus();
	}
	else if (event.charCode == 48) {
		current_frame = 1;
		redraw_all();
	}
	else if (event.charCode == 45) {
		current_frame -= 1;
		redraw_all();
	}
	else if (event.charCode == 61) {
		current_frame += 1;
		redraw_all();
	}
	else if (event.charCode == 115) {
		// New seq and frame.
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection;
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].seq = target;
			game.world.sprite[selection[s]].frame = current_frame <= 0 || current_frame >= info.sequences[target].length ? 0 : current_frame;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all();
		canvas.focus();
	}
	else if (event.charCode == 116) {
		// Touch
		var target;
		if (sprite_selection === null || typeof sprite_selection != 'string') {
			target = null;
		}
		else {
			target = sprite_selection;
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].touch_seq = target;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
}

function collection_keypress(event) {
	//console.info(['collection', event.charCode, event.keyCode]);
	if (event.keyCode == 27) {
		gui.redraw_impl = redraw_map;
		redraw_all(true);
		canvas.focus();
	}
	else if (event.charCode == 48) {
		current_frame = 1;
		redraw_all();
	}
	else if (event.charCode == 45) {
		current_frame -= 1;
		redraw_all();
	}
	else if (event.charCode == 61) {
		current_frame += 1;
		redraw_all();
	}
	else if (event.charCode == 105) {
		// Idle
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection[0];
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].base_idle = target;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
	else if (event.charCode == 119) {
		// Walk
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection[0];
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].base_walk = target;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
	else if (event.charCode == 97) {
		// Attack
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection[0];
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].base_attack = target;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
	else if (event.charCode == 100) {
		// Death
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection[0];
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].base_death = target;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
	else if (event.charCode == 115) {
		// Touch
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection;
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].seq = target;
			if (target !== null) {
				game.world.sprite[selection[s]].frame = current_frame <= 0 || current_frame >= info.collections[target[0]][target[1]].length ? 0 : current_frame;
			}
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
	else if (event.charCode == 116) {
		// Touch
		var target;
		if (sprite_selection === null || typeof sprite_selection == 'string') {
			target = null;
		}
		else {
			target = sprite_selection;
		}
		for (var s = 0; s < selection.length; ++s) {
			game.world.sprite[selection[s]].touch_seq = target;
		}
		gui.redraw_impl = redraw_map;
		update_ui();
		redraw_all(true);
		canvas.focus();
	}
}
// }}}

// Maps. {{{
function update_maps() {
	gui.map_current.ClearAll();
	for (var y = 0; y < 24; ++y) {
		for (var x = 0; x < 32; ++x) {
			var n = mapnr(x, y);
			if (game.world[n]) {
				var opt = gui.map_current.AddElement('option').AddText(x + ',' + y);
				opt.value = n;
				if (n == current_map)
					gui.map_current.selectedIndex = opt.index;
			}
		}
	}
}

function update_map_gui() {
	var m = game.world[current_map];
	if (m) {
		//gui.map_hard.selectedIndex = ...
		gui.map_script.value = m.script;
		//gui.map_music.selectedIndex = ...
		gui.map_indoor.checked = m.indoor;
	}
	else {
		gui.map_hard.selectedIndex = 0;
		gui.map_script.value = '';
		gui.map_music.selectedIndex = 0;
		gui.map_indoor.checked = false;
	}
	update_maps();
}

function maps_init() {
	gui.redraw_impl = redraw_map;
	gui.map_current = document.getElementById('map_current');
	gui.map_hard = document.getElementById('map_hard');
	gui.map_script = document.getElementById('map_script');
	gui.map_music = document.getElementById('map_music');
	gui.map_indoor = document.getElementById('map_indoor');
	update_maps();
	for (var y = 0; y < 24; ++y) {
		var m = [];
		var s = [];
		for (var x = 0; x < 32; ++x) {
			s.push(null);
			m.push(null);
		}
		map.push(m);
	}
	gui.map_music.AddElement('option').AddText('-').value = '';
	for (var m = 0; m < info.music.length; ++m) {
		gui.map_music.AddElement('option').AddText(music[info.music[m][0]] ? info.music[m][0] : '[' + info.music[m][0] + ']').value = info.music[m][0];
	}
}

function sprite_sound_play() {
	if (current_audio !== null) {
		current_audio.pause();
		current_audio = null;
	}
	var s = gui.sprite_sound.options[gui.sprite_sound.selectedIndex].value;
	if (!s || !sound[s])
		return;
	current_audio = sound[s];
	sound[s].play();
}

function map_music_play() {
	if (current_audio !== null) {
		current_audio.pause();
		current_audio = null;
	}
	var m = gui.map_music.options[gui.map_music.selectedIndex].value;
	if (!m || !music[m])
		return;
	current_audio = music[m];
	music[m].play();
}

function mapnr(x, y) {
	return y * 32 + x + 1;
}

function sprite_init() {
	gui.single = document.getElementById('single');
	gui.sprite_select = document.getElementById('spritelist');
	gui.sprite_name = document.getElementById('sprite_name');
	gui.sprite_brain = document.getElementById('sprite_brain');
	gui.sprite_script = document.getElementById('sprite_script');
	gui.sprite_use_hard = document.getElementById('sprite_use_hard');
	gui.sprite_vision = document.getElementById('sprite_vision');
	gui.sprite_speed = document.getElementById('sprite_speed');
	gui.sprite_timing = document.getElementById('sprite_timing');
	gui.sprite_sound = document.getElementById('sprite_sound');
	gui.sprite_strength = document.getElementById('sprite_strength');
	gui.sprite_defense = document.getElementById('sprite_defense');
	gui.sprite_hp = document.getElementById('sprite_hp');
	gui.sprite_exp = document.getElementById('sprite_exp');
	gui.sprite_touch = document.getElementById('sprite_touch');
	gui.sprite_gold = document.getElementById('sprite_gold');

	gui.sprite_layer = document.getElementById('sprite_layer');
	gui.sprite_x = document.getElementById('sprite_x');
	gui.sprite_y = document.getElementById('sprite_y');
	gui.sprite_seq = document.getElementById('sprite_seq');
	gui.sprite_frame = document.getElementById('sprite_frame');
	gui.sprite_size = document.getElementById('sprite_size');
	gui.sprite_que = document.getElementById('sprite_que');
	gui.sprite_walk = document.getElementById('sprite_walk');
	gui.sprite_idle = document.getElementById('sprite_idle');
	gui.sprite_attack = document.getElementById('sprite_attack');
	gui.sprite_die = document.getElementById('sprite_die');
	gui.sprite_nohit = document.getElementById('sprite_nohit');
	gui.sprite_map = document.getElementById('sprite_map');

	gui.sprite_warp = document.getElementById('sprite_warp');
	gui.sprite_warp_map = document.getElementById('sprite_warp_map');
	gui.sprite_warp_x = document.getElementById('sprite_warp_x');
	gui.sprite_warp_y = document.getElementById('sprite_warp_y');
	gui.sprite_touch_seq = document.getElementById('sprite_touch_seq');
	gui.sprite_hard = document.getElementById('sprite_hard');
	gui.sprite_left = document.getElementById('sprite_left');
	gui.sprite_top = document.getElementById('sprite_top');
	gui.sprite_right = document.getElementById('sprite_right');
	gui.sprite_bottom = document.getElementById('sprite_bottom');

	gui.sprite_sound.AddElement('option').AddText('-').value = '';
	for (var s = 0; s < info.sound.length; ++s) {
		gui.sprite_sound.AddElement('option').AddText(info.sound[s][0]).value = info.sound[s][0];
	}
}

function sprite_selected(name) {
	return selection.indexOf(name) >= 0;
}

function redraw_one_map(x, y) {
	var c = Create('canvas');
	c.width = 600;
	c.height = 400;
	var ctx = c.getContext('2d');
	if (!game.world[mapnr(x, y)]) {
		ctx.fillStyle = '#848';
		ctx.fillRect(0, 0, 600, 400);
	}
	else {
		// Tiles.
		for (var ty = 0; ty < 8; ++ty) {
			for (var tx = 0; tx < 12; ++tx) {
				t = game.world[mapnr(x, y)].tiles[ty][tx];
				ctx.drawImage(tilemaps[t[0]][0], 50 * t[1], 50 * t[2], 50, 50, tx * 50, ty * 50, 50, 50);
			}
		}
	}
	// Prepare sprites.
	var bg = [];
	var fg = [];
	var warp = [];
	var wsize = 20, wr = 15;
	for (var s in game.world.sprite) {
		var spr = game.world.sprite[s];
		if (typeof(spr) != 'object') {
			continue;
		}
		if (gui.layer[spr.layer][0].selectedIndex > 2) {
			continue;
		}
		var seq;
		var img;
		if (typeof(spr.seq) == 'string') {
			seq = info.seq[spr.seq];
			img = sequences[spr.seq];
		}
		else {
			seq = info.collections[spr.seq[0]][spr.seq[1]];
			img = collections[spr.seq[0]][spr.seq[1]];
		}
		if (seq === undefined)
			continue;
		var frame = seq[spr.frame];
		if (spr.warp !== null) {
			var wx = Math.floor((spr.warp[0] - 1) % 32) * 600 + spr.warp[1] - 20 - x * 600;
			var wy = Math.floor((spr.warp[0] - 1) / 32) * 400 + spr.warp[2] - y * 400;
			if (wx - wsize < 600 && wx + wsize >= 0 && wy - wsize < 400 && wy + wsize >= 0) {
				warp.push([wx, wy, sprite_selected(s)]);
			}
		}
		if (spr.x + frame.bbox[0] >= (x + 1) * 600 || spr.x + frame.bbox[2] < x * 600 || spr.y + frame.bbox[1] >= (y + 1) * 400 || spr.y + frame.bbox[3] < y * 400) {
			continue;
		}
		// this is get_box from the original pde.py.
		var args;
		var w = frame.bbox[2] - frame.bbox[0];
		var h = frame.bbox[3] - frame.bbox[1];
		var x_compat = Math.trunc(Math.trunc(w * (spr.size - 100) / 100) / 2);
		var y_compat = Math.trunc(Math.trunc(h * (spr.size - 100) / 100) / 2);
		var l = spr.x - x * 600 + frame.bbox[0] - x_compat;
		var t = spr.y - y * 400 + frame.bbox[1] - y_compat;
		var r = l + w * spr.size / 100;
		var b = t + h * spr.size / 100;
		if (spr.left || spr.top || spr.right || spr.bottom) {
			var box = [];
			box[0] = spr.left > w ? w : spr.left;
			box[1] = spr.top > h ? h : spr.top;
			box[2] = spr.right > w ? w : spr.right;
			box[3] = spr.bottom > h ? h : spr.bottom;
			l += box[0];
			t += box[1];
			r += box[2] - w;
			b += box[3] - h;
			args = [img[spr.frame][0], box[0], box[1], box[2] - box[0], box[3] - box[1], l, t, r - l, b - t];
		}
		else {
			args = [img[spr.frame][0], 0, 0, w, h, l, t, r - l, b - t];
		}
		var alpha;
		switch (gui.layer[spr.layer][0].selectedIndex) {
		case 0:
			alpha = 1;
			break;
		case 1:
			alpha = .5;
			break;
		default:
			alpha = 0;
			break;
		}
		var selected = sprite_selected(s);
		if (game.layer[1][spr.layer])
			bg.push([spr.y - spr.que, args, alpha, spr, frame, selected]);
		else
			fg.push([spr.y - spr.que, args, alpha, spr, frame, selected]);
	}
	var cmp = function(a, b) {
		return a[0] - b[0];
	};
	bg.sort(cmp);
	fg.sort(cmp);
	// Background.
	for (var i = 0; i < bg.length; ++i) {
		if (bg[i][2]) {
			ctx.save();
			ctx.globalAlpha = bg[i][2];
			try {
				ctx.drawImage(bg[i][1][0], bg[i][1][1], bg[i][1][2], bg[i][1][3], bg[i][1][4], bg[i][1][5], bg[i][1][6], bg[i][1][7], bg[i][1][8]);
			}
			catch (e) {
				console.info('Failed to draw bg image');
			}
			ctx.restore();
		}
	}
	// Foreground.
	for (var i = 0; i < fg.length; ++i) {
		if (fg[i][2]) {
			ctx.save();
			ctx.globalAlpha = fg[i][2];
			try {
				ctx.drawImage(fg[i][1][0], fg[i][1][1], fg[i][1][2], fg[i][1][3], fg[i][1][4], fg[i][1][5], fg[i][1][6], fg[i][1][7], fg[i][1][8]);
			}
			catch (e) {
				console.info('Failed to draw image');
			}
			ctx.restore();
		}
	}
	// TODO: Tile hardness.
	// Sprite hardness.
	// Sprite que.
	// Sprite centers.
	var draw_sprite = function(spr, frame, selected) {
		ctx.save();
		ctx.lineWidth = 2;
		ctx.globalAlpha = .5;
		// Hardbox.
		if (spr.hard) {
			ctx.strokeStyle = spr.warp !== null ? '#f88' : '#fff';
			ctx.strokeRect(spr.x - x * 600 + frame.hardbox[0], spr.y - y * 400 + frame.hardbox[1], frame.hardbox[2] - frame.hardbox[0], frame.hardbox[3] - frame.hardbox[1]);
		}
		if (spr.layer == gui.active_layer.options[gui.active_layer.selectedIndex].value) {
			// Que.
			if (action == 'que') {
				ctx.strokeStyle = '#00f';
				ctx.beginPath();
				ctx.moveTo(spr.x - x * 600 - 35, spr.y - y * 400 - spr.que);
				ctx.lineTo(spr.x - x * 600 + 35, spr.y - y * 400 - spr.que);
				ctx.stroke();
			}
			// Position.
			ctx.strokeStyle = '#fff';
			var size = selected ? 20 : 10;
			ctx.beginPath();
			ctx.moveTo(spr.x - x * 600 - size, spr.y - y * 400);
			ctx.lineTo(spr.x - x * 600 + size, spr.y - y * 400);
			ctx.moveTo(spr.x - x * 600, spr.y - y * 400 - size);
			ctx.lineTo(spr.x - x * 600, spr.y - y * 400 + size);
			if (selected) {
				ctx.save();
				ctx.strokeStyle = '#fff';
				ctx.lineWidth = 8;
				ctx.stroke();
				ctx.restore();
				ctx.strokeStyle = '#f00';
			}
			ctx.stroke();
		}
		ctx.restore();
	};
	for (var i = 0; i < bg.length; ++i) {
		draw_sprite(bg[i][3], bg[i][4], bg[i][5]);
	}
	for (var i = 0; i < fg.length; ++i) {
		draw_sprite(fg[i][3], fg[i][4], fg[i][5]);
	}
	// Sprite warp targets.
	ctx.save();
	ctx.lineWidth = 2;
	ctx.globalAlpha = 1;
	for (var w = 0; w < warp.length; ++w) {
		ctx.beginPath();
		ctx.moveTo(warp[w][0] - wsize, warp[w][1]);
		ctx.lineTo(warp[w][0] + wsize, warp[w][1]);
		ctx.moveTo(warp[w][0], warp[w][1] - wsize);
		ctx.lineTo(warp[w][0], warp[w][1] + wsize);
		ctx.moveTo(warp[w][0] + wr, warp[w][1]);
		ctx.arc(warp[w][0], warp[w][1], wr, 0, 2 * Math.PI, false);
		ctx.strokeStyle = warp[w][2] ? '#f00' : '#fff';
		ctx.stroke();
	}
	ctx.restore();
	ctx.fillStyle = '#fff';
	ctx.fillText(String(y * 32 + x + 1) + ' (' + x + ',' + y + ')', 300, 200);
	return [c, ctx];
}

function redraw_map(flush) {
	gui.settings.RemoveClass('invisible');
	canvas.AddClass('visible');
	gui.tiles_canvas.RemoveClass('visible');
	gui.world_canvas.RemoveClass('visible');
	gui.seq_canvas.RemoveClass('visible');
	gui.collection_canvas.RemoveClass('visible');
	var newcache = {};
	canvas.width = canvasdiv.clientWidth;
	canvas.height = canvasdiv.clientHeight;
	var ul = [Math.floor((pos[0] - canvas.width / 2) / 600), Math.floor((pos[1] - canvas.height / 2) / 400)];
	for (var y = ul[1]; y < ul[1] + canvas.height / 400 + 1; ++y) {
		if (y < 0 || y >= 32)
			continue;
		for (var x = ul[0]; x < ul[0] + canvas.width / 600 + 1; ++x) {
			if (x < 0 || x >= 32)
				continue;
			if (!flush && map[y] && map[y][x]) {
				newcache[[x, y]] = canvascache[[x, y]];
				delete canvascache[[x, y]];
			}
			else {
				newcache[[x, y]] = [x, y, redraw_one_map(x, y)];
				map[y][x] = newcache[[x, y]][2];
			}
			context.drawImage(map[y][x][0], x * 600 + canvas.width / 2 - pos[0], y * 400 + canvas.height / 2 - pos[1]);
		}
	}
	var x = Math.floor(pos[0] / 600);
	var y = Math.floor(pos[1] / 400);
	var n = mapnr(x, y);
	if (n != current_map) {
		current_map = n;
		update_map_gui();
	}
	if (game.world[n] === undefined || !game.world[n].indoor)
		context.strokeStyle = '#f44';
	else
		context.strokeStyle = '#ff4';
	context.lineWidth = 4;
	context.strokeRect(x * 600 + canvas.width / 2 - pos[0] - 2, y * 400 + canvas.height / 2 - pos[1] - 2, 604, 404);
	for (var i in canvascache) {
		if (typeof(i) != 'object' || i.length != 3)
			continue;
		delete map[i[1]][i[0]];
		map[i[1]][i[0]] = null;
	}
	canvascache = newcache;
}
// }}}

// Sequences and collections. {{{
function get_geom(w, h, len) {
	var tilesize = Math.floor(Math.sqrt(w * h / len));
	while (true) {
		var width = Math.floor(w / tilesize);
		if (width > 0) {
			var ns = Math.floor((len + width - 1) / width);
			if (ns * tilesize <= h) {
				break;
			}
		}
		tilesize -= 1;
	}
	return [tilesize, width, ns, (w - tilesize * width) / 2 + tilesize / 2, (h - tilesize * ns) / 2 + tilesize / 2];
}

function draw_frame(ctx, index, geom, img, seq) {
		var x = Math.floor(index % geom[1]);
		var y = Math.floor(index / geom[1]);
		var size = [seq.bbox[2] - seq.bbox[0], seq.bbox[3] - seq.bbox[1]];
		var scale = geom[0] / (size[0] < size[1] ? size[1] : size[0]);
		ctx.drawImage(img, 0, 0, size[0], size[1], geom[3] + geom[0] * x - size[0] * scale / 2, geom[4] + geom[0] * y - size[1] * scale / 2, size[0] * scale, size[1] * scale);
}

function redraw_seqs() {
	gui.settings.AddClass('invisible');
	canvas.RemoveClass('visible');
	gui.tiles_canvas.RemoveClass('visible');
	gui.world_canvas.RemoveClass('visible');
	gui.collection_canvas.RemoveClass('visible');
	gui.seq_canvas.AddClass('visible');
	gui.seq_canvas.focus();
	gui.redraw_impl = redraw_seqs;
	var w = gui.seq_canvas.width = canvasdiv.clientWidth;
	var h = gui.seq_canvas.height = canvasdiv.clientHeight;
	var geom = get_geom(w, h, seqnames.length);
	for (var s = 0; s < seqnames.length; ++s) {
		var seq = info.seq[seqnames[s]][current_frame];
		if (!seq || seq.source) {	// TODO: handle seqs with source.
			continue;
		}
		draw_frame(gui.seq_ctx, s, geom, sequences[seqnames[s]][current_frame][0], seq);
	}
	if (typeof sprite_selection == 'string') {
		var n = seqnames.indexOf(sprite_selection);
		var x = Math.trunc(n % geom[1]);
		var y = Math.trunc(n / geom[1]);
		gui.seq_ctx.strokeStyle = '#f00';
		gui.seq_ctx.strokeRect(geom[3] + (x - .5) * geom[0], geom[4] + (y - .5) * geom[0], geom[0], geom[0]);
	}
}

function find_collection_dir(collection) {
	var convert = {
		1: [1, 9, 3, 7, 2, 4, 6, 8],
		2: [2, 8, 1, 3, 4, 6, 7, 9],
		3: [3, 7, 1, 9, 2, 4, 6, 8],
		4: [4, 6, 1, 7, 2, 8, 3, 9],
		'die': ['die'],
		6: [6, 4, 3, 9, 2, 8, 1, 7],
		7: [7, 3, 9, 1, 2, 4, 6, 8],
		8: [8, 2, 7, 9, 4, 6, 1, 3],
		9: [9, 1, 7, 3, 2, 4, 6, 8]
	}[gui.current_collection_dir];
	for (var dir = 0; dir < convert.length; ++dir) {
		if (collection[convert[dir]]) {
			return convert[dir];
		}
	}
	return null;
}

function redraw_collections() {
	gui.settings.AddClass('invisible');
	canvas.RemoveClass('visible');
	gui.tiles_canvas.RemoveClass('visible');
	gui.world_canvas.RemoveClass('visible');
	gui.seq_canvas.RemoveClass('visible');
	gui.collection_canvas.AddClass('visible');
	gui.collection_canvas.focus();
	gui.redraw_impl = redraw_collections;
	var w = gui.collection_canvas.width = canvasdiv.clientWidth;
	var h = gui.collection_canvas.height = canvasdiv.clientHeight;
	var geom = get_geom(w, h, collectionnames.length);
	for (var c = 0; c < collectionnames.length; ++c) {
		var collection = info.collections[collectionnames[c]];
		var dir = find_collection_dir(collection);
		if (dir === null) {
			continue;
		}
		var seq = collection[dir][current_frame];
		if (!seq || seq.source) {	// TODO: handle seqs with source.
			continue;
		}
		draw_frame(gui.collection_ctx, c, geom, collections[collectionnames[c]][dir][current_frame][0], seq);
	}
	if (sprite_selection !== null && typeof sprite_selection != 'string') {
		n = collectionnames.indexOf(sprite_selection[0]);
		var x = Math.trunc(n % geom[1]);
		var y = Math.trunc(n / geom[1]);
		gui.collection_ctx.strokeStyle = '#f00';
		gui.collection_ctx.strokeRect(geom[3] + (x - .5) * geom[0], geom[4] + (y - .5) * geom[0], geom[0], geom[0]);
	}
}

function select_new_seq() {
	redraw_seqs();
}

function select_new_collection(dir) {
	gui.current_collection_dir = dir;
	redraw_collections();
}
// }}}
