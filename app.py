import gradio as gr
import requests
import datetime
import io
import torch
import soundfile as sf
import numpy as np
import tempfile
import os

# ── CONFIG ──
SHEET_ID   = "1bQaqMXb9Uuu6H5x9VdIvIjDrZNMQoAMw7iXPRkUZQCY"
SHEET_NAME = "licencas"

# ── LICENÇA ──
def limpar(v):
    return str(v).strip().strip('"').strip("'").strip()

def parse_csv(texto):
    linhas = texto.strip().split("\n")
    sep = ";" if linhas[0].count(";") > linhas[0].count(",") else ","
    cabecalho = [limpar(c) for c in linhas[0].split(sep)]
    rows = []
    for linha in linhas[1:]:
        if not linha.strip():
            continue
        cols = [limpar(c) for c in linha.split(sep)]
        rows.append(dict(zip(cabecalho, cols)))
    return rows

def validar_licenca(chave_raw):
    chave = limpar(chave_raw).upper()
    if not chave or not chave.startswith("V8VM-"):
        return False, None, "Formato inválido. Use V8VM-XXXXXX"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return False, None, "Erro ao verificar licença. Tente novamente."
        rows = parse_csv(resp.text)
        for row in rows:
            if row.get("chave","").upper() == chave:
                if row.get("ativo","").upper() != "TRUE":
                    return False, None, "Licença desativada. Contate o suporte."
                exp = row.get("expira","")
                if exp and exp.lower() != "ilimitado":
                    try:
                        if datetime.date.today() > datetime.datetime.strptime(exp, "%Y-%m-%d").date():
                            return False, None, f"Licença expirada em {exp}."
                    except: pass
                usos = row.get("usos_restantes","ilimitado")
                if usos.lower() != "ilimitado":
                    try:
                        if int(usos) <= 0:
                            return False, None, "Usos esgotados."
                    except: pass
                return True, row, ""
        return False, None, "Chave não encontrada."
    except Exception as e:
        return False, None, f"Erro: {str(e)}"

# ── TTS ──
modelo_cache = {}

def carregar_chatterbox():
    if "chatterbox" not in modelo_cache:
        from chatterbox.tts import ChatterboxTTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        modelo_cache["chatterbox"] = ChatterboxTTS.from_pretrained(device=device)
    return modelo_cache["chatterbox"]

def gerar_narrador(chave, texto, expressividade):
    ok, dados, erro = validar_licenca(chave)
    if not ok:
        return None, f"❌ {erro}"
    if not texto.strip():
        return None, "⚠️ Cole o roteiro no campo acima."
    try:
        model = carregar_chatterbox()
        wav = model.generate(texto, exaggeration=float(expressividade), cfg_weight=0.5)
        audio_np = wav.squeeze().numpy()
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, audio_np, model.sr)
        dur = len(audio_np) / model.sr
        nome = dados.get("nome","Usuário")
        plano = dados.get("plano","BASICO")
        return tmp.name, f"✅ Gerado! {dur/60:.1f} min · {nome} · {plano}"
    except Exception as e:
        return None, f"❌ Erro: {str(e)}"

def gerar_clone(chave, texto, audio_ref, expressividade):
    ok, dados, erro = validar_licenca(chave)
    if not ok:
        return None, f"❌ {erro}"
    plano = dados.get("plano","BASICO").upper()
    if plano not in ["PRO","FULL"]:
        return None, "❌ Clone de voz disponível apenas nos planos PRO e FULL."
    if not texto.strip():
        return None, "⚠️ Cole o roteiro."
    if audio_ref is None:
        return None, "⚠️ Faça upload do áudio de referência."
    try:
        model = carregar_chatterbox()
        wav = model.generate(texto, audio_prompt_path=audio_ref, exaggeration=float(expressividade), cfg_weight=0.5)
        audio_np = wav.squeeze().numpy()
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, audio_np, model.sr)
        dur = len(audio_np) / model.sr
        return tmp.name, f"✅ Clone gerado! {dur/60:.1f} min"
    except Exception as e:
        return None, f"❌ Erro: {str(e)}"

# ── CSS ──
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Space+Mono&display=swap');

body, .gradio-container {
    background: #080808 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.gradio-container { max-width: 860px !important; margin: 0 auto !important; padding: 40px 24px !important; }

#header {
    text-align: center;
    padding: 48px 0 36px;
    border-bottom: 1px solid #1a1a1a;
    margin-bottom: 36px;
}

#logo {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 3px;
    color: #333;
    margin-bottom: 16px;
    text-transform: uppercase;
}

#titulo {
    font-size: 38px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -1px;
    line-height: 1.1;
}

#titulo span { color: #ff3c00; }

#sub {
    font-size: 14px;
    color: #444;
    margin-top: 10px;
    font-family: 'Space Mono', monospace;
}

