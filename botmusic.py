"""
Bot de Música para Discord
---------------------------
Toca músicas do YouTube (e outros sites suportados pelo yt-dlp) em canais de voz.

Requisitos:
    pip install -r requirements.txt
    FFmpeg instalado e no PATH do sistema (https://ffmpeg.org/download.html)

Configuração:
    1. Crie um arquivo ".env" na mesma pasta com:
        DISCORD_TOKEN=seu_token_aqui
    2. Rode: python bot.py

Comandos (prefixo padrão "!"):
    !play <nome ou link>   -> toca ou adiciona música à fila
    !pause                 -> pausa a música atual
    !resume                -> retoma a música pausada
    !skip                  -> pula para a próxima da fila
    !queue                 -> mostra a fila atual
    !nowplaying            -> mostra a música tocando agora
    !volume <0-100>        -> ajusta o volume
    !stop                  -> para tudo e limpa a fila
    !leave                 -> desconecta o bot do canal de voz
"""

import asyncio
import os
import shutil
import tempfile
from collections import deque

import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ---------------------------------------------------------------------------
# Configurações do yt-dlp e do FFmpeg
# ---------------------------------------------------------------------------

YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",  # permite buscar por nome, não só por link
    "source_address": "0.0.0.0",
    "noprogress": True,
    "restrictfilenames": True,
    # Baixamos o áudio para um arquivo local antes de tocar, em vez de streamar
    # direto da URL do YouTube. As URLs de streaming do YouTube podem expirar
    # ou exigir condições de rede muito específicas, o que fazia o FFmpeg
    # "terminar" silenciosamente sem tocar nada. Baixando primeiro, evitamos
    # esse problema por completo.
    "outtmpl": os.path.join(tempfile.gettempdir(), "discord_music_bot_cache", "%(id)s.%(ext)s"),
}

os.makedirs(os.path.join(tempfile.gettempdir(), "discord_music_bot_cache"), exist_ok=True)

# --- Cookies do navegador (ajuda a evitar o erro "Sign in to confirm you're not a bot") ---
# Defina no .env: YTDL_COOKIES_BROWSER=chrome  (ou firefox, edge, brave, etc.)
# Feche o navegador antes de rodar o bot, ou o arquivo de cookies pode ficar bloqueado.
_cookies_browser = os.getenv("YTDL_COOKIES_BROWSER")
if _cookies_browser:
    YTDL_FORMAT_OPTIONS["cookiesfrombrowser"] = (_cookies_browser,)

# Alternativa: cookies exportados manualmente em formato Netscape (arquivo cookies.txt)
# Defina no .env: YTDL_COOKIES_FILE=cookies.txt
_cookies_file = os.getenv("YTDL_COOKIES_FILE")
if _cookies_file:
    YTDL_FORMAT_OPTIONS["cookiefile"] = _cookies_file

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)


