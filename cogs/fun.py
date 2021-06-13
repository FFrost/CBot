import discord
from discord.ext import commands

from modules import utils, checks

import re
import random
import aiohttp
import asyncio
from random import randint, uniform
from lxml import html
from urllib.parse import quote
from http.client import responses
import nltk
from nltk.corpus import wordnet
from googletrans import LANGUAGES

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.magic8ball_choices = [["It is certain", "yes"], ["It is decidedly so", "yes"],
                                   ["Without a doubt", "yes"], ["Yes definitely", "yes"],
                                   ["You may rely on it", "yes"], ["As I see it, yes", "yes"],
                                   ["Most likely", "yes"], ["Outlook good", "yes"], ["Yep", "yes"],
                                   ["Signs point to yes", "yes"],
                                   
                                   ["Reply hazy try again", "maybe"],
                                   ["Ask again later", "maybe"], ["Better not tell you now", "maybe"],
                                   ["Cannot predict now", "maybe"], ["Concentrate and ask again", "maybe"],

                                   ["Don't count on it", "no"], ["My reply is no", "no"],
                                   ["My sources say no", "no"], ["Outlook not so good", "no"],
                                   ["Very doubtful", "no"],
        ]
        
        self.mention_regex = re.compile(r"(<@[0-9]{18}>)")

        self.rolls = {}

    @commands.command(description="random number generator, supports hexadecimal and floats",
                      brief="random number generator, supports hex/floats",
                      name="random",
                      aliases=["rand"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def _random(self, ctx, low: str, high: str):                
        base = 10
                
        hex_exp = "0[xX][0-9a-fA-F]+" # hex number regex (0x0 to 0xF)
        alpha_exp = "[a-zA-Z]" # alphabet regex (a to Z)
                
        is_float = (any("." in t for t in [low, high]))
                
        for n in [low, high]:
            if (re.search(alpha_exp, n)):
                if (re.search(hex_exp, n)):
                    base = 16
                else:
                    await ctx.send(f"{ctx.author.mention} format: !random low high")
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
            await ctx.send(f"{ctx.author.mention} !random: low and high must be numbers")
            return
                
        if (low == high):
            await ctx.send(f"{ctx.author.mention} rolled a {low}")
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
                
        await ctx.send(f"{ctx.author.mention} rolled a {result}")
        
    # TODO: reenable this if we find a workaround for rate limits
    @commands.command(description="reverse image search",
                      brief="reverse image search",
                      aliases=["rev"],
                      enabled=False,
                      hidden=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def reverse(self, ctx, *, query: str = ""):
        message = ctx.message
        
        async with ctx.channel.typing():
            if (not query):
                if (message.attachments):
                    query = message.attachments[0]["url"]
                else:
                    query = await self.bot.bot_utils.find_last_image(message)
                    
            if (not query):
                await ctx.send(f"{ctx.author.mention} No image found")
                return
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
            url = "https://images.google.com/searchbyimage?image_url={}&encoded_image=&image_content=&filename=&hl=en".format(quote(query))
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as r:
                    if (r.status != 200):
                        await ctx.send(f"{ctx.author.mention} Query for `{query}` failed with status code `{r.status} ({responses[r.status]})` (maybe try again)")
                        return
                    
                    text = await r.text()
        
                    tree = html.fromstring(text)
                    
                    path = tree.xpath("//div[@class='_hUb']/a/text()")
                    
                    if (not path):
                        await ctx.send(f"{ctx.author.mention} Query for `{query}` failed (maybe try again)")
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
                    
                    await ctx.send(embed=embed)
        
    @commands.command(description="ask the magic 8 ball something",
                      brief="ask the magic 8 ball something",
                      name="8ball",
                      aliases=["8b", "8"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def magic8ball(self, ctx):
        choice = random.choice(self.magic8ball_choices)
        msg = await ctx.send(f"{ctx.author.mention} {choice[0]}")

        if (choice[1] == "maybe"):
            emoji = "\N{Clockwise Rightwards and Leftwards Open Circle Arrows}"
            await msg.add_reaction(emoji)

            def check(reaction, user):
                return (user == ctx.author and str(reaction.emoji) == emoji)

            try:
                await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                choice = random.choice([s for s in self.magic8ball_choices if s[1] != "maybe"])
                await msg.edit(content=f"{ctx.author.mention} {choice[0]}")
            except asyncio.TimeoutError:
                pass
            finally:
                await msg.clear_reaction(emoji)

    @commands.command(description="annoys someone (owner only)",
                    brief="annoys someone (owner only)",
                    hidden=True)
    @commands.check(checks.is_owner)
    async def annoy(self, ctx, user: discord.User, amount: int = 5):
        await ctx.message.delete()

        for _i in range(amount):
            msg = await ctx.send(user.mention)
            await msg.delete()

    @commands.command(description="scrambles someone out of a voice channel (owner only)",
                      brief="scrambles someone out of a voice channel (owner only)",
                      hidden=True)
    @commands.check(checks.is_owner)
    async def scramble(self, ctx, user: discord.Member, amount: int = 5):
        await ctx.message.delete()

        if (not user.voice):
            return

        old_channel = user.voice.channel

        if (not old_channel):
            return

        channels = ctx.guild.voice_channels

        for _i in range(amount):
            try:
                await user.move_to(random.choice(channels))
            
            except discord.errors.DiscordException:
                pass

        await user.move_to(old_channel)

    @commands.group(description="ask the bot something",
                    brief="ask the bot something",)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def what(self, ctx):
        if (not ctx.invoked_subcommand):
            await ctx.send(f"{ctx.author.mention} Invalid command")

    @commands.command(description="chooses for you",
                      brief="chooses for you",
                      aliases=["choice"])
    async def choose(self, ctx, *options):
        if (not options):
            return
        
        await ctx.send(random.choice(options))

    @commands.command(description="thesaurizes text",
                      brief="thesaurize text",
                      aliases=["th"])
    async def thesaurize(self, ctx, *, text: str=""):
        async with ctx.channel.typing():
            if (not text):
                text = await self.bot.bot_utils.find_last_text(ctx.message)

                if (not text):
                    await ctx.send(f"{ctx.author.mention} Failed to find text")
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

            await ctx.send(" ".join(new_text))
    
    @commands.command(description="puts text through random translations",
                      brief="puts text through random translations",
                      aliases=["ts"])
    async def translation_scramble(self, ctx, *, text: str=""):
        async with ctx.channel.typing():
            if (not text):
                text = await self.bot.bot_utils.find_last_text(ctx.message)

                if (not text):
                    await ctx.send(f"{ctx.author.mention} Failed to find text")
                    return

            # remove discord mentions
            text = self.mention_regex.sub("", text)

            # save original language
            source_lang_code = self.bot.translator.detect(text).lang

            if (source_lang_code not in list(LANGUAGES.keys())):
                await ctx.send(f"{ctx.author.mention} Can't detect language, defaulting source language to English")

            source_lang_code = "en"

            times = 8
            languages = [source_lang_code]
            
            for _i in range(times):
                dest_lang_code = random.choice(list(LANGUAGES.keys()))

                try:
                    result = self.bot.translator.translate(text, dest=dest_lang_code)
                    text = result.text
                    languages.append(result.dest)
                except Exception:
                    await ctx.send(f"{ctx.author.mention} Failed to translate text")
                    return

            # translate it back to the original language
            result = self.bot.translator.translate(text, dest=source_lang_code)
            text = result.text
            languages.append(source_lang_code)

            await ctx.send(f"`{times} translations: {' -> '.join([LANGUAGES[langcode].capitalize() for langcode in languages])}`\n{text}")

    @commands.command(description="",
                      brief="")
    async def roll(self, ctx, max_roll: int=None):
        if (not max_roll):
            if (not ctx.channel.id in self.rolls):
                await ctx.send(f"{ctx.author.mention} A maximum is required for the first roll")
                return
            
            max_roll = self.rolls[ctx.channel.id]
        elif (max_roll <= 1):
            await ctx.send(f"{ctx.author.mention} Max roll must be greater than 1")
            return

        r = randint(1, max_roll)

        if (r == 1):
            await ctx.send(f"{ctx.author.mention} rolled a 1 and won!")

            if (ctx.channel.id in self.rolls):
                del self.rolls[ctx.channel.id]
                
            return

        self.rolls[ctx.channel.id] = r
        await ctx.send(f"{ctx.author.mention} rolled a {r}")

    @commands.command(description="lists translations for a word in different languages",
                      brief="lists translations for a word in different languages",
                      aliases=["tl"])
    async def translation_list(self, ctx, word: str):
        await ctx.trigger_typing()
        #async with ctx.channel.typing():
        if True:
            # remove discord mentions
            word = self.mention_regex.sub("", word)
            ret = {}

            for lang_code in LANGUAGES.keys():
                try:
                    result = self.bot.translator.translate(word, dest=lang_code)
                    if (not result or not result.text):
                        continue

                    ret[lang_code] = result.text
                except Exception as e:
                    print(e)
                    continue

            if (not ret):
                await ctx.send("Failed to get translations, try again later")
                return

            s = "```\n"
            for code, translated_text in ret.items():
                s += f"{LANGUAGES[code]}: {translated_text}\n"
            s += "```"

            if (len(s) < 2000):
                await ctx.send(s)
            else:
                for i in range(0, len(s) // 2000 + 1):
                    await ctx.send(s[i * 2000 : (i + 1) * 2000])

def setup(bot):
    bot.add_cog(Fun(bot))
