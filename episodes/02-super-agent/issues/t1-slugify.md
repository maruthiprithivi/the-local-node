# slugify collapses punctuation poorly and leaves edge dashes

`widgets.textutil.slugify` should turn a title into a URL slug: lowercase ASCII words joined by single dashes.

Expected:
- `slugify("Hello,  World!")` -> `hello-world`
- `slugify("  --Already--Slugged--  ")` -> `already-slugged`
- `slugify("Café au lait")` -> `cafe-au-lait`
- `slugify("a___b...c")` -> `a-b-c`
- `slugify("!!!")` -> `""`

Right now punctuation runs become repeated dashes, and dashes on the ends are not always stripped.
