extern int herb;

void talk ()
{
	if (sp_brain (current_sprite) == brain_code ("monster"))
		return;
	freeze (1);
	freeze (current_sprite);
	int dx;
	int d;
	int up;
	int down;
	if (sp_x (current_sprite) < 320)
	{
		dx = 50;
		d = 4;
		up = 9;
		down = 3;
	}
	else
	{
		dx = -50;
		d = 6;
		up = 7;
		down = 1;
	}
	// Always move diagonally with the last argument 0.
	// This makes sure that the move will succeed (dink will slide off trees)
	// and he cannot end up inside hardness.
	if (sp_y (current_sprite) > 200)
		move_stop (1, up, sp_x (current_sprite) + dx, 0);
	else
		move_stop (1, down, sp_x (current_sprite) + dx, 0);
	sp_dir (1, d);
	say_stop ("Good night.", 1);
	say_stop ("`9...", current_sprite);
	say_stop ("I said good night!", 1);
	say_stop ("`9...", current_sprite);
	say_stop ("Say your name, stranger!", 1);
	say_stop ("`9...", current_sprite);
	say_stop ("Then I shall fight you!", 1);
	screenlock (1);
	sp_brain (current_sprite, "monster");
	sp_target (current_sprite, 1);
	sp_hitpoints (current_sprite, 200);
	sp_strength (current_sprite, 10);
	sp_touch_damage (current_sprite, 5);
	unfreeze (current_sprite);
	unfreeze (1);
	// Change music
}

void hit ()
{
	if (sp_brain (current_sprite) != brain_code ("monster"))
	{
		freeze (1);
		freeze (current_sprite);
		say_stop ("Oops, sorry about that!", 1);
		say_stop ("`9No problem, it didn't hurt.", current_sprite);
		unfreeze (current_sprite);
		unfreeze (1);
		return;
	}
	if (life > 2)
	{
		say ("`9Ha! You hit me, but I hit you, too!", current_sprite);
		hurt (1, 2);
	}
	else
	{
		sp_touch_damage (current_sprite, 0);
		freeze (1);
		freeze (current_sprite);
		int me = create_sprite (sp_x (1), sp_y (1), "none", "silverknight die", 1);
		dink_can_walk_off_screen (1);
		sp_y (1, 500);
		say_stop ("Stop! You win!", me);
		say_stop ("`9Tell me your name!", current_sprite);
		say_stop ("I am Dink Smallwood.", me);
		say_stop ("`9Dink? But you were banished!", current_sprite);
		say_stop ("You think I don't know that?", me);
		say_stop ("There's a reason I'm wearing this armour...", me);
		say_stop ("`9I see.", current_sprite);
		say_stop ("You have shown to be an extremely good fighter.", me);
		say_stop ("Perhaps even as good as King Daniel himself.", me);
		say_stop ("I am very anxious to know who you are.", me);
		say_stop ("Would you please tell me?", me);
		say_stop ("`9I am er... Adelbrecht.", current_sprite);
		say_stop ("`9I'm a great thief.", current_sprite);
		say_stop ("`9I steal from churches and poor people.", current_sprite);
		say_stop ("But that's evil! They don't have anything to spare!", me);
		say_stop ("`9Ha! I care not! It makes me rich!", current_sprite);
		say_stop ("Well then, Adelbrecht, if you will spare my life,", me);
		say_stop ("I would be honoured to be your partner tonight.", me);
		say_stop ("`9Dink, you have a great reputation.", current_sprite);
		say_stop ("`9I accept your proposal.", current_sprite);
		say_stop ("`9Shall we steal from king Daniel?", current_sprite);
		say_stop ("No, the king is a good man.", me);
		say_stop ("I shall not steal from him.", me);
		say_stop ("`9You are loyal even after er... he banished you?", current_sprite);
		say_stop ("`9You are truly noble!", current_sprite);
		say_stop ("`9But where should we go then?", current_sprite);
		say_stop ("Let us go to Eggeric van Eggermonde.", me);
		say_stop ("He is an evil man.", me);
		say_stop ("`9Isn't he married to my er... the king's sister?", current_sprite);
		say_stop ("Ah, yes, the beautiful Machteld.", me);
		say_stop ("Every man wanted to marry her.", me);
		say_stop ("Eggeric tricked her father into giving her to him.", me);
		say_stop ("She was very unhappy about it.", me);
		say_stop ("`9Yes, she told me about it.", current_sprite);
		say_stop ("You know her personally?", me);
		say_stop ("`9Er, well, er, we just talked a bit...", current_sprite);
		say_stop ("`9Anyway, why do we go to Eggeric?", current_sprite);
		say_stop ("`9He's one of the king's men!", current_sprite);
		say_stop ("Yes, but he's not loyal to the king.", me);
		say_stop ("And he has a saddle that is worth a lot of gold.", me);
		say_stop ("`9Very well, let's go there.", current_sprite);
		fade_down_stop ();
		unfreeze (current_sprite);
		unfreeze (1);
		script_attach (1000);
		bedink.main ();
		player_map = 35;
		sp_x (1, 340);
		sp_y (1, 125);
		sp_dir (1, 2);
		life = lifemax;
		dink_can_walk_off_screen (0);
		load_screen ();
		draw_screen ();
		draw_status ();
		fade_up_stop ();
		int adelbrecht = sp ("adelbrecht2");
		freeze (1);
		freeze (adelbrecht);
		sp_dir (1, 6);
		say_stop ("We're here.", 1);
		say_stop ("`9Right. What do we do now?", adelbrecht);
		say_stop ("You are a thief, right?", 1);
		say_stop ("`9Oh, yes, right. So... we break in?", adelbrecht);
		say_stop ("Of course we do! That's what we came for!", 1);
		say_stop ("`9Eh, yes, right.", adelbrecht);
		say_stop ("What did you bring?", 1);
		say_stop ("`9This? That's a rake I found on the way.", adelbrecht);
		say_stop ("What for?", 1);
		say_stop ("`9It might be useful to break the door open...", adelbrecht);
		say_stop ("`9Not?", adelbrecht);
		say_stop ("`9Never mind that...", adelbrecht);
		editor_layer(sp_code("rake"), 0, 0);
		sp_active (sp ("rake"), 0);
		say_stop ("`9I'll put it away.", adelbrecht);
		say_stop ("Right...", 1);
		say_stop ("(Weirdo...)", 1);
		say_stop ("How about I go in and steal his things,", 1);
		say_stop ("and you stand guard outside?", 1);
		say_stop ("`9YES! That sounds like a great idea!", adelbrecht);
		say_stop ("Hush, don't get too excited.", 1);
		say_stop ("`9Sorry.", adelbrecht);
		say_stop ("Before I go in, I want to ask the animals if it's safe.", 1);
		say_stop ("`9You can talk to animals?", adelbrecht);
		say_stop ("If I put a certain flower behind my teeth, I can.", 1);
		say_stop ("`9Cool!", adelbrecht);
		say_stop ("I'll go and find the flower.", 1);
		say_stop ("`9I'll just wait here, shall I?", adelbrecht);
		say_stop ("Yes, please.", 1);
		unfreeze (adelbrecht);
		unfreeze (1);
		herb = 1;
		sp_brain (adelbrecht, "person");
		save_game (-1);
		kill_this_task ();
	}
}
