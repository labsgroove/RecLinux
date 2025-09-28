import tkinter as tk
from tkinter import ttk
import subprocess
import datetime
import signal
import re
import threading
import time

processo = None
gravacao_playlist_ativa = False
thread_playlist = None

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

def iniciar_gravacao(nome_arquivo=None):
    """Inicia uma gravação com ffmpeg."""
    global processo
    parar_gravacao()  # Garante que qualquer gravação anterior seja parada

    dispositivo = combo.get()
    
    if nome_arquivo is None:
        nome_musica = get_spotify_track_name()
        if nome_musica:
            nome_arquivo = f"{nome_musica}.mp3"
        else:
            nome_arquivo = f"gravacao_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp3"

    comando = [
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", dispositivo,
        "-ac", "2",
        "-ar", "44100",
        "-b:a", "192k",
        nome_arquivo
    ]

    try:
        processo = subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status_label.config(text=f"🎙 Gravando: {nome_arquivo}")
    except Exception as e:
        status_label.config(text=f"Erro ao iniciar ffmpeg: {e}")


def parar_gravacao():
    """Para a gravação ffmpeg se estiver em execução."""
    global processo
    if processo and processo.poll() is None:
        processo.send_signal(signal.SIGINT)
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()
        status_label.config(text="⏹ Gravação parada.")
    processo = None


def get_spotify_track_name():
    """Captura o nome da música e artista do Spotify."""
    try:
        saida = subprocess.check_output(
            ["playerctl", "metadata", "--format", "{{artist}} - {{title}}"]
        ).decode().strip()
        if saida:
            return re.sub(r'[\\/*?:"<>|]', "", saida)
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def monitorar_playlist():
    """Monitora o playerctl para mudanças de faixa e gerencia as gravações."""
    global gravacao_playlist_ativa
    
    ultimo_nome_musica = None
    
    # Inicia o processo de monitoramento
    monitor_process = subprocess.Popen(
        ["playerctl", "--follow", "metadata", "--format", "{{artist}} - {{title}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    while gravacao_playlist_ativa:
        linha = monitor_process.stdout.readline().strip()
        
        if not gravacao_playlist_ativa:
            break

        if linha:
            nome_musica_atual = re.sub(r'[\\/*?:"<>|]', "", linha)
            if nome_musica_atual != ultimo_nome_musica:
                parar_gravacao()
                time.sleep(1) # Pequena pausa para garantir que tudo foi finalizado
                iniciar_gravacao(f"{nome_musica_atual}.mp3")
                ultimo_nome_musica = nome_musica_atual
        else:
            # Se a linha estiver vazia, o player pode ter sido fechado
            time.sleep(1)

    # Finaliza o processo de monitoramento e a última gravação
    monitor_process.terminate()
    parar_gravacao()
    status_label.config(text="⏹ Gravação da playlist parada.")


def iniciar_gravacao_playlist():
    """Inicia a thread de monitoramento da playlist."""
    global gravacao_playlist_ativa, thread_playlist
    if not gravacao_playlist_ativa:
        gravacao_playlist_ativa = True
        thread_playlist = threading.Thread(target=monitorar_playlist)
        thread_playlist.start()
        status_label.config(text="▶️ Iniciando gravação da playlist...")
        # Desabilita/habilita botões
        btn_iniciar_playlist.config(state=tk.DISABLED)
        btn_parar_playlist.config(state=tk.NORMAL)
        btn_iniciar.config(state=tk.DISABLED)
        btn_parar.config(state=tk.DISABLED)

def parar_gravacao_playlist():
    """Para a thread de monitoramento da playlist."""
    global gravacao_playlist_ativa
    if gravacao_playlist_ativa:
        gravacao_playlist_ativa = False
        if thread_playlist:
            thread_playlist.join(timeout=2)
        parar_gravacao()
        status_label.config(text="⏹ Gravação da playlist parada.")
        # Reabilita/desabilita botões
        btn_iniciar_playlist.config(state=tk.NORMAL)
        btn_parar_playlist.config(state=tk.DISABLED)
        btn_iniciar.config(state=tk.NORMAL)
        btn_parar.config(state=tk.NORMAL)

# --- UI ---
root = tk.Tk()
root.title("Gravador de Áudio Linux")

# Frame para os controles principais
main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10)

tk.Label(main_frame, text="Selecione o dispositivo de áudio:").pack(pady=5)
dispositivos = listar_dispositivos()
combo = ttk.Combobox(main_frame, values=dispositivos, width=60)
if dispositivos:
    combo.set(dispositivos[0])
combo.pack(pady=5, padx=5)

# Frame para botões de gravação manual
manual_frame = tk.LabelFrame(main_frame, text="Gravação Manual")
manual_frame.pack(pady=10, padx=10, fill="x")

btn_iniciar = tk.Button(manual_frame, text="▶ Iniciar Gravação", command=lambda: iniciar_gravacao(), width=25)
btn_iniciar.pack(pady=5)
btn_parar = tk.Button(manual_frame, text="⏹ Parar Gravação", command=parar_gravacao, width=25)
btn_parar.pack(pady=5)

# Frame para botões de gravação de playlist
playlist_frame = tk.LabelFrame(main_frame, text="Gravação de Playlist (Automático)")
playlist_frame.pack(pady=10, padx=10, fill="x")

btn_iniciar_playlist = tk.Button(playlist_frame, text="▶️ Gravar Playlist", command=iniciar_gravacao_playlist, width=25)
btn_iniciar_playlist.pack(pady=5)
btn_parar_playlist = tk.Button(playlist_frame, text="⏹ Parar Playlist", command=parar_gravacao_playlist, width=25, state=tk.DISABLED)
btn_parar_playlist.pack(pady=5)

status_label = tk.Label(root, text="Aguardando...", relief=tk.SUNKEN, width=50)
status_label.pack(pady=10, padx=10, fill="x")

def on_closing():
    """Garante que tudo seja finalizado ao fechar a janela."""
    parar_gravacao_playlist()
    parar_gravacao()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
