#!/usr/bin/env python3
"""
Minimal local web frontend for Lambda-Script Diff Spring.

Uses only the Python standard library.
Serves a single HTML page with:
- Textarea for LS_JSON_PATCH_V1 JSON
- Submit button
- Output panel showing absorb-and-ship results

Launch with:
    python scripts/web/patch_chat.py
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def get_repo_root():
    try:
        root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
        # MSYS2 path conversion
        try:
            converted = subprocess.check_output(['cygpath', '-w', root], text=True).strip()
            root = converted
        except Exception:
            pass
        return root
    except Exception:
        print("Error: Not inside a git repository.")
        sys.exit(1)


HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lambda-Script Patch Chat</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 40px; background: #f8f9fa; }
        h1 { color: #222; }
        textarea { width: 100%; height: 280px; font-family: monospace; font-size: 14px; padding: 12px; box-sizing: border-box; }
        button { padding: 12px 24px; font-size: 16px; background: #0066cc; color: white; border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background: #0055aa; }
        #output { white-space: pre-wrap; background: #fff; padding: 16px; border: 1px solid #ddd; min-height: 200px; font-family: monospace; margin-top: 20px; }
        .log { color: #444; }
    </style>
</head>
<body>
    <h1>Lambda-Script Patch Chat</h1>
    <p>Paste a valid <code>LS_JSON_PATCH_V1</code> JSON below, then click Submit.</p>
    
    <form id="patchForm">
        <textarea id="jsonInput" placeholder="Paste LS_JSON_PATCH_V1 JSON here..." required></textarea>
        <br><br>
        <button type="submit">Submit Patch</button>
    </form>
    
    <h3>Output / Log</h3>
    <div id="output" class="log">Ready. Submit a patch to see results here.</div>

    <script>
        const form = document.getElementById('patchForm');
        const output = document.getElementById('output');
        const jsonInput = document.getElementById('jsonInput');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            output.textContent = 'Submitting...';
            
            const response = await fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ json: jsonInput.value })
            });
            
            const result = await response.json();
            output.textContent = result.output || result.error || 'No output';
        });
    </script>
</body>
</html>
'''


class PatchChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != '/submit':
            self.send_error(404)
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data)
            json_str = data.get('json', '').strip()

            if not json_str:
                self._send_json({'error': 'No JSON provided'})
                return

            # Parse and validate
            try:
                patch = json.loads(json_str)
            except json.JSONDecodeError as e:
                self._send_json({'error': f'Invalid JSON: {e}'})
                return

            if not isinstance(patch, dict) or patch.get('format') != 'LS_JSON_PATCH_V1':
                self._send_json({'error': 'Not a valid LS_JSON_PATCH_V1 patch'})
                return

            # Check drop folder
            drop_dir = Path('spring/diff/drop')
            drop_dir.mkdir(parents=True, exist_ok=True)

            if any(drop_dir.glob('*.json')):
                self._send_json({'error': 'spring/diff/drop already contains a .json file. Absorb or clear first.'})
                return

            # Save patch
            timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
            filename = f'web-patch-{timestamp}.json'
            filepath = drop_dir / filename
            filepath.write_text(json_str, encoding='utf-8')

            # Run absorber
            result = subprocess.run(
                ['bash', 'scripts/diff_spring/absorb-and-ship.sh'],
                capture_output=True, text=True, check=False
            )

            output = result.stdout + result.stderr
            if result.returncode == 0:
                self._send_json({'output': f'✅ Patch absorbed successfully!\n\n{output}'})
            else:
                self._send_json({'output': f'❌ Absorption failed (code {result.returncode})\n\n{output}'})

        except Exception as e:
            self._send_json({'error': str(e)})

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))


if __name__ == '__main__':
    root = get_repo_root()
    os.chdir(root)

    port = 8765
    print(f"Starting Lambda-Script Patch Chat on http://localhost:{port}")
    print("Press Ctrl+C to stop.")

    server = HTTPServer(('', port), PatchChatHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
