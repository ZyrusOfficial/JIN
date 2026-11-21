#!/usr/bin/env python3
"""Local HTTP server for JARVIS UI live preview.

Serves the ui/jarvis directory so the glassmorphism interface can be viewed
in a browser during development. Bind to 0.0.0.0 for Arena live preview.
"""
import http.server
import socketserver
import os
import sys

PORT = 8765
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def main():
    os.chdir(UI_DIR)
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        sa = httpd.server_address
        print(f"JARVIS UI server running at http://{sa[0]}:{sa[1]}/")
        print(f"Serving directory: {UI_DIR}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
            httpd.server_close()


if __name__ == "__main__":
    main()
