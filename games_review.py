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
MODELO_IA = "openai/gpt-oss-120b"

# --- AI IMAGE GENERATION (Pollinations.ai) ---
# Optional: if not configured, or if any step fails, the script automatically
# falls back to the old method (Openverse image search).
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # optional: removes watermark and raises the rate limit
# Without a token: 1 request every 15s. With a free token (auth.pollinations.ai): every 5s.
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
QTD_MIN_IMAGENS = 5
QTD_MAX_IMAGENS = 10

# --- Blogger tags/labels by category (the AI picks the right one) ---
CATEGORIAS_TAGS = {
    "console-retro": ["retro games", "classic console", "nostalgia"],
    "console-moderno": ["console", "playstation", "xbox", "nintendo"],
    "pc": ["pc gaming", "games", "steam"],
    "arcade": ["arcade", "arcade games", "pinball"],
    "mobile": ["mobile games", "phone gaming", "games"],
    "tabuleiro": ["board game", "tabletop game"],
    "card": ["card game", "tcg", "collectible"],
    "rpg-mesa": ["tabletop rpg", "rpg", "tabletop"],
    "rua": ["street games", "childhood games", "nostalgia"],
    "vr": ["virtual reality", "vr games", "technology"],
    "crossover": ["games in pop culture", "movies and tv", "games"],
    "esports": ["esports", "competitive gaming", "games"],
}

