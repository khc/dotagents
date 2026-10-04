#!/usr/bin/env -S uv run --script
from datetime import date

print(date.today().strftime("%d.%m.%Y"))
