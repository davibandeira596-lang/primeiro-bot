import random
import discord
from discord.ext import commands, tasks
from google import genai
from datetime import datetime, timedelta
import pytz
from settings import settings

# ==========================
# CONFIGURAÇÕES ADICIONAIS
# ==========================

# Insira aqui a sua chave de API do Gemini (se não quiser colocar direto nas settings)
GEMINI_API_KEY = settings.get("GEMINI_API_KEY", "SUA_CHAVE_GEMINI_AQUI")

# ID do canal onde o bot enviará os avisos automáticos de prova
CANAL_PROVAS = 1532137072775790692

# ID do canal onde o bot enviará as mensagens de boas-vindas
CANAL_BOAS_VINDAS = 123456789012345678  # <--- Substitua pelo ID do seu canal

# ==========================
# GEMINI & FUSO HORÁRIO
# ==========================

gemini = genai.Client(api_key=GEMINI_API_KEY)
fuso = pytz.timezone("America/Sao_Paulo")

# ==========================
# CALENDÁRIO DE PROVAS
# ==========================

calendario_provas = {
    "31/07": "Redação",
    "04/08": "Geografia",
    "07/08": "Matemática",
    "11/08": "Biologia",
    "12/08": "Sociologia",
    "14/08": "História",
    "17/08": "Inglês",
    "18/08": "Química",
    "21/08": "Arte",
    "28/08": "Português",
    "31/08": "Física",
    "01/09": "Filosofia",
    "04/09": "Ed. Digital"
}

avisos_enviados = []

# --- LÓGICA DO BOT (bot_logic) ---

def gen_pass(pass_length):
    caracteres = "+-/*!&$#?=@abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    senha = ""
    while len(senha) < pass_length:
        senha += random.choice(caracteres)
    return senha

def gen_emodji():
    emodji = ["\U0001f600", "\U0001f642", "\U0001F606", "\U0001F923", "\U0001F609", "\U0001F60A", "\U0001F60D", "\U0001F618", "\U0001F970",
              "\U0001F60E", "\U0001F917", "\U0001F92D", "\U0001F92A", "\U0001F92B",
              "\U0001F914", "\U0001F910", "\U0001F928", "\U0001F610", "\U0001F611",
              "\U0001F636", "\U0001F60C", "\U0001F61B", "\U0001F61C", "\U0001F61D",
              "\U0001F924", "\U0001F612", "\U0001F613", "\U0001F614", "\U0001F615", "\U0001F643", "\U0001F911", "\U0001F632", "\U0001F641",]
    return random.choice(emodji)

def flip_coin(num_flips):
    results = []
    for _ in range(num_flips):
        flip = random.randint(0, 1)
        results.append("cara" if flip == 0 else "coroa")
    return results

def cal_jokenpo(escolha_usuario):
    opcoes = ["pedra", "papel", "tesoura"]
    choice = random.choice(opcoes)
    if escolha_usuario == choice:
        return "Empate!"
    elif (escolha_usuario == "pedra" and choice == "tesoura") or \
         (escolha_usuario == "papel" and choice == "pedra") or \
         (escolha_usuario == "tesoura" and choice == "papel"):
        return "Você venceu!"
    else:
        return "Você perdeu!"

# --- CONFIGURAÇÃO E ESTRUTURA DO BOT (commands.Bot) ---

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=settings.get("prefix", "#"), intents=intents)

# ==========================
# AVISO AUTOMÁTICO DAS PROVAS
# ==========================

@tasks.loop(minutes=1)
async def verificar_provas():
    agora = datetime.now(fuso)

    # Só envia às 15:00
    if agora.hour != 15 or agora.minute != 0:
        return

    amanha = agora + timedelta(days=1)
    data_amanha = amanha.strftime("%d/%m")

    if data_amanha in calendario_provas and data_amanha not in avisos_enviados:
        materia = calendario_provas[data_amanha]
        canal = bot.get_channel(CANAL_PROVAS)

        if canal:
            await canal.send(
                f"📚 **Aviso de prova!**\n\n"
                f"Amanhã ({data_amanha}) tem prova de **{materia}**.\n\n"
                f"📖 Aproveite hoje para revisar.\n"
                f"Boa sorte! 🍀"
            )
            avisos_enviados.append(data_amanha)

