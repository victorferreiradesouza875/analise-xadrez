# ♟️ Analisador de Xadrez

Ferramenta em Python para analisar suas partidas de xadrez a partir de um arquivo PGN (Lichess, Chess.com etc.). Funciona de duas formas:

- **Interface gráfica** (`app_xadrez.py`): tabuleiro no navegador, navegação lance a lance, classificação dos lances e gráfico de avaliação.
- **Linha de comando** (`analisador_xadrez.py`): relatório em texto direto no terminal.

## O que ele faz

**Sem Stockfish** (estatísticas básicas):
- Jogadores, ratings, resultado, abertura e controle de tempo
- Por lado: lances, capturas, xeques, promoções, lance do roque e material final

**Com Stockfish** (análise completa):
- Avaliação da posição após cada lance
- Classificação de cada lance e o melhor lance que existia
- Precisão de cada jogador
- Gráfico de avaliação ao longo da partida
- Os momentos mais críticos (erros e blunders)

### Classificação dos lances

A classificação usa a queda na chance de vitória (win%) causada pelo lance:

| Classe | Queda de win% |
|---|---|
| ★ melhor | jogou o lance do engine ou perdeu menos de 2% |
| bom | de 2% a 5% |
| ?! imprecisão | de 5% a 10% |
| ? erro | de 10% a 20% |
| ?? blunder | 20% ou mais |

A precisão é uma aproximação da fórmula do Lichess, então os números podem não bater exatamente com os do site.

## Requisitos

- Python 3.9 ou mais novo (recomendado: **3.12**)
- Bibliotecas `chess` e `streamlit`
- [Stockfish](https://stockfishchess.org/download/) (opcional, mas necessário para a análise dos lances)

## Instalação

1. Coloque `app_xadrez.py` e `analisador_xadrez.py` **na mesma pasta**.
2. Abra o terminal nessa pasta e instale as bibliotecas:

   ```
   pip install streamlit chess
   ```

3. Instale o Stockfish:
   - **Windows:** baixe em [stockfishchess.org/download](https://stockfishchess.org/download/), extraia o `.zip` e guarde o caminho do arquivo `.exe`.
   - **Mac:** `brew install stockfish`
   - **Linux:** `sudo apt install stockfish`

## Como usar a interface gráfica

```
streamlit run app_xadrez.py
```

O navegador abre em `http://localhost:8501`. Para fechar o app, aperte `Ctrl+C` no terminal.

1. Na barra lateral, envie o arquivo `.pgn` ou cole o texto da partida. Se o arquivo tiver várias partidas, escolha qual abrir.
2. No campo **Caminho do Stockfish**, informe o caminho completo do executável. Exemplo no Windows:

   ```
   C:\Users\seu_usuario\xadrez\stockfish\stockfish-windows-x86-64-avx2.exe
   ```

   No Mac e no Linux o app costuma encontrar o Stockfish sozinho.
3. Ajuste a profundidade (14 é um bom equilíbrio entre velocidade e qualidade) e clique em **Analisar com Stockfish**. Uma partida costuma levar de 1 a 3 minutos.
4. Navegue pelos lances com os botões ⏮ ◀ ▶ ⏭ ou com o slider. Nos lances ruins, uma seta verde mostra o melhor lance.
5. Marque **Ver do lado das pretas** para virar o tabuleiro.

## Como usar pela linha de comando

```
python analisador_xadrez.py partida.pgn
python analisador_xadrez.py partida.pgn --stockfish "C:\caminho\stockfish.exe" --depth 16
python analisador_xadrez.py partidas.pgn --jogo 3
```

| Opção | Descrição |
|---|---|
| `--stockfish` | Caminho do executável (se omitido, procura no sistema) |
| `--depth` | Profundidade da análise (padrão: 14) |
| `--jogo` | Número da partida dentro do arquivo (padrão: 1) |

## Como obter o PGN das suas partidas

- **Lichess:** abra a partida e use o botão de baixar/exportar PGN.
- **Chess.com:** abra a partida, clique em compartilhar e escolha a aba PGN.

## Solução de problemas

**"Uma política de Controle de Aplicativo bloqueou este arquivo" (DLL load failed)**
O Windows (Smart App Control) bloqueou uma biblioteca compilada. A interface já evita pandas e numpy por causa disso. Se o erro continuar em outro ponto, instale o Python 3.12 e use:

```
py -3.12 -m pip install streamlit chess
py -3.12 -m streamlit run app_xadrez.py
```

O mesmo bloqueio pode acontecer com o `stockfish.exe`. Se acontecer, clique com o botão direito no arquivo, abra Propriedades e marque "Desbloquear", se a opção existir.

**O campo "Caminho do Stockfish" está vazio**
O app não encontrou o Stockfish no sistema. Baixe o programa e cole o caminho completo do `.exe` (sem aspas).

**"Não consegui ler nenhuma partida desse PGN"**
Confira se o arquivo é realmente um PGN e se o texto não foi cortado ao copiar.

**A análise está lenta**
Diminua a profundidade na barra lateral (por exemplo, 10 a 12).

## Estrutura do projeto

```
analisador_xadrez.py   # análise (estatísticas, Stockfish, relatório no terminal)
app_xadrez.py          # interface gráfica em Streamlit (usa o arquivo acima)
README.md
```

## Tecnologias

- [python-chess](https://python-chess.readthedocs.io/) para ler PGN, validar lances e conversar com a engine
- [Stockfish](https://stockfishchess.org/) para avaliar as posições
- [Streamlit](https://streamlit.io/) para a interface web
