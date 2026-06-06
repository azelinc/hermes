#!/usr/bin/env python3
"""Tiny HTTP forward proxy for Termux on Android phone.
Run: python3 homeproxy.py
Then access via: curl -x http://localhost:8080 http://example.com
"""

import http.server
import urllib.request
import sys
import os
import json
import signal

PORT = int(os.environ.get('PROXY_PORT', '8080'))
PID_FILE = '/data/data/com.termux/files/home/.homeproxy.pid'

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._proxy()
    def do_POST(self):
        self._proxy()
    def do_CONNECT(self):
        # HTTPS CONNECT tunneling
        try:
            host, port = self.path.split(':')
            port = int(port)
        except:
            self.send_error(400)
            return
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            self.send_response(200, 'Connection Established')
            self.end_headers()
            # In production: bidirectional copy
            # For HTTPS, we'd need to relay raw bytes
            s.close()
        except Exception as e:
            self.send_error(502, str(e))

    def _proxy(self):
        url = self.path
        try:
            headers = {}
            for k, v in self.headers.items():
                if k.lower() not in ('host', 'proxy-connection', 'proxy-authorization'):
                    headers[k] = v
            req = urllib.request.Request(url, data=self._body(), headers=headers)
            # Remove accept-encoding so we get raw content
            req.add_header('Accept-Encoding', 'identity')
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ('transfer-encoding', 'content-encoding'):
                        self.send_header(k, v)
                # Fix content-length
                body = resp.read()
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, str(e)[:200])

    def _body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length) if length > 0 else None

    def log_message(self, format, *args):
        print(f"[proxy] {self.client_address[0]} - {format % args}")

if __name__ == '__main__':
    server = http.server.HTTPServer(('127.0.0.1', PORT), ProxyHandler)
    print(f"HOMEPROXY running on 127.0.0.1:{PORT}")
    print(f"Ready to serve as HTTP proxy")
    # Save PID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.shutdown()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
