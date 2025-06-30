from flask import Flask, request, jsonify
from collections import defaultdict

app = Flask(__name__)
# Mapping: peer_id -> {'ip': ip, 'port': port, 'files': [filenames]}
peers = {}
# Inverse index: filename -> set of peer_ids
file_index = defaultdict(set)

@app.route('/handshake', methods=['POST'])
def handshake():
    data = request.get_json()
    peer_id = data.get('peer_id')
    ip = data.get('ip')
    port = data.get('port')
    files = data.get('files', [])
    if not peer_id or not ip or not port:
        return jsonify({'error': 'peer_id, ip, and port required'}), 400

    # Register or update peer
    # Remove old files
    old = peers.get(peer_id, {})
    for f in old.get('files', []):
        file_index[f].discard(peer_id)
    
    peers[peer_id] = {'ip': ip, 'port': port, 'files': files}
    for f in files:
        file_index[f].add(peer_id)

    return jsonify({'status': 'registered', 'peer_count': len(peers)})

@app.route('/list', methods=['GET'])
def list_files():
    result = {}
    for fname, peer_ids in file_index.items():
        result[fname] = [ {'peer_id': pid, 'ip': peers[pid]['ip'], 'port': peers[pid]['port']} for pid in peer_ids ]
    return jsonify(result)

@app.route('/peers', methods=['GET'])
def list_peers():
    return jsonify(peers)

@app.route('/disconnect', methods=['POST'])
def disconnect():
    data = request.get_json()
    peer_id = data.get('peer_id')
    if not peer_id or peer_id not in peers:
        return jsonify({'error': 'peer_id inválido'}), 400

    # Remover arquivos indexados
    for f in peers[peer_id]['files']:
        file_index[f].discard(peer_id)
        if not file_index[f]:
            del file_index[f]

    # Remover peer
    del peers[peer_id]
    return jsonify({'status': 'disconnected'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)