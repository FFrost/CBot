import discord
from discord.ext import commands

from modules import checks, utils

import json
import asyncio, aiohttp
import requests
import time
from lxml import html
from urllib.parse import quote
from http.client import responses
from googletrans import Translator, LANGUAGES, LANGCODES
from datetime import datetime

class Utility:
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        
    @commands.command(description="info about a Discord user", brief="info about a Discord user", pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def info(self, ctx, *, name : str=""):
        embed = discord.Embed()

        if (ctx.message.mentions):
            user = ctx.message.mentions[0]
        elif (name):
            user = await self.bot.bot_utils.find(name)
                    
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `{}`".format(name))
                return
                    
        else:
            user = ctx.message.author

        if (not isinstance(user, discord.Member)):
            member = user.member
        else:
            member = user

        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)

        if (member.color):
            embed.color = member.color
        else:
            embed.color = discord.Color.green()

        embed.add_field(name="User", value="{}#{}".format(user.name, user.discriminator))
        embed.add_field(name="ID", value=user.id)

        if (member.game):
            embed.add_field(name="Playing", value=member.game)

        created_at = datetime.strptime(str(user.created_at), "%Y-%m-%d %H:%M:%S.%f")

        embed.add_field(name="Created at", value=created_at.strftime("%H:%M on %-m/%-d/%Y"))

        if (member.joined_at):
            embed.add_field(name="Joined the server at", value=member.joined_at.strftime("%H:%M on %-m/%-d/%Y"))

        if (member.top_role):
            embed.add_field(name="Highest role", value=member.top_role)

        if (user.display_name != user.name):
            embed.add_field(name="Nickname", value=user.display_name)

        if (user.bot):
            embed.add_field(name="Bot", value=":white_check_mark:")

        embed.set_image(url=user.avatar_url)
    
        await self.bot.send_message(ctx.message.channel, embed=embed)
        
    @commands.command(description="get a user's avatar", brief="get a user's avatar", pass_context=True)
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def avatar(self, ctx, *, name : str=""):
        if (ctx.message.mentions):
            users = ctx.message.mentions
        elif (name):
            user = await self.bot.bot_utils.find(name)
            
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `{}`".format(name))
                return
            else:
                users = [user]
        else:
            users = [ctx.message.author]
        
        for user in users:
            embed = utils.create_image_embed(user, image=user.avatar_url)
            await self.bot.send_message(ctx.message.channel, embed=embed)
        
    @commands.command(description="deletes the last X messages",
                      brief="deletes the last X messages",
                      pass_context=True)
    @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.check(checks.can_manage_messages)
    async def purge(self, ctx, num_to_delete : int=1, user : str=""):
        num_to_delete = abs(num_to_delete)

        if (num_to_delete > self.bot.CONFIG["MAX_PURGE"]):
            await self.bot.messaging.reply(ctx.message, "Number of messages to delete too high, max: {}".format(self.bot.CONFIG["MAX_PURGE"]))
            return

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
        
        num_deleted = await self.bot.bot_utils.purge(ctx, num_to_delete, users)
        
        temp = await self.bot.say("Deleted last {} message(s)".format(num_deleted))
        await asyncio.sleep(5)
        
        if (not ctx.message.channel.is_private):
            await self.bot.bot_utils.delete_message(ctx.message)
        
        try: # if a user runs another purge command within 5 seconds, the temp message won't exist
            await self.bot.bot_utils.delete_message(temp)
        
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
            string = await self.bot.bot_utils.find_last_text(ctx.message)
            
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
    async def gameinfo(self, ctx, *, query : str):
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
        
        embed = utils.create_game_info_embed(data, ctx.message.author)
        await self.bot.send_message(ctx.message.channel, embed=embed)
        
    @commands.command(description="get info about a server",
                 brief="get info about a server",
                 pass_context=True,
                 aliases=["sinfo"])
    @commands.cooldown(1, 5, commands.BucketType.server)
    async def serverinfo(self, ctx, *, search : str=""):
        embed = discord.Embed()
        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
        embed.color = discord.Color.dark_blue()

        if (ctx.message.channel.is_private and not search):
            channel = ctx.message.channel

            embed.title = channel.name

            if (channel.owner is not None):
                embed.add_field(name="Owner", value="{}#{}".format(channel.owner.name, channel.owner.discriminator))
            
            embed.add_field(name="ID", value=channel.id)
            embed.add_field(name="Number of members", value=len(channel.recipients))
            embed.add_field(name="Created at", value=channel.created_at)
            
            await self.bot.send_message(ctx.message.channel, embed=embed)
            return
        
        server = ctx.message.server
        
        if (checks.is_owner(ctx)): # only allow the bot owner to access the other servers the bot is in
            if (search):
                server = self.bot.bot_utils.find_server(search)
        
        if (not server):
            await self.bot.messaging.reply(ctx.message, "No server found for `{}`".format(search))
            return
        
        if (server.unavailable):
            await self.bot.messaging.reply(ctx.message, "Server `{}` ({}) is currently unavailable".format(server.id, search))
            return None

        embed.title = server.name

        embed.add_field(name="Owner", value="{}#{}".format(server.owner.name, server.owner.discriminator))
        embed.add_field(name="ID", value=server.id)
        embed.add_field(name="Number of members", value=server.member_count)
        embed.add_field(name="Created at", value=server.created_at)

        embed.set_thumbnail(url=server.icon_url)
        
        await self.bot.send_message(ctx.message.channel, embed=embed)

def setup(bot):
    bot.add_cog(Utility(bot))
