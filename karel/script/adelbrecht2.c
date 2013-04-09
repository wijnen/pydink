extern int herb;

void main ()
{
	if (herb > 0)
		sp_brain (current_sprite, "person");
}

void talk ()
{
	freeze (1);
	freeze (current_sprite);
	if (herb == 1)
	{
		say_stop ("`9Did you find the flower?", current_sprite);
		say_stop ("Not yet.", 1);
		say_stop ("`9Do you want me to help you find it?", current_sprite);
		say_stop ("No! Er, I'll find it soon!", 1);
		say_stop ("You just stay here and don't do anything stupid!", 1);
		say_stop ("`9Sure thing.", current_sprite);
	}
	else if (herb == 2)
	{
		int duck = sp ("eggeric_duck");
		int pig = sp ("eggeric_pig");
		say_stop ("I've found the flower.", 1);
		say_stop ("`9Great, now what do we do?", current_sprite);
		say_stop ("We put it in our mouth.", 1);
		say_stop ("`9And then what?", current_sprite);
		say_stop ("Then we listen.", 1);
		say_stop ("`6Dude! The king is walking around outside the castle!", pig);
		say_stop ("`4Dude! Is he mad?", duck);
		say_stop ("`6Dude! I guess he has his reasons!", pig);
		say_stop ("`4Dude! I suppose so!", duck);
		say_stop ("The king? We can't risk getting caught!", 1);
		say_stop ("We shouldn't steal tonight.", 1);
		say_stop ("`9Are you afraid? I thought you were brave!", current_sprite);
		say_stop ("Well, yes, but... The King!", 1);
		say_stop ("Come on, what do those beasts know of us.", current_sprite);
		say_stop ("`9Let's focus on the task at hand.", current_sprite);
		say_stop ("Allright. Please return the flower to me.", 1);
		say_stop ("`9Hey, it's gone, where did it go?", current_sprite);
		say_stop ("Dude, you're no thief at all!", 1);
		say_stop ("You'd get caught before you even started!", 1);
		say_stop ("`9Well, eh, ...", current_sprite);
		say_stop ("I took the flower from under your nose.", 1);
		say_stop ("`9Oh, that explains it...", current_sprite);
		say_stop ("Well then. I'll go inside.", 1);
		herb = 3;
		save_game (-1);
	}
	else if (herb == 3)
	{
		say_stop ("`9What are you waiting for?", current_sprite);
		say_stop ("Nothing, I'll go inside now.", 1);
	}
	else if (herb == 4)
	{
		say_stop ("`9Are we done?", current_sprite);
		say_stop ("No, I didn't find anything yet.", 1);
		say_stop ("I'll go back in.", 1);
		say_stop ("`9Hurry up, will you?", current_sprite);
		say_stop ("Relax, all will be fine.", 1);
		herb = 3;
	}
	else if (herb == 5)
	{
		say_stop ("`9Are we done?", current_sprite);
		say_stop ("No, I found some gold, but not the saddle.", 1);
		say_stop ("It must be worth at least 10000 gold pieces.", 1);
		say_stop ("It is decorated with bells and everything.", 1);
		say_stop ("`9Hurry up, will you?", current_sprite);
		say_stop ("Relax, all will be fine.", 1);
		herb = 6;
		save_game (-1);
	}
	else if (herb == 6)
	{
		say_stop ("`9Are we done?", current_sprite);
		say_stop ("No, I didn't find the saddle yet.", 1);
		say_stop ("`9Hurry up, will you?", current_sprite);
		say_stop ("Relax, all will be fine.", 1);
	}
	unfreeze (current_sprite);
	unfreeze (1);
}
