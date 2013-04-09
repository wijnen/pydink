void die ()
{
	freeze (1);
	update_status = 0;
	sp_nohit (1, 1);
	sp_base_idle (1, "");
	sp_brain (1, "none");
	if (count_item ("item-axe") == 0)
	{
		// Normal dink.
		sp_seq (1, "die");
		wait (3000);
	}
	else
	{
		// Knight.
		sp_seq (1, "");
		sp_pseq (1, "silverknight die");
		sp_pframe (1, 1);
		wait (1000);
	}
	int c = choice_stop (game_exist (-1), "Retry", "Back to title", "Quit game");
	if (c == 1)
		load_game (-1);
	if (c != 2)
		kill_game ();
	restart_game ();
}
