# MuscleMemory Data File Schema

This document describes the line format used by the main MuscleMemory `.dat` files,
including files such as `data/bb_male.dat` and `data/bb_female.dat`.

## Record Format

Each non-empty line is one contest result for one athlete.

```text
Last, First; YYYY; Contest Name - ORG; division-code-place; optional-fields;
```

Examples:

```text
Lunsford, Derek; 2025; Olympia - IFBB; OP-1;
Smith, John [2]; 2025; Arnold Classic - IFBB; PH-3; c=US;
```

Fields are separated by semicolon plus a single space (`; `). Lines conventionally
end with a trailing semicolon.

## Fields

| Position | Field | Required | Description |
|---:|---|---|---|
| 1 | Athlete name | Yes | `Family, Given`, with optional disambiguation suffix.<br>East Asian and Hungarian names are `Family Given` |
| 2 | Year | Yes | Four-digit contest year. |
| 3 | Contest | Yes | Contest title followed by organization suffix: `Contest Name - ORG`.<br>Some contest titles have no organization suffix. |
| 4 | Result | Yes | Division code and placing joined with a hyphen, for example `OP-1`.<br>Some records have no division code. |
| 5+ | Optional fields | No | Metadata fields such as `c=XX` country code. |

## Athlete Names

Names use `Family, Given` order:

```text
Dauda, Samson
```

When the same display name identifies more than one athlete, append a numeric
disambiguation suffix to the later identity:

```text
Smith, John
Smith, John [2]
Smith, John [3]
```

The suffix uses a space before the opening bracket and square brackets literally.
Incoming or preliminary files usually omit `[n]` suffixes until they are verified
against the master files.

For accented characters, master files use ASCII-safe internal character codes.
See `docs/special-chars-reference.md`.

## Contest Names

Contest names use the MuscleMemory form:

```text
Contest Name - ORG
```

Examples:

```text
Olympia - IFBB
Arnold Classic - IFBB
Ace of Stage Championships - NPC
Cancun Naturals - NPC Worldwide
```

Source sites may prefix the organization, but `.dat` records suffix it. For example,
`IFBB Arnold Classic` becomes `Arnold Classic - IFBB`.

## Result Field

The result field has this structure:

```text
division-code-place
```

Examples:

```text
OP-1
PH-3
BB-0
```

The division code is the part before the hyphen. The placing is the part after the
hyphen. Overall winners are commonly recorded with placing `0`.

Division codes are defined in `docs/divisions-reference.md`.

## Optional Fields

Optional metadata fields follow the result field. The most common optional field is
country:

```text
c=US;
c=UK;
c=KO;
```

Country codes are two-character internet / top-level-domain style codes, uppercase,
matching existing `.dat` conventions. Omit `c=` when the source country is blank or
not trustworthy.

Parsers should treat optional fields as a semicolon-delimited list after the result
field rather than assuming only one optional field exists.

## Parsing Notes

- Split records on semicolons, then trim surrounding whitespace from each field.
- Ignore the empty field produced by the trailing semicolon.
- Field index `0` is the athlete name.
- Field index `1` is the year.
- Field index `2` is the contest.
- Field index `3` is the result.
- Extract the organization from the contest field as the final text after ` - `.
- Extract the division from the result field as the text before the first hyphen.
- Extract country codes by finding `c=XX` optional fields.

## Related References

- `docs/divisions-reference.md` - division-code meanings.
- `docs/special-chars-reference.md` - internal ASCII-safe character codes.
- `docs/sources-reference.md` - source-specific contest-name conventions.
- `docs/ifbb-wac-pdf-parsing-rules.md` - extraction rules for IFBB WAC prelim files.
