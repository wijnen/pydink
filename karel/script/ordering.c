extern int g_dink;
extern int g_daniel;
extern int g_adelbrecht;
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
	sp_brain (g_adelbrecht, "person");
	sp_brain (g_dink, "person");
	sp_brain (g_eggeric, "person");
	sp_brain (g_machteld, "person");
	freeze (g_adelbrecht);
	freeze (g_dink);
	freeze (g_eggeric);
	freeze (g_machteld);
	sp_base_walk (g_adelbrecht, "soldier");
	sp_base_walk (g_dink, "walk");
	sp_base_walk (g_eggeric, "merchant");
	sp_base_walk (g_machteld, "bluemaiden");
	sp_timing (g_dink, 33);
	sp_speed (g_dink, 2);
	move_stop (g_dink, 2, 400, 1);
	say_stop ("I'll do some ordering for you!", g_dink);
	sp_pseq (g_dink, "walk 7");
	sp_pseq (g_eggeric, "merchant 1");
	sp_pseq (g_machteld, "bluemaiden 1");
	say_stop ("Adelbrecht, turn around!", g_dink);
	say_stop ("`9Allright, relax.", g_adelbrecht);
	sp_pseq (g_adelbrecht, "soldier 7");
	sp_pseq (g_dink, "walk 9");
	say_stop ("Eggeric, sit down!", g_dink);
	sp_brain (g_eggeric, "none");
	say_stop ("`0I don't take orders from you!", g_eggeric);
	sp_pseq (g_dink, "walk 4");
	say_stop ("Daniel, sit straight!", g_dink);
	sp_pseq (g_machteld, "bluemaiden 1");
	say_stop ("`#Er, excuse me, Dink?", g_machteld);
	sp_pseq (g_dink, "walk 6");
	sp_pseq (g_adelbrecht, "soldier 3");
	say_stop ("Yes, dear?", g_dink);
	sp_pseq (g_eggeric, "merchant 3");
	say_stop ("`#I think 'ordering' is about buying this game.", g_machteld);
	sp_pseq (g_eggeric, "merchant 1");
	say_stop ("Buying?", g_dink);
	say_stop ("You mean it's not free?", g_dink);
	sp_pseq (g_eggeric, "merchant 3");
	say_stop ("`#I think so...", g_machteld);
	sp_pseq (g_eggeric, "merchant 1");
	say_stop ("No way!", g_dink);
	say_stop ("Don't you know who wrote this?", g_dink);
	say_stop ("Bas Wijnen, wijnen@debian.org!", g_dink);
	say_stop ("`9I thought it was shevek", g_adelbrecht);
	sp_pseq (g_dink, "walk 7");
	say_stop ("That's his nickname.", g_dink);
	say_stop ("`9Oh, right. Sorry.", g_adelbrecht);
	sp_pseq (g_dink, "walk 6");
	say_stop ("He's a free software freak!", g_dink);
	say_stop ("Anything he writes is free and open source.", g_dink);
	sp_pseq (g_eggeric, "merchant 3");
	say_stop ("`#But why did he put this button in then?", g_machteld);
	say_stop ("`#I'm sure he doesn't want you to give orders.", g_machteld);
	sp_pseq (g_eggeric, "merchant 1");
	say_stop ("No, that's true.", g_dink);
	say_stop ("I suppose he just used all the available buttons", g_dink);
	say_stop ("His editor doesn't support custom artwork yet, you know.", g_dink);
	sp_pseq (g_eggeric, "merchant 3");
	say_stop ("`#Oh, really?", g_machteld);
	say_stop ("`#He should fix that.", g_machteld);
	sp_pseq (g_eggeric, "merchant 1");
	say_stop ("Indeed.", g_dink);
	say_stop ("`0Hey you, with the ugly clothes!", g_eggeric);
	sp_pseq (g_dink, "walk 9");
	say_stop ("Are you talking to me?", g_dink);
	say_stop ("`0You bet I am!", g_eggeric);
	say_stop ("`0Are you done talking to my wife?", g_eggeric);
	say_stop ("`0Why are you called Dink, and the king Daniel?", g_eggeric);
	say_stop ("`0And why is my wife called Machteld?", g_eggeric);
	say_stop ("Of course the king really should be called emperor Karel", g_dink);
	say_stop ("Or Charlemagne in English.", g_dink);
	say_stop ("And I should be called Elegast.", g_dink);
	say_stop ("Or Elbegast in English.", g_dink);
	say_stop ("But then faithful Dink-players would get confused.", g_dink);
	say_stop ("Now Machteld is a different story.", g_dink);
	say_stop ("She doesn't have a name in the original story.", g_dink);
	say_stop ("But this game is made in honour of her birthday.", g_dink);
	say_stop ("`3You told me it was to test your dmod builder!", g_daniel);
	sp_pseq (g_dink, "walk 4");
	say_stop ("Yes, that too.", g_dink);
	sp_pseq (g_adelbrecht, "soldier 1");
	say_stop ("`#What?", g_machteld);
	sp_pseq (g_adelbrecht, "soldier 3");
	sp_pseq (g_eggeric, "merchant 3");
	sp_pseq (g_dink, "walk 6");
	say_stop ("`#But I thought it was for me!", g_machteld);
	sp_pseq (g_eggeric, "merchant 1");
	say_stop ("It is!", g_dink);
	sp_pseq (g_eggeric, "merchant 3");
	say_stop ("`#Pff, you just say that!", g_machteld);
	sp_pseq (g_eggeric, "merchant 1");
	say_stop ("No, really!", g_dink);
	say_stop ("Oh, forget it!", g_dink);
	move_stop (g_dink, 8, 350, 1);
	sp_y (g_dink, 350);
	sp_brain (g_dink, "repeat");
	sp_seq (g_dink, "walk 3");
	sp_pseq (g_adelbrecht, "soldier 3");
	sp_brain (g_adelbrecht, "repeat");
	sp_pseq (g_eggeric, "merchant 3");
	sp_brain (g_eggeric, "repeat");
	sp_pseq (g_machteld, "bluemaiden 3");
	sp_brain (g_machteld, "repeat");
	sp_brain (1, "pointer");
}
