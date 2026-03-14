import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from verify_and_complete import (
    strip_disambig, base_name_of, get_next_disambig,
    build_athlete_index, AthleteEntry, all_master_names,
    soundex, find_all_candidates, CandidateMatch,
    parse_out_new_athletes, apply_name_corrections,
    expand_special_codes, strip_to_ascii, get_incoming_year,
    strip_generational_suffix, is_auto_accept,
)

SAMPLE_MASTER = [
    "Smith, John; 2015; Arnold Classic - IFBB; OP-1;\n",
    "Smith, John; 2016; Tampa Pro - IFBB; OP-2;\n",
    "Smith, John [2]; 2021; Arnold Classic - IFBB; PH-3;\n",
    "Jones, Bob; 2020; Olympia - IFBB; CL-5;\n",
]


# --- strip_disambig ---

def test_strip_disambig_plain():
    assert strip_disambig("Smith, John") == "Smith, John"

def test_strip_disambig_numbered():
    assert strip_disambig("Smith, John [2]") == "Smith, John"
    assert strip_disambig("Smith, John [12]") == "Smith, John"

def test_base_name_of():
    assert base_name_of("Smith, John") == "Smith, John"
    assert base_name_of("Smith, John [3]") == "Smith, John"


# --- get_next_disambig ---

def test_get_next_disambig_none_exist():
    assert get_next_disambig("Jones, Bob", set()) == "Jones, Bob [2]"

def test_get_next_disambig_plain_exists():
    assert get_next_disambig("Jones, Bob", {"Jones, Bob"}) == "Jones, Bob [2]"

def test_get_next_disambig_gap():
    existing = {"Jones, Bob", "Jones, Bob [2]"}
    assert get_next_disambig("Jones, Bob", existing) == "Jones, Bob [3]"


# --- build_athlete_index / all_master_names ---

def test_build_athlete_index_keys():
    idx = build_athlete_index(SAMPLE_MASTER)
    assert "Smith, John" in idx
    assert "Jones, Bob" in idx

def test_build_athlete_index_variants():
    idx = build_athlete_index(SAMPLE_MASTER)
    assert len(idx["Smith, John"]) == 2

def test_build_athlete_index_summary():
    idx = build_athlete_index(SAMPLE_MASTER)
    entry = next(e for e in idx["Smith, John"] if e.full_name == "Smith, John")
    assert entry.count == 2
    assert entry.y0 == 2015
    assert entry.y1 == 2016
    assert "OP" in entry.divisions

def test_build_athlete_index_all_names():
    idx = build_athlete_index(SAMPLE_MASTER)
    all_names = all_master_names(idx)
    assert "Smith, John" in all_names
    assert "Smith, John [2]" in all_names


# --- soundex ---

def test_soundex_basic():
    assert soundex("Smith") == soundex("Smithe")
    assert soundex("John") != soundex("Smith")

def test_soundex_same():
    assert soundex("Smith") == soundex("Smith")


# --- special chars ---

def test_expand_special_codes_tilde():
    assert expand_special_codes("Pen~a") == "Peña"

def test_expand_special_codes_acute():
    assert expand_special_codes("e'") == "é"

def test_expand_special_codes_multi():
    # Multiple codes in one string
    assert expand_special_codes("n~a'") == "ñá"
    # No codes — unchanged
    assert expand_special_codes("Gonzalez") == "Gonzalez"

def test_strip_to_ascii_special_code():
    assert strip_to_ascii("Pen~a") == "pena"

def test_strip_to_ascii_unicode():
    assert strip_to_ascii("Peña") == "pena"

def test_strip_to_ascii_plain():
    assert strip_to_ascii("Pena") == "pena"

def test_strip_to_ascii_all_same():
    assert strip_to_ascii("Pen~a") == strip_to_ascii("Peña") == strip_to_ascii("Pena")


# --- generational suffix ---

def test_strip_generational_suffix_jr():
    assert strip_generational_suffix("John Jr") == "John"
    assert strip_generational_suffix("John Jr.") == "John"

def test_strip_generational_suffix_roman():
    assert strip_generational_suffix("John II") == "John"
    assert strip_generational_suffix("John III") == "John"
    assert strip_generational_suffix("John IV") == "John"

def test_strip_generational_suffix_none():
    assert strip_generational_suffix("John") == "John"
    assert strip_generational_suffix("Mary Ann") == "Mary Ann"


# --- get_incoming_year ---

def test_get_incoming_year():
    lines = ["Smith, John; 2025; Arnold Classic - IFBB; OP-1;\n"]
    assert get_incoming_year(lines) == 2025

def test_get_incoming_year_empty():
    assert get_incoming_year([]) == 0


# --- find_all_candidates ---

