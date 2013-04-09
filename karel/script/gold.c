extern int herb;

void talk ()
{
	freeze (1);
	say_stop ("He left lots of gold on the table.", 1);
	say_stop ("I'll take that.", 1);
	gold += 1548;
	herb = 5;
	unfreeze (1);
	editor_type (sp_editor_num (current_sprite), 1);
	int self = current_sprite;
	script_attach (1000);
	sp_active (self, 0);
	draw_hard_map ();
	kill_this_task ();
}
