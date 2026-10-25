"""
ETAPA 5B — REEL DIÁRIO (VÍDEO VERTICAL 1080 x 1920, ~15 s)
===========================================================

POR QUE EXISTE

Imagem e carrossel o Instagram entrega quase só para quem já segue o perfil.
Reels é o formato que o algoritmo mostra para quem NÃO segue — é o que traz
seguidor novo. Este módulo transforma as peças que o robô já gera em um Reel
curto, com trilha sonora própria (gerada aqui mesmo, sem direito autoral).

ROTEIRO (4 cenas, transições suaves)

  0,0 s  GANCHO     "O RADAR 15 ACERTOU 9 DE 15" — legível no primeiro frame
  2,8 s  RESULTADO  peça de conferência (sorteadas x jogo do Radar 15)
  7,2 s  PRÓXIMO    as 15 dezenas do próximo concurso (peça de stories)
 12,0 s  CTA        siga / salve / compartilhe + aviso +18

Como rodar sozinho:
    python -m src.reels --concurso 3812
"""

from __future__ import annotations

import argparse
import base64
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any

from src import pecas

LARGURA, ALTURA, FPS = 1080, 1920, 30
ESTILO = "radar"

# (nome, duração em segundos). As transições de 0,4 s "comem" a ponta de cada cena.
CENAS = [("gancho", 3.2), ("resultado", 4.8), ("proximo", 5.2), ("cta", 3.2)]
TRANSICAO = 0.4


# ---------------------------------------------------------------------------
# FFMPEG
# ---------------------------------------------------------------------------


def _ffmpeg() -> str:
    """ffmpeg do sistema ou, na falta dele, o binário estático do imageio-ffmpeg."""
    sistema = shutil.which("ffmpeg")
    if sistema:
        return sistema
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as erro:
        raise RuntimeError("ffmpeg não encontrado (instale ffmpeg ou imageio-ffmpeg)") from erro


# ---------------------------------------------------------------------------
# TRILHA SONORA PRÓPRIA (sintetizada — zero risco de direito autoral)
# ---------------------------------------------------------------------------


def gerar_trilha(destino: Path, duracao: float, bpm: int = 112, taxa: int = 44100) -> Path:
    """
    Batida eletrônica discreta: pad de 4 acordes, baixo, bumbo e chimbal.
    Fica baixa de propósito — o vídeo é para ser lido, a música só dá ritmo.
    """
    import random

    rnd = random.Random(15)
    n = int(duracao * taxa)
    batida = 60 / bpm
    # Lá menor · Fá · Dó · Sol (i–VI–III–VII), um acorde a cada 2 tempos
    acordes = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63),
               (196.0, 261.63, 329.63), (196.0, 246.94, 293.66)]
    baixos = [110.0, 87.31, 130.81, 98.0]

    amostras = []
    for i in range(n):
        t = i / taxa
        tempo = t / batida
        idx = int(tempo // 2) % 4
        fase = (tempo % 1) * batida            # segundos desde o último tempo

        pad = sum(math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t)
                  for f in acordes[idx]) * 0.045
        baixo = math.sin(2 * math.pi * baixos[idx] * t) * 0.16 * math.exp(-3.2 * fase)
        bumbo = math.sin(2 * math.pi * (52 + 90 * math.exp(-28 * fase)) * fase) \
            * 0.55 * math.exp(-9 * fase)
        meio = ((tempo + 0.5) % 1) * batida    # chimbal no contratempo
        chimbal = (rnd.random() * 2 - 1) * 0.07 * math.exp(-55 * meio)

        v = pad + baixo + bumbo + chimbal
        # entrada e saída suaves
        env = min(1.0, t / 0.6, (duracao - t) / 1.2)
        amostras.append(max(-1.0, min(1.0, v * env * 0.8)))

    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(b"".join(struct.pack("<h", int(a * 32767)) for a in amostras))
    return destino


# ---------------------------------------------------------------------------
# CENAS EM HTML (mesma identidade visual das peças)
# ---------------------------------------------------------------------------


