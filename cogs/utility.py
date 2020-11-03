import discord
from discord.ext import commands

from modules import checks, utils

import asyncio
import aiohttp
from lxml import html
from urllib.parse import quote
from http.client import responses
from googletrans import LANGUAGES, LANGCODES
from datetime import datetime

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="info about a user",
                      brief="info about a user")
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def info(self, ctx, user: discord.User = None):
        if (not user):
            user = ctx.author

        is_member = isinstance(user, discord.Member)

        if (not is_member and hasattr(user, "member")):
            member = user.member
            is_member = True
        else:
            member = user

        embed = discord.Embed()

        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        if (is_member and member.color):
            embed.color = member.color
        else:
            embed.color = discord.Color.green()

        embed.add_field(name="User", value="{}#{}".format(user.name, user.discriminator))
        embed.add_field(name="ID", value=user.id)

        if (is_member and member.activity):
            embed.add_field(name="Playing", value=member.activity)

        created_at = datetime.strptime(str(user.created_at), "%Y-%m-%d %H:%M:%S.%f")

        embed.add_field(name="Created at", value=utils.format_time(created_at))

        if (is_member and member.joined_at):
            embed.add_field(name="Joined the server at", value=utils.format_time(member.joined_at))

        if (is_member and member.top_role):
            embed.add_field(name="Highest role", value=member.top_role)

        if (user.display_name != user.name):
            embed.add_field(name="Nickname", value=user.display_name)

        if (user.bot):
            embed.add_field(name="Bot", value=":white_check_mark:")

        embed.set_thumbnail(url=user.avatar_url)

        if (is_member and member.guild):
            embed.set_footer(text=f"Server: {utils.cap_string_and_ellipsis(member.guild.name, 64, 1)}")
    
        await ctx.message.channel.send(embed=embed)
        
    @commands.command(description="get a user's avatar",
                      brief="get a user's avatar")
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def avatar(self, ctx, user: discord.User = None):
        if (not user):
            user = ctx.author
        
        embed = discord.Embed(color=discord.Colour.blue())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_image(url=user.avatar_url)

        await ctx.channel.send(embed=embed)
        
    @commands.command(description="deletes the last X messages",
                      brief="deletes the last X messages")
    @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def purge(self, ctx, num_to_delete: int = 1, user: str = ""):
        num_to_delete = abs(num_to_delete)

        if (num_to_delete > self.bot.CONFIG["max_purge"]):
            await ctx.send(f"{ctx.author.mention} Number of messages to delete too high, max: {self.bot.CONFIG['max_purge']}")
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
                    await ctx.send(f"{ctx.author.mention} Failed to find user `{user}`")
                    return
                else:
                    users = [u]
        
        num_deleted = await self.bot.bot_utils.purge(ctx, num_to_delete, users)

        await ctx.send(f"Deleted last {num_deleted} message(s)", delete_after=5)
        
        if (not isinstance(ctx.channel, discord.abc.PrivateChannel)):
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass
    
    @commands.command(description="translates text into another language\n" + \
                      "list of language codes: https://cloud.google.com/translate/docs/languages",
                      brief="translates text into another language",
                      aliases=["tr"])
    async def translate(self, ctx, language: str = "en", *, string: str = ""):
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
                await ctx.send(f"{ctx.author.mention} Failed to find text to translate")
                return
        
        try:
            result = self.bot.translator.translate(string, dest=language)
        except Exception:
            await ctx.send(f"{ctx.author.mention} Failed to translate text")
            return
        
        src = LANGUAGES[result.src.lower()]
        dest = LANGUAGES[result.dest.lower()]
        msg = "`{src} to {dest}`: {text}".format(src=src, dest=dest, text=result.text)
        await ctx.send(msg)
        
    @commands.command(description="searches for info on a game",
                      brief="searches for info on a game",
                      enabled=False) # rate limited
    async def gameinfo(self, ctx, *, query: str):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
        url = f"https://www.google.com/search?q={quote(query)}"  # escape query for url
        
        conn = aiohttp.TCPConnector(verify_ssl=False) # for https
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url, headers=headers) as r:
                if (r.status != 200):
                    await ctx.send(f"{ctx.author.mention} Query for `{query}` failed with status code `{r.status} ({responses[r.status]})` (maybe try again)")
                    return
                
                text = await r.text()
                
        data = {}
        
        tree = html.fromstring(text)
        
        # header

        header = tree.xpath("//div[@class='_fdf _odf']/div[@class='_Q1n']/div")
        
        if (not header or len(header) < 2):
            await ctx.send(f"{ctx.author.mention} No results found for `{query}`")
            return
        elif (len(header) > 2):
            header = header[:2]
        
        data["title"] = header[0].text_content()
        data["description"] = header[1].text_content()
        
        # game info

        info = tree.xpath("//div[@class='_RBg']/div[@class='mod']")
        
        if (not info or len(info) < 1):
            await ctx.send(f"{ctx.author.mention} Failed to find info for `{query}`")
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
        
        # wikipedia link
        
        wiki_link = tree.xpath("//a[@class='q _KCd _tWc fl']/@href")
        
        if (not wiki_link):
            wiki_link = ""
        else:
            wiki_link = wiki_link[0]
        
        data["wiki"] = wiki_link
        
        # game image
        
        game_img = tree.xpath("//a[@jsaction='fire.ivg_o']/@href")[0]
        
        start_tag       = "/imgres?imgurl="
        end_tag         = "&imgrefurl="
        start_index     = game_img.find(start_tag)
        end_index       = game_img.find(end_tag)
        data["image"]   = game_img[start_index + len(start_tag) : end_index]
        
        embed = utils.create_game_info_embed(data, ctx.author)
        await ctx.channel.send(embed=embed)
        
    @commands.command(description="get info about a server",
                 brief="get info about a server",
                 aliases=["sinfo", "server"])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def serverinfo(self, ctx, *, search: str = ""):
        embed = discord.Embed(color=discord.Color.dark_blue())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        channel = ctx.channel

        if (isinstance(ctx.channel, discord.DMChannel)):
            embed.title = ctx.author.name

            embed.add_field(name="ID", value=channel.id)
            embed.add_field(name="Created at", value=channel.created_at)

            await ctx.send(embed=embed)
            return
        elif (isinstance(ctx.channel, discord.abc.PrivateChannel) and not search):
            embed.title = channel.name

            if (channel.owner is not None):
                embed.add_field(name="Owner", value="{}#{}".format(channel.owner.name, channel.owner.discriminator))
            
            embed.add_field(name="ID", value=channel.id)
            embed.add_field(name="Users", value=len(channel.recipients))
            embed.add_field(name="Created at", value=channel.created_at)
            
            await ctx.send(embed=embed)
            return
        
        guild = ctx.message.guild
        
        if (checks.is_owner(ctx)): # only allow the bot owner to access the other servers the bot is in
            if (search):
                guild = self.bot.bot_utils.find_guild(search)
        
        if (not guild):
            await ctx.send(f"{ctx.author.mention} No server found for `{search}`")
            return
        
        if (guild.unavailable):
            await ctx.send(f"{ctx.author.mention} Server `{guild.id}` ({search}) is currently unavailable")
            return None

        embed.title = guild.name

        embed.add_field(name="Owner", value=f"{guild.owner.name}#{guild.owner.discriminator}")
        embed.add_field(name="ID", value=guild.id)
        embed.add_field(name="Number of members", value=guild.member_count)
        embed.add_field(name="Created at", value=guild.created_at)

        embed.set_thumbnail(url=guild.icon_url)
        
        await ctx.message.channel.send(embed=embed)

    @commands.command(aliases=["ss"])
    @commands.check(checks.is_in_voice_channel)
    async def screenshare(self, ctx):
        url = f"http://www.discordapp.com/channels/{ctx.guild.id}/{ctx.author.voice.channel.id}"
        await ctx.send(url)

def setup(bot):
    bot.add_cog(Utility(bot))
