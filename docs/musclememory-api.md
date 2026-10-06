# MuscleMemory API Reference

**Base URL: `http://localhost:3000`** (local musmem server). The public musclememory.org/.net API requires a signed request (anti-scraping) and rejects unsigned calls with `Invalid or missing request signature` — never call it directly.

Before any API call, check that the local server is up (`curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/contests/2025` → `200`). If nothing is running on port 3000, stop and ask the user to start the local musmem server — do not start it yourself, and never fall back to musclememory.org/.net.

## Endpoints

### Get contest names by org
```
GET http://localhost:3000/api/org?name={org}
```
Returns a list of all contest names for the given org (e.g., `IFBB`, `NPC`, `NAC`).

### Get years a contest has been held
```
GET http://localhost:3000/api/contest/years?name={contest_name}
```
Returns a list of years for which results exist for the given contest name.

### Get contest results
```
GET http://localhost:3000/api/contest?name={contest-name}&year={year}
```
Returns results for a specific contest and year.

## Rate Limiting

The server enforces two rate limits:

| Limit | Window | Cap |
|-------|--------|-----|
| Short-term | 10 seconds | 30 requests |
| Long-term | 1 hour | 1,000 requests |

**Bypass header:** Include `X-Rate-Limit-Bypass: {secret}` to skip the long-term hourly limit. The short-term limit is always enforced.  

Secret defined in musmem .env  `RATE_LIMIT_BYPASS_SECRET`
