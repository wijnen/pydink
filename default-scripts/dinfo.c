void die ()
{
	int r;
	freeze (1);
	sp_base_idle (1, "");
	sp_brain (1, "none");
	sp_seq (1, "die");
	sp_frame (1, 1);
	sp_nohit (1, 1);
	wait (3000);
	while (1)
	{
		r = choice ("Load", "Restart", "Quit");
		if (r == 1)
			escape.load ();
		else if (r == 2)
			restart_game ();
		else if (r == 3)
			kill_game ();
	}
}
