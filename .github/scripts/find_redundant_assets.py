#!/usr/bin/env python3
"""
Find (and optionally delete) ALAS asset images in en/jp/tw that are identical
to the cn version, since ALAS falls back to cn when a server has no file.

An "asset" is a group of files sharing a base name in the same folder, e.g.
    SWITCH_2_HARD.png, SWITCH_2_HARD.SEARCH.png, SWITCH_2_HARD.2.png ...
A server's asset is only redundant if it has EXACTLY the same set of files as
cn and every file matches. Otherwise it is server-specific and left alone.

Usage:
    python find_redundant_assets.py ./assets            # dry run (default)
    python find_redundant_assets.py ./assets --pixels   # also compare decoded pixels
    python find_redundant_assets.py ./assets --delete   # actually delete
    python find_redundant_assets.py ./assets --strict-scope   # only what button_extract.py actually processes

Run it on a clean git tree, delete, re-run dev_tools/button_extract.py and
check `git diff` on the regenerated assets.py files.
"""
import argparse
import hashlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

BASE_SERVER = "cn"
DEFAULT_SERVERS = ["en", "jp", "tw"]


@lru_cache(maxsize=None)
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def same_pixels(a: Path, b: Path) -> bool:
    """Slow fallback: same image content even if the PNG bytes differ."""
    from PIL import Image  # pip install pillow

    with Image.open(a) as ia, Image.open(b) as ib:
        return ia.size == ib.size and ia.convert("RGBA").tobytes() == ib.convert("RGBA").tobytes()


def files_equal(a: Path, b: Path, use_pixels: bool) -> bool:
    if sha256(a) == sha256(b):
        return True
    return use_pixels and same_pixels(a, b)


def collect(server_dir: Path, strict: bool = False) -> dict:
    """Return {(relative_folder, asset_name): {filename: path}} for one server.

    strict=True limits this to what dev_tools/button_extract.py turns into assets.py entries:
    files directly inside assets/<server>/<module>/, names not starting with a digit,
    and only groups whose base image NAME.png exists.
    """
    groups = defaultdict(dict)
    for p in server_dir.rglob("*.png"):
        rel = p.relative_to(server_dir)
        if strict and len(rel.parts) != 2:
            continue
        asset_name = p.name.split(".")[0]  # NAME.SEARCH.png -> NAME
        if strict and asset_name[:1].isdigit():
            continue
        groups[(rel.parent.as_posix(), asset_name)][p.name] = p
    if strict:
        groups = {k: v for k, v in groups.items() if f"{k[1]}.png" in v}
    return groups


def find_redundant(assets_dir: Path, servers, use_pixels: bool, strict: bool = False):
    base_groups = collect(assets_dir / BASE_SERVER, strict)
    results = []  # (server, (folder, asset_name), [paths])

    for server in servers:
        server_dir = assets_dir / server
        if not server_dir.is_dir():
            print(f"[skip] {server_dir} does not exist")
            continue
        for key, files in collect(server_dir, strict).items():
            base = base_groups.get(key)
            if base is None:
                continue  # not in cn, nothing to fall back to
            if files.keys() != base.keys():
                continue  # different companion files -> server-specific
            if all(files_equal(files[n], base[n], use_pixels) for n in files):
                results.append((server, key, list(files.values())))
    return results


def remove_empty_parents(path: Path, stop_at: Path):
    parent = path.parent
    while parent != stop_at and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("assets_dir", type=Path, help="path to the ALAS ./assets folder")
    ap.add_argument("--servers", nargs="+", default=DEFAULT_SERVERS, help="servers to check against cn")
    ap.add_argument("--pixels", action="store_true", help="also compare decoded pixels (needs Pillow, slower)")
    ap.add_argument("--strict-scope", action="store_true",
                    help="only consider files the extractor turns into assets.py entries (recommended for automation)")
    ap.add_argument("--delete", action="store_true", help="delete redundant files (default is dry run)")
    ap.add_argument("--report", type=Path, default=None,
                    help="report file to write (default: redundant_assets.txt, or redundant_assets_pixels.txt with --pixels)")
    args = ap.parse_args()

    if args.report is None:
        args.report = Path("redundant_assets_pixels.txt" if args.pixels else "redundant_assets.txt")

    if not (args.assets_dir / BASE_SERVER).is_dir():
        raise SystemExit(f"{args.assets_dir / BASE_SERVER} not found")

    results = find_redundant(args.assets_dir, args.servers, args.pixels, args.strict_scope)

    total_files = sum(len(paths) for _, _, paths in results)
    total_bytes = sum(p.stat().st_size for _, _, paths in results for p in paths)

    lines = []
    per_server = defaultdict(int)
    for server, (folder, name), paths in sorted(results, key=lambda r: (r[0], r[1])):
        per_server[server] += len(paths)
        for p in paths:
            lines.append(str(p))
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Redundant assets: {len(results)} ({total_files} files, {total_bytes / 1024 / 1024:.2f} MiB)")
    for server, n in sorted(per_server.items()):
        print(f"  {server}: {n} files")
    print(f"File list written to {args.report}")

    if not args.delete:
        print("Dry run only. Re-run with --delete to remove them.")
        return

    for server, _, paths in results:
        for p in paths:
            p.unlink()
            remove_empty_parents(p, args.assets_dir / server)
    print("Deleted. Now re-run dev_tools/button_extract.py and check `git diff`.")


if __name__ == "__main__":
    main()
