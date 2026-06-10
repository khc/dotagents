#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "jinja2",
# ]
# ///

def get_date():
    from datetime import date

    return date.today().strftime("%d.%m.%Y")


def render(date_val: str | None = None) -> str:
    import os
    import sys
    from jinja2 import Environment, FileSystemLoader

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(script_dir, "..", "templates")

        if not os.path.isdir(templates_dir):
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("hello_template.jinja2")

        # Resolve date parameter: explicitly passed > environment variable > current date
        resolved_date = date_val or os.environ.get("HELLO_DATE") or get_date()

        return template.render(date=resolved_date)
    except Exception as e:
        sys.stderr.write(f"Error rendering template: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    import sys

    try:
        parser = argparse.ArgumentParser(description="Dynamic hello skill template renderer.")
        parser.add_argument("--date", help="Contextual date override for the hello template.")
        args = parser.parse_args()

        skill = render(date_val=args.date)
        print(skill)
    except Exception as e:
        sys.stderr.write(f"Execution failed: {e}\n")
        sys.exit(1)