def test_find_candidates_exact_single():
    idx = build_athlete_index(["Smith, John; 2020; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Smith, John", idx, 2022, 8)
    assert len(results) == 1
    assert results[0].match_types == ["exact"]

def test_find_candidates_exact_returns_all_variants():
    # [n] variants should all be returned under the same base
    idx = build_athlete_index([
        "Smith, John; 2015; Test - IFBB; OP-1;\n",
        "Smith, John [2]; 2020; Test - IFBB; PH-1;\n",
    ])
    results = find_all_candidates("Smith, John", idx, 2022, 8)
    full_names = {r.entry.full_name for r in results}
    assert "Smith, John" in full_names
    assert "Smith, John [2]" in full_names

def test_find_candidates_exact_generational_variant():
    idx = build_athlete_index(["Smith, John Jr; 2020; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Smith, John", idx, 2022, 8)
    assert any(r.entry.full_name == "Smith, John Jr" for r in results)

def test_find_candidates_diacritic_code_to_plain():
    idx = build_athlete_index(["Pen~a, Jose; 2020; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Pena, Jose", idx, 2022, 8)
    assert any(r.entry.full_name == "Pen~a, Jose" for r in results)
    assert any("diacritic" in r.match_types for r in results)

def test_find_candidates_diacritic_unicode_to_code():
    idx = build_athlete_index(["Pen~a, Jose; 2020; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Peña, Jose", idx, 2022, 8)
    assert any(r.entry.full_name == "Pen~a, Jose" for r in results)

def test_find_candidates_subset_extra_name():
    idx = build_athlete_index(["Smith, Lisa Marie; 2020; Test - IFBB; FI-1;\n"])
    results = find_all_candidates("Smith, Lisa", idx, 2022, 8)
    assert any(r.entry.full_name == "Smith, Lisa Marie" for r in results)
    assert any("subset" in r.match_types for r in results)

def test_find_candidates_space_normalization():
    idx = build_athlete_index(["Shu, Xiaofan; 2020; Test - IFBB; PH-1;\n"])
    results = find_all_candidates("Shu, Xiao Fan", idx, 2022, 8)
    assert any(r.entry.full_name == "Shu, Xiaofan" for r in results)
    assert any("space" in r.match_types for r in results)

def test_find_candidates_eastern_format():
    idx = build_athlete_index(["Shu, Xiaofan; 2020; Test - IFBB; PH-1;\n"])
    results = find_all_candidates("Xiaofan Shu", idx, 2022, 8)
    assert any(r.entry.full_name == "Shu, Xiaofan" for r in results)

def test_find_candidates_word_order():
    idx = build_athlete_index(["Smith, John; 2020; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("John, Smith", idx, 2022, 8)
    assert any(r.entry.full_name == "Smith, John" for r in results)

def test_find_candidates_soundex_fallback():
    idx = build_athlete_index(["Lunsford, Derek; 2020; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Lunsford, Derik", idx, 2022, 8)
    assert any(r.entry.full_name == "Lunsford, Derek" for r in results)

def test_find_candidates_no_false_positives():
    idx = build_athlete_index(["Jones, Alice; 2020; Test - IFBB; FI-1;\n"])
    results = find_all_candidates("Smith, John", idx, 2022, 8)
    assert results == []

def test_find_candidates_temporal_gap():
    idx = build_athlete_index(["Pearl, Bill; 1972; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Pearl, Bill", idx, 2019, 8)
    assert len(results) == 1
    assert results[0].temporal_gap == 47

def test_find_candidates_all_same_plain():
    # Pena, Pen~a, and Peña in master should all appear when searching Pena
    idx = build_athlete_index([
        "Pena, Jose; 2018; Test - IFBB; OP-1;\n",
        "Pen~a, Jose; 2019; Test - IFBB; OP-1;\n",
    ])
    results = find_all_candidates("Pena, Jose", idx, 2022, 8)
    full_names = {r.entry.full_name for r in results}
    assert "Pena, Jose" in full_names
    assert "Pen~a, Jose" in full_names


# --- is_auto_accept ---

def test_is_auto_accept_single_exact_within_gap():
    idx = build_athlete_index(["Smith, John; 2018; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Smith, John", idx, 2022, 8)
    assert is_auto_accept(results, 2022, 8)

def test_is_auto_accept_fails_large_gap():
    idx = build_athlete_index(["Pearl, Bill; 1972; Test - IFBB; OP-1;\n"])
    results = find_all_candidates("Pearl, Bill", idx, 2019, 8)
    assert not is_auto_accept(results, 2019, 8)

def test_is_auto_accept_fails_multiple_candidates():
    idx = build_athlete_index([
        "Smith, John; 2015; Test - IFBB; OP-1;\n",
        "Smith, John [2]; 2020; Test - IFBB; PH-1;\n",
    ])
    results = find_all_candidates("Smith, John", idx, 2022, 8)
    assert not is_auto_accept(results, 2022, 8)

def test_is_auto_accept_fails_diacritic_ambiguity():
    # Pena (plain) and Pen~a both in master — ambiguous
    idx = build_athlete_index([
        "Pena, Jose; 2018; Test - IFBB; OP-1;\n",
        "Pen~a, Jose; 2019; Test - IFBB; OP-1;\n",
    ])
    results = find_all_candidates("Pena, Jose", idx, 2022, 8)
    assert not is_auto_accept(results, 2022, 8)


# --- parse_out_new_athletes / apply_name_corrections ---

SAMPLE_OUT = [
    "Smithe, John; 2025; Arnold Classic - IFBB; OP-3;\n",
    "Dauda, Samson; 2025; Arnold Classic - IFBB; OP-2;\n",
    "Smithe, John; 2025; Arnold Classic - IFBB; OV-1;\n",
]

SAMPLE_MASTER_LINES = [
    "Dauda, Samson; 2024; Tampa Pro - IFBB; OP-1;\n",
]

def test_parse_out_new_athletes():
    idx = build_athlete_index(SAMPLE_MASTER_LINES)
    master_names = all_master_names(idx)
    new_athletes = parse_out_new_athletes(SAMPLE_OUT, master_names)
    assert "Smithe, John" in new_athletes
    assert "Dauda, Samson" not in new_athletes

def test_apply_name_corrections_renames_all():
    corrections = {"Smithe, John": "Smith, John"}
    result = apply_name_corrections(SAMPLE_OUT, corrections)
    assert result[0].startswith("Smith, John;")
    assert result[2].startswith("Smith, John;")

def test_apply_name_corrections_no_change():
    corrections = {}
    result = apply_name_corrections(SAMPLE_OUT, corrections)
    assert result == SAMPLE_OUT
