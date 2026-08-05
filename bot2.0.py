import random
import discord
from discord.ext import commands
from settings import settings

# --- LÓGICA DO BOT (bot_logic) ---

def gen_pass(pass_length):
    caracteres = "+-/*!&$#?=@abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    senha = ""
    while len(senha) < pass_length:
        senha += random.choice(caracteres)
    return senha

def gen_emodji():
    emodji = ["\U0001f600", "\U0001f642", "\U0001F606", "\U0001F923"]
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
intents.message_content = True

bot = commands.Bot(command_prefix=settings.get("prefix", "#"), intents=intents)

@bot.event
async def on_ready():
    print(f'Fizemos login como {bot.user} (ID: {bot.user.id})')
    print('------')

# --- COMANDOS CONVERTIDOS ---

@bot.command()
async def oi(ctx):
    """Responde com uma saudação."""
    await ctx.send('Olá! Eu sou um bot')

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
    # Joined at can be None in very bizarre cases so just handle that as well
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

bot.remove_command('help')

@bot.command(name="ajuda", aliases=["help"])
async def ajuda(ctx):
    """Exibe a lista de comandos disponíveis e como usá-los."""
    embed = discord.Embed(
        title="🤖 Central de Ajuda do Bot",
        description="Aqui estão todos os comandos disponíveis e como utilizá-los:",
        color=discord.Color.blue()
    )

    # Adiciona seções de comandos na mensagem
    embed.add_field(
        name="👋 Interações Básicas",
        value="`>oi` - Recebe uma saudação.\n"
              "`>tchau` - Despedida do bot.\n"
              "`>emoji` - Envia um emoji aleatório.",
        inline=False
    )

    embed.add_field(
        name="🎲 Jogos e Sorteios",
        value="`>moeda [quantidade]` - Joga moedas (ex: `>moeda 3`).\n"
              "`>jokenpo <pedra|papel|tesoura>` - Joga pedra, papel ou tesoura.\n"
              "`>rolar <NdN>` - Rola dados no formato RPG (ex: `>rolar 2d6`).\n"
              "`>escolha <opção1> <opção2>...` - Escolhe um item aleatório.",
        inline=False
    )

    embed.add_field(
        name="🧮 Úteis & Matemática",
        value="`>senha [tamanho]` - Gera uma senha segura (padrão: 10 caracteres).\n"
              "`>soma <num1> <num2>` - Soma dois números.\n"
              "`>subtrair <num1> <num2>` - Subtrai dois números.\n"
              "`>multiplicar <num1> <num2>` - Multiplica dois números.\n"
              "`>dividir <num1> <num2>` - Divide dois números.",
        inline=False
    )

    embed.add_field(
        name="📱 Outros",
        value="`>repetir <quantidade> [mensagem]` - Repete uma mensagem várias vezes.\n"
              "`>entrada <@usuário>` - Mostra quando um usuário entrou no servidor.\n",
        inline=False
    )

    embed.set_footer(text="Dica: Parâmetros entre < > são obrigatórios e [ ] são opcionais.")

    await ctx.send(embed=embed)

# Execução do Bot utilizando a chave TOKEN do dicionário de configurações
bot.run(settings["TOKEN"])
