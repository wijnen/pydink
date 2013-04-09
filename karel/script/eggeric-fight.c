void main ()
{
	wait (1);
	sp_speed (current_sprite, 2);
	sp_timing (current_sprite, 33);
	sp_target (current_sprite, 1);
	sp_distance (current_sprite, 50);
	sp_range (current_sprite, 50);
}

void die ()
{
	script_attach (1000);
	freeze (1);
	int wife = sp ("wife-fight");
	say_stop ("Very well, that's done.", 1);
	say_stop ("`#Dink, my hero!", wife);
	say_stop ("Hey baby, are you single?", 1);
	say_stop ("`#No, I'm... Oh wait, yes I am!", wife);
	say_stop ("I thought so. (grin) And beautiful, too.", 1);
	say_stop ("`#Thanks. (blush)", wife);
	fade_down_stop ();
	bedink.main ();
	player_map = 1;
	sp_x (1, 320);
	sp_y (1, 500);
	load_screen ();
	draw_screen ();
	fade_up ();
	freeze (1);
	dink_can_walk_off_screen (1);
	move_stop (1, 8, 300, 1);
	int daniel = sp ("daniel-intro");
	say_stop ("`3SMALLWOOD HAS RETURNED!", daniel);
	say_stop ("(sigh)", 1);
	say_stop ("`3Sorry.", daniel);
	say_stop ("`3So you killed Eggeric?", daniel);
	say_stop ("Yeah, piece of cake.", 1);
	say_stop ("`3Oh, so then you don't need a reward, good.", daniel);
	say_stop ("Er, no, wait, it was really hard!", 1);
	say_stop ("`3Right...", daniel);
	say_stop ("`3So can you think of a reward that doesn't cost me anything?", daniel);
	say_stop ("Er, how about your sister?", 1);
	say_stop ("`3You want my sister? Sure, you can have her.", daniel);
	say_stop ("`3Now get out of here.", daniel);
	say_stop ("Sure thing. See you!", 1);
	move_stop (1, 2, 500, 1);
	fade_down_stop ();
	say_stop_xy ("So Dink married Daniel's sister.", 0, 200);
	say_stop_xy ("He made her much happier than Eggeric.", 0, 200);
	say_stop_xy ("And they lived happily ever after.", 0, 200);
	say_stop_xy ("Or at least until Dink's next adventure...", 0, 200);
	player_map = 69;
	save_game (-1);
	kill_game ();
}
