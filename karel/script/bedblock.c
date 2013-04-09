extern int herb;

void main ()
{
	if (herb < 6)
	{
		sp_disabled (current_sprite, 1);
		sp_nohard (current_sprite, 0);
		draw_hard_sprite (current_sprite);
	}
	else
	{
		sp_active (current_sprite, 0);
	}
}

void touch ()
{
	freeze (1);
	move_stop (1, 2, 50, 1);
	say_stop ("I hear voices next door!", 1);
	say_stop ("Eggeric must be there with his wife.", 1);
	say_stop ("It's better not to go there until they're sleeping.", 1);
	unfreeze (1);
}
