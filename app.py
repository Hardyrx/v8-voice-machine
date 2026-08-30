import streamlit as st
import requests
import datetime
import torch
import soundfile as sf
import tempfile
import os

# ── PAGE CONFIG ──
st.set_page_config(
    page_title="V8 Voice Machine",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Space+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #080808;
    color: #ccc;
}

.header {
    text-align: center;
    padding: 40px 0 32px;
    border-bottom: 1px solid #1a1a1a;
    margin-bottom: 32px;
}

.logo {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 3px;
    color: #333;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.titulo {
    font-size: 42px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -1px;
    line-height: 1.1;
}

.titulo span { color: #ff3c00; }

.sub {
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    color: #444;
    margin-top: 8px;
}

.card {
    background: #0e0e0e;
    border: 1px solid #1a1a1a;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}

.label {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: #444;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.status-ok {
    background: #0a0a0a;
    border-left: 3px solid #00ff88;
    padding: 14px 18px;
    border-radius: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    color: #888;
    margin: 8px 0;
}

.status-err {
    background: #0a0a0a;
    border-left: 3px solid #ff3c00;
    padding: 14px 18px;
    border-radius: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    color: #888;
    margin: 8px 0;
}

.stTextInput input, .stTextArea textarea {
    background: #111 !important;
    border: 1px solid #222 !important;
    border-radius: 8px !important;
    color: #ddd !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.stButton button {
    background: #ff3c00 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    padding: 10px 28px !important;
    width: 100%;
}

.stButton button:hover { opacity: 0.85 !important; }

.stSlider { color: #888 !important; }
.stTabs [data-baseweb="tab"] { color: #444; font-family: 'Space Grotesk', sans-serif; }
.stTabs [aria-selected="true"] { color: #ff3c00 !important; border-bottom: 2px solid #ff3c00 !important; }

footer { display: none !important; }
#MainMenu { visibility: hidden; }
header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── CONFIG ──
SHEET_ID   = "1bQaqMXb9Uuu6H5x9VdIvIjDrZNMQoAMw7iXPRkUZQCY"
SHEET_NAME = "licencas"

# ── HEADER ──
st.markdown("""
<div class="header">
    <div class="logo">Algoritmo Secreto</div>
    <div class="titulo">V8 <span>Voice</span> Machine</div>
    <div class="sub">estúdio de voz IA · clone qualquer voz · PT-BR</div>
</div>
""", unsafe_allow_html=True)

# ── FUNÇÕES ──
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
            return False, None, "Erro ao verificar licença."
        rows = parse_csv(resp.text)
        for row in rows:
            if row.get("chave","").upper() == chave:
                if row.get("ativo","").upper() != "TRUE":
                    return False, None, "Licença desativada."
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

@st.cache_resource
def carregar_modelo():
    from chatterbox.tts import ChatterboxTTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return ChatterboxTTS.from_pretrained(device=device)

# ── LICENÇA ──
st.markdown('<div class="label">Chave de acesso</div>', unsafe_allow_html=True)
chave = st.text_input("", placeholder="V8VM-XXXXXX", label_visibility="collapsed")

licenca_ok = False
dados_licenca = None

if chave:
    ok, dados, erro = validar_licenca(chave)
    if ok:
        nome  = dados.get("nome","Usuário")
        plano = dados.get("plano","BASICO").upper()
        exp   = dados.get("expira","ilimitado")
        st.markdown(f"""
        <div class="status-ok">
            ✅ <b style="color:#00ff88">ACESSO LIBERADO</b><br>
            👤 {nome} &nbsp;|&nbsp; 📦 {plano} &nbsp;|&nbsp; 📅 {exp}
        </div>
        """, unsafe_allow_html=True)
        licenca_ok = True
        dados_licenca = dados
    else:
        st.markdown(f'<div class="status-err">❌ {erro}</div>', unsafe_allow_html=True)

st.markdown("---")

# ── ABAS ──
tab1, tab2 = st.tabs(["🎙️ Narrador", "🧬 Clone de voz"])

# ── TAB 1: NARRADOR ──
with tab1:
    st.markdown('<div class="label">Roteiro</div>', unsafe_allow_html=True)
    roteiro = st.text_area("", placeholder="Cole aqui o roteiro do vídeo...", height=200, label_visibility="collapsed")
    expressividade = st.slider("Expressividade", 0.0, 1.0, 0.3, 0.05, help="0 = neutro · 1.0 = máxima expressividade")
    nome_arquivo = st.text_input("Nome do arquivo", value="narracao_01")

    if st.button("⚡ Gerar narração", key="btn_narrador"):
        if not licenca_ok:
            st.error("❌ Insira uma chave válida acima.")
        elif not roteiro.strip():
            st.warning("⚠️ Cole o roteiro acima.")
        else:
            with st.spinner("Carregando modelo de voz..."):
                model = carregar_modelo()
            with st.spinner("Gerando narração..."):
                try:
                    wav = model.generate(roteiro, exaggeration=expressividade, cfg_weight=0.5)
                    audio_np = wav.squeeze().numpy()
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    sf.write(tmp.name, audio_np, model.sr)
                    dur = len(audio_np) / model.sr
                    st.success(f"✅ Gerado! {dur/60:.1f} minutos")
                    st.audio(tmp.name, format="audio/wav")
                    with open(tmp.name, "rb") as f:
                        st.download_button("⬇️ Baixar áudio", f, file_name=f"{nome_arquivo}.wav", mime="audio/wav")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

# ── TAB 2: CLONE ──
with tab2:
    if licenca_ok and dados_licenca and dados_licenca.get("plano","").upper() not in ["PRO","FULL"]:
        st.warning("🔒 Clone de voz disponível apenas nos planos PRO e FULL.")
    else:
        st.markdown('<div class="label">Áudio de referência (10 a 60 segundos)</div>', unsafe_allow_html=True)
        audio_ref = st.file_uploader("", type=["wav","mp3","m4a"], label_visibility="collapsed")

        st.markdown('<div class="label">Roteiro</div>', unsafe_allow_html=True)
        roteiro_clone = st.text_area("", placeholder="Cole o texto que será narrado com a voz clonada...", height=180, key="roteiro_clone", label_visibility="collapsed")
        expr_clone = st.slider("Expressividade", 0.0, 1.0, 0.3, 0.05, key="expr_clone")
        nome_clone = st.text_input("Nome do arquivo", value="clone_01", key="nome_clone")

        if st.button("🧬 Clonar e gerar", key="btn_clone"):
            if not licenca_ok:
                st.error("❌ Insira uma chave válida acima.")
            elif audio_ref is None:
                st.warning("⚠️ Faça upload do áudio de referência.")
            elif not roteiro_clone.strip():
                st.warning("⚠️ Cole o roteiro.")
            else:
                tmp_ref = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp_ref.write(audio_ref.read())
                tmp_ref.close()
                with st.spinner("Carregando modelo..."):
                    model = carregar_modelo()
                with st.spinner("Clonando voz e gerando áudio..."):
                    try:
                        wav = model.generate(roteiro_clone, audio_prompt_path=tmp_ref.name, exaggeration=expr_clone, cfg_weight=0.5)
                        audio_np = wav.squeeze().numpy()
                        tmp_out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                        sf.write(tmp_out.name, audio_np, model.sr)
                        dur = len(audio_np) / model.sr
                        st.success(f"✅ Clone gerado! {dur/60:.1f} minutos")
                        st.audio(tmp_out.name, format="audio/wav")
                        with open(tmp_out.name, "rb") as f:
                            st.download_button("⬇️ Baixar áudio", f, file_name=f"{nome_clone}.wav", mime="audio/wav")
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")

# ── FOOTER ──
st.markdown("""
<div style="text-align:center;padding:32px 0 8px;border-top:1px solid #111;margin-top:32px">
    <div style="font-family:monospace;font-size:10px;color:#222;letter-spacing:2px">
        V8 VOICE MACHINE · ALGORITMO SECRETO · algoritmosecreto.com
    </div>
</div>
""", unsafe_allow_html=True)
