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

## Escaping a literal apostrophe

Letters `A C E I S U Y n z` (and lowercase `a c e i s u y`) use a bare `'` suffix to mean an
accent (see mapping table below), so a literal apostrophe right after one of these letters
would otherwise be misread as an accent code.

To force a literal apostrophe with no accent, use the universal escape `\'` (backslash +
apostrophe) after **any** letter:

| Code | Renders as |
|------|-----------|
| `y\'` | y' |
| `a\'` | a' |
| `n\'` | n' |

This is a single, letter-independent rule — no per-letter table entry is needed. (Letters
that don't use `'` for an accent, e.g. `L`/`l` and `O`/`o` which use `''` for their acute
accent, already render a bare apostrophe literally without any escaping.)

**Legacy:** `a''` (two apostrophes, lowercase `a` only) is an older, `a`-specific escape kept
for backward compatibility with existing data. New data should use `\'` instead.

Implemented in `specialChars.ts` as `replaceOld["\\'"]`, `replaceUtf["\\'"]`, and `"\\'"` in
the `keys` array. Because the token has no letter prefix, it doesn't need the
alphabetical/length ordering the other keys require — just needs to be present in `keys`.
`removeInternal()`'s stripped-character class also includes the backslash, so `Jy\'cen`
normalizes to `Jycen` for plain-ASCII search matching, same as the legacy `Ja''ron` → `Jaron`.

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
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `G^` | Ğ | `g^` | ğ |

### I
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `I'` | Í | `i'` | í |
| `` I` `` | Ì | `` i` `` | ì |
| `I:` | Ï | `i:` | ï |
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
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `R^` | Ř | `r^` | ř |

### S
| Code | Character | Code | Character |
|------|-----------|------|-----------|
| `S^` | Š | `s^` | š |
| `S'` | Ś | `s'` | ś |
| `S--` | Ş | `s--` | ş |
| `S---` | Ș | `s---` | ș |
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
| `Jy\'cen` | Jy'cen | Jycen |