def _img64(caminho: Path) -> str:
    tipo = "png" if caminho.suffix == ".png" else "jpeg"
    return f"data:image/{tipo};base64,{base64.b64encode(caminho.read_bytes()).decode()}"


def _marca(e: dict, tamanho: int = 120) -> str:
    return f"""
<div style="display:flex;align-items:center;gap:22px;justify-content:center">
  {pecas._radar_svg(e['destaque'], tamanho)}
  <div style="font-size:{int(tamanho * .62)}px;font-weight:800;font-style:italic;letter-spacing:-.02em">
    RADAR <span class="destaque">15</span>
  </div>
</div>"""


def html_gancho(ctx: dict, e: dict) -> str:
    acertos = ctx["acertos"]
    rotulo = "ACERTOS" if acertos != 1 else "ACERTO"
    corpo = f"""
<div class="pad" style="justify-content:space-between;align-items:center;text-align:center;padding:190px 70px 400px">
  {_marca(e, 130)}
  <div>
    <div class="tag" style="align-self:center;margin:0 auto 46px;font-size:30px">
      <span class="ponto"></span> RESULTADO CONFERIDO
    </div>
    <h1 style="font-size:92px">O RADAR 15<br>FEZ</h1>
    <div class="destaque" style="font-size:430px;font-weight:900;line-height:.9;letter-spacing:-.05em;
         text-shadow:0 0 60px rgba(163,246,0,.35)">{acertos}</div>
    <h2 style="font-size:66px">{rotulo} DE 15</h2>
  </div>
  <div>
    <div style="font-size:44px;font-weight:800">Concurso <span class="destaque">{ctx['concurso']}</span></div>
    <div class="sub" style="font-size:34px;margin-top:10px">Sorteio de {ctx['data']} · Lotofácil</div>
  </div>
</div>"""
    return pecas._pagina(e, LARGURA, ALTURA, corpo)


def html_resultado(ctx: dict, e: dict, imagem: Path) -> str:
    corpo = f"""
<div class="pad" style="justify-content:center;gap:56px;padding:120px 0">
  <div style="text-align:center;padding:0 60px">
    <div class="sub" style="font-size:34px;letter-spacing:.1em;font-weight:700">CONFERÊNCIA OFICIAL</div>
    <h2 style="font-size:72px;margin-top:14px">Jogo publicado <span class="destaque">antes</span> do sorteio</h2>
  </div>
  <img src="{_img64(imagem)}" style="width:1080px;height:1080px;display:block">
  <div style="text-align:center" class="sub">Placar aberto: mostramos todo resultado, bom ou ruim.</div>
</div>"""
    return pecas._pagina(e, LARGURA, ALTURA, corpo)


def html_cta(ctx: dict, e: dict, proximo: int) -> str:
    itens = "".join(
        f'<div class="cartao" style="display:flex;align-items:center;gap:26px;padding:34px 40px">'
        f'<div class="destaque" style="font-size:54px;font-weight:900;width:60px">{n}</div>'
        f'<div style="font-size:42px;font-weight:750;text-align:left">{t}</div></div>'
        for n, t in ((1, "Siga <span class='destaque'>@radar15br</span>"),
                     (2, "Salve para conferir depois"),
                     (3, "Mande para quem joga com você"))
    )
    corpo = f"""
<div class="pad" style="justify-content:space-between;align-items:stretch;text-align:center;padding:170px 80px 120px">
  {_marca(e, 110)}
  <div>
    <h1 style="font-size:84px">Jogo do concurso<br><span class="destaque">{proximo}</span> já no perfil</h1>
    <div class="sub" style="margin-top:26px;font-size:36px">Resultado conferido todo dia, logo após o sorteio.</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:22px">{itens}</div>
  <div class="mini" style="font-size:25px">{pecas.AVISO_CURTO}</div>
</div>"""
    return pecas._pagina(e, LARGURA, ALTURA, corpo)


