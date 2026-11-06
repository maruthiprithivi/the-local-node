# parse_duration only accepts the 1h30m shape

`widgets.durations.parse_duration` should parse durations such as `1h30m`, `2h`, `45m`, `90s` or `1h2m3s` into seconds.

Expected:
- `parse_duration("1h30m")` == 5400
- `parse_duration("2h")` == 7200
- `parse_duration("45m")` == 2700
- `parse_duration("90s")` == 90
- `parse_duration("1h2m3s")` == 3723
- `parse_duration(" 10m ")` == 600

It should raise `ValueError` for bad input such as `""`, `"h"`, `"1x"`, `"m5"` and `"1h1h"`.
