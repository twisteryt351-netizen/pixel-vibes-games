import os
import urllib.parse
import re
import time
import base64
import random
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIG ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_GAMES_EN")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID_GAMES_EN", BLOGGER_ID),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Missing required environment variable/secret: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "llama-3.3-70b-versatile"

# --- AI IMAGE GENERATION (Pollinations.ai) ---
# Optional: if not configured, or if any step fails, the script automatically
# falls back to the old method (Openverse image search).
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # optional: removes watermark and raises the rate limit
# Without a token: 1 request every 15s. With a free token (auth.pollinations.ai): every 5s.
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
QTD_MIN_IMAGENS = 3
QTD_MAX_IMAGENS = 5

# --- Blogger tags/labels by category (the AI picks the right one) ---
CATEGORIAS_TAGS = {
    "cheat-code": ["cheat code", "secret code", "trick"],
    "move-input": ["combo", "special move", "fighting game"],
    "secret-unlock": ["secret", "unlockable", "easter egg"],
    "detonado": ["walkthrough", "guide", "how to beat"],
    "puzzle": ["puzzle", "puzzle solution", "guide"],
    "retro": ["retro games", "nostalgia", "classic games"],
    "moderno": ["games", "tips", "tricks"],
}

# --- CHEATS, CODES, COMBOS AND WALKTHROUGH TIPS DATABASE (real, documented facts) ---
# Providing the ready-made trick to the AI keeps it from inventing incorrect codes/commands,
# same approach used in the retro mode of the news bot.
ARQUIVO_HISTORICO = "history_games_cheats_en.txt"