# ---------------------------------------------------------------------------
# MONTAGEM
# ---------------------------------------------------------------------------


def _montar_video(quadros: list[Path], trilha: Path, destino: Path) -> Path:
    """Zoom lento em cada cena + transição em fade entre elas."""
    entradas: list[str] = []
    filtros: list[str] = []
    for i, ((_, dur), quadro) in enumerate(zip(CENAS, quadros)):
        entradas += ["-loop", "1", "-t", f"{dur}", "-framerate", str(FPS), "-i", str(quadro)]
        frames = int(dur * FPS)
        # Sobe a resolução antes do zoom para o movimento não "tremer"
        filtros.append(
            f"[{i}:v]scale={LARGURA * 2}:{ALTURA * 2},"
            f"zoompan=z='1+0.045*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={LARGURA}x{ALTURA}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
        )

    atual, deslocamento = "v0", 0.0
    for i in range(1, len(quadros)):
        deslocamento += CENAS[i - 1][1] - TRANSICAO
        saida = f"x{i}"
        filtros.append(f"[{atual}][v{i}]xfade=transition=fade:duration={TRANSICAO}"
                       f":offset={deslocamento:.2f}[{saida}]")
        atual = saida

    duracao = sum(d for _, d in CENAS) - TRANSICAO * (len(CENAS) - 1)
    comando = [
        _ffmpeg(), "-y", "-loglevel", "error", *entradas, "-i", str(trilha),
        "-filter_complex", ";".join(filtros),
        "-map", f"[{atual}]", "-map", f"{len(quadros)}:a",
        "-t", f"{duracao:.2f}",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "veryfast", "-crf", "24",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart", str(destino),
    ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(comando, check=True)
    return destino


def gerar(concurso: int, proximo: int | None = None) -> dict[str, Any]:
    """
    Monta o Reel do RESULTADO do `concurso` e chama para o jogo do `proximo`.
    Requer: peça de resultado do concurso e peças (stories) do próximo.
    """
    e = pecas.ESTILOS[ESTILO]
    proximo = proximo or concurso + 1
    ctx = pecas.contexto_resultado(concurso)

    pasta = pecas.PASTA_SAIDAS / str(concurso) / ESTILO / "reel"
    resultado_png = pecas.PASTA_SAIDAS / str(concurso) / ESTILO / "resultado" / "resultado.png"
    stories_png = pecas.PASTA_SAIDAS / str(proximo) / ESTILO / "stories.png"
    for exigido in (resultado_png, stories_png):
        if not exigido.exists():
            raise RuntimeError(f"Peça necessária para o Reel não existe: {exigido}")

    paginas = [
        ("gancho", html_gancho(ctx, e), LARGURA, ALTURA, pasta / "1-gancho.png"),
        ("resultado", html_resultado(ctx, e, resultado_png), LARGURA, ALTURA, pasta / "2-resultado.png"),
        ("cta", html_cta(ctx, e, proximo), LARGURA, ALTURA, pasta / "4-cta.png"),
    ]
    pecas.renderizar(paginas)
    quadros = [pasta / "1-gancho.png", pasta / "2-resultado.png", stories_png, pasta / "4-cta.png"]

    duracao = sum(d for _, d in CENAS)
    trilha = gerar_trilha(pasta / "trilha.wav", duracao)
    video = _montar_video(quadros, trilha, pasta / "reel.mp4")
    trilha.unlink(missing_ok=True)

    # A capa do Reel (cover_url) é o gancho — o .jpg já foi salvo pelo renderizar
    capa = pasta / "1-gancho.jpg"
    return {"concurso": concurso, "proximo": proximo, "acertos": ctx["acertos"],
            "video": str(video), "capa": str(capa),
            "tamanho_mb": round(video.stat().st_size / 1_048_576, 2)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o Reel do resultado")
    parser.add_argument("--concurso", type=int, required=True)
    parser.add_argument("--proximo", type=int, default=None)
    args = parser.parse_args()
    print(gerar(args.concurso, args.proximo))
