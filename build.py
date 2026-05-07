#!/usr/bin/env python

import contextlib
from io import BufferedWriter, FileIO
import os
import shutil
import git
from jinja2 import Environment, FileSystemLoader

SOURCES_DIR = "src"
DIST_DIR = "dist"

def latest_git_commit_year() -> int:
    return git.Repo(".").head.commit.authored_datetime.year

def build_template(env: Environment, src_path: str):
    rel_path = os.path.relpath(src_path, SOURCES_DIR)
    dist_path = os.path.splitext(os.path.join(DIST_DIR, rel_path))[0]

    template = env.get_template(rel_path)
    rendered_text = template.render(copyright_year = latest_git_commit_year())

    with BufferedWriter(FileIO(dist_path, "wb")) as writer:
        for line in rendered_text.splitlines():
            line = line.strip()
            if len(line) > 0:
                writer.write(line.encode())
                writer.write(b"\n")

def main():
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(DIST_DIR)

    env = Environment(
        loader=FileSystemLoader(SOURCES_DIR),
        autoescape=True
    )

    for root, _, files in os.walk(SOURCES_DIR):
        rel_dir_path = os.path.relpath(root, SOURCES_DIR)
        dist_root = os.path.join(DIST_DIR, rel_dir_path)
        os.makedirs(dist_root, exist_ok=True)

        for src_name in files:
            src_path = os.path.join(root, src_name)

            if src_name.endswith(".jinja"):
                if not src_name.startswith("_"):
                    build_template(env, src_path)

            else:
                dist_path = os.path.join(dist_root, src_name)
                shutil.copy(src_path, dist_path)

if __name__ == '__main__':
    main()
