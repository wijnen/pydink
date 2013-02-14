void use ()
{
	int d = sp_dir (1);
	if (d == 7 || d == 1)
		d = 4;
	else if (d == 3 || d == 9)
		d = 6;
	sp_nocontrol (1, 1);
	sp_dir (1, d);
	sp_seq (1, collection_code ("hit") + d);
	sp_frame (1, 1);
}
