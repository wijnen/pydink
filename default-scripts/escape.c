void main ()
{
	int r;
	while (1)
	{
		choice_title ("What do you want to do?");
		r = choice_stop ("Continue", "Load", "Restart", "Quit");
		if (r <= 1)
			break;
		else if (r == 2)
			load ();
		else if (r == 3)
			restart_game ();
		else if (r == 4)
			kill_game ();
	}
	kill_this_task ();
}

void load ()
{
	choice_title ("Choose a game to load");
	int r = choice_stop ("&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"&savegameinfo;",
		"Never mind");
	if (r > 0 && r < 11)
		load_game (r);
}