class Song:
    """Representa uma música baixada, pronta para tocar."""

    def __init__(self, local_path: str, title: str, webpage_url: str,
                 duration: int, requester: str):
        self.local_path = local_path
        self.title = title
        self.webpage_url = webpage_url
        self.duration = duration
        self.requester = requester

    @classmethod
    async def from_query(cls, query: str, requester: str, loop=None):
        loop = loop or asyncio.get_event_loop()
        # baixa o áudio (bloqueante) em outra thread para não travar o bot
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(query, download=True)
        )

        if "entries" in data:
            # resultado de busca -> pega o primeiro item
            data = data["entries"][0]

        local_path = ytdl.prepare_filename(data)

        return cls(
            local_path=local_path,
            title=data.get("title", "Título desconhecido"),
            webpage_url=data.get("webpage_url", ""),
            duration=data.get("duration", 0),
            requester=requester,
        )

    def format_duration(self) -> str:
        if not self.duration:
            return "??:??"
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class GuildMusicState:
    """Guarda a fila e o estado de reprodução para UM servidor (guild)."""

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.queue: deque[Song] = deque()
        self.voice_client: discord.VoiceClient | None = None
        self.current: Song | None = None
        self.volume: float = 0.5
        self.play_next_event = asyncio.Event()
        self.player_task = bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()
        while True:
            self.play_next_event.clear()

            if not self.queue:
                # espera até algo ser adicionado à fila
                await asyncio.sleep(1)
                continue

            self.current = self.queue.popleft()
            print(f"[FILA] Retirando da fila para tocar: '{self.current.title}'. Restantes: {len(self.queue)}")

            if self.voice_client is None or not self.voice_client.is_connected():
                await asyncio.sleep(1)
                continue

            source = discord.FFmpegPCMAudio(self.current.local_path, options="-vn")
            source = discord.PCMVolumeTransformer(source, volume=self.volume)

            finished_song = self.current  # referência para limpar o arquivo depois

            def after_playing(error):
                if error:
                    print(f"[ERRO ao reproduzir '{finished_song.title}']: {error}")
                # remove o arquivo temporário baixado, já que não precisamos mais dele
                try:
                    if os.path.exists(finished_song.local_path):
                        os.remove(finished_song.local_path)
                except Exception as cleanup_err:
                    print(f"[AVISO] Não consegui apagar o arquivo temporário: {cleanup_err}")
                self.bot.loop.call_soon_threadsafe(self.play_next_event.set)

            try:
                self.voice_client.play(source, after=after_playing)
                print(f"[OK] Reprodução iniciada: {self.current.title}")
            except Exception as e:
                print(f"[ERRO ao iniciar reprodução de '{self.current.title}']: {e}")
                self.play_next_event.set()
                continue

            await self.play_next_event.wait()

    def add(self, song: Song):
        self.queue.append(song)
        print(f"[FILA] '{song.title}' adicionada. Tamanho da fila agora: {len(self.queue)}")

    def clear(self):
        self.queue.clear()

    def destroy(self):
        self.player_task.cancel()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}

    def get_state(self, guild: discord.Guild) -> GuildMusicState:
        if guild.id not in self.states:
            self.states[guild.id] = GuildMusicState(self.bot, guild)
        return self.states[guild.id]

    async def ensure_voice(self, ctx: commands.Context) -> GuildMusicState:
        state = self.get_state(ctx.guild)

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            raise commands.CommandError("Você precisa estar em um canal de voz para usar esse comando.")

        if state.voice_client is None or not state.voice_client.is_connected():
            state.voice_client = await ctx.author.voice.channel.connect()
        elif state.voice_client.channel != ctx.author.voice.channel:
            await state.voice_client.move_to(ctx.author.voice.channel)

        return state

    @commands.command(name="play", aliases=["p", "tocar"])
    async def play(self, ctx: commands.Context, *, query: str):
        """Toca uma música (nome ou link) ou adiciona à fila."""
        state = await self.ensure_voice(ctx)

        async with ctx.typing():
            try:
                song = await Song.from_query(query, requester=ctx.author.display_name, loop=self.bot.loop)
            except Exception as e:
                await ctx.send(f"❌ Não consegui encontrar/carregar essa música: `{e}`")
                return

            state.add(song)

        if state.current is not None or len(state.queue) > 1:
            await ctx.send(f"➕ Adicionado à fila: **{song.title}** ({song.format_duration()})")
        else:
            await ctx.send(f"🎶 Tocando agora: **{song.title}** ({song.format_duration()})")

    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context):
        """Pausa a música atual."""
        state = self.get_state(ctx.guild)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.pause()
            await ctx.send("⏸️ Música pausada.")
        else:
            await ctx.send("Não há nada tocando agora.")

    @commands.command(name="resume", aliases=["unpause"])
    async def resume(self, ctx: commands.Context):
        """Retoma a música pausada."""
        state = self.get_state(ctx.guild)
        if state.voice_client and state.voice_client.is_paused():
            state.voice_client.resume()
            await ctx.send("▶️ Música retomada.")
        else:
            await ctx.send("Não há música pausada.")

    @commands.command(name="skip", aliases=["s", "pular"])
    async def skip(self, ctx: commands.Context):
        """Pula a música atual."""
        state = self.get_state(ctx.guild)
        if state.voice_client and (state.voice_client.is_playing() or state.voice_client.is_paused()):
            state.voice_client.stop()  # dispara o callback "after", que libera a próxima da fila
            await ctx.send("⏭️ Música pulada.")
        else:
            await ctx.send("Não há nada tocando para pular.")

    @commands.command(name="queue", aliases=["q", "fila"])
    async def queue_cmd(self, ctx: commands.Context):
        """Mostra a fila de músicas."""
        state = self.get_state(ctx.guild)

        if not state.current and not state.queue:
            await ctx.send("A fila está vazia.")
            return

        lines = []
        if state.current:
            lines.append(f"🎶 **Tocando agora:** {state.current.title} ({state.current.format_duration()})")

        if state.queue:
            lines.append("\n**Próximas na fila:**")
            for i, song in enumerate(state.queue, start=1):
                lines.append(f"{i}. {song.title} ({song.format_duration()}) — pedido por {song.requester}")

        await ctx.send("\n".join(lines))

    @commands.command(name="nowplaying", aliases=["np", "tocando"])
    async def nowplaying(self, ctx: commands.Context):
        """Mostra a música tocando no momento."""
        state = self.get_state(ctx.guild)
        if state.current:
            await ctx.send(
                f"🎶 Tocando agora: **{state.current.title}** "
                f"({state.current.format_duration()}) — pedido por {state.current.requester}\n"
                f"{state.current.webpage_url}"
            )
        else:
            await ctx.send("Não há nada tocando agora.")

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx: commands.Context, volume: int):
        """Ajusta o volume (0 a 100)."""
        state = self.get_state(ctx.guild)

        if not 0 <= volume <= 100:
            await ctx.send("O volume deve estar entre 0 e 100.")
            return

        state.volume = volume / 100
        if state.voice_client and state.voice_client.source:
            state.voice_client.source.volume = state.volume

        await ctx.send(f"🔊 Volume ajustado para {volume}%.")

    @commands.command(name="stop", aliases=["parar"])
    async def stop(self, ctx: commands.Context):
        """Para a reprodução e limpa a fila."""
        state = self.get_state(ctx.guild)
        state.clear()
        if state.voice_client:
            state.voice_client.stop()
        await ctx.send("⏹️ Reprodução parada e fila limpa.")

    @commands.command(name="leave", aliases=["disconnect", "sair"])
    async def leave(self, ctx: commands.Context):
        """Desconecta o bot do canal de voz."""
        state = self.get_state(ctx.guild)
        state.clear()
        if state.voice_client:
            await state.voice_client.disconnect()
            state.voice_client = None
        await ctx.send("👋 Até mais!")


def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN não encontrado. Crie um arquivo .env com DISCORD_TOKEN=seu_token_aqui"
        )

    if shutil.which("ffmpeg") is None:
        print(
            "⚠️  AVISO: o executável 'ffmpeg' não foi encontrado no PATH do sistema.\n"
            "   O bot vai conectar e mostrar a música, mas NENHUM áudio vai tocar.\n"
            "   Instale o FFmpeg (ex: 'winget install ffmpeg' no Windows) e reinicie o terminal.\n"
        )

    intents = discord.Intents.default()
    intents.message_content = True  # necessário para ler comandos de texto

    bot = commands.Bot(command_prefix="<", intents=intents, help_command=commands.DefaultHelpCommand())

    @bot.event
    async def on_ready():
        print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")

    @bot.event
    async def on_command_error(ctx, error):
        await ctx.send(f"⚠️ {error}")

    async def setup():
        await bot.add_cog(Music(bot))

    async def runner():
        async with bot:
            await setup()
            await bot.start(TOKEN)

    asyncio.run(runner())


if __name__ == "__main__":
    main()