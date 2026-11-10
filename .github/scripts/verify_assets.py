#!/usr/bin/env python3
"""
Verify regenerated module/*/assets.py files against a baseline copy.

After duplicate server PNGs were deleted and dev_tools/button_extract.py re-run, the
only acceptable change to an entry is that a non-cn server's `file` path now points
at the cn file (the extractor's fallback). Everything else must be untouched:
    - area / color / button of every server
    - the cn file path
    - the set of entries and their type (Button / Template)

If a server's values changed, its deleted PNGs were not truly equivalent. With
--restore they are restored from git and the script exits with 10, so the caller
can regenerate and verify again.

Exit codes:
    0   everything matches
    10  violations found and their files restored (regenerate and run again)
    1   unrecoverable problem (or violations without --restore)
"""
import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path


def parse_assets(path: Path) -> dict:
    """Return {name: (call_type, {keyword: literal_value})} for one assets.py."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    entries = {}
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
        ):
            continue
        call = node.value
        kind = call.func.id if isinstance(call.func, ast.Name) else None
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
        entries[node.targets[0].id] = (kind, kwargs)
    return entries


def compare_entry(before, after):
    """Return (problems, moved_servers). problems is a list of (server, reason)."""
    kind_b, kw_b = before
    kind_a, kw_a = after
    if kind_b != kind_a or kw_b.keys() != kw_a.keys():
        return [("*", "entry type or arguments changed")], []

    problems = []
    for key in kw_b:
        if key == "file" or kw_b[key] == kw_a[key]:
            continue
        b, a = kw_b[key], kw_a[key]
        if isinstance(b, dict) and isinstance(a, dict):
            for server in sorted(set(b) | set(a)):
                if b.get(server) != a.get(server):
                    problems.append((server, f"{key} changed"))
        else:
            problems.append(("*", f"{key} changed"))

    fb, fa = kw_b.get("file", {}), kw_a.get("file", {})
    if fb.get("cn") != fa.get("cn"):
        problems.append(("cn", "cn file path changed"))

    moved = []
    for server in sorted((set(fb) | set(fa)) - {"cn"}):
        if fa.get(server) == fb.get(server):
            continue
        if fa.get(server) == fa.get("cn"):
            moved.append(server)
        else:
            problems.append((server, "file path is neither unchanged nor the cn fallback"))
    return problems, moved


def restore(violations, assets_dir: str):
    """Restore deleted asset groups (all files sharing NAME before the first dot)."""
    for module, name, server in sorted({(v["module"], v["name"], v["server"]) for v in violations}):
        folder = f"{assets_dir}/{server}/{module}"
        out = subprocess.run(
            ["git", "ls-files", "--deleted", "--", folder], capture_output=True, text=True, check=True
        ).stdout.splitlines()
        files = [f for f in out if Path(f).name.split(".")[0] == name]
        if files:
            subprocess.run(["git", "checkout", "--", *files], check=True)
            print(f"restored {len(files)} file(s): {server}/{module}/{name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline-dir", type=Path, required=True,
                    help="folder containing the baseline copies as module/<m>/assets.py")
    ap.add_argument("--assets-dir", default="assets")
    ap.add_argument("--restore", action="store_true", help="restore files behind violations")
    ap.add_argument("--json", type=Path, help="write violations to this file")
    args = ap.parse_args()

    violations, unrecoverable, moved_total = [], [], 0

    baseline_files = sorted(args.baseline_dir.rglob("assets.py"))
    if not baseline_files:
        raise SystemExit(f"no assets.py found under {args.baseline_dir}")

    for before_path in baseline_files:
        rel = before_path.relative_to(args.baseline_dir)
        module = rel.parts[-2]
        if not rel.exists():
            unrecoverable.append(f"{rel}: missing after regeneration")
            continue
        before, after = parse_assets(before_path), parse_assets(rel)
        for name in sorted(set(before) | set(after)):
            if name not in before or name not in after:
                unrecoverable.append(f"{rel}: entry {name} was added or removed")
                continue
            problems, moved = compare_entry(before[name], after[name])
            moved_total += len(moved)
            for server, reason in problems:
                if server in ("cn", "*"):
                    unrecoverable.append(f"{rel}: {name}: {reason}")
                else:
                    violations.append({"module": module, "name": name, "server": server, "reason": reason})

    if args.json:
        args.json.write_text(json.dumps({"violations": violations, "unrecoverable": unrecoverable}, indent=2))

    print(f"entries now falling back to cn: {moved_total}")
    print(f"violations: {len(violations)}, unrecoverable: {len(unrecoverable)}")
    for v in violations[:50]:
        print(f"  VIOLATION {v['server']}/{v['module']}/{v['name']}: {v['reason']}")
    for u in unrecoverable[:50]:
        print(f"  UNRECOVERABLE {u}")

    if unrecoverable:
        sys.exit(1)
    if violations:
        if not args.restore:
            sys.exit(1)
        restore(violations, args.assets_dir)
        sys.exit(10)


if __name__ == "__main__":
    main()
