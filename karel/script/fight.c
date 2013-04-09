void main ()
{
	wait (1);
	beknight.main ();
	sp_pseq (1, "silverknight 3");
	int eggeric = sp ("eggeric-knight");
	int wife = sp ("wife-fight");
	freeze (1);
	freeze (eggeric);
	sp_dir (eggeric, 1);
	fade_up_stop ();
	say_stop ("`0So you have my wife's blood on your hands!", eggeric);
	say_stop ("Indeed I do, you backstabber!", 1);
	say_stop ("`0That means you broke into my house, you thief!", eggeric);
	say_stop ("And it was a good thing I did, too!", 1);
	say_stop ("`#Dink, please kill him for me, will you.", wife);
	say_stop ("`#If you don't, he'll kill me, I'm sure!", wife);
	say_stop ("`0Indeed I will!", eggeric);
	say_stop ("I'll make sure that won't happen.", 1);
	say_stop ("For you, Machteld!", 1);
	say_stop ("`#Stop talking and start fighting!", wife);
	say ("`0YES, GET ON WITH IT!", eggeric);
	if (choice ("Get on with it", "Pray") == 2)
	{
		say_stop ("(God, please help me win this fight)", 1);
		strength += 10;
		defense += 5;
		lifemax += 40;
		life = lifemax;
	}
	say_stop ("YES, GET ON WITH IT!", 1);
	say ("", eggeric);
	unfreeze (1);
	unfreeze (eggeric);
}
