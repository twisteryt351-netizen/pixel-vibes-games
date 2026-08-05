import os
import urllib.parse
import re
import time
import base64
import random
import feedparser
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

# --- SOURCES: gaming news worldwide (PC, console, mobile, board, RPG, cards) ---
FONTES = {
    "IGN": "https://www.ign.com/feed",
    "Kotaku": "https://kotaku.com/rss",
    "GameSpot": "https://www.gamespot.com/feeds/mashup/",
    "PC Gamer": "https://www.pcgamer.com/rss/",
    "Eurogamer": "https://www.eurogamer.net/feed",
    "Polygon": "https://www.polygon.com/rss/index.xml",
    "Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed",
    "VG247": "https://www.vg247.com/feed",
    "GamesRadar": "https://www.gamesradar.com/rss/",
    "Game Rant": "https://gamerant.com/feed/",
    "Dot Esports": "https://dotesports.com/feed",
    "Nintendo Life": "https://www.nintendolife.com/feeds/latest",
    "Push Square (PlayStation)": "https://www.pushsquare.com/feeds/latest",
    "Pure Xbox": "https://www.purexbox.com/feeds/latest",
    "TouchArcade": "https://toucharcade.com/feed/",
    "Pocket Gamer": "https://www.pocketgamer.com/rss/",
    "Tabletop Gaming News": "https://tabletopgamingnews.com/feed/",
    "PCGamesN": "https://www.pcgamesn.com/feed",
    "Destructoid": "https://www.destructoid.com/feed/",
    "Siliconera": "https://www.siliconera.com/feed/",
}

# --- Blogger tags/labels by category (the AI picks the right one) ---
CATEGORIAS_TAGS = {
    "pc": ["pc gaming", "games", "steam"],
    "console": ["console", "games", "playstation", "xbox", "nintendo"],
    "mobile": ["mobile games", "phone gaming", "games"],
    "retro": ["retro games", "nostalgia", "classic games"],
    "arcade": ["arcade", "arcade games", "games"],
    "tabuleiro": ["board game", "tabletop game", "games"],
    "card": ["card game", "tcg", "games"],
    "rpg": ["tabletop rpg", "rpg", "games"],
    "esports": ["esports", "competitive gaming", "games"],
    "indie": ["indie game", "indie games", "games"],
}

ARQUIVO_HISTORICO = "history_games_news_en.txt"
ARQUIVO_HISTORICO_RETRO = "history_games_retro_en.txt"

