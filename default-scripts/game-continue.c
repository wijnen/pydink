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
