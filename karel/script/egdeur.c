extern int herb;

void main ()
{
	if (herb > 2)
		sp_nohard (current_sprite, 0);
	else
		sp_nohard (current_sprite, 1);
	draw_hard_sprite (current_sprite);
}
