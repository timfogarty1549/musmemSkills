import html, json, os

input_path = os.path.expanduser('~/workspace/musmem/data/unicode.txt')
output_path = os.path.expanduser('~/workspace/musmem/data/athletes_localized.json')

result = {}
duplicates = []
parse_errors = []

with open(input_path, encoding='utf-8') as f:
    for lineno, raw in enumerate(f, 1):
        line = raw.strip()
        if not line:
            continue
        # Split on first semicolon only — entity values also contain semicolons
        idx = line.find(';')
        if idx == -1:
            parse_errors.append(f"  line {lineno}: no semicolon — {repr(line)}")
            continue
        key = line[:idx].strip()
        value = html.unescape(line[idx+1:].strip())
        if key in result:
            duplicates.append(f"  {repr(key)} (line {lineno}) — keeping first occurrence")
        else:
            result[key] = value

# Report
print(f"Entries: {len(result)}")
if duplicates:
    print(f"Duplicates skipped ({len(duplicates)}):")
    for d in duplicates:
        print(d)
if parse_errors:
    print(f"Parse errors ({len(parse_errors)}):")
    for e in parse_errors:
        print(e)

# Preview a sample
print("\nSample entries (decoded):")
for k, v in list(result.items())[:5]:
    print(f"  {k!r}: {v!r}")
print("  ...")
for k, v in list(result.items())[-3:]:
    print(f"  {k!r}: {v!r}")

# Write JSON (ensure_ascii=False preserves actual UTF-8 characters)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\nWritten: {output_path}")
print(f"File size: {os.path.getsize(output_path)} bytes")
