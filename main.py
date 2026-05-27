import os
import sys
import shutil
import subprocess
import platform
import tempfile
import zipfile
from pathlib import Path
import argparse
import importlib.util
import requests

GITHUB_OWNER = "HyperSonic-Games"
GITHUB_REPO = "Magma"


# -----------------------------
# BUILD FILE TEMPLATE (FIXED)
# -----------------------------

BUILD_FILE_TEMPLATE = """
import os
import shutil
from pathlib import Path

import Magma.COPY_FILES as magma

DEP_MODULES = [
    magma
]

PROJECT_ROOT = Path(__file__).resolve().parent
BUILD_DIR = PROJECT_ROOT / "build"

RUNTIME_OS = "windows" if os.name == "nt" else "unix"


def match_os(rule_os: str | None) -> bool:
    if rule_os is None:
        return True
    if rule_os == "windows":
        return RUNTIME_OS == "windows"
    if rule_os == "unix":
        return RUNTIME_OS != "windows"
    return False


def resolve(p: str) -> Path:
    if p.startswith("./"):
        return (PROJECT_ROOT / p[2:]).resolve()
    return (PROJECT_ROOT / "Magma" / "vendor" / p).resolve()


def copy(src: Path, dst: Path):
    if not src.exists():
        raise RuntimeError(f"Missing file: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    print(f"[COPY] {src} -> {dst}")


def run():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    for mod in DEP_MODULES:
        for rule in mod.RULES:

            if not match_os(rule.get("os")):
                continue

            src = resolve(rule["from"])
            dst = BUILD_DIR / rule["to"]

            copy(src, dst)


if __name__ == "__main__":
    run()
"""


# -----------------------------
# MAIN TEMPLATE
# -----------------------------

MAIN_FILE_TEMPLATE = """
package main

import "Magma/2D/Renderer"
import "Magma/2D/EventSys"
import "Magma/Types"

backend: Renderer.GraphicsBackend = .SOFTWARE

main :: proc() {
    ctx := Renderer.Init("hello", "hello", 800, 500, backend)

    mouse := new(EventSys.Mouse)
    keyboard := new(EventSys.Keyboard)
    win_state := new(EventSys.WindowState)

    rect_pos: Types.Vector2f = {52, 50}
    rect_size: Types.Vector2f = {100, 100}
    speed: f32 = 100.0

    running := true

    for running {
        EventSys.HandleEvents(mouse, keyboard, win_state)
        dt := Renderer.GetDeltaTime()
        if dt < 0.001 { dt = 0.001 }

        if keyboard.states[EventSys.KEYS.W] { rect_pos.y -= speed * dt }
        if keyboard.states[EventSys.KEYS.S] { rect_pos.y += speed * dt }
        if keyboard.states[EventSys.KEYS.A] { rect_pos.x -= speed * dt }
        if keyboard.states[EventSys.KEYS.D] { rect_pos.x += speed * dt }

        Renderer.ClearScreen(&ctx, {0,0,0,255})
        Renderer.DrawRect(&ctx, rect_pos, rect_size, {255,255,255,255})
        Renderer.Update(&ctx)
        Renderer.PresentScreen(&ctx)

        if win_state.should_quit {
            running = false
        }
    }

    free(mouse)
    free(keyboard)
    free(win_state)
}
"""


# -----------------------------
# DOWNLOAD
# -----------------------------

def download_zip(ref: str, out_path: Path):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/zipball/{ref}"
    headers = {"Accept": "application/vnd.github+json"}

    r = requests.get(url, headers=headers, stream=True, timeout=60)
    r.raise_for_status()

    with out_path.open("wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)


def safe_extract(zip_path: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            target = (dst / member).resolve()
            if not str(target).startswith(str(dst.resolve())):
                raise RuntimeError("Unsafe zip path detected")

        z.extractall(dst)


def extract_and_normalize(zip_path: Path, project_dir: Path, repo_dir: str = "Magma"):
    staging = Path(tempfile.mkdtemp())

    try:
        safe_extract(zip_path, staging)

        top_level = next(staging.iterdir())
        repo_target = project_dir / repo_dir

        if repo_target.exists():
            shutil.rmtree(repo_target)

        project_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(top_level), str(repo_target))

    finally:
        shutil.rmtree(staging, ignore_errors=True)


# -----------------------------
# PROJECT SETUP
# -----------------------------

def setup_project_files(project_dir: Path):
    (project_dir / "assets").mkdir(parents=True, exist_ok=True)
    (project_dir / "main.odin").write_text(MAIN_FILE_TEMPLATE, encoding="utf-8")
    (project_dir / "README.md").write_text("", encoding="utf-8")
    (project_dir / "LICENSE").write_text("", encoding="utf-8")


# -----------------------------
# BUILD PIPELINE
# -----------------------------

def run_build_pipeline(project_dir: Path):
    build_file = project_dir / "Build.py"

    if not build_file.exists():
        return

    print("[ASSETS] Running Build.py pipeline...")

    subprocess.run(
        [sys.executable, str(build_file)],
        cwd=project_dir,
        check=True
    )


# -----------------------------
# ODIN
# -----------------------------

def find_odin():
    odin = shutil.which("odin")
    if not odin:
        raise RuntimeError("odin not found in PATH")
    return odin


def run_build(project_name: str, args: list[str]):
    project_dir = Path(project_name).resolve()
    build_dir = project_dir / "build"

    odin = find_odin()

    no_assets = "-no-assets-bundle" in args
    args = [a for a in args if a != "-no-assets-bundle"]

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.mkdir(parents=True, exist_ok=True)

    cmd = [odin, "build", "."] + args
    print("Running:", " ".join(cmd))

    subprocess.run(cmd, cwd=project_dir, check=True)

    if not no_assets:
        run_build_pipeline(project_dir)

    system = platform.system().lower()
    exe_ext = ".exe" if system == "windows" else ""

    binary_name = project_dir.name + exe_ext
    binary_path = project_dir / binary_name

    final_assets = project_dir / "assets"

    (build_dir / "assets").mkdir(parents=True, exist_ok=True)

    if binary_path.exists():
        shutil.move(str(binary_path), str(build_dir / binary_name))

    if final_assets.exists() and not no_assets:
        shutil.copytree(final_assets, build_dir / "assets", dirs_exist_ok=True)

    zip_path = project_dir / "build.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in build_dir.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(build_dir))

    print("Build complete:", zip_path)

    shutil.rmtree(build_dir, ignore_errors=True)


# -----------------------------
# CREATE PROJECT
# -----------------------------

def create_project(ref: str, project_name: str):
    if ref == "none":
        ref = "main"

    project_dir = Path(project_name).resolve()

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        print(f"Downloading {ref}...")
        download_zip(ref, tmp_path)

        print("Extracting...")
        extract_and_normalize(tmp_path, project_dir)

        setup_project_files(project_dir)

    finally:
        tmp_path.unlink(missing_ok=True)

    print("Done.")


# -----------------------------
# CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="magma-sdk",
        description="Magma SDK CLI tool"
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    c.add_argument("ref")
    c.add_argument("project")

    b = sub.add_parser("build")
    b.add_argument("project")
    b.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.cmd == "create":
        create_project(args.ref, args.project)
    elif args.cmd == "build":
        run_build(args.project, args.args)


if __name__ == "__main__":
    main()
