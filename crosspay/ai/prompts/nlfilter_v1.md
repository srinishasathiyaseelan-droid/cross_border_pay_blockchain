<!-- version: nlfilter_v1 -->
Translate the officer's search request into a filter. Use only the fields below; omit anything not asked for.
Never output SQL. Dates must be chosen from the reference dates given in the input.

Schema (all fields optional):
{"decision": "APPROVED"|"HOLD"|"BLOCKED"|"REJECTED", "risk_level": "LOW"|"MEDIUM"|"HIGH",
 "receiver_country": one of the listed countries, "currency": one of the listed currency codes,
 "min_amount_usd": number, "max_amount_usd": number, "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD",
 "text": "short text to match TX ID, sender or receiver"}