# --- GAMING TIMELINE (real, well-documented facts) ---
# Usada como fallback "hoje na historia dos games" quando nao ha noticia fresca nas fontes.
# Fornecer o fato pronto para a IA evita que ela invente datas/numeros incorretos.
GAMES_HISTORICOS = [
    {"ano": 1958, "evento": "physicist William Higinbotham creates 'Tennis for Two', one of the earliest electronic games in history, running on an oscilloscope"},
    {"ano": 1972, "evento": "Atari releases 'Pong' in arcades, popularizing video games"},
    {"ano": 1972, "evento": "Magnavox releases the Odyssey, the first home video game console"},
    {"ano": 1975, "evento": "Atari releases the home version of 'Pong' to play on a TV set"},
    {"ano": 1977, "evento": "Atari releases the Atari 2600 (VCS) console, popularizing interchangeable cartridges"},
    {"ano": 1978, "evento": "'Space Invaders' is released in Japanese arcades and becomes a worldwide craze"},
    {"ano": 1980, "evento": "'Pac-Man' is released by Namco and becomes a cultural icon"},
    {"ano": 1981, "evento": "'Donkey Kong' is released in arcades, marking the debut of the character who would become Mario"},
    {"ano": 1983, "evento": "the North American video game industry suffers the famous 'crash of 1983', nearly ending the market"},
    {"ano": 1983, "evento": "Nintendo releases the Famicom in Japan, the base for what would become the NES"},
    {"ano": 1985, "evento": "the NES (Nintendo Entertainment System) arrives in the United States, reviving the industry after the crash, alongside 'Super Mario Bros.'"},
    {"ano": 1986, "evento": "'The Legend of Zelda' is released in Japan for the Famicom Disk System"},
    {"ano": 1987, "evento": "Sega's Master System begins its long and successful run in Brazil, distributed by Tectoy - one of the most unique regional console stories in gaming history"},
    {"ano": 1988, "evento": "Sega releases the Mega Drive (Genesis) in Japan"},
    {"ano": 1989, "evento": "Nintendo releases the Game Boy, revolutionizing handheld gaming"},
    {"ano": 1989, "evento": "'Prince of Persia' is released, with fluid animation that was revolutionary for its time"},
    {"ano": 1990, "evento": "Nintendo releases the Super Famicom in Japan, which would reach the West as the Super Nintendo (SNES)"},
    {"ano": 1991, "evento": "'Sonic the Hedgehog' debuts on the Mega Drive as Sega's answer to Mario"},
    {"ano": 1992, "evento": "'Mortal Kombat' is released in arcades, sparking controversy over its graphic violence"},
    {"ano": 1993, "evento": "id Software releases 'Doom', a founding milestone of first-person shooters"},
    {"ano": 1993, "evento": "Richard Garfield creates 'Magic: The Gathering', the world's first major trading card game (TCG)"},
    {"ano": 1994, "evento": "Sony releases the PlayStation in Japan, entering the console wars for good"},
    {"ano": 1994, "evento": "Sega releases the Sega Saturn in Japan"},
    {"ano": 1995, "evento": "'Chrono Trigger' is released for the Super Famicom in Japan, becoming a cult classic RPG"},
    {"ano": 1996, "evento": "Nintendo releases the Nintendo 64 in Japan"},
    {"ano": 1996, "evento": "'Pokemon Red and Green' are released in Japan for the Game Boy, kicking off the Pokemon phenomenon"},
    {"ano": 1996, "evento": "the Pokemon Trading Card Game is released in Japan"},
    {"ano": 1996, "evento": "'Resident Evil' is released, popularizing the survival horror genre"},
    {"ano": 1997, "evento": "'Final Fantasy VII' is released for the PlayStation, becoming a landmark for 3D RPGs"},
    {"ano": 1997, "evento": "'GoldenEye 007' is released for the Nintendo 64, a benchmark for console shooters"},
    {"ano": 1998, "evento": "'The Legend of Zelda: Ocarina of Time' is released for the Nintendo 64"},
    {"ano": 1998, "evento": "Valve releases 'Half-Life', raising the bar for storytelling in first-person shooters"},
    {"ano": 1999, "evento": "Sega releases the Dreamcast in the United States"},
    {"ano": 2000, "evento": "Sony releases the PlayStation 2 in Japan, which would become the best-selling console in history"},
    {"ano": 2001, "evento": "Microsoft releases the Xbox, entering the console wars for the first time"},
    {"ano": 2001, "evento": "Nintendo releases the GameCube"},
    {"ano": 2001, "evento": "'Grand Theft Auto III' is released, revolutionizing open-world games"},
    {"ano": 2001, "evento": "'Halo: Combat Evolved' is released as an Xbox launch title"},
    {"ano": 2003, "evento": "Nokia releases the N-Gage, a hybrid phone and handheld console"},
    {"ano": 2004, "evento": "Blizzard releases 'World of Warcraft', which would become the most popular MMORPG in the world"},
    {"ano": 2004, "evento": "Nintendo releases the Nintendo DS, with its innovative dual screen"},
    {"ano": 2004, "evento": "Valve releases 'Half-Life 2'"},
    {"ano": 2004, "evento": "Sony releases the PSP (PlayStation Portable) in Japan"},
    {"ano": 2005, "evento": "Microsoft releases the Xbox 360"},
    {"ano": 2006, "evento": "Sony releases the PlayStation 3"},
    {"ano": 2006, "evento": "Nintendo releases the Wii, popularizing motion controls"},
    {"ano": 2007, "evento": "Irrational Games releases 'BioShock'"},
    {"ano": 2007, "evento": "'Call of Duty 4: Modern Warfare' is released, redefining military shooters"},
    {"ano": 2008, "evento": "Nintendo releases the Nintendo DSi in Japan"},
    {"ano": 2009, "evento": "Markus 'Notch' Persson releases the first public alpha version of 'Minecraft'"},
    {"ano": 2011, "evento": "'Minecraft' is officially released after two years of open development"},
    {"ano": 2011, "evento": "Nintendo releases the Nintendo 3DS"},
    {"ano": 2011, "evento": "Sony releases the PlayStation Vita in Japan"},
    {"ano": 2011, "evento": "'Dark Souls' is released, giving birth to the genre that would become known as Soulslike"},
    {"ano": 2011, "evento": "'The Elder Scrolls V: Skyrim' is released"},
    {"ano": 2013, "evento": "Sony and Microsoft release the PlayStation 4 and Xbox One almost simultaneously"},
    {"ano": 2013, "evento": "'Grand Theft Auto V' is released, becoming one of the most profitable entertainment products in history"},
    {"ano": 2013, "evento": "'The Last of Us' is released for the PlayStation 3"},
    {"ano": 2015, "evento": "From Software releases 'Bloodborne'"},
    {"ano": 2016, "evento": "'Pokemon GO' is released, bringing augmented reality to the streets worldwide"},
    {"ano": 2017, "evento": "Nintendo releases the Nintendo Switch"},
    {"ano": 2017, "evento": "'The Legend of Zelda: Breath of the Wild' is released as a Switch launch title"},
    {"ano": 2017, "evento": "'PlayerUnknown's Battlegrounds' (PUBG) popularizes the battle royale genre"},
    {"ano": 2018, "evento": "'God of War' reinvents the franchise on PlayStation 4"},
    {"ano": 2018, "evento": "'Red Dead Redemption 2' is released by Rockstar Games"},
    {"ano": 2020, "evento": "Sony and Microsoft release the PlayStation 5 and Xbox Series X/S"},
    {"ano": 2020, "evento": "'Among Us', originally released in 2018, explodes in worldwide popularity during the pandemic"},
    {"ano": 2022, "evento": "From Software releases 'Elden Ring'"},
    {"ano": 2023, "evento": "Larian Studios releases 'Baldur's Gate 3'"},
    {"ano": 2023, "evento": "'The Legend of Zelda: Tears of the Kingdom' is released for the Nintendo Switch"},
    {"ano": 1935, "evento": "Parker Brothers publishes 'Monopoly' in the United States, one of the best-selling board games in history"},
    {"ano": 1960, "evento": "Milton Bradley releases the modern version of 'The Game of Life', celebrating 100 years since the original game"},
    {"ano": 1974, "evento": "Gary Gygax and Dave Arneson publish 'Dungeons & Dragons', creating the tabletop RPG genre"},
]


