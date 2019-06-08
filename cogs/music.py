"""
mostly stolen from https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34
"""

import discord
from discord.ext import commands

from modules import utils

import asyncio
import itertools
from functools import partial
from async_timeout import timeout
from youtube_dl import YoutubeDL
from youtube_dl import DownloadError

# TODO: necessary?
import sys
import traceback

ytdlopts = {
    "no_color": True,
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0" # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    "before_options": "-nostdin",
    "options": "-vn"
}

ytdl = YoutubeDL(ytdlopts)

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""

class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

        self.data = data

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=False)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title'], "data": data}

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

class MusicPlayer:
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(15):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)
            
            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'\n`{e}```\n')
                    continue

            self.current = source

            if (not self._guild.voice_client):
                continue

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))

            data = source.data

            if (data["extractor"].startswith("youtube")):
                embed = utils.create_youtube_embed(data, self.current.requester)
            elif (data["extractor"] == "soundcloud"):
                embed = utils.create_soundcloud_embed(data, self.current.requester)

            await self._channel.send(f"Playing **{source.title}**", embed=embed)

            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    # TODO: necessary?
    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    async def _connect(self, ctx):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise InvalidVoiceChannel("You must be in a voice channel to use this command")

        vc = ctx.voice_client

        if (vc):
            if (vc.channel.id == channel.id):
                return
            try:
                vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Timed out moving to <{channel}>")
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Timed out moving to <{channel}>")

    @commands.command(description="plays a video over voice, supported sites: " + \
                      "https://rg3.github.io/youtube-dl/supportedsites.html",
                      brief="plays a video over voice")
    async def play(self, ctx, *, query: str = ""):
        async with ctx.channel.typing():
            if (not query):
                query = await self.bot.bot_utils.find_last_youtube_embed(ctx.message)
                
                if (not query):
                    await ctx.channel.send(f"{ctx.author.mention} No YouTube video found")
                    return
            
            vc = ctx.voice_client

            if (not vc):
                await self._connect(ctx)

            player = self.get_player(ctx)

            source = await YTDLSource.create_source(ctx, query, loop=self.bot.loop)

            if (not player.queue.empty() or (ctx.voice_client is not None and ctx.voice_client.is_playing())):
                await ctx.send(f"{ctx.author.mention} Queued **{source['data']['title']}**")

            await player.queue.put(source)
    
    @commands.command(description="skips the currently playing song and plays the next song in queue",
                      brief="skips the currently playing song and plays the next song in queue")
    async def skip(self, ctx):
        vc = ctx.voice_client

        if (not vc or not vc.is_connected() or not vc.is_playing()):
            return

        title = vc.source.title

        vc.stop()

        await ctx.send(f"{ctx.author.mention} Skipped **{title}**")

    @commands.command(name="queue",
                      description="shows the queued songs",
                      brief="shows the queued songs")
    async def queue_info(self, ctx):
        vc = ctx.voice_client

        if (not vc or not vc.is_connected()):
            return await ctx.send(f"{ctx.author.mention} Not connected to voice")

        player = self.get_player(ctx)

        if (player.queue.empty()):
            return await ctx.send(f"{ctx.author.mention} No songs queued")

        queued = list(itertools.islice(player.queue._queue, 0, 7))
        desc = "\n".join(f"#{i + 1} - **{q['title']}**" for i, q in enumerate(queued))

        embed = discord.Embed(title="Queued", description=desc)

        await ctx.send(embed=embed)

    @commands.command(description="stops playing songs and clears the queue",
                      brief="stops playing songs and clears the queue")
    async def stop(self, ctx):
        vc = ctx.voice_client

        if (not vc or not vc.is_connected()):
            return

        await self.cleanup(ctx.guild)

    @commands.command(description="finds the first YouTube result for a given query",
                      brief="finds the first YouTube result for a given query",
                      aliases=["youtube"])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def yt(self, ctx, *, query: str):
        await ctx.trigger_typing()

        search_query = query

        if (not search_query.startswith("ytsearch:")):
            search_query = f"ytsearch:{query}"

        try:
            info = ytdl.extract_info(search_query, download=False, process=False)
        except DownloadError as e:
            await ctx.send(f"{ctx.author.mention} Failed to find `{query}`: {e}")
            return

        if (info.get("extractor_key") == "YoutubeSearch"):
            try:
                video_id = info.get("entries")[0].get("url")

                if (not video_id):
                    raise KeyError
            except (IndexError, KeyError, TypeError):
                await ctx.send(f"{ctx.author.mention} No results found for `{query}`")
                return
            else:
                url = f"https://youtube.com/watch?v={video_id}"
                info = ytdl.extract_info(url, download=False, process=False)

        embed = utils.create_youtube_embed(info, ctx.author)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Music(bot))
