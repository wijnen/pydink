// Dink's axe item

void use ()
{
	// disallow diagonal hits, the animations don't exist.
	int d = sp_dir (1);
	if (d == 1 || d == 3)
		d = 2;
	if (d == 7 || d == 9)
		d = 8;
	// use attack sequence for this direction.
	sp_seq(1, collection_code ("silverknightattack") + d);
	sp_frame(1, 1);
	sp_nocontrol(1, 1);
}
