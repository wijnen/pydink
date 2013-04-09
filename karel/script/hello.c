void talk ()
{
	freeze (1);
	freeze (current_sprite);
	say_stop ("Good night.", 1);
	say_stop ("`1Good night, knight.", current_sprite);
	int a = random (4, 0);
	if (a == 0)
	{
		say_stop ("`1Lovely weather, don't you think?", current_sprite);
		say_stop ("Yes, perfect for a walk in the forest.", 1);
	}
	else if (a == 1)
	{
		say_stop ("`1You have a nice armour.", current_sprite);
		say_stop ("Thank you.", 1);
	}
	else if (a == 2)
	{
		say_stop ("`1Have you seen the stars?", current_sprite);
		say_stop ("Yes, they're beautiful, aren't they?", 1);
	}
	else if (a == 3)
	{
		say_stop ("`1I think this is a very nice forest.", current_sprite);
		say_stop ("Yes, I think so, too.", 1);
	}
	unfreeze (current_sprite);
	unfreeze (1);
}

void hit ()
{
	say ("`1Hey! Don't do that, it hurts!", current_sprite);
}
