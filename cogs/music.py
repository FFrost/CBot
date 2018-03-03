import discord
from discord.ext import commands

from modules import checks

import asyncio, aiohttp
import time
import youtube_dl
from lxml import html
from urllib.parse import quote

# mostly stolen from PyVox (https://github.com/Hiroyu/_PyVox) and Rapptz's playlist example (https://github.com/Rapptz/discord.py/blob/async/examples/playlist.py)

class VoiceEntry:
    def __init__(self, message, player):
        self.author = message.author
        self.channel = message.channel
        self.player = player
        
    def get_info(self):
        return self.player.yt.extract_info(self.player.url, download=False)

    def __str__(self):
        duration = time.strftime("%H:%M:%S", time.gmtime(self.player.duration))
        return "**{title}** - [{duration}]".format(title=self.player.title, duration=duration)

class VoiceState:
    def __init__(self, bot):
        self.bot = bot
        
        self.voice_client = None
        
        self.current = None
        self.queue = asyncio.Queue()
        self.play_next_song = asyncio.Event()
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
        
    def is_playing(self):
        if (self.voice_client is None or self.current is None):
            return False
        
        return not (self.current.player.is_done())
    
    @property
    def player(self):
        return self.current.player
    
    def skip(self):
        if (self.is_playing()):
            self.player.stop()
        
    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)
        
    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.queue.get()
            
            yt_embed = None
            
            if (self.bot.utils.youtube_url_validation(self.player.url) is None):
                yt_embed = self.bot.utils.create_youtube_embed(self.current.get_info())
            
            await self.bot.send_message(self.current.channel, "Playing " + str(self.current), embed=yt_embed)
             
            self.current.player.start()
            await self.play_next_song.wait()
            
            if (not self.is_playing() and self.queue.empty()):
                self.disconnect()
            
    def disconnect(self):
        try:
            self.audio_player.cancel()
                
            if (self.voice_client):
                self.bot.loop.create_task(self.voice_client.disconnect())
            
        except Exception:
            pass

class Music:
    def __init__(self, bot):
        self.bot = bot
        
        # load opus library for voice
        if (not discord.opus.is_loaded()):
            discord.opus.load_opus("opus")
            
        self.voice_states = {}
        
    def __unload(self):
        for state in self.voice_states.values():
            state.disconnect()
    
    # returns the first video result from youtube with the given query
    async def get_first_yt_result(self, query):
        ydl = youtube_dl.YoutubeDL()
        
        url = "https://www.youtube.com/results?search_query=" + quote(query)
        
        conn = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url) as req:
                if (req.status == 200):
                    content = await req.text()
                    tree = html.fromstring(content)
                    results = tree.xpath("//div[@id='results']//h3[@class='yt-lockup-title ']//a/@href")
                    
                    if (not results):
                        return None, None
                    
                    for r in results:
                        if ("&list" in r): # ignore playlists
                            continue
                        
                        if (r.startswith("/watch")):
                            ret = "http://youtube.com" + r
                            
                            try:
                                info = ydl.extract_info(ret, download=False, process=False)
                                
                            except youtube_dl.utils.DownloadError: # video unavailable
                                continue
                            
                            except Exception as e:
                                await self.bot.messaging.error_alert(e)
                                continue
                            
                            return ret, info
                    
        return None, None
    
    # returns the first video result from youtube with the given query
    @commands.command(description="first YouTube result for given query",
                      brief="first YouTube result for given query",
                      pass_context=True,
                      aliases=["youtube"])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def yt(self, ctx, *, query : str):
        await self.bot.send_typing(ctx.message.channel)
        
        try:
            result, info = await self.get_first_yt_result(query)
            
        except aiohttp.errors.ClientOSError:
            await self.bot.messaging.reply(ctx.message, "Failed to connect to host (maybe try again)")
            return
        
        if (not result):
            await self.bot.messaging.reply(ctx.message, "No videos found for `{}`".format(query))
        else:
            if (info):
                embed = self.bot.utils.create_youtube_embed(info)
                
                await self.bot.send_message(ctx.message.channel, embed=embed)
            else:
                await self.bot.messaging.reply(ctx.message, "No info found for `{}` {}".format(query, result))
                
    @commands.command(description="plays a YouTube video over voice",
                      brief="plays a YouTube video over voice",
                      pass_context=True,
                      no_pm=True)
    @commands.check(checks.is_in_voice_channel)
    @commands.cooldown(1, 5, commands.BucketType.server)
    async def play(self, ctx, *, query : str=""): # TODO: if no query, find last video embed and play that
        if (not query):
            query = await self.bot.utils.find_last_youtube_embed(ctx.message)
            
            if (not query):
                await self.bot.messaging.reply(ctx.message, "No YouTube video found")
                return
        
        voice_channel = ctx.message.author.voice_channel
        
        voice_state = self.voice_states.get(ctx.message.server.id)
        voice_client_in_server = self.bot.voice_client_in(ctx.message.server)
        
        if (not voice_state):
            voice_state = VoiceState(self.bot)
        elif (voice_state is not None and voice_client_in_server is None):
            ctx.invoke(self.stop)
            voice_state = VoiceState(self.bot)
            voice_state.voice_client = await self.bot.join_voice_channel(voice_channel) 
        
        if (not voice_state.voice_client):
            voice_state.voice_client = voice_client_in_server
            
            if (not voice_state.voice_client):
                voice_state.voice_client = await self.bot.join_voice_channel(voice_channel)  
        elif (voice_state.voice_client.channel != voice_channel):
            await voice_state.voice_client.move_to(voice_channel)
        
        opts = {
            "default_search": "auto",
            "quiet": True,
            "noplaylist": True,
            }
        
        try:
            player = await voice_state.voice_client.create_ytdl_player(query, ytdl_options=opts, after=voice_state.toggle_next)
        except Exception as e:
            await self.bot.messaging.reply(ctx.message, "An error occured: {}".format(e))
        else:
            entry = VoiceEntry(ctx.message, player)
            
            if (not voice_state.queue.empty() or voice_state.is_playing()):
                await self.bot.messaging.reply(ctx.message, "Queued " + str(entry))
            
            await voice_state.queue.put(entry)
        
        self.voice_states[ctx.message.server.id] = voice_state
        
    # this command is intentionally left without the is_in_voice_channel check
    # in case the bot breaks and needs to be reset
    @commands.command(description="stops playing songs and clears the queue",
                      brief="stops playing songs and clears the queue",
                      pass_context=True,
                      no_pm=True)
    async def stop(self, ctx):
        voice_state = self.voice_states.get(ctx.message.server.id)
        
        if (voice_state.is_playing()):
            player = voice_state.player
            player.stop()
            
        try:
            voice_state.audio_player.cancel()
            del self.voice_states[ctx.message.server.id]
            await voice_state.voice_client.disconnect()
        except Exception as e:
            print(e)
            
    @commands.command(description="skips the currently playing song and plays the next song in queue",
                      brief="skips the currently playing song and plays the next song in queue",
                      pass_context=True,
                      no_pm=True)
    @commands.check(checks.is_in_voice_channel)
    async def skip(self, ctx):
        voice_state = self.voice_states.get(ctx.message.server.id)
        voice_state.skip()
    
def setup(bot):
    bot.add_cog(Music(bot))