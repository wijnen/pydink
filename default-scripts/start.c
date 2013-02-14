int make_button (int button)
{
	sp_noclip (button, 1);
	sp_touch_damage (button, -1);
	return button;
}

void main ()
{
	fill_screen (0);
	sp_script (make_button (create_sprite (76, 40, "button", "button-start", 1)), "game-start");
	sp_script (make_button (create_sprite (524, 40, "button", "button-continue", 1)), "game-continue");
	sp_script (make_button (create_sprite (560, 440, "button", "button-quit", 1)), "game-quit");
}
