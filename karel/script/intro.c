extern int debug;

void main ()
{
	if (debug)
	{
		player_map = 400;
		sp_x (1, 320);
		sp_y (1, 200);
		kill_this_task ();
	}
	script_attach (1000);
	player_map = 1;
	dink_can_walk_off_screen (1);
	sp_x (1, 320);
	sp_y (1, 500);
	load_screen ();
	draw_screen ();
	wait (1);
	int daniel = sp ("daniel-intro");
	int knight = create_sprite (320, 500, "none", "silverknight 7", 1);
	sp_base_walk (knight, "silverknight");
	freeze (1);
	sp_speed (knight, 3);
	freeze (knight);
	move_stop (knight, 8, 270, 1);
	say_stop ("`7Sire! Listen!", knight);
	say_stop ("`3What is it, John?", daniel);
	say_stop ("`7The maid in the bar says Dink has been rude to her!", knight);
	say_stop ("`3What?! That's outrageous!", daniel);
	say_stop ("`3Fetch him for me!", daniel);
	say_stop ("`7At once, sire!", knight);
	move_stop (knight, 2, 500, 1);
	sp_active (knight, 0);
	say_stop ("`3What would be a good punishment...", daniel);
	sp_x (1, 320);
	sp_y (1, 500);
	move_stop (1, 8, 270, 1);
	say_stop ("`3SMALLWOOD HAS RETURNED!", daniel);
	say_stop ("And his ears hurt...", 1);
	say_stop ("`3Dink! Your behaviour is intolerable!", daniel);
	say_stop ("`3You are banished from the kingdom!", daniel);
	say_stop ("Whatever you say, Danny. Bye!", 1);
	move_stop (1, 2, 500, 1);
	say_stop ("`3I hope that was a good idea...", daniel);
	fade_down_stop ();
	player_map = 400;
	load_screen ();
	draw_screen ();
	wait (1);
	bedink.main ();
	freeze (1);
	sp_x (1, 320);
	sp_y (1, -50);
	fade_up_stop ();
	move_stop (1, 2, 200, 1);
	say_stop ("Hmm, what to do now?", 1);
	say_stop ("I need money to buy food...", 1);
	say_stop ("Stealing is too evil for me...", 1);
	say_stop ("Unless... That's an idea!", 1);
	fade_down_stop ();
	say_stop_xy ("Dink decided to steal only from those who could spare it.", 10, 200);
	say_stop_xy ("When he wasn't 'working', he wore armour to hide himself.", 10, 200);
	say_stop_xy ("After a few years, he had become a very skilled thief.", 10, 200);
	say_stop_xy ("Then, one night...", 10, 200);
	beknight.main ();
	save_game (-1);
	kill_this_task ();
}
