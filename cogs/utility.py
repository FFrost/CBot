import discord
from discord.ext import commands

from modules import checks

import asyncio, aiohttp
import requests
from lxml import html
from urllib.parse import quote
from http.client import responses
from googletrans import Translator, LANGUAGES, LANGCODES


class Utility:

    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        
    @commands.command(description="info about a Discord user", brief="info about a Discord user", pass_context=True)
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def info(self, ctx, *, name : str=""):
        if (ctx.message.mentions):
            info_msg = self.bot.utils.get_user_info(ctx.message.mentions[0])
        elif (name):
            user = await self.bot.utils.find(name)
                    
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `{}`".format(name))
                return
                    
            info_msg = self.bot.utils.get_user_info(user)
        else:
            info_msg = self.bot.utils.get_user_info(ctx.message.author)
    
        await self.bot.messaging.reply(ctx, info_msg)
        
    @commands.command(description="get a user's avatar", brief="get a user's avatar", pass_context=True)
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def avatar(self, ctx, *, name : str=""):
        if (ctx.message.mentions):
            users = ctx.message.mentions
        elif (name):
            user = await self.bot.utils.find(name)
            
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `{}`".format(name))
                return
            else:
                users = [user]
        else:
            users = [ctx.message.author]
        
        for user in users:
            embed = self.bot.utils.create_image_embed(user, image=user.avatar_url)
            await self.bot.send_message(ctx.message.channel, embed=embed)
        
    @commands.command(description="deletes the last X messages",
                      brief="deletes the last X messages",
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @commands.check(checks.can_manage_messages)
    async def purge(self, ctx, num_to_delete : int=1, user : str=""):
        users = None
        
        if (ctx.message.mentions):
            users = ctx.message.mentions
        elif (user):
            if (user == "bot"):
                users = [self.bot.user]
            else:
                u = await self.bot.utils.find(user)
                
                if (not u):
                    await self.bot.messaging.reply(ctx.message, "Failed to find user `{}`".format(user))
                    return
                else:
                    users = [u]
        
        num_deleted = await self.bot.utils.purge(ctx, num_to_delete, users)
        
        temp = await self.bot.say("Deleted last {} message(s)".format(num_deleted))
        await asyncio.sleep(5)
        
        if (not ctx.message.channel.is_private):
            await self.bot.utils.delete_message(ctx.message)
        
        try: # if a user runs another purge command within 5 seconds, the temp message won't exist
            await self.bot.utils.delete_message(temp)
        
        except Exception:
            pass
    
    @commands.command(description="translates text into another language\n" + \
                      "list of language codes: https://cloud.google.com/translate/docs/languages",
                      brief="translates text into another language",
                      pass_context=True,
                      aliases=["tr"])
    async def translate(self, ctx, language : str="en", *, string : str=""):
        language = language.lower().strip()
            
        if (language not in LANGUAGES.keys()):
            if (language in LANGCODES):
                language = LANGCODES[language]
            else:
                # default to english if no valid language provided
                string = language + " " + string # command separates the first word from the rest of the string
                language = "en"
        
        if (not string):
            string = await self.bot.utils.find_last_text(ctx.message)
            
            if (not string):
                await self.bot.messaging.reply(ctx.message, "Failed to find text to translate")
                return
        
        result = self.translator.translate(string, dest=language)
        src = LANGUAGES[result.src.lower()]
        dest = LANGUAGES[result.dest.lower()]
        msg = "{src} to {dest}: {text}".format(src=src, dest=dest, text=result.text)
        await self.bot.messaging.reply(ctx.message, msg)
        
    @commands.command(description="searches for info on a game",
                      brief="searches for info on a game",
                      pass_context=True,
                      enabled=False) # rate limited
    async def game(self, ctx, *, query : str):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
        url = "https://www.google.com/search?q={}".format(quote(query))  # escape query for url
        
        conn = aiohttp.TCPConnector(verify_ssl=False)  # for https
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url, headers=headers) as r: 
                if (r.status != 200):
                    await self.bot.messaging.reply(ctx, "Query for `{query}` failed with status code `{code} ({string})` (maybe try again)".format(
                                query=query,
                                code=r.status,
                                string=responses[r.status]))
                    return
                
                text = await r.text()
                
        data = {}
        
        tree = html.fromstring(text)
        
        """
        header
        """
        
        header = tree.xpath("//div[@class='_fdf _odf']/div[@class='_Q1n']/div")
        
        if (not header or len(header) < 2):
            await self.bot.messaging.reply(ctx, "No results found for `{}`".format(query))
            return
        elif (len(header) > 2):
            header = header[:2]
        
        data["title"] = header[0].text_content()
        data["description"] = header[1].text_content()
        
        """
        game info
        """
                
        info = tree.xpath("//div[@class='_RBg']/div[@class='mod']")
        
        if (not info or len(info) < 1):
            await self.bot.messaging.reply(ctx.message, "Failed to find info for `{}`".format(query))
            return
        
        body = info[0].text_content().strip()
        
        if (body.endswith("Wikipedia")):
            body = body[:-len("Wikipedia")].strip()
        
        data["body"] = body
        
        data["content"] = []
        
        for entry in info[1:]:
            content = entry.text_content().strip()
            
            if (content):
                data["content"].append(content)
        
        """
        wikipedia link
        """
        
        wiki_link = tree.xpath("//a[@class='q _KCd _tWc fl']/@href")
        
        if (not wiki_link):
            wiki_link = ""
        else:
            wiki_link = wiki_link[0]
        
        data["wiki"] = wiki_link
        
        """
        game image
        """
        
        game_img = tree.xpath("//a[@jsaction='fire.ivg_o']/@href")[0]
        
        start_tag       = "/imgres?imgurl="
        end_tag         = "&imgrefurl="
        start_index     = game_img.find(start_tag)
        end_index       = game_img.find(end_tag)
        data["image"]   = game_img[start_index + len(start_tag) : end_index]
        
        embed = self.bot.utils.create_game_info_embed(data, ctx.message.author)
        await self.bot.send_message(ctx.message.channel, embed=embed)
            
def setup(bot):
    bot.add_cog(Utility(bot))