.card {
    background: #0e0e0e;
    border: 1px solid #1a1a1a;
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 16px;
}

label { color: #666 !important; font-size: 11px !important; letter-spacing: 1px !important; text-transform: uppercase !important; font-family: 'Space Mono', monospace !important; }

input[type="text"], textarea {
    background: #111 !important;
    border: 1px solid #222 !important;
    border-radius: 8px !important;
    color: #ddd !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

input[type="text"]:focus, textarea:focus {
    border-color: #ff3c00 !important;
    outline: none !important;
    box-shadow: 0 0 0 2px #ff3c0015 !important;
}

button.primary {
    background: #ff3c00 !important;
    border: none !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.5px !important;
    padding: 12px 28px !important;
    transition: opacity 0.2s !important;
}

button.primary:hover { opacity: 0.85 !important; }

.status-box {
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    border-left: 3px solid #ff3c00;
    background: #0e0e0e;
    color: #888;
}

.tabs { border-bottom: 1px solid #1a1a1a !important; }
.tab-nav button { color: #444 !important; font-family: 'Space Grotesk', sans-serif !important; }
.tab-nav button.selected { color: #ff3c00 !important; border-bottom: 2px solid #ff3c00 !important; }

footer { display: none !important; }
"""

# ── INTERFACE ──
with gr.Blocks(css=CSS, title="V8 Voice Machine") as demo:

    gr.HTML("""
    <div id="header">
        <div id="logo">Algoritmo Secreto</div>
        <div id="titulo">V8 <span>Voice</span> Machine</div>
        <div id="sub">estúdio de voz IA · clone qualquer voz · PT-BR</div>
    </div>
    """)

    # Chave de acesso global
    with gr.Group(elem_classes="card"):
        gr.HTML('<div style="color:#555;font-size:11px;font-family:monospace;letter-spacing:1px;margin-bottom:12px">ACESSO</div>')
        chave_input = gr.Textbox(
            placeholder="V8VM-XXXXXX",
            label="Chave de licença",
            max_lines=1
        )

    with gr.Tabs():

        # ── TAB 1: NARRADOR ──
        with gr.Tab("🎙️ Narrador"):
            with gr.Group(elem_classes="card"):
                gr.HTML('<div style="color:#555;font-size:11px;font-family:monospace;letter-spacing:1px;margin-bottom:12px">ROTEIRO</div>')
                texto_narrador = gr.Textbox(
                    placeholder="Cole aqui o roteiro do vídeo...",
                    label="",
                    lines=8,
                    max_lines=50
                )
                expressividade_1 = gr.Slider(
                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                    label="Expressividade (0 = neutro · 1.0 = máxima)"
                )
                btn_narrador = gr.Button("⚡ Gerar narração", variant="primary")

            status_1 = gr.Textbox(label="Status", interactive=False, elem_classes="status-box")
            audio_out_1 = gr.Audio(label="Áudio gerado", type="filepath")

            btn_narrador.click(
                fn=gerar_narrador,
                inputs=[chave_input, texto_narrador, expressividade_1],
                outputs=[audio_out_1, status_1]
            )

        # ── TAB 2: CLONE ──
        with gr.Tab("🧬 Clone de voz"):
            with gr.Group(elem_classes="card"):
                gr.HTML('<div style="color:#555;font-size:11px;font-family:monospace;letter-spacing:1px;margin-bottom:12px">REFERÊNCIA · upload de 10 a 60 segundos</div>')
                audio_ref = gr.Audio(label="", type="filepath", sources=["upload"])

                gr.HTML('<div style="color:#555;font-size:11px;font-family:monospace;letter-spacing:1px;margin:16px 0 12px">ROTEIRO</div>')
                texto_clone = gr.Textbox(
                    placeholder="Cole aqui o texto que será narrado com a voz clonada...",
                    label="",
                    lines=6
                )
                expressividade_2 = gr.Slider(
                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                    label="Expressividade"
                )
                btn_clone = gr.Button("🧬 Clonar e gerar", variant="primary")

            gr.HTML('<div style="color:#333;font-size:11px;font-family:monospace;padding:8px 0">Disponível nos planos PRO e FULL</div>')
            status_2 = gr.Textbox(label="Status", interactive=False, elem_classes="status-box")
            audio_out_2 = gr.Audio(label="Áudio clonado", type="filepath")

            btn_clone.click(
                fn=gerar_clone,
                inputs=[chave_input, texto_clone, audio_ref, expressividade_2],
                outputs=[audio_out_2, status_2]
            )

    gr.HTML("""
    <div style="text-align:center;padding:32px 0 8px;border-top:1px solid #111;margin-top:24px">
        <div style="font-family:monospace;font-size:10px;color:#222;letter-spacing:2px">
            V8 VOICE MACHINE · ALGORITMO SECRETO · algoritmosecreto.com
        </div>
    </div>
    """)

demo.launch()
