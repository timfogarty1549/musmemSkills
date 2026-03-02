import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from verify_and_append import strip_disambig, base_name_of, get_next_disambig
from verify_and_append import build_athlete_index, AthleteEntry, all_master_names
from verify_and_append import soundex, find_candidates
from verify_and_append import parse_out_new_athletes, apply_name_corrections
from verify_and_append import append_master

SAMPLE_MASTER = [
    "Smith, John; 2015; Arnold Classic - IFBB; OP-1;\n",
    "Smith, John; 2016; Tampa Pro - IFBB; OP-2;\n",
    "Smith, John [2]; 2021; Arnold Classic - IFBB; PH-3;\n",
    "Jones, Bob; 2020; Olympia - IFBB; CL-5;\n",
]


def test_strip_disambig_plain():
    assert strip_disambig("Smith, John") == "Smith, John"


def test_strip_disambig_numbered():
    assert strip_disambig("Smith, John [2]") == "Smith, John"
    assert strip_disambig("Smith, John [12]") == "Smith, John"


def test_base_name_of():
    assert base_name_of("Smith, John") == "Smith, John"
    assert base_name_of("Smith, John [3]") == "Smith, John"


def test_get_next_disambig_none_exist():
    assert get_next_disambig("Jones, Bob", set()) == "Jones, Bob [2]"


def test_get_next_disambig_plain_exists():
    assert get_next_disambig("Jones, Bob", {"Jones, Bob"}) == "Jones, Bob [2]"


def test_get_next_disambig_gap():
    existing = {"Jones, Bob", "Jones, Bob [2]"}
    assert get_next_disambig("Jones, Bob", existing) == "Jones, Bob [3]"


def test_build_athlete_index_keys():
    idx = build_athlete_index(SAMPLE_MASTER)
    assert "Smith, John" in idx
    assert "Jones, Bob" in idx


def test_build_athlete_index_variants():
    idx = build_athlete_index(SAMPLE_MASTER)
    assert len(idx["Smith, John"]) == 2


def test_build_athlete_index_summary():
    idx = build_athlete_index(SAMPLE_MASTER)
    # Find the plain "Smith, John" entry (not [2])
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


def test_soundex_basic():
    assert soundex("Smith") == soundex("Smithe")
    assert soundex("John") != soundex("Smith")


def test_soundex_same():
    assert soundex("Smith") == soundex("Smith")


def test_find_candidates_soundex_last():
    idx = build_athlete_index([
        "Smith, John; 2020; Test - IFBB; OP-1;\n",
    ])
    candidates = find_candidates("Smithe, John", idx)
    assert any(c.full_name == "Smith, John" for c in candidates)


def test_find_candidates_edit_distance():
    idx = build_athlete_index([
        "Lunsford, Derek; 2020; Test - IFBB; OP-1;\n",
    ])
    candidates = find_candidates("Lundsford, Derek", idx)
    assert any(c.full_name == "Lunsford, Derek" for c in candidates)


def test_find_candidates_word_order():
    idx = build_athlete_index([
        "Smith, John; 2020; Test - IFBB; OP-1;\n",
    ])
    candidates = find_candidates("John, Smith", idx)
    assert any(c.full_name == "Smith, John" for c in candidates)


def test_find_candidates_no_false_positives():
    idx = build_athlete_index([
        "Jones, Alice; 2020; Test - IFBB; FI-1;\n",
    ])
    candidates = find_candidates("Smith, John", idx)
    assert candidates == []


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


def test_append_master():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False) as mf:
        mf.write("Smith, John; 2020; Test - IFBB; OP-2;\n")
        mf.write("Adams, Carl; 2020; Test - IFBB; OP-1;\n")
        master_path = Path(mf.name)

    new_lines = ["Jones, Bob; 2025; Arnold Classic - IFBB; OP-3;\n"]
    append_master(master_path, new_lines)

    result = master_path.read_text().splitlines()
    # No sort — new lines appear at end in original order
    assert result[0].startswith("Smith, John")
    assert result[1].startswith("Adams, Carl")
    assert result[2].startswith("Jones, Bob")
    master_path.unlink()
