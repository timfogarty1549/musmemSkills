# Special Character Codes Reference

The MuscleMemory master `.dat` files use ASCII-safe codes for characters with diacritics,
because the files were first created in 1997 before Unicode was practical.

## Files to update when adding a new character

Four locations must be updated together:

1. **`~/workspace/node/musmem/src/utils/specialChars.ts`** — source of truth
   - `replaceOld` map: add `'X^': "&#NNN;"` (HTML entity decimal)
   - `replaceUtf` map: add `'X^': "Ẋ"` (UTF-8 character)
   - `keys` array: add `'X^'` and `'x^'` in alphabetical order (longer keys like `'D---'` must come before shorter ones like `'D--'` to match correctly)

2. **`~/workspace/musmem/php/format.php`** — `cleanUTF()` function (line ~40)
   - Add the UTF-8 character to the first array and its internal code to the second array

3. **This file** — add a row to the appropriate `### Letter` section in the Full mapping table below

---

The `verify_and_complete.py` matching pipeline (step 2) normalizes both directions —
internal codes and Unicode — to plain ASCII for comparison. All three forms of a name
are treated as equivalent: `Pen~a`, `Peña`, and `Pena` all normalize to `pena`.

---

## Code syntax

A code is a base letter followed by a punctuation suffix:

| Suffix | Meaning | Example code | Character |
|--------|---------|--------------|-----------|
| `'` | acute accent | `e'` | é |
| `` ` `` | grave accent | `e\`` | è |
| `:` | umlaut / diaeresis | `u:` | ü |
| `^` | caron / circumflex | `s^` | š |
| `~` | tilde | `n~` | ñ |
| `@` | ring above | `a@` | å |
| `*` | breve | `a*` | ă |
| `_` | macron | `a_` | ā |
| `.` | dot above | `e.` | ė |
| `/` | stroke | `o/` | ø |
| `--` | cedilla / eth | `c--` | ç |
| `---` | Vietnamese eth | `d---` | đ |
| `*` (s only) | German eszett | `s*` | ß |

---

## Full mapping

### A
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `A'` | Á | `a'` | á |
| `` A` `` | À | `` a` `` | à |
| `A:` | Ä | `a:` | ä |
| `A^` | Â | `a^` | â |
| `a~` | ã | | |
| `A@` | Å | `a@` | å |
| `A*` | Ă | `a*` | ă |
| `A_` | Ā | `a_` | ā |
| `A--` | Ą | `a--` | ą |

### C
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `C--` | Ç | `c--` | ç |
| `C^` | Č | `c^` | č |
| `C'` | Ć | `c'` | ć |

### D
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `D--` | Ð | `d--` | ð |
| `D---` | Đ | `d---` | đ |

### E
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `E'` | É | `e'` | é |
| `` E` `` | È | `` e` `` | è |
| `E:` | Ë | `e:` | ë |
| `e^` | ě | | |
| `E.` | Ė | `e.` | ė |
| `E_` | Ē | `e_` | ē |
| `E--` | Ę | `e--` | ę |

### G
| Code | Character |
|------|-----------|
| `g^` | ģ |

### I
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `I'` | Í | `i'` | í |
| `` I` `` | Ì | `` i` `` | ì |
| `I.` | İ | `i.` | ı |
| `I_` | Ī | `i_` | ī |

### L
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `L/` | Ł | `l/` | ł |
| `L''` | Ľ | `l''` | ľ |

### N
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `N~` | Ñ | `n~` | ñ |
| `N^` | Ň | `n^` | ň |
| | | `n'` | ń | | |

### O
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `O''` | Ó | `o''` | ó |
| `` O` `` | Ò | `` o` `` | ò |
| `O:` | Ö | `o:` | ö |
| `o^` | ô | | |
| `O~` | Õ | `o~` | õ |
| `O/` | Ø | `o/` | ø |

### R
| Code | Character |
|------|-----------|
| `r^` | ř |

### S
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `S^` | Š | `s^` | š |
| `S'` | Ś | `s'` | ś |
| `S--` | Ş | `s--` | ş |
| `s*` | ß | | |

### T
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `T^` | Ť | `t^` | ť |
| `T--` | Ţ | `t--` | ţ |
| `T---` | Ț | `t---` | ț |

### U
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `U'` | Ú | `u'` | ú |
| `U:` | Ü | `u:` | ü |
| `U^` | Û | `u^` | û |
| `u@` | ů | | |
| `U_` | Ū | `u_` | ū |

### Y
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `Y'` | Ý | `y'` | ý |
| `Y:` | Ÿ | `y:` | ÿ |

### Z
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `Z^` | Ž | `z^` | ž |
| `Z.` | Ż | `z.` | ż |
| | | `z'` | ź |

---

## Common examples in bodybuilding names

| Stored in master | Unicode | Plain ASCII |
|-----------------|---------|-------------|
| `Pen~a` | Peña | Pena |
| `Lun~ez` | Luñez | Lunez |
| `Alve's` | Alvés | Alves |
| `Rodri'guez` | Rodríguez | Rodriguez |
| `Fe'lix` | Félix | Felix |
| `Mo'ricz` | Móricz | Moricz |
| `Gu:nter` | Günter | Gunter |
| `Cze's` | Cześ | Czes |
| `S^tefan` | Štefan | Stefan |