# --- BASE LIST OF GAMING TOPICS (full history: street, board, arcade, consoles, PC, mobile, VR) ---
TEMAS = [
    # --- THE PREHISTORY AND BIRTH OF VIDEO GAMES ---
    "'Tennis for Two' (1958), one of the earliest electronic games in history",
    "the creation of 'Pong' by Atari and the birth of the video game industry",
    "the Magnavox Odyssey, the first home console in history",
    "'Space Invaders' and the craze that swept arcades around the world",
    "the birth of 'Pac-Man' and its impact on pop culture",
    "'Donkey Kong' and the debut of the character who would become Mario",
    "the video game crash of 1983 and how it nearly ended the industry in the US",
    "the rise and fall of arcades as a social gathering place",
    "the history of pinball before video games existed",
    "the early arcade games that defined entire genres",

    # --- CLASSIC CONSOLES (ATARI, NES, MASTER SYSTEM) ---
    "the Atari 2600 console and the revolution of interchangeable cartridges",
    "the worldwide legacy of Atari clones and bootleg consoles",
    "the NES (Nintendo Entertainment System) and how it rescued the industry after the crash",
    "the Sega Master System and its unique, wildly successful run in Brazil under local distributor Tectoy - one of gaming's strangest regional success stories",
    "the exclusive Brazilian-made games created for the Master System, unknown to most of the world",
    "the Nintendo vs Sega rivalry at its peak in the 80s and 90s",
    "the history of the Game & Watch, Nintendo's first handhelds",
    "hidden NES classics that few people know about",
    "video rental store culture and renting game cartridges in the 80s and 90s",
    "the history of gaming magazines and 90s games journalism (Nintendo Power, EGM)",

    # --- THE 16-BIT WAR (SNES, GENESIS) ---
    "the console war of the 90s: Super Nintendo vs Sega Genesis",
    "the Super Nintendo (SNES) and its legendary library of RPGs and platformers",
    "the Sega Genesis and Sonic the Hedgehog's charisma as Sega's answer to Nintendo",
    "the fighting games that dominated the SNES and Genesis",
    "the arrival of Chrono Trigger and the golden age of 16-bit RPGs",
    "Street Fighter II and the explosion of fighting games at home",
    "the bizarre accessories of the 16-bit era (Power Glove, Sega CD, 32X)",
    "the chiptune soundtracks of 16-bit consoles and their musical legacy",

    # --- ARCADE AND PINBALL ---
    "arcade culture around the world in the 80s and 90s",
    "the arcade fighting games that defined generations (Street Fighter, King of Fighters)",
    "light gun rail shooters that defined arcade cabinets",
    "classic pinball machines and their golden era",
    "the rhythm game phenomenon in arcades (Dance Dance Revolution)",
    "high score chasing and the competitive culture of classic arcades",

    # --- 3D CONSOLES (PS1, N64, SATURN, DREAMCAST) ---
    "the PlayStation 1 and Sony's overwhelming entry into the industry",
    "the Nintendo 64 and its pioneering analog stick and 3D games",
    "the Sega Saturn and why it couldn't compete with the PS1",
    "the Sega Dreamcast, the console ahead of its time that Sega discontinued too soon",
    "the Neo Geo, the most expensive and exclusive console of the 90s",
    "the Game Gear and Sega's attempt to compete with the Game Boy",
    "Final Fantasy VII and the 3D RPG revolution on the PS1",
    "Resident Evil and the birth of the survival horror genre",
    "Metal Gear Solid and Hideo Kojima's interactive cinema",
    "Crash Bandicoot and the exclusive mascots of the PS1 era",
    "Spyro the Dragon and 3D platformers of the PS1 era",
    "Tekken 3 and the evolution of 3D fighting games",
    "GoldenEye 007 and the revolution of console FPS games on the N64",
    "Ocarina of Time and why it's considered one of the greatest games of all time",
    "Banjo-Kazooie and Rare's golden age of 3D platformers",

    # --- PS2/XBOX/GAMECUBE GENERATION ---
    "the PlayStation 2, the best-selling console in history",
    "Microsoft's entry into the industry with the original Xbox",
    "the GameCube and Nintendo's bold (and misunderstood) gamble",
    "GTA San Andreas and the explosion of open-world games",
    "GTA III and the revolution that redefined the sandbox genre",
    "Halo: Combat Evolved and the birth of a phenomenon on Xbox",
    "Shadow of the Colossus and minimalist art in video games",
    "God of War (2005) and the stylized brutality of the PS2 era",
    "Silent Hill 2 and psychological horror in video games",
    "Devil May Cry and the creation of the stylish hack-and-slash genre",

    # --- PS3/XBOX 360/WII GENERATION ---
    "the PlayStation 3 vs Xbox 360 console war",
    "the Nintendo Wii and the motion control revolution",
    "Wii Sports and how it changed who played video games",
    "Call of Duty 4: Modern Warfare and the golden age of military FPS games",
    "BioShock and the philosophical storytelling inside Rapture",
    "Portal and GLaDOS's dark sense of humor",
    "The Elder Scrolls V: Skyrim and the obsession with giant open worlds",
    "Red Dead Redemption and the western genre in video games",
    "The Last of Us and the emotional storytelling that elevated games to art",
    "Dark Souls and Hidetaka Miyazaki's creation of the Soulslike genre",
    "Minecraft and how an indie block-building game conquered the world",
    "Rock Band and Guitar Hero and the music game craze",
    "the indie phenomenon Braid and the turning point for auteur-driven games",

    # --- PS4/XBOX ONE/SWITCH GENERATION ---
    "the PlayStation 4 and how Sony won back players' trust",
    "the Xbox One and Microsoft's rocky launch missteps",
    "the Nintendo Switch and the genius of merging handheld and home console",
    "Zelda: Breath of the Wild and the reinvention of the franchise formula",
    "God of War (2018) and Kratos reinvented as a father",
    "Bloodborne and From Software's gothic horror",
    "Elden Ring and how From Software conquered the mainstream",
    "Red Dead Redemption 2 and Rockstar's obsessive realism",
    "Grand Theft Auto V and why it never leaves the sales charts",
    "the battle royale phenomenon: from PUBG to Fortnite",
    "Among Us and the unexpected explosion of an indie game during the pandemic",
    "Hollow Knight and the new golden age of indie metroidvanias",
    "Undertale and subverting expectations in indie RPGs",
    "Stardew Valley and the revival of farming games",
    "Celeste and representation and difficulty in platform games",

    # --- CURRENT GENERATION (PS5, XBOX SERIES, AND THE FUTURE) ---
    "the PlayStation 5 and the era of ultra-fast SSD gaming",
    "the Xbox Series X/S and the Game Pass subscription strategy",
    "Baldur's Gate 3 and the triumphant return of classic RPGs",
    "Zelda: Tears of the Kingdom and the evolution of physics in games",
    "the rumors and expectations around the next console generation (what's being speculated about a PS6 and the future of Xbox)",
    "the anticipation and everything known so far about GTA VI",
    "the evolution of the Grand Theft Auto franchise from GTA 1 to today",
    "the impact of live-service games on today's industry",
    "the rise of remakes and remasters as an industry strategy",

    # --- HANDHELDS (GAME BOY, PSP, DS, VITA, N-GAGE) ---
    "the Game Boy and how it dominated handhelds for over a decade",
    "Pokemon Red and Blue and the birth of one of pop culture's biggest phenomena",
    "the Nintendo DS and the dual screen that reinvented handheld gaming",
    "the Nintendo 3DS and its risky bet on glasses-free 3D",
    "the Nintendo DSi and the quiet evolution of the DS line",
    "the PSP (PlayStation Portable) and Sony's attempt to dominate handhelds",
    "the PS Vita and why it's remembered as an underrated console",
    "the Nokia N-Gage, the bizarre hybrid between a phone and a handheld console",
    "the most memorable Game Boy Color and Game Boy Advance games",
    "the nostalgia of handheld games carried around in a school backpack",

    # --- MOBILE GAMES ---
    "the rise of mobile gaming and how it changed who plays video games",
    "Angry Birds and the explosion of casual mobile games",
    "Candy Crush and the addictive formula of mobile puzzle games",
    "Clash of Clans and the birth of competitive mobile strategy games",
    "Pokemon GO and the augmented reality revolution on the streets",
    "Free Fire and the mobile battle royale phenomenon in emerging markets",
    "Genshin Impact and the ambition of an open-world RPG on mobile",
    "classic Nokia phone games like Snake and the nostalgia of early mobile phones",
    "the economics of free-to-play games and microtransactions",

    # --- STREET GAMES AND PHYSICAL PLAY ---
    "the history and regional variations of tag around the world",
    "hide-and-seek and why this game crosses generations",
    "hopscotch and its surprisingly ancient origins",
    "dodgeball and its enduring popularity in schools around the world",
    "capture the flag and its regional variations across different countries",
    "jump rope games and rhyme-based playground traditions around the world",
    "improvised street bowling and other games made from recycled materials",
    "ring games and traditional children's singing games",
    "marbles and its golden era in schoolyards",
    "kite flying as both a pastime and a popular competition",

    # --- BOARD GAMES ---
    "the origin of Monopoly and the dispute over who really invented it",
    "The Game of Life and its journey of more than 160 years",
    "Risk and the addictive thrill of world domination on a board",
    "Cluedo (Clue) and the birth of deduction games",
    "Chess and its millennia-old history as the ultimate strategy game",
    "Checkers and its deceptively deep simplicity",
    "Uno and how a simple card game became a worldwide phenomenon",
    "Dominoes and its popularity worldwide, from bars to family game nights",
    "Monopoly's countless themed and licensed editions over the decades",
    "Trivial Pursuit and the golden age of quiz board games in the 90s and 2000s",
    "Pictionary and Charades and the family party game craze",
    "Catan and the revolution of modern board games (euro games)",

    # --- CARD GAMES AND COLLECTIBLES ---
    "the creation of Magic: The Gathering and the birth of collectible card games",
    "the Pokemon Trading Card Game and the craze for collecting and trading cards",
    "Yu-Gi-Oh! and how the anime powered one of the world's biggest TCGs",
    "Poker and its journey from smoky saloons to a global televised sport",
    "classic card decks and popular games like rummy, whist, and solitaire",
    "the culture of competitive card game tournaments around the world",
    "Hearthstone and the successful digital adaptation of card games",

    # --- TABLETOP RPG ---
    "the creation of Dungeons & Dragons and the birth of the tabletop RPG",
    "Vampire: The Masquerade and the personal horror RPGs of the 90s",
    "GURPS and the philosophy of a generic, flexible RPG system",
    "the culture of RPG tables and the community built around game masters and players",
    "how tabletop RPGs directly influenced electronic RPGs",
    "the rise of tabletop RPG livestreams and podcasts (Critical Role style)",

    # --- VIRTUAL REALITY ---
    "the history and failed attempts at virtual reality in the 90s",
    "PSVR and Sony's bet on virtual reality for consoles",
    "the Meta Quest and the popularization of standalone, wireless VR",
    "the games that defined what virtual reality can offer",
    "the future of virtual and augmented reality in games",

    # --- GAMES IN POP CULTURE: MOVIES, TV, AND CROSSOVERS ---
    "the TV adaptation of 'The Last of Us' and its reception",
    "'The Super Mario Bros. Movie' and the long history of trying to adapt games to film",
    "the animated series 'Arcane', based on the League of Legends universe",
    "the 'Fallout' series and its adaptation of the post-apocalyptic game universe",
    "the 'Sonic the Hedgehog' movie and the winning formula behind recent adaptations",
    "the 'Mortal Kombat' movies and the long history of adapting the fighting game",
    "the 'Pokemon' anime and its lasting impact beyond the games",
    "the 'Cyberpunk: Edgerunners' series and how it saved the game's reputation",
    "video games based on movies and TV shows and their reputation for dubious quality",
    "easter eggs and cross-references between gaming franchises and film",

    # --- ESPORTS AND COMPETITIVE CULTURE ---
    "the origins of esports and the first competitive video game tournaments",
    "the history of League of Legends and its rise as the world's biggest esport",
    "the competitive Counter-Strike scene, from 1.6 to CS2",
    "Dota 2 and The International tournament with its multi-million dollar prize pools",
    "LAN party culture in the 2000s and the birth of competitive gaming scenes around the world",
    "Free Fire and the explosion of mobile esports in emerging markets",
]

