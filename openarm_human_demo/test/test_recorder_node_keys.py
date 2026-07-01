from pynput import keyboard

from openarm_human_demo.recorder_node import classify_key


def test_space_is_toggle():
    assert classify_key(keyboard.Key.space) == "toggle"


def test_esc_is_quit():
    assert classify_key(keyboard.Key.esc) == "quit"


def test_q_char_is_quit():
    assert classify_key(keyboard.KeyCode.from_char("q")) == "quit"


def test_other_key_is_none():
    assert classify_key(keyboard.KeyCode.from_char("a")) is None
    assert classify_key(keyboard.Key.enter) is None
