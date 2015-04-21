extern int herb;

void touch ()
{
	say ("Here's the flower I'm looking for!", 1);
	herb = 2;
	editor_layer(sp_editor_num(current_sprite), 0, 0);
	int self = current_sprite;
	script_attach (1000);
	sp_active (self, 0);
	draw_hard_map ();
	kill_this_task ();
}
