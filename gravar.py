import tkinter as tk
from tkinter import ttk
import subprocess
import datetime
import signal
import re

processo = None

def listar_dispositivos():
    """Lista fontes de áudio disponíveis (pactl)."""
    try:
        saida = subprocess.check_output(["pactl", "list", "short", "sources"]).decode()
        dispositivos = []
        for linha in saida.strip().split("\n"):
            partes = linha.split("\t")
            if len(partes) > 1:
                dispositivos.append(partes[1])
        return dispositivos
    except Exception as e:
        print("Erro ao listar dispositivos:", e)
        return ["default"]

def iniciar_gravacao():
    global processo
    dispositivo = combo.get()
    nome_arquivo = f"gravacao_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp3"

    comando = [
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", dispositivo,
        "-ac", "2",       # estéreo
        "-ar", "44100",   # qualidade padrão
        "-b:a", "192k",   # bitrate bom
        nome_arquivo
    ]

    processo = subprocess.Popen(comando)
    status_label.config(text=f"🎙 Gravando: {nome_arquivo}")

def parar_gravacao():
    global processo
    if processo:
        processo.send_signal(signal.SIGINT)  # envia Ctrl+C pro ffmpeg
        processo = None
        status_label.config(text="⏹ Gravação parada.")

# UI
root = tk.Tk()
root.title("Gravador de Áudio Linux")

# Lista dispositivos no dropdown
dispositivos = listar_dispositivos()

tk.Label(root, text="Selecione o dispositivo:").pack(pady=5)
combo = ttk.Combobox(root, values=dispositivos, width=60)
combo.pack(pady=5)
combo.set(dispositivos[0])  # seleciona o primeiro por padrão

tk.Button(root, text="▶ Iniciar Gravação", command=iniciar_gravacao, width=25).pack(pady=10)
tk.Button(root, text="⏹ Parar Gravação", command=parar_gravacao, width=25).pack(pady=10)

status_label = tk.Label(root, text="Aguardando...")
status_label.pack(pady=10)

root.mainloop()
