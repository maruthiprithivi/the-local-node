# format_cents drops leading zeros and mishandles negatives

`widgets.money.format_cents` should format an integer number of cents as dollars.

Expected:
- `format_cents(5)` -> `$0.05`
- `format_cents(100)` -> `$1.00`
- `format_cents(1505)` -> `$15.05`
- `format_cents(-250)` -> `-$2.50`
- `format_cents(-5)` -> `-$0.05`
- `format_cents(0)` -> `$0.00`

Right now small amounts lose the leading zero in the cents field, and negative amounts do not keep the minus sign in front of the dollar sign.
