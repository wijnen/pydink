#ifdef PYDINK
extern int current_cursor_x;
extern int current_cursor_y;

void main ()
{
	int view = create_view ();
	set_view (view);
	sp_que (create_sprite (420, 287, "none", "menu", 1), 10000);
	draw_status ();
	sp_pseq (1, "menu");
	sp_pframe (1, 2);
	freeze (1);
	int n, seq, frame, x, y;
	for (y = 0; y < 4; y += 1)
	{
		for (x = 0; x < 2; x += 1)
		{
			// Magic.
			n = y * 2 + x + 1;
			seq = get_magic_seq (n);
			if (seq <= 0)
				continue;
			frame  = get_magic_frame (n);
			create_sprite (x * 83 + 89, y * 75 + 126, "none", seq, frame);
		}
		for (x = 0; x < 4; x += 1)
		{
			// Items.
			n = y * 4 + x - 2 + 1;
			seq = get_item_seq (n);
			if (seq <= 0)
				continue;
			frame  = get_item_frame (n);
			create_sprite (x * 83 + 138, y * 75 + 126, "none", seq, frame);
		}
	}
	while (1)
	{
		if (current_cursor_x < 2)
			sp_x (1, 90 + current_cursor_x * 83);
		else
			sp_x (1, 139 + current_cursor_x * 83);
		sp_y (1, 127 + current_cursor_y * 75);
		int b = wait_for_button ();
		if (b == 1)
		{
			// Action.
			if (current_cursor_x < 2)
			{
				// Magic.
				n = current_cursor_y * 2 + current_cursor_x + 1;
				if (get_magic_seq (n) > 0)
				{
					cur_magic = n;
					arm_magic ();
					draw_status ();
				}
			}
			else
			{
				// Item.
				n = current_cursor_y * 4 + current_cursor_x - 2 + 1;
				if (get_item_seq (n) > 0)
				{
					cur_weapon = n;
					arm_weapon ();
					draw_status ();
				}
			}
		}
		else if (b == 4)
		{
			// Inventory.
			set_view (0);
			kill_view (view);
			break;
		}
		else if (b == 12)
		{
			if (current_cursor_y < 3)
				current_cursor_y += 1;
		}
		else if (b == 14)
		{
			if (current_cursor_x > 0)
				current_cursor_x -= 1;
		}
		else if (b == 16)
		{
			if (current_cursor_x < 5)
				current_cursor_x += 1;
		}
		else if (b == 18)
		{
			if (current_cursor_y > 0)
				current_cursor_y -= 1;
		}
	}
	draw_status ();
}
#endif