# --- BASE DE MACETES, CHEATS, COMBOS E DICAS DE DETONADO (fatos reais e documentados) ---
# Fornecer o macete pronto para a IA evita que ela invente codigos/comandos incorretos.
MACETES = [
    {"jogo": "Contra", "plataforma": "NES", "tipo": "cheat-code",
     "macete": "the famous Konami Code (Up, Up, Down, Down, Left, Right, Left, Right, B, A, Start) grants 30 lives instead of 3, and became the most iconic cheat code in gaming history"},
    {"jogo": "Grand Theft Auto: San Andreas", "plataforma": "PS2/PC", "tipo": "cheat-code",
     "macete": "typing HESOYAM on the keyboard (or the equivalent controller code) instantly restores health, armor, and gives cash"},
    {"jogo": "Grand Theft Auto: Vice City", "plataforma": "PS2/PC", "tipo": "cheat-code",
     "macete": "the code THUGSTOOLS instantly gives the player a full arsenal of basic weapons"},
    {"jogo": "Street Fighter II", "plataforma": "Arcade/SNES", "tipo": "move-input",
     "macete": "Ryu and Ken's Hadouken is performed with the classic input: Down, Down-Forward, Forward + Punch"},
    {"jogo": "Street Fighter II", "plataforma": "Arcade/SNES", "tipo": "move-input",
     "macete": "the Shoryuken (dragon punch) is performed with Forward, Down, Down-Forward + Punch"},
    {"jogo": "Mortal Kombat II", "plataforma": "Arcade", "tipo": "move-input",
     "macete": "Liu Kang's Fatality (dragon transformation) is performed by crouching and rotating the joystick a full 360 degrees"},
    {"jogo": "Mortal Kombat", "plataforma": "Arcade", "tipo": "move-input",
     "macete": "Scorpion's iconic 'Get Over Here' move (spear) is performed with Down, Forward + Punch, pulling the opponent close"},
    {"jogo": "Dragon Ball Z: Super Butouden 2", "plataforma": "SNES", "tipo": "secret-unlock",
     "macete": "holding L+R on controller 2 during the title/match-start screen makes the game run at a faster speed"},
    {"jogo": "Sonic the Hedgehog 2", "plataforma": "Genesis", "tipo": "secret-unlock",
     "macete": "on the title screen, hold Up and press A, C, up, C, down, C, left, C, right, C to access the famous Level Select menu"},
    {"jogo": "Age of Empires II", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "typing 'HOW DO YOU TURN THIS ON' into the in-game chat box unlocks all technologies and reveals the whole map"},
    {"jogo": "Age of Empires II", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "the chat code 'ROCK ON' instantly grants 1000 units of stone"},
    {"jogo": "Command & Conquer: Red Alert", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "there's a hidden extra-player mode accessible via command line, plus full-map codes well documented by the community back in the day"},
    {"jogo": "GoldenEye 007", "plataforma": "Nintendo 64", "tipo": "secret-unlock",
     "macete": "completing certain levels within the time limit (on 'Agent' or harder difficulties) unlocks extra cheats like auto-aim and Paintball mode"},
    {"jogo": "The Legend of Zelda: Ocarina of Time", "plataforma": "Nintendo 64", "tipo": "detonado",
     "macete": "the 'Song of Storms', played on the ocarina with the pattern Down, Right, Up, Down, Right, Up, is essential to progress at several points in the game, including making the windmill spin"},
    {"jogo": "Resident Evil", "plataforma": "PlayStation", "tipo": "detonado",
     "macete": "the classic piano puzzle in the mansion requires playing the keys indicated on the sheet music you find, revealing a secret passage"},
    {"jogo": "Pokemon Red/Blue", "plataforma": "Game Boy", "tipo": "secret-unlock",
     "macete": "the MissingNo. glitch, triggered through a specific sequence involving the Old Man on Cinnabar Island and the Cinnabar Coast Swimmer, would duplicate the sixth item in the player's inventory"},
    {"jogo": "Doom", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "the code IDDQD activates god mode (invincibility), and IDKFA gives all weapons, ammo, and keys"},
    {"jogo": "The Sims", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "opening the console with Ctrl+Shift+C and typing 'motherlode' (or 'rosebud' in older versions) grants a solid chunk of Simoleons"},
    {"jogo": "Minecraft", "plataforma": "PC/Console", "tipo": "detonado",
     "macete": "to find diamonds efficiently in the classic version, the tried-and-true strategy was strip mining at layer 11 (Y=11), the ideal height for maximizing your chances of finding the ore"},
    {"jogo": "Super Mario 64", "plataforma": "Nintendo 64", "tipo": "secret-unlock",
     "macete": "it's possible to beat the game with as few as 70 collected stars to face Bowser in the final stage, without needing all 120 stars"},
    {"jogo": "Elden Ring", "plataforma": "PC/Console", "tipo": "detonado",
     "macete": "the boss Margit can be weakened with the Margit's Shackle item, and Torrent (the horse) helps dodge some of his toughest combos"},
    {"jogo": "Dark Souls", "plataforma": "PC/Console", "tipo": "detonado",
     "macete": "wearing the Covetous Silver Serpent Ring increases soul drops, and farming the Titanite Demons is a classic strategy for safely upgrading gear"},
    {"jogo": "Cave Story", "plataforma": "PC", "tipo": "secret-unlock",
     "macete": "you can get the game's true ending by avoiding picking up the Machine Gun in Grasstown and completing the Sacred Cave, which changes the entire third act"},
    {"jogo": "Chrono Trigger", "plataforma": "SNES", "tipo": "secret-unlock",
     "macete": "the game has multiple unlockable alternate endings depending on when the player chooses to face the final boss Lavos throughout the campaign, encouraging New Game+ replays"},
    {"jogo": "GTA V", "plataforma": "PS4/PS5/Xbox/PC", "tipo": "cheat-code",
     "macete": "on the controller, the code Up, Up, Down, Down, Left, Right, Left, Right, X/Square, Circle/B, L1/LB, R1/RB (varies by version) instantly spawns a parachute"},
    {"jogo": "The Legend of Zelda: Breath of the Wild", "plataforma": "Switch", "tipo": "detonado",
     "macete": "cooking meals by combining ingredients with matching effects (e.g. several cold-resistance items) multiplies the effect's duration, a barely explained mechanic that's essential for surviving extreme areas"},
    {"jogo": "Undertale", "plataforma": "PC", "tipo": "secret-unlock",
     "macete": "getting the True Pacifist route requires not killing a single enemy AND completing specific optional events with supporting characters before facing the Final Judgment"},
    {"jogo": "Banjo-Kazooie", "plataforma": "Nintendo 64", "tipo": "secret-unlock",
     "macete": "the game hides a final code ('Stop 'N' Swop') that would have allowed transferable items into the sequel, one of the most legendary and debated easter eggs of the N64 era"},
    {"jogo": "World of Warcraft", "plataforma": "PC", "tipo": "detonado",
     "macete": "farming reputation with specific factions before certain expansions launch is a classic veteran strategy to unlock recipes, mounts, and exclusive gear earlier than everyone else"},
    {"jogo": "Half-Life 2", "plataforma": "PC", "tipo": "cheat-code",
     "macete": "with the developer console enabled, the command 'god' activates invincibility and 'noclip' lets you walk through walls freely"},
    {"jogo": "Diablo II", "plataforma": "PC", "tipo": "detonado",
     "macete": "the famous 'Pindleskin run', repeatedly killing the secondary boss Pindleskin, was one of the community's most efficient rare-item farming routes"},
    {"jogo": "Tekken 3", "plataforma": "PlayStation", "tipo": "secret-unlock",
     "macete": "completing Arcade mode with certain characters without using continues unlocked secret characters like Dr. Bosconovitch and Gon"},
    {"jogo": "Monopoly", "plataforma": "Board Game", "tipo": "detonado",
     "macete": "a classic board strategy is to prioritize buying the orange and red properties, statistically the most-landed-on spaces for players coming out of jail, maximizing rent returns"},
    {"jogo": "Risk", "plataforma": "Board Game", "tipo": "detonado",
     "macete": "holding entire continents with few border territories (like Australia) grants a bonus army count per turn, one of the game's most time-tested strategies"},
    {"jogo": "Chess", "plataforma": "Board Game", "tipo": "detonado",
     "macete": "the Italian Game opening is one of the most studied and recommended for beginners, prioritizing control of the center of the board and rapid piece development"},
    {"jogo": "Magic: The Gathering", "plataforma": "Card Game", "tipo": "detonado",
     "macete": "the 'mana curve' (spreading out your deck's card costs in a balanced way) is one of the most important fundamentals for building a competitive deck"},
    {"jogo": "Pokemon Trading Card Game", "plataforma": "Card Game", "tipo": "detonado",
     "macete": "keeping a balanced ratio between Pokemon, Energy, and Trainer cards (a classic rule of thumb is around 60% Pokemon/Trainer to 40% Energy) is the foundation of solid decks"},
    {"jogo": "Dungeons & Dragons", "plataforma": "Tabletop RPG", "tipo": "detonado",
     "macete": "the 'advantage' rule (rolling two 20-sided dice and using the higher result) is a core mechanic introduced in the 5th edition to simplify situational bonuses"},
    {"jogo": "Angry Birds", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "aiming to hit the supporting structures at the base of buildings usually causes more chain damage than shooting the pigs directly"},
    {"jogo": "Candy Crush Saga", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "combining a striped candy with a wrapped candy creates a triple explosion that clears a huge area of the board"},
    {"jogo": "Pokemon GO", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "throwing the Poke Ball with a 'Curveball' (spinning it before releasing) grants bonus XP and increases the catch chance"},
    {"jogo": "Free Fire", "plataforma": "Mobile", "tipo": "detonado",
     "macete": "landing in less popular spots on the map and prioritizing looting before engaging in combat is a classic strategy for surviving longer in battle royale"},
    {"jogo": "Duck Hunt", "plataforma": "NES", "tipo": "secret-unlock",
     "macete": "using the Zapper (light gun), aiming very close to the screen drastically increased the hit rate, a trick well known among players at the time"},
    {"jogo": "Mega Man 2", "plataforma": "NES", "tipo": "detonado",
     "macete": "the classic recommended boss order exploits chained weaknesses between the stolen weapons, for example using the Metal Blade against multiple bosses thanks to its high versatility"},
    {"jogo": "Castlevania", "plataforma": "NES", "tipo": "cheat-code",
     "macete": "on the difficulty select screen, the code Up, Up, Down, Down, Left, Right, Left, Right, B, A lets you jump straight into the stage-select screen"},
    {"jogo": "Metal Gear Solid", "plataforma": "PlayStation", "tipo": "secret-unlock",
     "macete": "to beat the boss Psycho Mantis, you literally have to switch the controller from port 1 to port 2 on the PlayStation, since the character 'reads the player's mind' through the controller"},
]


