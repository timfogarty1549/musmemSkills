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


from review_athlete_names import apply_name_corrections

# --- apply_name_corrections ---

def test_apply_corrections_basic():
    lines = [
        "2015_nationals-npc-male:123 : Ortiz Guzman, Jose\n",
        "2015_nationals-npc-male:145 : Smith, John\n",
        "2015_nationals-npc-male:167 : Ortiz Guzman, Jose\n",
    ]
    corrections = {"Ortiz Guzman, Jose": "Ortiz, Jose"}
    result = apply_name_corrections(lines, corrections)
    assert result[0] == "2015_nationals-npc-male:123 : Ortiz, Jose\n"
    assert result[1] == "2015_nationals-npc-male:145 : Smith, John\n"
    assert result[2] == "2015_nationals-npc-male:167 : Ortiz, Jose\n"

def test_apply_corrections_no_match():
    lines = ["2015_nationals-npc-male:123 : Smith, John\n"]
    corrections = {"Jones, Bob": "Jones, Robert"}
    result = apply_name_corrections(lines, corrections)
    assert result == lines

def test_apply_corrections_empty():
    lines = ["2015_nationals-npc-male:123 : Smith, John\n"]
    result = apply_name_corrections(lines, {})
    assert result == lines

def test_apply_corrections_preserves_context_col():
    # The part before ' : ' must be unchanged
    lines = ["abc:99 : Pastor Cueto, German\n"]
    corrections = {"Pastor Cueto, German": "Pastor, German"}
    result = apply_name_corrections(lines, corrections)
    assert result[0].startswith("abc:99 : ")
    assert result[0].endswith("Pastor, German\n")
