extern int have_map;

void main ()
{
	if (have_map)
		show_bmp ("map", 1);
	else	
		say ("I don't have a map", 1);
	kill_this_task ();
}
