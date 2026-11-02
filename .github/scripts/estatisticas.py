"""Gera o cartão de estatísticas do perfil (dist/estatisticas.svg) com os números públicos do GitHub.

Roda no GitHub Actions (workflow cobra.yml) com o GITHUB_TOKEN do próprio repositório:
    python .github/scripts/estatisticas.py NatanaelSantz dist

Para testar o desenho sem internet:  python .github/scripts/estatisticas.py --exemplo dist
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

AQUI = Path(__file__).resolve().parent
ESCONDER = {"HTML", "CSS", "SCSS", "Jupyter Notebook"}  # marcação e notebooks não contam como linguagem do dia a dia

CONSULTA = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
  }
}
"""


def buscar(login: str, token: str) -> dict:
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": CONSULTA, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "perfil-natanaelsantz"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as resp:
        dados = json.loads(resp.read())
    if dados.get("errors"):
        raise SystemExit(f"GitHub respondeu com erro: {dados['errors']}")
    u = dados["data"]["user"]
    linguas: dict[str, list] = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            nome = e["node"]["name"]
            if nome in ESCONDER:
                continue
            item = linguas.setdefault(nome, [0, e["node"]["color"] or "#8B95B5"])
            item[0] += e["size"]
    return {
        "contribuicoes": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "repositorios": u["repositories"]["totalCount"],
        "estrelas": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "seguidores": u["followers"]["totalCount"],
        "linguas": sorted(([n, t, c] for n, (t, c) in linguas.items()), key=lambda x: -x[1]),
    }


EXEMPLO = {
    "contribuicoes": 812, "repositorios": 10, "estrelas": 9, "seguidores": 14,
    "linguas": [["Python", 900000, "#3572A5"], ["JavaScript", 120000, "#f1e05a"], ["TypeScript", 60000, "#3178c6"],
                ["C#", 30000, "#178600"], ["Shell", 8000, "#89e051"], ["PowerShell", 3000, "#012456"]],
}


def _visivel(cor: str) -> str:
    """Cores de linguagem muito escuras (PowerShell, C...) clareiam um pouco para aparecer no fundo escuro."""
    try:
        r, g, b = (int(cor.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "#8B95B5"
    if (0.299 * r + 0.587 * g + 0.114 * b) / 255 >= 0.32:
        return cor
    r, g, b = (round(c + (255 - c) * 0.45) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _numero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def desenhar(d: dict) -> str:
    W, H = 1200, 270
    fontes = (AQUI / "fontes.css").read_text(encoding="utf-8") if (AQUI / "fontes.css").exists() else ""
    hoje = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%d/%m/%Y")
    blocos = [
        (_numero(d["contribuicoes"]), "contribuições no último ano"),
        (_numero(d["repositorios"]), "repositórios públicos"),
        (_numero(d["estrelas"]), "estrelas recebidas"),
        (_numero(d["seguidores"]), "seguidores"),
    ]
    x0, larg = 64, (W - 128) / 4
    numeros = []
    for i, (valor, rotulo) in enumerate(blocos):
        x = x0 + i * larg
        if i:
            numeros.append(f'<rect x="{x - 28:.1f}" y="92" width="1" height="62" fill="#FFFFFF" fill-opacity=".1"/>')
        numeros.append(f'<text class="n" x="{x:.1f}" y="134">{escape(valor)}</text>'
                       f'<text class="r" x="{x:.1f}" y="160">{escape(rotulo)}</text>')
    # barra das linguagens (as 6 maiores; o resto vira "outras")
    linguas = d["linguas"]
    total = sum(t for _, t, _ in linguas) or 1
    topo = linguas[:6]
    resto = sum(t for _, t, _ in linguas[6:])
    if resto:
        topo = topo + [["Outras", resto, "#5B6690"]]
    topo = [[n, t, _visivel(c)] for n, t, c in topo]
    barra, legenda, x = [], [], x0
    largura_barra = W - 2 * x0
    for nome, t, cor in topo:
        w = largura_barra * t / total
        barra.append(f'<rect x="{x:.2f}" y="196" width="{max(w - 2, 1.5):.2f}" height="10" fill="{escape(cor)}"/>')
        x += w
    lx = x0
    for nome, t, cor in topo:
        txt = f"{nome} {t / total * 100:.1f}%".replace(".", ",")
        legenda.append(f'<circle cx="{lx + 5}" cy="{232}" r="5" fill="{escape(cor)}"/><text class="l" x="{lx + 16}" y="237">{escape(txt)}</text>')
        lx += 22 + len(txt) * 8.2 + 18
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Estatísticas do GitHub de Natanael Santos">
<title>Estatísticas do GitHub</title>
<style>
{fontes}
.h{{font-family:'Titulo',Georgia,serif;font-size:26px;fill:#F3F6FF}}
.a{{font-family:'Texto','Segoe UI',sans-serif;font-size:14px;fill:#7F8DB5}}
.n{{font-family:'Titulo',Georgia,serif;font-size:44px;fill:#F3F6FF}}
.r{{font-family:'Texto','Segoe UI',sans-serif;font-size:15.5px;fill:#A9B6D6}}
.l{{font-family:'Texto','Segoe UI',sans-serif;font-size:14px;fill:#C9D3EE}}
.sobe{{animation:sobe .8s cubic-bezier(.2,.7,.2,1) both}}
@keyframes sobe{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
.enche{{transform-box:fill-box;transform-origin:left center;animation:enche 1.2s .3s cubic-bezier(.2,.7,.2,1) both}}
@keyframes enche{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
</style>
<defs>
  <linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0A0F1E"/><stop offset="1" stop-color="#121C3A"/></linearGradient>
  <pattern id="pontos" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="#FFFFFF" fill-opacity=".06"/></pattern>
  <clipPath id="arredonda"><rect x="{x0}" y="196" width="{largura_barra}" height="10" rx="5"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="26" fill="url(#fundo)"/>
<rect width="{W}" height="{H}" rx="26" fill="url(#pontos)"/>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="26" fill="none" stroke="#FFFFFF" stroke-opacity=".08"/>
<text class="h" x="{x0}" y="62">Em números</text>
<text class="a" x="{W - x0}" y="62" text-anchor="end">atualizado em {hoje}</text>
<g class="sobe">{"".join(numeros)}</g>
<g clip-path="url(#arredonda)"><g class="enche">{"".join(barra)}</g></g>
{"".join(legenda)}
</svg>"""


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    login, destino = argv[1], Path(argv[2])
    if login == "--exemplo":
        dados = EXEMPLO
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print("Falta o GITHUB_TOKEN.")
            return 1
        dados = buscar(login, token)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "estatisticas.svg").write_text(desenhar(dados), encoding="utf-8")
    print(json.dumps({k: v for k, v in dados.items() if k != "linguas"}), [n for n, _, _ in dados["linguas"][:6]])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
