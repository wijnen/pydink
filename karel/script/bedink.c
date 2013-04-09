void main ()
{
	if (count_item ("item-fst"))
		return;
	if (count_item ("item-axe"))
		kill_this_item ("item-axe");
	sp_base_walk (1, "walk");
	sp_base_attack (1, "hit");
	sp_base_idle (1, "idle");
	add_item ("item-fst", "item-w", 1);
	cur_weapon = 1;
	arm_weapon ();
	push_active (1);
}
