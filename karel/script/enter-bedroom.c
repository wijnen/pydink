extern int allow_bedroom;

void touch ()
{
	if (allow_bedroom)
		return;
	freeze (1);
	say_stop ("I hear voices next door!", 1);
	say_stop ("Eggeric must be there with his wife.", 1);
	say_stop ("It's better not to go there until they're sleeping.", 1);
	move_stop (1, 2, 50, 1);
	unfreeze (1);
}
