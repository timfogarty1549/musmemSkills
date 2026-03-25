import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from review_athlete_names import last_names_word_close

# --- last_names_word_close ---

def test_exact_shared_word():
    # "Ortiz" appears in both last names
    assert last_names_word_close("Ortiz Guzman", "Ortiz") is True

def test_exact_shared_word_reversed():
    assert last_names_word_close("Ortiz", "Ortiz Guzman") is True

def test_typo_one_char_missing_end():
    assert last_names_word_close("Alvardo", "Alvarado") is True

def test_typo_one_char_missing_start():
    assert last_names_word_close("Lvarado", "Alvarado") is True

def test_al_prefix_different_names():
    # Only shared word is "al" (len 2) — should fail
    assert last_names_word_close("Al Kindy", "Al Saif") is False

def test_al_prefix_different_names_2():
    assert last_names_word_close("Al Sabea", "Al Saif") is False

def test_no_shared_words():
    assert last_names_word_close("Alamo Serrano", "Almaguer") is False

def test_no_shared_words_2():
    assert last_names_word_close("Alberto Cancel", "Albarado Rodriguez") is False

def test_shared_word_min_len_boundary():
    # "van" is len 3 — should count
    assert last_names_word_close("van Berg", "van Berg Jr") is True

def test_both_single_words_close():
    # Single words, edit distance 1
    assert last_names_word_close("Smithe", "Smith") is True

def test_both_single_words_far():
    # Single words, completely different
    assert last_names_word_close("Jones", "Smith") is False
