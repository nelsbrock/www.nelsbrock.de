#!/usr/bin/env python


import contextlib
import os
import shutil
from io import BufferedWriter, FileIO

import git
import magic
from compression import gzip, zstd
from jinja2 import Environment, FileSystemLoader

SOURCES_DIR = "src"
DIST_DIR = "dist"
COMPR_THRESHOLD = 512

# mostly taken from https://caddyserver.com/docs/caddyfile/directives/encode
COMPR_MIME_PREFIXES = [
    "application/atom+xml",
    "application/eot",
    "application/font",
    "application/geo+json",
    "application/graphql+json",
    "application/javascript",
    "application/json",
    "application/ld+json",
    "application/manifest+json",
    "application/opentype",
    "application/otf",
    "application/rss+xml",
    "application/truetype",
    "application/ttf",
    "application/vnd.api+json",
    "application/vnd.ms-fontobject",
    "application/wasm",
    "application/x-httpd-cgi",
    "application/x-javascript",
    "application/x-opentype",
    "application/x-otf",
    "application/x-perl",
    "application/x-protobuf",
    "application/x-ttf",
    "application/xhtml+xml",
    "application/xml",
    "font/otf",
    "font/ttf",
    "image/svg+xml",
    "image/vnd.microsoft.icon",
    "image/x-icon",
    "multipart/bag",
    "multipart/mixed",
    "text/",
]


def latest_git_commit_year() -> int:
    return git.Repo(".").head.commit.authored_datetime.year


def build_template(env: Environment, src_path: str) -> tuple[str, int]:
    rel_path = os.path.relpath(src_path, SOURCES_DIR)
    dist_path = os.path.splitext(os.path.join(DIST_DIR, rel_path))[0]

    template = env.get_template(rel_path)
    rendered_text = template.render(copyright_year=latest_git_commit_year())

    size = 0
    with BufferedWriter(FileIO(dist_path, "wb")) as writer:
        for line in rendered_text.splitlines():
            line = line.strip()
            if len(line) > 0:
                line_b = line.encode()
                size += len(line_b) + 1
                _ = writer.write(line.encode())
                _ = writer.write(b"\n")

    return dist_path, size


def compress(path: str):
    with open(path, "rb") as reader, open(path + ".zst", "wb") as zstd_writer, open(path + ".gz", "wb") as gzip_writer:
        content = reader.read()
        zstd_compressed = zstd.compress(content, level=15)
        _ = zstd_writer.write(zstd_compressed)
        gzip_compressed = gzip.compress(content, compresslevel=9)
        _ = gzip_writer.write(gzip_compressed)


def main():
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(DIST_DIR)

    env = Environment(loader=FileSystemLoader(SOURCES_DIR), autoescape=True)

    mime = magic.Magic(mime=True)

    for root, _, files in os.walk(SOURCES_DIR):
        rel_dir_path = os.path.relpath(root, SOURCES_DIR)
        dist_root = os.path.join(DIST_DIR, rel_dir_path)
        os.makedirs(dist_root, exist_ok=True)

        for src_name in files:
            src_path = os.path.join(root, src_name)

            if src_name.endswith(".jinja"):
                if not src_name.startswith("_"):
                    dist_path, size = build_template(env, src_path)
                    if size >= COMPR_THRESHOLD:
                        compress(dist_path)
            else:
                dist_path = os.path.join(dist_root, src_name)
                _ = shutil.copy(src_path, dist_path)
                if os.path.getsize(dist_path) >= COMPR_THRESHOLD:
                    m = mime.from_file(dist_path)
                    if any(m.startswith(prefix) for prefix in COMPR_MIME_PREFIXES):
                        compress(dist_path)


if __name__ == "__main__":
    main()
