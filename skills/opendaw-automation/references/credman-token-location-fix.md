# credman PyPI Token Location (2026-07-04)

## Problem

SKILL.md says "token in credman `pypi/__token__`" — this is wrong. The PyPI token is **not** in the `api_tokens` table.

## Correct location

```python
import sqlite3
c = sqlite3.connect('credentials/credentials.db')
# token is in the ACCOUNTS table, not api_tokens
r = c.execute("SELECT password FROM accounts WHERE service='pypi'").fetchone()
token = r[0]  # starts with pypi-AgEIc...
# username is __token__
```

## Tables in credentials.db

- `accounts` — service/username/email/phone/password/mfa — **PyPI token lives here**
- `api_tokens` — service/token/scope — has aliyun, 2captcha, vk.com, freetheai (NOT pypi)
- `sessions` — service/token/token_type
- `emails`, `phones`, `bb_programs`

## twine command

```bash
TWINE_TOKEN=$(python3 -c "
import sqlite3
c = sqlite3.connect('credentials/credentials.db')
r = c.execute('SELECT password FROM accounts WHERE service=?', ('pypi',)).fetchone()
print(r[0] if r else '')
")
twine upload dist/* -u __token__ -p "$TWINE_TOKEN"
```