def macete_ja_usado(macete):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    chave = f"{macete['jogo']}|{macete['macete'][:40]}"
    return chave in linhas[-40:]


def marcar_macete_usado(macete):
    chave = f"{macete['jogo']}|{macete['macete'][:40]}"
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(chave + "\n")


def escolher_macete():
    disponiveis = [m for m in MACETES if not macete_ja_usado(m)]
    if not disponiveis:
        disponiveis = MACETES
    return random.choice(disponiveis)


IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": palavra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboCulturaPop/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO


DIMENSOES_RATIO = {
    "16:9": (1280, 720),
    "1:1": (1024, 1024),
    "9:16": (720, 1280),
}


def gerar_imagem_pollinations(prompt, ratio="16:9"):
    """Gera uma imagem via Pollinations.ai (gratuito, sem chave, sem cota diaria).
    Retorna bytes da imagem ou None se falhar."""
    largura, altura = DIMENSOES_RATIO.get(ratio, (1280, 720))
    try:
        prompt_codificado = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        params = {
            "width": largura,
            "height": altura,
            "model": "flux",
            "seed": random.randint(1, 999999),
            "nologo": "true",
        }
        headers = {}
        if POLLINATIONS_TOKEN:
            headers["Authorization"] = f"Bearer {POLLINATIONS_TOKEN}"
        resposta = requests.get(url, params=params, headers=headers, timeout=120)
        resposta.raise_for_status()
        content_type = resposta.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise ValueError(f"Resposta nao parece ser uma imagem (Content-Type: {content_type})")
        return resposta.content
    except Exception as e:
        print(f"⚠️ Pollinations.ai falhou para o prompt '{prompt[:40]}...': {e}")
        return None