# --- EVENTOS DO BOT ---

@bot.event
async def on_ready():
    print(f'Fizemos login como {bot.user} (ID: {bot.user.id})')
    print('------')
    
    # Inicia o loop de aviso de provas
    if not verificar_provas.is_running():
        verificar_provas.start()

@bot.event
async def on_member_join(member):
    """Envia uma mensagem de boas-vindas ao novo membro em um canal específico."""
    channel = bot.get_channel(CANAL_BOAS_VINDAS)
    if channel is not None:
        to_send = f'Welcome {member.mention} to {member.guild.name}!'
        await channel.send(to_send)

@bot.event
async def on_message(message):
    # Ignora mensagens enviadas por bots
    if message.author.bot:
        return

    # Processa todos os comandos registrados (ex: #oi, #provas, #soma, etc.)
    await bot.process_commands(message)

    # Lógica do Gemini (disparada quando o bot é mencionado diretamente e não é um comando)
    if bot.user in message.mentions and not message.content.startswith(bot.command_prefix):
        pergunta = message.content

        for mention in message.mentions:
            pergunta = pergunta.replace(mention.mention, "")

        pergunta = pergunta.strip()

        if not pergunta:
            await message.channel.send(f"Olá {message.author.mention}! Como posso ajudar?")
            return

        async with message.channel.typing():
            try:
                resposta = gemini.models.generate_content(
                    model="gemini-flash-latest",
                    contents=pergunta
                )

                texto = resposta.text

                while len(texto) > 2000:
                    await message.channel.send(texto[:2000])
                    texto = texto[2000:]

                if texto:
                    await message.channel.send(texto)

            except Exception as erro:
                print(erro)
                await message.channel.send(f"Erro: {erro}")

# --- COMANDOS CONVERTIDOS E EXISTENTES ---

@bot.command()
async def oi(ctx):
    """Responde com uma saudação."""
    await ctx.send('Olá! Eu sou um bot')

@bot.command()
async def hello(ctx):
    """Responde com uma saudação rápida."""
    await ctx.send("Olá! 👋")

@bot.command()
async def tchau(ctx):
    """Responde com uma despedida."""
    await ctx.send('Tchau! Até mais!')

@bot.command()
async def emoji(ctx):
    """Envia um emoji aleatório."""
    await ctx.send(gen_emodji())

@bot.command()
async def moeda(ctx, num_flips: int):
    """Joga uma moeda (cara ou coroa)."""
    await ctx.send(flip_coin(num_flips))

@bot.command()
async def senha(ctx, tamanho: int):
    """Gera uma senha aleatória com o tamanho especificado."""
    await ctx.send(gen_pass(tamanho))

@bot.command()
async def soma(ctx, a: float, b: float):
    """Soma dois números."""
    await ctx.send(a + b)

@bot.command()
async def subtrair(ctx, a: float, b: float):
    """Subtrai dois números."""
    await ctx.send(a - b)

@bot.command()
async def multiplicar(ctx, a: float, b: float):
    """Multiplica dois números."""
    await ctx.send(a * b)

@bot.command()
async def dividir(ctx, a: float, b: float):
    """Divide dois números."""
    if b == 0:
        await ctx.send("Não é possível dividir por zero!")
    else:
        await ctx.send(a / b)

