import os
import sys
import argparse
import threading
import uuid
import requests
import signal
import tkinter as tk
from tkinter import messagebox, Listbox, Scrollbar, END
from flask import Flask, send_from_directory

app = Flask(__name__)
args = None
peer_id = str(uuid.uuid4())
file_list = []

@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    return send_from_directory(args.share_folder_abs, filename, as_attachment=True)

def start_server():
    app.run(host='0.0.0.0', port=args.port)

def handshake():
    files = os.listdir(args.share_folder_abs)
    data = {'peer_id': peer_id, 'ip': args.host, 'port': args.port, 'files': files}
    try:
        r = requests.post(f"{args.orch}/handshake", json=data)
        r.raise_for_status()
    except Exception as e:
        print(f"Handshake error: {e}")

def disconnect():
    try:
        r = requests.post(f"{args.orch}/disconnect", json={'peer_id': peer_id})
        if r.ok:
            print('Disconnected from orchestrator.')
    except Exception as e:
        print(f"Error disconnecting: {e}")

def handle_exit(signum=None, frame=None):
    print('\nExiting...')
    disconnect()
    os._exit(0)

def download_file(fname):
    try:
        r = requests.get(f"{args.orch}/list")
        r.raise_for_status()
        data = r.json()
        if fname not in data:
            messagebox.showerror("Erro", f"Arquivo {fname} não encontrado na rede.")
            return
        peer = data[fname][0]
        url = f"http://{peer['ip']}:{peer['port']}/download/{fname}"
        resp = requests.get(url)
        if resp.status_code == 200:
            path = os.path.join(args.download_folder_abs, fname)
            with open(path, 'wb') as f:
                f.write(resp.content)
            # Move to shared folder se necessário
            if args.download_folder_abs != args.share_folder_abs:
                os.replace(path, os.path.join(args.share_folder_abs, fname))
            handshake()
            messagebox.showinfo("Sucesso", f"Arquivo {fname} baixado com sucesso.")
        else:
            messagebox.showerror("Erro", f"Erro ao baixar {fname}: {resp.status_code}")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def update_file_list(lb):
    global file_list
    try:
        r = requests.get(f"{args.orch}/list")
        r.raise_for_status()
        data = r.json()
        file_list = sorted(data.keys())
        lb.delete(0, END)
        for f in file_list:
            lb.insert(END, f)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao atualizar lista: {e}")

def create_gui():
    root = tk.Tk()
    root.title("Compartilhamento de Arquivos")
    root.geometry("400x400")

    scrollbar = Scrollbar(root)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    lb = Listbox(root, yscrollcommand=scrollbar.set)
    lb.pack(expand=True, fill=tk.BOTH)

    scrollbar.config(command=lb.yview)

    def on_double_click(event):
        widget = event.widget
        index = widget.curselection()
        if index:
            fname = widget.get(index[0])
            download_file(fname)

    lb.bind("<Double-1>", on_double_click)

    btn = tk.Button(root, text="Atualizar", command=lambda: update_file_list(lb))
    btn.pack(fill=tk.X)

    update_file_list(lb)
    root.protocol("WM_DELETE_WINDOW", handle_exit)
    root.mainloop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File Sharing Client')
    parser.add_argument('--orch', required=True, help='Orchestrator URL, e.g. http://localhost:5000')
    parser.add_argument('--host', default='127.0.0.1', help='Client host IP')
    parser.add_argument('--port', type=int, default=6000, help='Port for client file server')
    parser.add_argument('--share-folder', required=True, help='Folder to share')
    parser.add_argument('--download-folder', required=True, help='Folder to save downloads')
    args = parser.parse_args()

    args.share_folder_abs = os.path.abspath(args.share_folder)
    args.download_folder_abs = os.path.abspath(args.download_folder)

    os.makedirs(args.share_folder_abs, exist_ok=True)
    os.makedirs(args.download_folder_abs, exist_ok=True)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    handshake()

    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    create_gui()