def hospedar_imagem(imagem_bytes, nome_arquivo="imagem.png"):
    """Sobe a imagem gerada para o imgbb.com (host gratuito via API) e retorna a URL publica.
    Catbox.moe bloqueia uploads vindos de IPs de datacenter (ex: GitHub Actions), por isso
    usamos o imgbb, que aceita chamadas de API normalmente."""
    if not IMGBB_API_KEY:
        print("Falha ao hospedar imagem: IMGBB_API_KEY nao configurada")
        return None
    try:
        b64 = base64.b64encode(imagem_bytes).decode("utf-8")
        resposta = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64, "name": nome_arquivo},
            timeout=30,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("success"):
            return dados["data"]["url"]
        raise ValueError(f"Resposta inesperada do imgbb: {dados}")
    except Exception as e:
        print(f"Falha ao hospedar imagem gerada: {e}")
        return None


def gerar_imagem_ia(prompt, ratio="16:9"):
    """Pipeline completo: gera a imagem no Pollinations.ai e hospeda no imgbb. Retorna URL ou None."""
    imagem_bytes = gerar_imagem_pollinations(prompt, ratio)
    if not imagem_bytes:
        return None
    return hospedar_imagem(imagem_bytes)


def _limpar_tag(texto):
    return re.sub(r"<[^>]+>", "", texto).strip()


def extrair_titulos_h2(html):
    return re.findall(r"<h2[^>]*>(.*?)</h2>", html, flags=re.IGNORECASE | re.DOTALL)


def contar_palavras_html(html):
    texto = re.sub(r"<[^>]+>", " ", html)
    return len(texto.split())


def calcular_qtd_imagens(wc, minimo, maximo, base_palavras, palavras_por_imagem_extra):
    if wc <= base_palavras:
        return minimo
    extras = (wc - base_palavras) // palavras_por_imagem_extra
    return min(maximo, minimo + extras)


def gerar_prompts_imagens_ia(titulo_post, secoes, quantidade, contexto_extra=""):
    """Asks the AI for image prompts in English: the first one styled as an eye-catching
    store/shelf thumbnail to drive clicks, the rest tied to each section of the post."""
    qtd_secoes = max(0, quantidade - 1)
    secoes_usadas = secoes[:qtd_secoes]
    lista_secoes = "\n".join(f"- {s}" for s in secoes_usadas) or "- (no subheadings defined, use the post's general theme)"

    prompt = f"""
You are an art director creating prompts for an AI image generator (Stable Diffusion/Flux style).
Post title: "{titulo_post}"
{contexto_extra}

I need exactly {quantidade} image prompts in ENGLISH, each on its own line, WITHOUT numbering,
WITHOUT quotes, WITHOUT explanations - just the prompts, one per line, in this order:

1) The FIRST line is the COVER/THUMBNAIL image: it needs to look like a professional digital
   storefront thumbnail (eye-catching streaming or games/movies store cover style), extremely
   high visual impact, vibrant colors, central composition, dramatic lighting, focused on the
   main element of the topic, no text written in the image, designed to maximize clicks.
2) The following lines are one image for EACH of these moments/sections of the post (in this order):
{lista_secoes}
   Each prompt must visually relate to that specific section's content, keeping stylistic
   consistency with the overall theme.

Each prompt: descriptive, rich in visual detail (setting, lighting, art style, composition),
WITHOUT naming specific characters, works, or trademarks - describe visually without naming
specific copyrighted works. Respond ONLY with the {quantidade} prompt lines.
"""
    resposta = pedir_ia_groq(prompt, temperatura=0.8)
    linhas = [l.strip(" -\"") for l in resposta.strip().splitlines() if l.strip()]
    if len(linhas) < quantidade:
        while len(linhas) < quantidade:
            linhas.append(linhas[-1] if linhas else titulo_post)
    return linhas[:quantidade]


