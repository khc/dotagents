#!/usr/bin/env -S uv run --locked --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
from datetime import date

print(date.today().strftime("%d.%m.%Y"))
