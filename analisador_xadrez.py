#!/usr/bin/env python3
"""
Analisador de partidas de xadrez
--------------------------------
Lê um arquivo PGN (Lichess / Chess.com) e mostra:
  - resumo da partida e estatísticas básicas (sem precisar de engine)
  - análise lance a lance com Stockfish (opcional): avaliação, perda,
    classificação (melhor / bom / imprecisão / erro / blunder) e precisão

Instalação:
    pip install chess
    # Stockfish: https://stockfishchess.org/download/  (ou: sudo apt install stockfish)

Uso:
    python analisador_xadrez.py partida.pgn
    python analisador_xadrez.py partida.pgn --stockfish /caminho/stockfish --depth 16
    python analisador_xadrez.py partidas.pgn --jogo 3
"""

import argparse
import math
import shutil
import sys

import chess
import chess.engine
import chess.pgn

CLASSES = ["melhor", "bom", "imprecisão", "erro", "blunder"]
SIMBOLOS = {"melhor": "★", "bom": " ", "imprecisão": "?!", "erro": "?", "blunder": "??"}
VALORES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


# ----------------------------------------------------------------- utilidades
def win_percent(cp: float) -> float:
    """Converte centipeões em chance de vitória (0-100), fórmula do Lichess."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def precisao(perda_media_wp: float) -> float:
    """Aproximação da precisão do Lichess a partir da perda média de win%."""
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * perda_media_wp) - 3.1669))


def classificar(perda_wp: float, foi_melhor: bool) -> str:
    if foi_melhor or perda_wp < 2:
        return "melhor"
    if perda_wp < 5:
        return "bom"
    if perda_wp < 10:
        return "imprecisão"
    if perda_wp < 20:
        return "erro"
    return "blunder"


def formatar_aval(cp: int) -> str:
    if abs(cp) >= 9000:
        return f"M{'+' if cp > 0 else '-'}"
    return f"{cp / 100:+.2f}"


def material(board: chess.Board, cor: bool) -> int:
    return sum(len(board.pieces(p, cor)) * v for p, v in VALORES.items())


def carregar_partida(caminho: str, indice: int) -> chess.pgn.Game:
    with open(caminho, encoding="utf-8", errors="replace") as f:
        jogo = None
        for _ in range(indice):
            jogo = chess.pgn.read_game(f)
            if jogo is None:
                sys.exit(f"O arquivo não tem a partida número {indice}.")
    return jogo


# ----------------------------------------------------------------- estatísticas
def estatisticas_basicas(jogo: chess.pgn.Game) -> dict:
    board = jogo.board()
    stats = {
        True: {"lances": 0, "capturas": 0, "xeques": 0, "roque": None, "promocoes": 0},
        False: {"lances": 0, "capturas": 0, "xeques": 0, "roque": None, "promocoes": 0},
    }
    for lance in jogo.mainline_moves():
        cor = board.turn
        s = stats[cor]
        s["lances"] += 1
        if board.is_capture(lance):
            s["capturas"] += 1
        if lance.promotion:
            s["promocoes"] += 1
        if board.is_castling(lance) and s["roque"] is None:
            s["roque"] = board.fullmove_number
        board.push(lance)
        if board.is_check():
            s["xeques"] += 1
    return {"stats": stats, "final": board}


def mostrar_resumo(jogo: chess.pgn.Game, dados: dict) -> None:
    h = jogo.headers
    print("=" * 62)
    print(f"{h.get('White', '?')} ({h.get('WhiteElo', '?')})  vs  "
          f"{h.get('Black', '?')} ({h.get('BlackElo', '?')})")
    print(f"Resultado: {h.get('Result', '*')}   Data: {h.get('Date', '?')}   "
          f"Controle: {h.get('TimeControl', '?')}")
    if h.get("Opening") or h.get("ECO"):
        print(f"Abertura: {h.get('ECO', '')} {h.get('Opening', '')}".strip())
    print("=" * 62)

    final = dados["final"]
    print(f"{'':14}{'Brancas':>10}{'Pretas':>10}")
    for rotulo, chave in [("Lances", "lances"), ("Capturas", "capturas"),
                          ("Xeques", "xeques"), ("Promoções", "promocoes")]:
        print(f"{rotulo:14}{dados['stats'][True][chave]:>10}{dados['stats'][False][chave]:>10}")
    rb = dados["stats"][True]["roque"] or "-"
    rp = dados["stats"][False]["roque"] or "-"
    print(f"{'Roque (lance)':14}{rb!s:>10}{rp!s:>10}")
    print(f"{'Material final':14}{material(final, True):>10}{material(final, False):>10}")
    print()


# ----------------------------------------------------------------- engine
def analisar_com_engine(jogo, caminho_engine, profundidade, progresso=None):
    engine = chess.engine.SimpleEngine.popen_uci(caminho_engine)
    limite = chess.engine.Limit(depth=profundidade)
    board = jogo.board()
    lances = list(jogo.mainline_moves())

    avals, melhores = [], []  # avaliação (ponto de vista das brancas) e melhor lance por posição

    def avaliar(b):
        info = engine.analyse(b, limite)
        cp = info["score"].white().score(mate_score=10000)
        pv = info.get("pv")
        return cp, (pv[0] if pv else None)

    try:
        cp, melhor = avaliar(board)
        avals.append(cp)
        melhores.append(melhor)
        resultados = []
        total = len(lances)
        for i, lance in enumerate(lances, 1):
            if progresso:
                progresso(i, total)
            else:
                print(f"\rAnalisando lance {i}/{total}...", end="", file=sys.stderr, flush=True)
            cor = board.turn
            san = board.san(lance)
            numero = board.fullmove_number
            melhor_antes = melhores[-1]
            san_melhor = board.san(melhor_antes) if melhor_antes else "-"
            aval_antes = avals[-1]

            board.push(lance)
            if board.is_game_over():
                if board.is_checkmate():
                    aval_dep = 10000 if cor == chess.WHITE else -10000
                else:
                    aval_dep = 0
                melhor_dep = None
            else:
                aval_dep, melhor_dep = avaliar(board)
            avals.append(aval_dep)
            melhores.append(melhor_dep)

            # perda de win% do ponto de vista de quem jogou
            sinal = 1 if cor == chess.WHITE else -1
            wp_antes = win_percent(sinal * aval_antes)
            wp_depois = win_percent(sinal * aval_dep)
            perda = max(0.0, wp_antes - wp_depois)
            cls = classificar(perda, lance == melhor_antes)

            resultados.append({
                "cor": cor, "num": numero, "san": san, "aval": aval_dep,
                "perda": perda, "classe": cls, "melhor": san_melhor,
                "melhor_uci": melhor_antes.uci() if melhor_antes else None,
            })
        if not progresso:
            print(file=sys.stderr)
    finally:
        engine.quit()
    return resultados


def mostrar_analise(resultados):
    print(f"{'#':>4} {'Lance':<9}{'Aval':>7}  {'Classe':<11}{'Melhor era'}")
    print("-" * 62)
    for r in resultados:
        prefixo = f"{r['num']}." if r["cor"] == chess.WHITE else f"{r['num']}..."
        marca = SIMBOLOS[r["classe"]]
        melhor = "" if r["classe"] in ("melhor", "bom") else r["melhor"]
        print(f"{prefixo:>5} {r['san'] + marca:<9}{formatar_aval(r['aval']):>7}  "
              f"{r['classe']:<11}{melhor}")
    print()

    print(f"{'Resumo':14}{'Brancas':>10}{'Pretas':>10}")
    for cls in CLASSES:
        b = sum(1 for r in resultados if r["cor"] and r["classe"] == cls)
        p = sum(1 for r in resultados if not r["cor"] and r["classe"] == cls)
        print(f"{cls:14}{b:>10}{p:>10}")
    for cor, nome in [(True, "Brancas"), (False, "Pretas")]:
        perdas = [r["perda"] for r in resultados if r["cor"] == cor]
        if perdas:
            print(f"Precisão {nome}: {precisao(sum(perdas) / len(perdas)):.1f}%")
    print()

    # gráfico simples da avaliação (cada coluna = 1 lance, limitado a +-5 peões)
    print("Gráfico de avaliação (acima = brancas melhor):")
    altura = 5
    valores = [max(-500, min(500, r["aval"])) for r in resultados]
    for nivel in range(altura, -altura - 1, -1):
        linha = ""
        for v in valores:
            alvo = round(v / 100)
            if nivel == 0:
                linha += "─"
            elif nivel > 0 and 0 < nivel <= alvo:
                linha += "█"
            elif nivel < 0 and alvo <= nivel < 0:
                linha += "█"
            else:
                linha += " "
        print(f"{nivel:+3d} |{linha}")
    print()

    erros = [r for r in resultados if r["classe"] in ("erro", "blunder")]
    if erros:
        print("Momentos críticos:")
        for r in sorted(erros, key=lambda x: -x["perda"])[:5]:
            lado = "Brancas" if r["cor"] else "Pretas"
            print(f"  lance {r['num']} ({lado}): {r['san']} -> {r['classe']}, "
                  f"melhor era {r['melhor']}")


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Analisador de partidas de xadrez (PGN)")
    ap.add_argument("pgn", help="arquivo .pgn")
    ap.add_argument("--jogo", type=int, default=1, help="número da partida no arquivo (padrão: 1)")
    ap.add_argument("--stockfish", help="caminho do executável do Stockfish")
    ap.add_argument("--depth", type=int, default=14, help="profundidade da análise (padrão: 14)")
    args = ap.parse_args()

    jogo = carregar_partida(args.pgn, args.jogo)
    dados = estatisticas_basicas(jogo)
    mostrar_resumo(jogo, dados)

    caminho = args.stockfish or shutil.which("stockfish")
    if not caminho:
        print("Stockfish não encontrado: mostrando só as estatísticas básicas.")
        print("Instale o Stockfish ou use --stockfish /caminho para a análise lance a lance.")
        return
    resultados = analisar_com_engine(jogo, caminho, args.depth)
    mostrar_analise(resultados)


if __name__ == "__main__":
    main()
