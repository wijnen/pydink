extern int g_dink;
extern int g_daniel;
extern int g_adelbrecht;
extern int g_eggeric;
extern int g_machteld;

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
	freeze (1);
	load_game (-1);
	// This is reached if the game didn't exist.
	sp_brain (g_dink, "person");
	sp_base_idle (g_dink, "idle");
	sp_base_walk (g_dink, "walk");
	sp_timing (g_dink, 33);
	sp_speed (g_dink, 2);
	freeze (g_dink);
	move_stop (g_dink, 2, 400, 1);
	sp_dir (g_dink, 2);
	say_stop ("Continue?", g_dink);
	say_stop ("You haven't even started yet!", g_dink);
	say_stop ("Hmpf!", g_dink);
	move_stop (g_dink, 8, 350, 1);
	sp_y (g_dink, 350);
	sp_seq (g_dink, collection_code ("walk") + 3);
	sp_brain (g_dink, "repeat");
	sp_brain (1, "pointer");
	unfreeze (1);
}