def montar_galeria_ia(titulo_post, corpo_html, minimo, maximo, contexto_extra=""):
    """Gera a galeria completa de imagens via Pollinations.ai. Lanca excecao se qualquer
    etapa falhar, para o chamador cair no fallback do Openverse."""
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY nao configurada")

    secoes_brutas = extrair_titulos_h2(corpo_html)
    secoes = [_limpar_tag(s) for s in secoes_brutas]

    wc = contar_palavras_html(corpo_html)
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=500, palavras_por_imagem_extra=250)
    if secoes:
        qtd = min(qtd, len(secoes) + 1)
    qtd = max(1, qtd)

    prompts = gerar_prompts_imagens_ia(titulo_post, secoes, qtd, contexto_extra)

    galeria = []
    for i, prompt in enumerate(prompts):
        url = gerar_imagem_ia(prompt, ratio="16:9")
        if not url:
            raise RuntimeError(f"Falha ao gerar/hospedar imagem {i + 1}/{qtd} da galeria")
        alt = titulo_post if i == 0 else (secoes[i - 1] if i - 1 < len(secoes) else titulo_post)
        galeria.append((url, alt))
        if i < len(prompts) - 1:
            time.sleep(INTERVALO_POLLINATIONS)  # respeita o rate limit do Pollinations.ai

    return galeria, secoes_brutas


def inserir_imagens_no_corpo(corpo_html, secoes_brutas, galeria):
    """Insere as imagens de secao (a partir do indice 1 da galeria) logo apos os respectivos <h2>."""
    novo_html = corpo_html
    imagens_secao = galeria[1:]
    for i, (url, alt) in enumerate(imagens_secao):
        if i >= len(secoes_brutas):
            break
        h2_bruto = secoes_brutas[i]
        padrao = re.compile(r"(<h2[^>]*>" + re.escape(h2_bruto) + r"</h2>)", re.IGNORECASE)
        img_html = gerar_tabela_imagem_blogger(url, alt)
        novo_html, _ = padrao.subn(lambda m: m.group(1) + img_html, novo_html, count=1)
    return novo_html


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return (
        '<table align="center" cellpadding="0" cellspacing="0" '
        'class="tr-caption-container" style="margin-left: auto; margin-right: auto;">'
        '<tbody><tr><td style="text-align: center;">'
        f'<img alt="{alt_title}" border="0" height="360" src="{url_img}" '
        f'title="{alt_title}" width="640" /></td></tr></tbody></table><br />'
    )


