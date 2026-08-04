from settings import settings
import discord
# import * - isso é o mesmo que listar todos os arquivos
from bot_logic import *

# Variáveis de intenção - armazena privilégios do bot
intents = discord.Intents.default()
# Habilita o privilégio de ler mensagens
intents.message_content = True
# Criamos um bot na variável do cliente e passamos todos os privilégios
client = discord.Client(intents=intents)


# Quando o bot estiver pronto, ele escreverá seu nome no console!
@client.event
async def on_ready():
    print(f'Fizemos login como {client.user}')


# Quando o bot recebe uma mensagem, ele envia algumas mensagens para o mesmo canal!
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('#oi'):
        await message.channel.send('Olá! Eu sou um bot')
    elif message.content.startswith('#emoji'):
        await message.channel.send(gen_emodji())
    elif message.content.startswith('#moeda'):
        await message.channel.send(flip_coin())
    elif message.content.startswith('#senha'):
        await message.channel.send(gen_pass(10))
    else:
        await message.channel.send("Não entendo esse comando!")

client.run(settings["TOKEN"])()


    