import discord
from discord.ext import commands

from modules import utils, checks

import re
import random
import aiohttp
from random import randint, uniform
from lxml import html
from urllib.parse import quote
from http.client import responses
import nltk
from nltk.corpus import wordnet
from googletrans import LANGUAGES

class Fun:
    def __init__(self, bot):
        self.bot = bot

        self.magic8ball_choices = ["It is certain", "It is decidedly so",
                                   "Without a doubt", "Yes definitely",
                                   "You may rely on it", "As I see it, yes",
                                   "Most likely", "Outlook good", "Yep",
                                   "Signs point to yes", "Reply hazy try again",
                                   "Ask again later", "Better not tell you now",
                                   "Cannot predict now", "Concentrate and ask again",
                                   "Don't count on it", "My reply is no",
                                   "My sources say no", "Outlook not so good",
                                   "Very doubtful"
                                   ]
        
        self.mention_regex = re.compile(r"(<@[0-9]{18}>)")

    @commands.command(description="random number generator, supports hexadecimal and floats",
                      brief="random number generator, supports hex/floats",
                      pass_context=True,
                      name="random",
                      aliases=["rand"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def _random(self, ctx, low: str, high: str):
        message = ctx.message
                
        base = 10
                
        hex_exp = "0[xX][0-9a-fA-F]+" # hex number regex (0x0 to 0xF)
        alpha_exp = "[a-zA-Z]" # alphabet regex (a to Z)
                
        is_float = (any("." in t for t in [low, high]))
                
        for n in [low, high]:
            if (re.search(alpha_exp, n)):
                if (re.search(hex_exp, n)):
                    base = 16
                else:
                    await self.bot.messaging.reply(message, "format: !random low high")
                    return
                
        try:
            if (base == 16):
                low = int(low, base)
                high = int(high, base)
            else:
                if (is_float):
                    low = float(low)
                    high = float(high)
                else:
                    low = int(low, base)
                    high = int(high, base)
                    
        except Exception:
            await self.bot.messaging.reply(message, "!random: low and high must be numbers")
            return
                
        if (low == high):
            await self.bot.messaging.reply(message, "rolled a {}".format(low))
            return
                
        if (low > high):
            temp_high = high
            high = low
            low = temp_high
                
        if (is_float):
            r = uniform(low, high)
        else:
            r = randint(low, high)
                
        result = ""
        
        if (base == 16):
            hex_result = hex(r).upper()
            hex_result = hex_result.replace("X", "x")
                    
            result = hex_result
        else:
            result = r
                
        await self.bot.messaging.reply(ctx, "rolled a {}".format(result))
        
    # TODO: reenable this if we find a workaround for rate limits
    @commands.command(description="reverse image search",
                      brief="reverse image search",
                      pass_context=True,
                      aliases=["rev"],
                      enabled=False)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def reverse(self, ctx, *, query: str = ""):
        message = ctx.message
        
        await self.bot.send_typing(message.channel)
        
        if (not query):
            if (message.attachments):
                query = message.attachments[0]["url"]
            else:
                query = await self.bot.bot_utils.find_last_image(message)
                
        if (not query):
            await self.bot.messaging.reply(message, "No image found")
            return
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
        url = "https://images.google.com/searchbyimage?image_url={}&encoded_image=&image_content=&filename=&hl=en".format(quote(query))
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                if (r.status != 200):
                    await self.bot.messaging.reply(ctx, "Query for `{query}` failed with status code `{code} ({string})` (maybe try again)".format(
                        query=query,
                        code=r.status,
                        string=responses[r.status]))
                    return
                
                text = await r.text()
    
                tree = html.fromstring(text)
                
                path = tree.xpath("//div[@class='_hUb']/a/text()")
                
                if (not path):
                    await self.bot.messaging.reply(ctx, "Query for `{}` failed (maybe try again)".format(query))
                    return
                    
                if (isinstance(path, list)):
                    path = path[0].strip()
                elif (isinstance(path, str)):
                    path = path.strip()
                    
                embed = utils.create_image_embed(message.author,
                                                          title="Best guess for this image:",
                                                          description=path,
                                                          thumbnail=query,
                                                          color=discord.Color.green())
                
                await self.bot.messaging.bot.send_message(message.channel, embed=embed)
        
    @commands.command(description="ask the magic 8 ball something",
                      brief="ask the magic 8 ball something",
                      pass_context=True,
                      name="8ball",
                      aliases=["8b", "8"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def magic8ball(self, ctx):
        choice = random.choice(self.magic8ball_choices)
        await self.bot.messaging.reply(ctx.message, choice)

    @commands.command(description="annoys someone (owner only)",
                    brief="annoys someone (owner only)",
                    pass_context=True,
                    hidden=True)
    @commands.check(checks.is_owner)
    async def annoy(self, ctx, user: discord.User, amount: int = 5):
        await self.bot.bot_utils.delete_message(ctx.message)

        for _i in range(amount):
            msg = await self.bot.send_message(ctx.message.channel, "{.mention}".format(user))
            await self.bot.bot_utils.delete_message(msg)

    @commands.command(description="scrambles someone out of a voice channel (owner only)",
                      brief="scrambles someone out of a voice channel (owner only)",
                      pass_context=True,
                      hidden=True)
    @commands.check(checks.is_owner)
    async def scramble(self, ctx, user: discord.User, amount: int = 5):
        await self.bot.bot_utils.delete_message(ctx.message)

        old_channel = user.voice_channel

        if (not old_channel):
            return

        channels = list(filter(lambda chan: chan.type == discord.ChannelType.voice, ctx.message.server.channels))

        for _i in range(amount):
            try:
                await self.bot.move_member(user, random.choice(channels))
            
            except discord.errors.DiscordException:
                pass

        await self.bot.move_member(user, old_channel)

    @commands.group(description="ask the bot something",
                    brief="ask the bot something",
                    pass_context=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def what(self, ctx):
        if (not ctx.invoked_subcommand):
            await self.bot.messaging.reply(ctx.message, "Invalid command")

    @commands.command(description="chooses for you",
                      brief="chooses for you",
                      pass_context=True)
    async def choose(self, ctx, *options):
        if (not options):
            return
        
        await self.bot.say(random.choice(options))

    @commands.command(description="thesaurizes text",
                      brief="thesaurize text",
                      pass_context=True,
                      aliases=["th"])
    async def thesaurize(self, ctx, *, text: str=""):
        await self.bot.send_typing(ctx.message.channel)

        if (not text):
            text = await self.bot.bot_utils.find_last_text(ctx.message)

            if (not text):
                await self.bot.messaging.reply(ctx.message, "Failed to find text")
                return

        # remove discord mentions
        text = self.mention_regex.sub("", text)

        tokens = nltk.word_tokenize(text)

        new_text = []

        for token in tokens:
            if (len(token) <= 3): # TODO: better way of filtering out "a", "the", "its", "it's", etc
                new_text.append(token)
                continue
            
            synonyms = wordnet.synsets(token)

            if (not synonyms):
                new_text.append(token)
                continue
            
            lemma_name = None

            for synset in list(synonyms):
                try:
                    lemma_name = synset.lemma_names()[0]

                    if (lemma_name == token.lower()):
                        lemma_name = None
                        continue

                    lemma_name = lemma_name.replace("_", " ")
                except (IndexError, AttributeError):
                    continue
                else:
                    new_text.append(str(lemma_name))
                    break

            if (lemma_name is None):
                new_text.append(token)

        await self.bot.say(" ".join(new_text))
    
    @commands.command(description="puts text through random translations",
                      brief="puts text through random translations",
                      pass_context=True,
                      aliases=["ts"])
    async def translation_scramble(self, ctx, *, text: str=""):
        await self.bot.send_typing(ctx.message.channel)

        if (not text):
            text = await self.bot.bot_utils.find_last_text(ctx.message)

            if (not text):
                await self.bot.messaging.reply(ctx.message, "Failed to find text")
                return

        # remove discord mentions
        text = self.mention_regex.sub("", text)

        # save original language
        source_lang_code = self.bot.translator.detect(text).lang

        times = 8
        languages = [source_lang_code]
        
        for _i in range(times):
            dest_lang_code = random.choice(list(LANGUAGES.keys()))

            try:
                result = self.bot.translator.translate(text, dest=dest_lang_code)
                text = result.text
                languages.append(result.dest)
            except Exception:
                await self.bot.messaging.reply(ctx.message, "Failed to translate text")
                return

        # translate it back to the original language
        result = self.bot.translator.translate(text, dest=source_lang_code)
        text = result.text
        languages.append(source_lang_code)

        await self.bot.say(f"`{times} translations: {' -> '.join([LANGUAGES[langcode].capitalize() for langcode in languages])}`\n{text}")

def setup(bot):
    bot.add_cog(Fun(bot))