def pedir_ia_groq(prompt, temperatura=0.7):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def extrair_palavra_chave(macete):
    prompt = (
        f"Game: '{macete['jogo']}' ({macete['plataforma']}). Give just ONE keyword in "
        f"English that visually describes this game/genre (e.g. 'retro console', 'fighting game', "
        f"'board game', 'arcade cabinet'). Reply with just the word."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(macete):
    categorias_validas = list(CATEGORIAS_TAGS.keys())
    prompt = (
        f"Trick type: '{macete['tipo']}'. Game: '{macete['jogo']}' ({macete['plataforma']}). "
        f"Pick the most fitting category among: {', '.join(categorias_validas)}. "
        f"Reply ONLY with the category word."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return macete["tipo"] if macete["tipo"] in categorias_validas else "moderno"


def gerar_titulo(macete):
    prompt = (
        f"Game: {macete['jogo']} ({macete['plataforma']})\n"
        f"Trick/tip: {macete['macete']}\n\n"
        f"Create a catchy, SEO-optimized title in English, no quotation marks, for a blog "
        f"post about this game trick/cheat/tip. Use words like 'cheat', 'secret', 'how to', "
        f"'trick', or similar to attract clicks from people searching for this kind of "
        f"content. Reply with just the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo(macete):
    prompt = f"""
You are a writer specialized in cheats, tricks, combos, and walkthroughs for games in every
form (PC, console, mobile, arcade, board games, tabletop RPGs, card games), for a highly
engaged fan blog focused on helping the player. Write with high quality, real care, and build
community with the reader.

Today's trick (a real, confirmed fact - DO NOT change the commands/codes or invent others
besides this one, use ONLY this as the factual anchor and build the article around it):

Game: {macete['jogo']} ({macete['plataforma']})
Type: {macete['tipo']}
Trick/tip: {macete['macete']}

IMPORTANT RULES:
- Explain the trick clearly and step by step, restating the command/code exactly as provided
  above (do not alter it or invent variations you aren't sure about).
- EXPAND with real, relevant context: why this trick exists (a bug, an intentional developer
  feature, community lore), the game's history, well-known behind-the-scenes trivia, and why
  players love this kind of secret.
- DO NOT invent specific facts (dates, numbers, names) you aren't sure about.
- DO NOT be repetitive: every paragraph brings new information.
- Length: between 500 and 900 words.

FORMATTING RULES (pure HTML, no Markdown):
1. Engaging opening paragraph that builds curiosity about the trick.
2. One <h2> subheading with a clear step-by-step of how to perform the trick/cheat.
3. AT LEAST 2 other <h2> subheadings (e.g. the game's context/history, trivia about the
   trick, why it works).
4. Insert 2 funny, light author's notes inside <blockquote> tags, with gamer humor (never
   mean-spirited or offensive).
5. End by inviting readers to share other tricks they know from this or other games.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Liked this trick?</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Leave a comment, like the post, and share it with fellow gamers who follow this too!</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
        <a href="#" onclick="window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(document.title + ' - ' + window.location.href), '_blank'); return false;" style="background-color: #25d366; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">WhatsApp</a>
        <a href="#" onclick="window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #1877f2; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">Facebook</a>
        <a href="#" onclick="window.open('https://twitter.com/intent/tweet?url=' + encodeURIComponent(window.location.href), '_blank'); return false;" style="background-color: #000; color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold;">X</a>
    </div>
</div>
"""


def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return creds


def publicar_no_blogger(titulo, conteudo, tags):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {
        'kind': 'blogger#post',
        'title': titulo,
        'content': conteudo,
        'labels': tags,
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("Sorteando macete/cheat/dica de games do dia...")
    macete = escolher_macete()
    print(f"Macete escolhido: {macete['jogo']} ({macete['plataforma']}) - {macete['macete'][:80]}...")

    try:
        categoria = identificar_categoria(macete)
        tags = CATEGORIAS_TAGS.get(categoria, ["games"]) + [macete["jogo"], macete["plataforma"]]
        tags = list(dict.fromkeys(tags))  # remove duplicatas mantendo a ordem

        titulo = gerar_titulo(macete)
        corpo = gerar_artigo(macete)

        try:
            galeria, secoes_brutas = montar_galeria_ia(
                titulo,
                corpo,
                minimo=QTD_MIN_IMAGENS,
                maximo=QTD_MAX_IMAGENS,
                contexto_extra=f"Jogo: {macete['jogo']} ({macete['plataforma']}). Macete: {macete['macete']}",
            )
            img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
            corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
            print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
        except Exception as e:
            print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
            palavra_chave = extrair_palavra_chave(macete)
            img_url = buscar_imagem_openverse(palavra_chave)
            img_html = gerar_tabela_imagem_blogger(img_url, titulo)

        cta = gerar_cta()

        aviso = (
            '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
            '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
            "Cheats and tricks have been part of gaming culture forever - use them in "
            "moderation so you don't spoil the fun of your first playthrough!</p>"
        )

        html_final = f"{img_html}{corpo}{cta}{aviso}"
        publicar_no_blogger(titulo, html_final, tags)
        marcar_macete_usado(macete)
        print("Concluido!")
    except Exception as e:
        print(f"Erro durante geracao/publicacao: {e}")
