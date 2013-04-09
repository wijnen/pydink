void main ()
{
	int c = choice_stop ("Continue", game_exist (-1), "Retry", "Back to title", "Quit game");
	if (c == 1)
		return;
	if (c == 2)
		load_game (-1);
	if (c != 3)
		kill_game ();
	restart_game ();
}
