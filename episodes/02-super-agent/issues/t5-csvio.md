# read_rows splits on every comma and does not handle a BOM

`widgets.csvio.read_rows` should parse CSV text with a header row into a list of dicts, with values kept as strings.

Expected:
- Quoted fields can contain commas, and doubled quotes inside a quoted field become a single quote.
- A UTF-8 BOM at the start of the text is ignored, so the first header is `name` rather than a BOM plus `name`.
- Blank lines are skipped.

Example: a file starting with a BOM and the header `name,note,qty`, then a row `"Smith, John","said ""hi""",3` and a row `plain,x,1`, should produce:

```
[{"name": "Smith, John", "note": "said \"hi\"", "qty": "3"},
 {"name": "plain", "note": "x", "qty": "1"}]
```
