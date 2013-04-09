extern int debug;
extern int g_dink;
extern int g_daniel;
extern int g_adelbrecht;
extern int g_eggeric;
extern int g_machteld;

int star (int text, int x, int seq, int frame)
{
	int spr;
	if (frame != 0)
	{
		spr = create_sprite (x + 30, 350, "none", seq, frame);
	}
	else
	{
		spr = create_sprite (x + 30, 350, "repeat", seq, 1);
		sp_seq (spr, seq);
		sp_frame (spr, 1);
	}
	sp_noclip (spr, 1);
	sp_x (text, x - 280);
	sp_y (text, 380);
	sp_noclip (text, 1);
	sp_kill (text, 0);
	return spr;
}

int make_button (int x, int y, int seq)
{
	int spr = create_sprite (x, y, "button", seq, 1);
	sp_noclip (spr, 1);
	sp_touch_damage (spr, -1);
	return spr;
}

void build ()
{
	int s = say_xy ("`%Karel ende Elegast", 0, 130);
	sp_kill (s, 0);
	s = say_xy ("`%Starring", 0, 190);
	sp_kill (s, 0);
	g_daniel = star (say_xy ("`3Daniel", 0, 0), 100, seq_code ("food"), 31);
	g_adelbrecht = star (say_xy ("`9Adelbrecht", 0, 0), 200, collection_code ("soldier") + 3, 0);
	g_dink = star (say_xy ("Dink", 0, 0), 300, collection_code ("walk") + 3, 0);
	g_eggeric = star (say_xy ("`0Eggeric", 0, 0), 400, collection_code ("merchant") + 3, 0);
	g_machteld = star (say_xy ("`#Machteld", 0, 0), 500, collection_code ("bluemaiden") + 3, 0);
}

void main ()
{
	debug = 0;
	fill_screen (0);
	sp_script (make_button (76, 40, seq_code ("button-start")), "begin");
	sp_script (make_button (524, 40, seq_code ("button-continue")), "continue");
	sp_script (make_button (104, 440, seq_code ("button-ordering")), "ordering");
	sp_script (make_button (560, 440, seq_code ("button-quit")), "quit");
	sp_x (1, 320);
	sp_y (1, 200);
	build ();
	kill_this_task ();
}
