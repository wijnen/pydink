void main ()
{
	debug ("running beknight");
	if (count_item ("item-axe"))
	{
		debug ("I have axe already");
		return;
	}
	if (count_item ("item-fst"))
	{
		debug ("I had fist");
		kill_this_item ("item-fst");
	}
	sp_base_walk (1, "silverknight");
	sp_base_attack (1, "silverknightattack");
	sp_base_idle (1, "");
	add_item ("item-axe", "item-w", 6);
	cur_weapon = 1;
	arm_weapon ();
	sp_seq (1, "");
	sp_pseq (1, "silverknight 1");
	sp_pframe (1, 1);
	push_active (0);
	debug ("reached end of script");
}