@bot.command()
async def rolar(ctx, dice: str):
    """Rolls a dice in NdN format."""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await ctx.send('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await ctx.send(result)

@bot.command(description='For when you wanna settle the score some other way')
async def escolha(ctx, *choices: str):
    """Chooses between multiple choices."""
    await ctx.send(random.choice(choices))

@bot.command()
async def entrada(ctx, member: discord.Member):
    """Says when a member joined."""
    if member.joined_at is None:
        await ctx.send(f'{member} has no join date.')
    else:
        await ctx.send(f'{member} joined {discord.utils.format_dt(member.joined_at)}')

@bot.command()
async def repetir(ctx, times: int, content='repeating...'):
    """Repeats a message multiple times."""
    for i in range(times):
        await ctx.send(content)

@bot.command()
async def jokenpo(ctx, escolha: str):
    """Joga jokenpo (pedra, papel ou tesoura)."""
    await ctx.send(cal_jokenpo(escolha.lower()))

@bot.command()
async def provas(ctx):
    """Exibe o calendário completo de provas."""
    texto = "📚 **Calendário de Provas**\n\n"
    for data, materia in calendario_provas.items():
        texto += f"📅 {data} - {materia}\n"
    await ctx.send(texto)

@bot.command()
async def melhor(ctx, name: str):
    """dizer que algo é o melhor."""
    await ctx.send(f"O {name} é o melhor!")

# --- AJUDA / HELP ---

bot.remove_command('help')

@bot.command(name="ajuda", aliases=["help"])
async def ajuda(ctx):
    """Exibe a lista de comandos disponíveis e como usá-los."""
    p = bot.command_prefix
    embed = discord.Embed(
        title="🤖 Central de Ajuda do Bot",
        description="Aqui estão todos os comandos disponíveis e como utilizá-los:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="👋 Interações Básicas",
        value=f"`{p}oi` / `{p}hello` - Recebe uma saudação.\n"
              f"`{p}tchau` - Despedida do bot.\n"
              f"`{p}emoji` - Envia um emoji aleatório.\n"
              f"`@Bot <pergunta>` - Conversa com a IA do Gemini.",
        inline=False
    )

    embed.add_field(
        name="📖 Escolar / Provas",
        value=f"`{p}provas` - Mostra o calendário completo das provas.",
        inline=False
    )

    embed.add_field(
        name="🎲 Jogos e Sorteios",
        value=f"`{p}moeda [quantidade]` - Joga moedas (ex: `{p}moeda 3`).\n"
              f"`{p}jokenpo <pedra|papel|tesoura>` - Joga pedra, papel ou tesoura.\n"
              f"`{p}rolar <NdN>` - Rola dados no formato RPG (ex: `{p}rolar 2d6`).\n"
              f"`{p}escolha <opção1> <opção2>...` - Escolhe um item aleatório.",
        inline=False
    )

    embed.add_field(
        name="🧮 Úteis & Matemática",
        value=f"`{p}senha [tamanho]` - Gera uma senha segura (padrão: 10 caracteres).\n"
              f"`{p}soma <num1> <num2>` - Soma dois números.\n"
              f"`{p}subtrair <num1> <num2>` - Subtrai dois números.\n"
              f"`{p}multiplicar <num1> <num2>` - Multiplica dois números.\n"
              f"`{p}dividir <num1> <num2>` - Divide dois números.",
        inline=False
    )

    embed.add_field(
        name="musical 🎵",
        value=f"`<tocar <nome ou link>` - toca ou adiciona música à fila.\n"
              f"`<pause` - pausa a música atual.\n"
              f"`<resume` - retoma a música pausada.\n"
              f"`<pular` - Pula a música atual.\n"
              f"`<fila` - Mostra a fila de músicas.\n"
              f"`<tocando` - Mostra a música tocando no momento.\n"
              f"`<volume <0-100>` - Ajusta o volume.\n"
              f"`<parar` - Para a reprodução e limpa a fila.\n"
              f"`<sair` - Desconecta o bot do canal de voz.",
        inline=False
    )

    embed.add_field(
        name="📱 Outros",
        value=f"`{p}repetir <quantidade> [mensagem]` - Repete uma mensagem várias vezes.\n"
              f"`{p}entrada <@usuário>` - Mostra quando um usuário entrou no servidor.",
        inline=False
    )

    embed.set_footer(text="Dica: Parâmetros entre < > são obrigatórios e [ ] são opcionais.")

    await ctx.send(embed=embed)

# Execução do Bot utilizando a chave TOKEN do dicionário de configurações
bot.run(settings["TOKEN"])
