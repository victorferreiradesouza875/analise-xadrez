"""
Interface gráfica (Streamlit) para o analisador de xadrez.

Instalação:
    pip install streamlit chess

Uso (na mesma pasta do analisador_xadrez.py):
    streamlit run app_xadrez.py
"""

import io
import shutil

import chess
import chess.pgn
import chess.svg
import streamlit as st

from analisador_xadrez import (
    SIMBOLOS, analisar_com_engine, estatisticas_basicas, formatar_aval, precisao,
)

CORES = {"melhor": "#2e9e5b", "bom": "#7fb069", "imprecisão": "#e6b800",
         "erro": "#e67e22", "blunder": "#d64545"}

st.set_page_config(page_title="Analisador de Xadrez", page_icon="♟️", layout="wide")
st.title("♟️ Analisador de Xadrez")


# ------------------------------------------------------------------ helpers (sem pandas/numpy)
def tabela_md(cabecalho, linhas):
    """Tabela em markdown puro (evita st.table/st.dataframe, que exigem pandas)."""
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    out += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(out)


def grafico_svg(avals, ply, largura=420, altura=150):
    """Gráfico da avaliação em SVG puro, limitado a +-5 peões."""
    n = len(avals)
    meio = altura / 2
    pts = []
    for i, cp in enumerate(avals):
        x = 8 + (largura - 16) * (i / max(1, n - 1))
        y = meio - max(-5.0, min(5.0, cp / 100)) / 5 * (meio - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    marcador = ""
    if ply > 0:
        mx = 8 + (largura - 16) * ((ply - 1) / max(1, n - 1))
        marcador = (f'<line x1="{mx:.1f}" y1="0" x2="{mx:.1f}" y2="{altura}" '
                    f'stroke="#d64545" stroke-width="1.5"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
            f'viewBox="0 0 {largura} {altura}">'
            f'<line x1="0" y1="{meio}" x2="{largura}" y2="{meio}" stroke="#999" '
            f'stroke-dasharray="4"/>{marcador}'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="#4a90d9" stroke-width="2"/>'
            f'</svg>')


# ------------------------------------------------------------------ entrada
def ler_partidas(texto: str):
    flujo = io.StringIO(texto)
    partidas = []
    while (g := chess.pgn.read_game(flujo)) is not None:
        partidas.append(g)
    return partidas


with st.sidebar:
    st.header("Partida")
    arquivo = st.file_uploader("Arquivo PGN", type=["pgn", "txt"])
    colado = st.text_area("...ou cole o PGN aqui", height=120)
    st.header("Engine")
    caminho = st.text_input("Caminho do Stockfish", value=shutil.which("stockfish") or "")
    profundidade = st.slider("Profundidade", 8, 22, 14)
    virar = st.checkbox("Ver do lado das pretas")

texto = arquivo.getvalue().decode("utf-8", errors="replace") if arquivo else colado
if not texto.strip():
    st.info("Envie ou cole um PGN na barra lateral (Lichess e Chess.com permitem exportar).")
    st.stop()

partidas = ler_partidas(texto)
if not partidas:
    st.error("Não consegui ler nenhuma partida desse PGN.")
    st.stop()

rotulos = [f"{i + 1}. {g.headers.get('White', '?')} vs {g.headers.get('Black', '?')} "
           f"({g.headers.get('Date', '?')})" for i, g in enumerate(partidas)]
idx = rotulos.index(st.sidebar.selectbox("Partida", rotulos)) if len(partidas) > 1 else 0
jogo = partidas[idx]
chave = f"{hash(texto)}-{idx}"

lances = list(jogo.mainline_moves())
h = jogo.headers
st.subheader(f"{h.get('White', '?')} ({h.get('WhiteElo', '?')}) vs "
             f"{h.get('Black', '?')} ({h.get('BlackElo', '?')}) — {h.get('Result', '*')}")

# ------------------------------------------------------------------ análise
analises = st.session_state.setdefault("analises", {})
if st.sidebar.button("Analisar com Stockfish", type="primary"):
    if not caminho:
        st.sidebar.error("Informe o caminho do Stockfish.")
    else:
        barra = st.sidebar.progress(0.0, text="Analisando...")
        try:
            analises[chave] = analisar_com_engine(
                jogo, caminho, profundidade,
                progresso=lambda i, n: barra.progress(i / n, text=f"Lance {i}/{n}"),
            )
        except Exception as e:  # engine não encontrada, PGN inválido etc.
            st.sidebar.error(f"Erro na análise: {e}")
        barra.empty()

res = analises.get(chave)

# ------------------------------------------------------------------ navegação
ply = st.session_state.get("ply", {}).get(chave, 0)


def ir(novo):
    st.session_state.setdefault("ply", {})[chave] = max(0, min(len(lances), novo))


c1, c2, c3, c4, _ = st.columns([1, 1, 1, 1, 6])
c1.button("⏮", on_click=ir, args=(0,), use_container_width=True)
c2.button("◀", on_click=ir, args=(ply - 1,), use_container_width=True)
c3.button("▶", on_click=ir, args=(ply + 1,), use_container_width=True)
c4.button("⏭", on_click=ir, args=(len(lances),), use_container_width=True)

# monta a posição atual
board = jogo.board()
san_atual = ""
for m in lances[:ply]:
    san_atual = board.san(m)
    board.push(m)
ultimo = lances[ply - 1] if ply > 0 else None

setas = []
if res and ply > 0:
    r = res[ply - 1]
    if r["classe"] in ("imprecisão", "erro", "blunder") and r["melhor_uci"]:
        mm = chess.Move.from_uci(r["melhor_uci"])
        setas.append(chess.svg.Arrow(mm.from_square, mm.to_square, color="#2e9e5b"))

col_tab, col_info = st.columns([3, 2])
with col_tab:
    st.image(chess.svg.board(board, lastmove=ultimo, arrows=setas, size=520,
                             flipped=virar,
                             orientation=chess.BLACK if virar else chess.WHITE))
    st.slider("Lance", 0, len(lances), ply, key=f"slider-{chave}",
              on_change=lambda: ir(st.session_state[f"slider-{chave}"]))

with col_info:
    if ply == 0:
        st.markdown("**Posição inicial**")
    else:
        num = (ply + 1) // 2
        prefixo = f"{num}." if ply % 2 == 1 else f"{num}..."
        if res:
            r = res[ply - 1]
            st.markdown(
                f"### {prefixo} {r['san']}{SIMBOLOS[r['classe']].strip()}\n"
                f"<span style='color:{CORES[r['classe']]};font-weight:700'>"
                f"{r['classe'].upper()}</span> &nbsp; avaliação "
                f"**{formatar_aval(r['aval'])}**", unsafe_allow_html=True)
            if r["classe"] in ("imprecisão", "erro", "blunder"):
                st.write(f"Melhor era **{r['melhor']}** (seta verde no tabuleiro).")
        else:
            st.markdown(f"### {prefixo} {san_atual}")
            st.caption("Clique em *Analisar com Stockfish* para ver avaliação e classificação.")

    if res:
        st.markdown("**Precisão**")
        a, b = st.columns(2)
        for col, cor, nome in [(a, True, "Brancas"), (b, False, "Pretas")]:
            perdas = [x["perda"] for x in res if x["cor"] == cor]
            col.metric(nome, f"{precisao(sum(perdas) / len(perdas)):.1f}%" if perdas else "-")

        st.markdown("**Avaliação ao longo da partida** (+ = brancas melhor)")
        st.image(grafico_svg([x["aval"] for x in res], ply))

        contagem = {c: [0, 0] for c in CORES}
        for x in res:
            contagem[x["classe"]][0 if x["cor"] else 1] += 1
        st.markdown(tabela_md(["Classe", "Brancas", "Pretas"],
                              [[c, v[0], v[1]] for c, v in contagem.items()]))

# ------------------------------------------------------------------ lista de lances
with st.expander("Lista de lances e estatísticas"):
    if res:
        st.markdown(tabela_md(
            ["#", "Lance", "Aval", "Classe", "Melhor era"],
            [[(f"{x['num']}." if x["cor"] else f"{x['num']}..."), x["san"],
              formatar_aval(x["aval"]), x["classe"],
              "" if x["classe"] in ("melhor", "bom") else x["melhor"]] for x in res]))
    dados = estatisticas_basicas(jogo)
    st.markdown(tabela_md(
        ["", "Brancas", "Pretas"],
        [[k, dados["stats"][True][k], dados["stats"][False][k]] for k in dados["stats"][True]]))
