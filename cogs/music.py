import discord
from discord.ext import commands

import asyncio, aiohttp
from lxml import html
import youtube_dl
from urllib.parse import quote

# inspired by PyVox (https://github.com/Hiroyu/_PyVox) and Rapptz's playlist example (https://github.com/Rapptz/discord.py/blob/async/examples/playlist.py)

class Music:
    def __init__(self, bot):
        self.bot = bot
        
        # load opus library for voice
        if (not discord.opus.is_loaded()):
            discord.opus.load_opus("opus")
    
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
    async def yt(self, ctx, *, query):
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
    
def setup(bot):
    bot.add_cog(Music(bot))