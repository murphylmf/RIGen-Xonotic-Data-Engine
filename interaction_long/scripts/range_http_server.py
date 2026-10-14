                      
"""Small static review server with single-range byte request support."""

from __future__ import annotations

import argparse
import functools
import os
import re
import shutil
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class RangeRequestHandler(SimpleHTTPRequestHandler):
    range_to_copy: tuple[int, int] | None = None

    def send_head(self):                                
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self.range_to_copy = None
            return super().send_head()
        try:
            source = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        stat = os.fstat(source.fileno())
        size = stat.st_size
        range_header = self.headers.get("Range")
        selected: tuple[int, int] | None = None
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                source.close()
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return None
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            elif last:
                suffix = min(int(last), size)
                start, end = size - suffix, size - 1
            else:
                source.close()
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return None
            if start >= size or end < start:
                source.close()
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return None
            selected = (start, end)

        self.range_to_copy = selected
        self.send_response(HTTPStatus.PARTIAL_CONTENT if selected else HTTPStatus.OK)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        if selected:
            start, end = selected
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
        else:
            self.send_header("Content-Length", str(size))
        self.end_headers()
        return source

    def copyfile(self, source, outputfile):                                
        if self.range_to_copy is None:
            shutil.copyfileobj(source, outputfile)
            return
        start, end = self.range_to_copy
        source.seek(start)
        remaining = end - start + 1
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    handler = functools.partial(RangeRequestHandler, directory=args.directory)
    with ThreadingHTTPServer((args.bind, args.port), handler) as server:
        print(f"Serving {args.directory} on {args.bind}:{args.port} with byte ranges", flush=True)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
