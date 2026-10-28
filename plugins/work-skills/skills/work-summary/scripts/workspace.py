#!/usr/bin/env python3
"""Manage the user-wide work-summary workspace and enumerate candidate files."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import date


def config_path():
    root = os.environ.get("XDG_CONFIG_HOME") or (os.environ.get("APPDATA") if os.name == "nt" else None)
    return (Path(root).expanduser() if root else Path.home() / ".config") / "work-summary" / "config.json"


def directory(value):
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    # Check actual access rather than permission bits, including ACLs.
    with os.scandir(path) as entries:
        next(entries, None)
    with tempfile.TemporaryFile(dir=path):
        pass
    return path


def get_workspace():
    config = config_path()
    if not config.exists():
        raise FileNotFoundError(f"Workspace not configured: {config}")
    data = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid workspace configuration: {config}")
    value = data.get("workspace")
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError(f"Invalid workspace configuration: {config}")
    return directory(value)


def set_workspace(value):
    path = directory(value)
    config = config_path()
    config.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so an interrupted update does not corrupt the prior setting.
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=config.parent, delete=False) as f:
            name = f.name
            json.dump({"workspace": str(path)}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(name, config)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return path


def discover(value):
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    files, errors = [], []
    def onerror(error):
        errors.append({"path": error.filename, "error": str(error)})
    for current, dirs, names in os.walk(root, onerror=onerror, followlinks=False):
        dirs.sort()
        for name in sorted(names):
            path = Path(current) / name
            if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
                continue
            try:
                path.read_text(encoding="utf-8-sig")
                files.append(str(path))
            except (OSError, UnicodeError) as exc:
                errors.append({"path": str(path), "error": str(exc)})
    return {"files": files, "errors": errors}


def reserve(value, end, mode):
    root = directory(value)
    date.fromisoformat(end)
    label = {"personal": "个人工作总结", "team": "团队工作总结"}[mode]
    for i in range(10000):
        suffix = f" ({i + 1})" if i else ""
        path = root / f"{end} - {label}{suffix}.md"
        try:
            with path.open("x", encoding="utf-8"):
                pass
            return path
        except FileExistsError:
            continue
    raise FileExistsError("No available output name")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("get")
    sub.add_parser("set").add_argument("directory")
    sub.add_parser("discover").add_argument("directory")
    out = sub.add_parser("reserve")
    out.add_argument("directory")
    out.add_argument("end", help="exclusive end date, YYYY-MM-DD")
    out.add_argument("mode", choices=("personal", "team"))
    args = parser.parse_args()
    try:
        if args.command == "get": result = str(get_workspace())
        elif args.command == "set": result = str(set_workspace(args.directory))
        elif args.command == "discover": result = discover(args.directory)
        else: result = str(reserve(args.directory, args.end, args.mode))
        print(json.dumps(result, ensure_ascii=True))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"work-summary: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
