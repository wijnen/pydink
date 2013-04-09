extern int g_dink;
extern int g_daniel;
extern int g_adelbrecht;
extern int g_eggeric;
extern int g_machteld;

int main ()
{
	freeze (1);
	update_status = 0;
	sp_nodraw (1, 1);
	fill_screen (0);
	sp_noclip (create_sprite (76, 40, "none", "button-start", 1), 1);
	sp_noclip (create_sprite (524, 40, "none", "button-continue", 2), 1);
	sp_noclip (create_sprite (104, 440, "none", "button-ordering", 1), 1);
	sp_noclip (create_sprite (560, 440, "none", "button-quit", 1), 1);
	make_start.build ();
	say_stop ("I thought you won already?", g_daniel);
	say_stop ("I did!", g_dink);
	say_stop ("Am I dead already?", g_eggeric);
	say_stop ("I'm afraid so...", g_adelbrecht);
	say_stop ("That's not a bad thing at all!", g_machteld);
	say_stop ("Anyway, no point to continue, the story is over.", g_daniel);
	restart_game ();
}
