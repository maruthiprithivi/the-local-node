You are working in a tiny Node.js repository.

Implement the missing function in src/slugify.js so that `npm test` passes. Do not edit the test file. Do not add dependencies.

The required behaviour of slugify(input):
- convert to a string
- lowercase
- trim leading and trailing whitespace
- replace any run of whitespace with a single hyphen
- remove any character that is not a-z, 0-9, or hyphen
- collapse consecutive hyphens into one
- strip leading and trailing hyphens
- if the result is empty, return "n-a"

After the tests pass, commit your change with a short message and stop.
When you are finished, print <promise>COMPLETE</promise> on its own line.
