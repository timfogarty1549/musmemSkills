# MuscleMemory API Reference

## Endpoints

### Get contest names by org
```
GET https://musclememory.org/api/org?name={org}
```
Returns a list of all contest names for the given org (e.g., `IFBB`, `NPC`, `NAC`).

### Get years a contest has been held
```
GET https://musclememory.org/api/contest/years?name={contest_name}
```
Returns a list of years for which results exist for the given contest name.

### Get contest results
```
GET https://musclememory.org/api/contest?name={contest-name}&year={year}
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
