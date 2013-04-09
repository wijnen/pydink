extern int debug;
extern int g_daniel;
extern int g_adelbrecht;
extern int g_dink;
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
	if (debug)
	{
		strength += 10;
		defense += 10;
		lifemax += 40;
		life = lifemax;
	}
	else
	{
		freeze (1);
		sp_brain (g_machteld, "person");
		sp_base_walk (g_machteld, "bluemaiden");
		sp_timing (g_machteld, 33);
		sp_speed (g_machteld, 2);
		freeze (g_machteld);
		move_stop (g_machteld, 1, 470, 1);
		move_stop (g_machteld, 4, 320, 1);
		sp_dir (g_machteld, 2);
		sp_brain (g_adelbrecht, "person");
		sp_brain (g_dink, "person");
		sp_brain (g_eggeric, "person");
		sp_base_walk (g_adelbrecht, "soldier");
		sp_base_walk (g_dink, "walk");
		sp_base_walk (g_eggeric, "merchant");
		freeze (g_adelbrecht);
		freeze (g_dink);
		freeze (g_eggeric);
		sp_dir (g_adelbrecht, 3);
		sp_dir (g_dink, 2);
		sp_dir (g_eggeric, 1);
		say_stop ("`#Listen, please.", g_machteld);
		say_stop ("`#Before you begin, know this:", g_machteld);
		say_stop ("`#This dmod tells an ancient story.", g_machteld);
		say_stop ("`#It tries to follow it quite closely.", g_machteld);
		say_stop ("`#This means you don't have many choices.", g_machteld);
		say_stop ("`#Also, you need to read the text.", g_machteld);
		say_stop ("`#Otherwise it's no fun at all.", g_machteld);
		say_stop ("`#It's more like a movie than a game.", g_machteld);
		say_stop ("`#Understood?", g_machteld);
		int d = say ("`3Yes, Machteld.", g_daniel);
		int a = say ("`9Yes, Machteld.", g_adelbrecht);
		say_stop ("`0Yes, Machteld.", g_eggeric);
		sp_active (d, 0);
		sp_active (a, 0);
		say_stop ("`#Dink?", g_machteld);
		say_stop ("Yes, Machteld.", g_dink);
		say_stop ("`#Good. Let's start.", g_machteld);
		unfreeze (1);
	}
	start_game ();
	kill_this_task ();
}
