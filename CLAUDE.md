# MuscleMemory Skills — Project Rules

## Workflow

- **Do not auto-advance phases.** Complete the requested phase, report what was done, and stop. Wait for explicit instruction before moving to the next phase.
- **No parallel agents.** Process contests sequentially — multiple agents hit rate limits before completing.
- **Fully autonomous within a phase.** Do not ask for permission at each step; just do the work.

## MuscleMemory API

See [docs/musclememory-api.md](docs/musclememory-api.md) for available API endpoints.

- **Never call musclememory.org/.net `/api/*` directly.** The public API requires a signed request (anti-scraping) that Claude cannot generate. All database checks go to the local server at `http://localhost:3000/api/...`, which serves the same endpoints unsigned.
- **If nothing is running on port 3000, ask the user to start the local musmem server.** Don't start it yourself or fall back to the public site.

## Skills

- **Project skill files live in `.claude/skills/` within this project.** Do not read from `~/.claude/skills`. Always invoke skills via the `Skill` tool — never read skill files directly.

## Bash Commands

- **NEVER use multiline `python3 -c "..."` or `python3 - <<'PYEOF'` heredocs** — the `Bash(python3 *)` permission glob does not match newlines and will trigger a prompt every time. For any script longer than one line, write it to `/tmp/script.py` using the Write tool, then run `python3 /tmp/script.py`. This is always the correct pattern for non-trivial Python.
- **Always use absolute paths for `/tmp/`** — never relative paths like `../../../../../tmp/`. The `Write(/tmp/*)` permission rule only matches the absolute path `/tmp/...`.
- **`&&`-chained commands are checked individually.** Each command in a chain must match an allow rule. Only `curl`, `python3`, `mkdir`, `wc`, `sort`, `mv`, and `ls` are pre-approved. Use python to handle anything else (file reads, counting, piping, head/tail/grep) rather than piping to unapproved shell utilities.
- **`>` redirects to files trigger Write permission checks.** `/tmp/*` and `~/workspace/musmem/*` are pre-approved write destinations.
