import discord
from discord.ext import commands

from modules import checks, utils, siege

import json
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
            info_msg = utils.get_user_info(ctx.message.mentions[0])
        elif (name):
            user = await self.bot.bot_utils.find(name)
                    
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `{}`".format(name))
                return
                    
            info_msg = utils.get_user_info(user)
        else:
            info_msg = utils.get_user_info(ctx.message.author)
    
        await self.bot.messaging.reply(ctx, info_msg)
        
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
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def serverinfo(self, ctx, *, search : str=""):
        msg = """```\n{name} [{id}]
Owned by {owner}
Created at {date}
{num_members} users
```"""

        if (ctx.message.channel.is_private and not search):
            channel = ctx.message.channel
            msg = msg.format(name=channel.name,
                             id=channel.id,
                             owner=channel.owner,
                             date=channel.created_at,
                             num_members=len(channel.recipients))
            
            await self.bot.messaging.reply(ctx.message, msg)
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
        
        msg = msg.format(name=server.name,
                         id=server.id,
                         owner=("{name}#{disc}".format(name=server.owner.name, disc=server.owner.discriminator)),
                         date=server.created_at,
                         num_members=server.member_count)
        
        await self.bot.messaging.reply(ctx.message, msg)

    async def get_fortnite_stats(self, name, platform):
        headers = {
            "TRN-Api-Key": self.bot.CONFIG["trn_api_key"]
        }

        url = "https://api.fortnitetracker.com/v1/profile/{platform}/{name}".format(platform=platform, name=name)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as r:              
                    if (r.status != 200):
                        return r.status

                    return await r.json()

        except Exception:
            return None

    @commands.command(description="finds Fortnite stats for a user",
                      brief="finds Fortnite stats for a user",
                      pass_context=True,
                      aliases=["fstats"])
    @commands.cooldown(1, 1, commands.BucketType.server)
    async def fortnite(self, ctx, name : str, stats : str="lifetime"):
        await self.bot.send_typing(ctx.message.channel)

        if (not "trn_api_key" in self.bot.CONFIG):
            await self.bot.messaging.reply(ctx.message, "No Tracker API key found")
            return

        stats_options = ["lifetime", "solo", "duo", "squad"]
        if (stats not in stats_options):
            await self.bot.messaging.reply(ctx.message, "Invalid stat selection `{}`, options are: {}".format(stats,
                ", ".join("`{}`".format(s) for s in stats_options)))
            return

        platforms = ["pc", "xbl", "psn"]

        success = False

        for platform in platforms:
            data = await self.get_fortnite_stats(name, platform)
            await asyncio.sleep(1) # cooldown in between each request, according to the api's guidelines

            if (not data):
                continue

            if (isinstance(data, int)):
                self.bot.bot_utils.log_error_to_file("Failed to get Fortnite stats for \"{name}\" ({platform}) failed with status code {code} ({string})".format(
                        name=name,
                        platform=platform,
                        code=data,
                        string=responses[data] if (data in responses) else "unknown"), prefix="Fortnite")
                continue

            try:
                data = dict(data)

            except Exception as e:
                self.bot.bot_utils.log_error_to_file("Failed to find Fortnite stats for \"{}\" ({}) because of exception: {}".format(name, platform, e),
                        prefix="Fortnite")
                continue

            if ("error" in data):
                if (data["error"] != "Player Not Found"):
                    self.bot.bot_utils.log_error_to_file("API error for \"{}\" ({}): {}".format(name, platform, data["error"]), prefix="Fortnite")
                
                continue

            embed = utils.create_fortnite_stats_embed(ctx.message.author,
                                                        data,
                                                        stats,
                                                        title=name)

            if (not embed):
                await self.bot.messaging.reply(ctx.message, "Failed to find `{}` Fortnite stats for `{}`".format(stats, name))
                return

            await self.bot.send_message(ctx.message.channel, embed=embed)
            success = True

        if (not success):
            await self.bot.messaging.reply(ctx.message, "Failed to find `{}` Fortnite stats for `{}`".format(stats, name))

    @commands.command(description="finds Rainbow Six Siege stats for a user",
                      brief="finds Rainbow Six Siege stats for a user",
                      pass_context=True,
                      aliases=["r6s", "r6stats"])
    @commands.cooldown(1, 5, commands.BucketType.server)
    async def siege(self, ctx, username : str, stats_selection : str="all", platform : str="uplay"):
        stats_options = ["overall", "ranked", "casual", "all"]
        if (stats_selection not in stats_options):
            await self.bot.messaging.reply(ctx.message, "Invalid stat selection `{}`, options are: {}".format(stats_selection,
                ", ".join("`{}`".format(s) for s in stats_options)))
            return

        if (platform not in siege.platforms.keys()):
            await self.bot.messaging.reply(ctx.message, "Invalid platform selection `{}`, options are: {}".format(platform,
                ", ".join("`{}`".format(s) for s in siege.platforms.keys())))
            return

        msg = await self.bot.messaging.reply(ctx.message, "Searching for stats (might take a while)...")
        await self.bot.send_typing(ctx.message.channel)

        stats = await siege.get_player(username, platform=platform)

        await self.bot.bot_utils.delete_message(msg)

        if (not stats):
            await self.bot.messaging.reply(ctx.message, "Failed to find `{}` stats for `{}` on `{}`".format(stats_selection, username, platform))
            return

        if (not "player" in stats):
            if ("errors" in stats):
                for error in stats["errors"]:
                    detail = "Unknown error."
                    description = "Unknown."

                    if ("detail" in error):
                        detail = error["detail"]

                    if ("meta" in error and "description" in error["meta"]):
                        description = error["meta"]["description"]

                    await self.bot.messaging.reply(ctx.message, "An error occured searching for `{}` on `{}`: {} {}".format(username,
                        platform,
                        detail,
                        description))

            return

        stats = stats["player"]

        if (stats_selection == "all"):
            stats_option = stats_options[:-1]
        else:
            stats_option = [stats_selection]

        success = False

        for option in stats_option:
            embed = await siege.create_siege_embed(ctx.message.author, stats, stats_selection=option)

            if (not embed):
                continue

            success = True
            await self.bot.send_message(ctx.message.channel, embed=embed)

        if (not success):
            await self.bot.messaging.reply(ctx.message, "Failed to find `{}` stats for `{}` on `{}`".format(stats_selection, username, platform))

def setup(bot):
    bot.add_cog(Utility(bot))