ARQUIVO_HISTORICO = "history_games_review_en.txt"


def tema_ja_usado(tema):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    # Evita repetir o mesmo tema exato nos últimos 30 ciclos (lista bem maior agora)
    return tema in linhas[-30:]


def marcar_tema_usado(tema):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(tema + "\n")


def escolher_tema():
    disponiveis = [t for t in TEMAS if not tema_ja_usado(t)]
    if not disponiveis:
        disponiveis = TEMAS
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
            headers={"User-Agent": "RoboResenhaJogos/1.0"},
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
   consistency with the overall theme (nostalgic/documentary tone).

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
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=1400, palavras_por_imagem_extra=250)
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


def pedir_ia_groq(prompt, temperatura=0.7, max_tokens=None):
    kwargs = {
        "messages": [{"role": "user", "content": prompt}],
        "model": MODELO_IA,
        "temperature": temperatura,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = groq_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


def gerar_esqueleto(instrucao_tema):
    """STEP 1: Rolls a random angle and asks for a detailed skeleton.
    Injecting the angle guarantees fresh posts going forward."""
    
    angulos = [
        "Behind-the-Scenes and Development Focus (how it was made, production struggles, the team, creation secrets).",
        "Critical and Thematic Analysis (what made this game/console/pastime work, design, mechanics, symbolism).",
        "Cultural Impact and Legacy (how it changed the industry, genre-defining revolution, works it influenced).",
        "Little-Known Trivia and Easter Eggs (odd facts, easy-to-miss details, myths and truths).",
        "Nostalgic Perspective and Regional Reception (how it landed in different parts of the world, localization/dubbing, the fan craze at the time, LAN parties, video rental stores).",
        "Comparison with Today's Landscape (what changed, what still influences games/pastimes today, what feels dated now)."
    ]
    angulo_sorteado = random.choice(angulos)
    
    prompt = f"""
You are a documentary screenwriter covering the history of games in the broadest sense: PC and
console video games, arcade games, board games, card games, tabletop RPGs, street games, mobile
games, and virtual reality.

Today's central topic: {instrucao_tema}

⚠️ MANDATORY ANGLE FOR TODAY'S PIECE:
"{angulo_sorteado}"

First, BEFORE writing the article, put together a detailed SKELETON guided by that angle:
- Confirm the main topic and the chosen angle.
- List 6 to 8 topics/sections the article will cover (enough for a long, dense article).
- For each topic, write 1-2 sentences summarizing what will be covered, WITHOUT repeating information.

Reply with just that skeleton, in plain text (no HTML).
"""
    return pedir_ia_groq(prompt, temperatura=0.6)


def gerar_artigo_completo(esqueleto):
    """STEP 2: Requests the full article using the skeleton as a mandatory guide."""
    prompt = f"""
You are an award-winning games writer, a true chronicler! You write documentary-style/review
articles for a highly engaged fan blog about games in all their forms: PC and console video
games, arcade, board games, card games, tabletop RPGs, street games, mobile, and VR. Write with
GREAT care, no rush - this is a flagship article for the blog.
You research deeply, know how to build reasoning, memory, and a pleasant, funny writing style,
digging into behind-the-scenes details, dropping a bit of gossip, and building community.

Use this skeleton as a MANDATORY guide, developing each of its topics in depth, without
skipping any and without repeating information between sections:

{esqueleto}

CONTENT RULES:
- Base the article on real historical and cultural facts about the topic. DO NOT invent dates or numbers you're not sure about.
- Write in an enjoyable, engaging way, with a nostalgic, conversational tone that builds community.
- REPEATING the same sentence or idea is FORBIDDEN. Every paragraph must move the narrative forward.
- If the topic involves future releases or rumors (e.g. next console generation), make it clear
  in the text that this is speculation/expectation, not confirmed fact.
- MANDATORY length: AT LEAST 1600 words. Develop each section well - if needed, go deeper into
  trivia, comparisons, and historical context to reach that length with quality, without
  padding or repetition.

FORMATTING RULES (pure HTML, no Markdown):
1. Start directly with an intriguing opening paragraph (no h1).
2. Each skeleton topic becomes its own <h2> subheading.
3. Include AT LEAST 3 funny, light author's notes, each inside a <blockquote>, with nostalgic
   gamer-fan commentary, spread throughout the post.
4. Do not include links in the body text.
5. End with a reflective closing paragraph about the topic's legacy, inviting readers to share
   their own memories or opinions in the comments.
"""
    return pedir_ia_groq(prompt, temperatura=0.75)


def gerar_titulo(esqueleto):
    prompt = (
        f"Based on this article skeleton:\n{esqueleto}\n\n"
        f"Create an engaging, nostalgic, SEO-optimized blog title in English, no quotation "
        f"marks. Reply with just the title, plain text."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def extrair_palavra_chave(esqueleto):
    prompt = (
        f"Based on this article skeleton:\n{esqueleto}\n\n"
        f"Give just ONE keyword in English that visually describes the main topic "
        f"(e.g. 'retro console', 'arcade cabinet', 'board game', 'tabletop rpg', 'vintage video game'). "
        f"Reply with just the word."
    )
    return pedir_ia_groq(prompt, temperatura=0.3).strip().lower().split()[0]


def identificar_categoria(esqueleto):
    categorias_validas = list(CATEGORIAS_TAGS.keys())
    prompt = (
        f"Based on this article skeleton about games:\n{esqueleto}\n\n"
        f"Pick the most fitting category among: {', '.join(categorias_validas)}. "
        f"Reply ONLY with the category word."
    )
    resposta = pedir_ia_groq(prompt, temperatura=0.2).strip().lower()
    for cat in categorias_validas:
        if cat in resposta:
            return cat
    return "console-retro"


def gerar_cta():
    return """
<div style="background-color: #f4f6f8; border-radius: 12px; margin: 30px 0; padding: 25px; text-align: center; font-family: sans-serif;">
    <p style="font-size: 17px; font-weight: bold; color: #333; margin: 0 0 10px 0;">Enjoyed this trip down memory lane?</p>
    <p style="font-size: 14px; color: #555; margin: 0 0 15px 0;">Like it, drop a comment sharing your own memories, and share it with someone who'll feel nostalgic too!</p>
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
    print("Gerando resenha/documentario de games...")
    instrucao_tema = escolher_tema()
    print(f"Tema sorteado: {instrucao_tema}")

    esqueleto = gerar_esqueleto(instrucao_tema)
    print("Esqueleto e ângulo gerados. Escrevendo artigo completo...")

    corpo = gerar_artigo_completo(esqueleto)
    titulo = gerar_titulo(esqueleto)

    categoria = identificar_categoria(esqueleto)
    tags = CATEGORIAS_TAGS.get(categoria, ["games"]) + ["review", "documentary", "games"]
    tags = list(dict.fromkeys(tags))  # remove duplicates while keeping order

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"Esqueleto/tema do artigo: {esqueleto[:600]}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
    except Exception as e:
        print(f"Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
        palavra_chave = extrair_palavra_chave(esqueleto)
        img_url = buscar_imagem_openverse(palavra_chave)
        img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    cta = gerar_cta()

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">This article is cultural, '
        'historical, and opinion-based content about games, for entertainment and nostalgia purposes.</p>'
    )

    html_final = f"{img_html}{corpo}{cta}{aviso}"
    publicar_no_blogger(titulo, html_final, tags)
    marcar_tema_usado(instrucao_tema)
    print("Concluído com sucesso!")