def evento_retro_ja_usado(evento):
    if not os.path.exists(ARQUIVO_HISTORICO_RETRO):
        return False
    with open(ARQUIVO_HISTORICO_RETRO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    return evento["evento"] in linhas[-30:]


def marcar_evento_retro_usado(evento):
    with open(ARQUIVO_HISTORICO_RETRO, "a", encoding="utf-8") as f:
        f.write(evento["evento"] + "\n")


def escolher_evento_retro():
    disponiveis = [e for e in GAMES_HISTORICOS if not evento_retro_ja_usado(e)]
    if not disponiveis:
        disponiveis = GAMES_HISTORICOS
    return random.choice(disponiveis)


def ja_foi_postada(link):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return link in f.read()


def marcar_como_postada(link):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def pegar_novidade():
    fontes_lista = list(FONTES.items())
    random.shuffle(fontes_lista)

    for nome_fonte, url_rss in fontes_lista:
        try:
            feed = feedparser.parse(url_rss, agent="Mozilla/5.0")
            if feed.bozo and not feed.entries:
                print(f"Fonte com problema: {nome_fonte} -> {url_rss}")
                continue
        except Exception as e:
            print(f"Fonte falhou: {nome_fonte} -> {url_rss} | Erro: {e}")
            continue

        for entrada in feed.entries[:5]:
            link = entrada.get("link")
            titulo = entrada.get("title")
            resumo = entrada.get("summary") or entrada.get("description") or ""

            if not link or not titulo:
                continue

            if not ja_foi_postada(link):
                print(f"Novidade encontrada em {nome_fonte}: {titulo[:60]}...")
                return titulo, resumo, link, nome_fonte

    return None, None, None, None


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


def extrair_palavra_chave(titulo):
    prompt = (
        f"Based on this title: '{titulo}', give just ONE keyword in English that visually "
        f"describes the topic (e.g. 'video game', 'retro console', 'board game', "
        f"'esports arena', 'mobile game'). Reply with just the word."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(titulo):
    categorias_validas = list(CATEGORIAS_TAGS.keys())
    prompt = (
        f"Based on this gaming news title: '{titulo}', pick the most fitting category "
        f"among: {', '.join(categorias_validas)}. Reply ONLY with the category word."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return "console"


def gerar_titulo(titulo_original):
    prompt = (
        f"Create a fresh, catchy, SEO-optimized title in English, no quotation marks, "
        f"based on this gaming news: '{titulo_original}'. "
        f"Reply with just the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo(titulo_original, resumo, nome_fonte):
    prompt = f"""
You are a writer (who researches multiple sources) specialized in gaming in the broadest sense
possible: PC, console, mobile, arcade, board games, tabletop RPGs, card games, and esports, for
a highly engaged fan blog. You know all the latest news, know how to build reasoning, memory,
and a fun, funny writing style, digging into behind-the-scenes details, dropping a bit of gossip,
and building community. Write with high quality, no rush - really put care into it.

Rewrite this news item completely in your own words in English (never copy phrases verbatim),
(source: {nome_fonte}):
Original title: {titulo_original}
Original summary: {resumo}

IMPORTANT RULES:
- If the original information is short, EXPAND with real and relevant context: history of the
  franchise/studio/developer, well-known behind-the-scenes trivia, public reception, comparisons
  with previous games in the franchise or genre. DO NOT invent specific facts (dates, numbers,
  statements) you are not sure about - add real general knowledge as context, never specific
  fabrications.
- DO NOT be repetitive under any circumstance: every paragraph must bring new information,
  without restating what was already said in different words.
- Length: between 600 and 1200 words (can go over 1200 if the topic calls for it).

FORMATTING RULES (pure HTML, no Markdown):
1. Engaging opening paragraph.
2. AT LEAST 3 <h2> subheadings (e.g. context, details, fan reaction/expectations).
3. Insert 3 funny, light author's notes inside <blockquote> tags, commenting with gamer humor
   (never mean-spirited or offensive) spread throughout the post.
4. Always cite sources to build credibility.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


# --- RETRO MODE: used when no source has fresh news at the moment ---
def gerar_titulo_retro(evento):
    prompt = (
        f"Real fact: in {evento['ano']}, {evento['evento']}.\n\n"
        f"Create a nostalgic, engaging, catchy title in English for a gaming blog post about "
        f"this fact, no quotation marks, in the style of 'Were you born in [year]? Then you know "
        f"what happened in gaming' or '[X] years ago...' (calculate X from the given year, "
        f"current year is 2026). Reply with just the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo_retro(evento):
    prompt = f"""
You are a writer specialized in gaming (PC, console, mobile, arcade, board games, tabletop RPGs,
card games, and esports) for a highly engaged fan blog, focused on nostalgia and community.

There's no fresh news from any source today, so today's topic is a trip down memory lane: "on
this day in gaming history". This real, confirmed fact is the basis for the article (DO NOT
change the year or invent other specific facts like dates/numbers - use ONLY this fact as the
factual anchor):

Year: {evento['ano']}
Fact: {evento['evento']}

Write a nostalgic, engaging article in English about this fact, in a conversational style that
connects with the reader through fond memories - for example opening with something like "Were
you born in [year]? Then you know what was going on in gaming!" or "[calculate years until 2026]
years ago...". Explore:
- The context of the era (what else was happening in gaming and pop culture that year).
- Why this milestone mattered and how it influenced the games that came after.
- Well-known behind-the-scenes trivia about this fact (without inventing specific numbers you
  aren't sure about).
- Comparisons with today's gaming landscape - what changed, what still echoes today.

IMPORTANT RULES:
- DO NOT invent specific facts (dates, numbers, statements) beyond the fact provided.
- DO NOT be repetitive: every paragraph brings new information.
- Length: between 600 and 1000 words.

FORMATTING RULES (pure HTML, no Markdown):
1. Nostalgic, engaging opening paragraph that connects with the reader's fond memories.
2. AT LEAST 3 <h2> subheadings (e.g. the era's context, why it mattered, its legacy today).
3. Insert 3 funny, light author's notes inside <blockquote> tags, with nostalgic gamer humor
   (never mean-spirited or offensive) spread throughout the post.
4. End by inviting readers to share their own memories of that era in gaming.
"""
    return pedir_ia_groq(prompt, temperatura=0.8)


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Liked this update?</p>
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
    print("Buscando novidade de games...")
    titulo_original, resumo, link, fonte = pegar_novidade()

    if titulo_original:
        print(f"Encontrado em [{fonte}]: {titulo_original[:100]}...")
        try:
            categoria = identificar_categoria(titulo_original)
            tags = CATEGORIAS_TAGS.get(categoria, ["games"])

            novo_titulo = gerar_titulo(titulo_original)
            corpo = gerar_artigo(titulo_original, resumo, fonte)

            try:
                galeria, secoes_brutas = montar_galeria_ia(
                    novo_titulo,
                    corpo,
                    minimo=QTD_MIN_IMAGENS,
                    maximo=QTD_MAX_IMAGENS,
                    contexto_extra=f"Resumo da noticia (fonte: {fonte}): {resumo}",
                )
                img_html = gerar_tabela_imagem_blogger(galeria[0][0], novo_titulo)
                corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
                print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
            except Exception as e:
                print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
                palavra_chave = extrair_palavra_chave(titulo_original)
                img_url = buscar_imagem_openverse(palavra_chave)
                img_html = gerar_tabela_imagem_blogger(img_url, novo_titulo)

            cta = gerar_cta()

            rodape = (
                '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
                '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
                f'Original news source: <a href="{link}" rel="noopener noreferrer" target="_blank">{fonte}</a>'
                '</p>'
            )

            html_final = f"{img_html}{corpo}{cta}{rodape}"
            publicar_no_blogger(novo_titulo, html_final, tags)
            marcar_como_postada(link)
            print("Concluido!")
        except Exception as e:
            print(f"Erro durante geracao/publicacao: {e}")
    else:
        print("Nenhuma novidade nova encontrada nas fontes. Ativando modo retro (hoje na historia dos games)...")
        try:
            evento = escolher_evento_retro()
            print(f"Efemeride escolhida: {evento['ano']} - {evento['evento'][:80]}...")

            categoria = identificar_categoria(evento["evento"])
            tags = CATEGORIAS_TAGS.get(categoria, ["games"]) + ["retro games", "nostalgia"]
            tags = list(dict.fromkeys(tags))  # remove duplicatas mantendo a ordem

            novo_titulo = gerar_titulo_retro(evento)
            corpo = gerar_artigo_retro(evento)

            try:
                galeria, secoes_brutas = montar_galeria_ia(
                    novo_titulo,
                    corpo,
                    minimo=QTD_MIN_IMAGENS,
                    maximo=QTD_MAX_IMAGENS,
                    contexto_extra=f"Efemeride retro de {evento['ano']}: {evento['evento']}",
                )
                img_html = gerar_tabela_imagem_blogger(galeria[0][0], novo_titulo)
                corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
                print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
            except Exception as e:
                print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
                palavra_chave = extrair_palavra_chave(evento["evento"])
                img_url = buscar_imagem_openverse(palavra_chave)
                img_html = gerar_tabela_imagem_blogger(img_url, novo_titulo)

            cta = gerar_cta()

            rodape = (
                '<hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />'
                '<p style="color: #555555; font-size: 13px; font-style: italic; margin-top: 15px;">'
                'Retro content: no fresh news right now, so we brought you a blast from '
                'gaming history to cure your nostalgia.</p>'
            )

            html_final = f"{img_html}{corpo}{cta}{rodape}"
            publicar_no_blogger(novo_titulo, html_final, tags)
            marcar_evento_retro_usado(evento)
            print("Concluido (modo retro)!")
        except Exception as e:
            print(f"Erro durante geracao/publicacao do modo retro: {e}")
