import os
import sys
import argparse
import threading
import uuid
import requests
from flask import Flask, send_from_directory

# CLI + HTTP server in one
app = Flask(__name__)
args = None
peer_id = str(uuid.uuid4())

@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    # Serve file from shared folder (absolute path)
    return send_from_directory(args.share_folder_abs, filename, as_attachment=True)

def start_server():
    app.run(host='0.0.0.0', port=args.port)


def handshake():
    # Scan share folder (absolute)
    files = os.listdir(args.share_folder_abs)
    data = {'peer_id': peer_id, 'ip': args.host, 'port': args.port, 'files': files}
    r = requests.post(f"{args.orch}/handshake", json=data)
    r.raise_for_status()
    print(f"Handshake response: {r.json()}")


def cli_loop():
    while True:
        cmd = input('> ').strip().split()
        if not cmd:
            continue
        if cmd[0] == 'list':
            r = requests.get(f"{args.orch}/list")
            r.raise_for_status()
            data = r.json()
            for fname, peers in data.items():
                print(f"{fname}: {len(peers)} peers")
                for p in peers:
                    print(f"  - {p['peer_id']} @ {p['ip']}:{p['port']}")
        elif cmd[0] == 'download' and len(cmd) == 2:
            fname = cmd[1]
            r = requests.get(f"{args.orch}/list")
            data = r.json()
            if fname not in data:
                print('File not found in network')
                continue
            # pick first peer
            peer = data[fname][0]
            url = f"http://{peer['ip']}:{peer['port']}/download/{fname}"
            print(f"Downloading from {url}...")
            resp = requests.get(url)
            if resp.status_code == 200:
                path = os.path.join(args.download_folder_abs, fname)
                with open(path, 'wb') as f:
                    f.write(resp.content)
                print(f"Saved to {path}")
            else:
                print(f"Error: {resp.status_code}")
        elif cmd[0] in ('exit', 'quit'):
            print('Exiting...')
            os._exit(0)
        else:
            print('Commands: list, download <filename>, exit')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File Sharing Client')
    parser.add_argument('--orch', required=True, help='Orchestrator URL, e.g. http://localhost:5000')
    parser.add_argument('--host', default='127.0.0.1', help='Client host IP')
    parser.add_argument('--port', type=int, default=6000, help='Port for client file server')
    parser.add_argument('--share-folder', required=True, help='Folder to share')
    parser.add_argument('--download-folder', required=True, help='Folder to save downloads')
    args = parser.parse_args()

    # Resolve absolute paths for share and download folders
    args.share_folder_abs = os.path.abspath(args.share_folder)
    args.download_folder_abs = os.path.abspath(args.download_folder)

    # Validate folders
    os.makedirs(args.share_folder_abs, exist_ok=True)
    os.makedirs(args.download_folder_abs, exist_ok=True)

    # Register with orchestrator
    handshake()

    # Start HTTP server thread
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # CLI loop
    cli_loop()
