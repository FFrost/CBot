import discord
from discord.ext import commands

import asyncio
from googletrans import Translator, LANGUAGES, LANGCODES

class Utility:
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        
    @commands.command(description="info about a Discord user", brief="info about a Discord user", pass_context=True)
    async def info(self, ctx, *, name : str=""):
        if (ctx.message.mentions):
            info_msg = self.bot.utils.get_user_info(ctx.message.mentions[0])
        elif (name):
            user = await self.bot.utils.find(name)
                    
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `%s`" % name)
                return
                    
            info_msg = self.bot.utils.get_user_info(user)
        else:
            info_msg = self.bot.utils.get_user_info(ctx.message.author)
    
        await self.bot.messaging.reply(ctx, info_msg)
        
    @commands.command(description="get a user's avatar", brief="get a user's avatar", pass_context=True)
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
            
    @commands.command(description="undo bot's last message(s)", brief="undo bot's last message(s)", pass_context=True)    
    async def undo(self, ctx, num_to_delete=1):
        cur = 0
    
        async for message in self.bot.logs_from(ctx.message.channel, before=ctx.message):
            if (cur >= num_to_delete):
                break
            
            if (message.author == self.bot.user):
                await self.bot.utils.delete_message(message)
                cur += 1
        
        if (not ctx.message.channel.is_private):
            await self.bot.utils.delete_message(ctx.message)
        
        temp = await self.bot.say("Deleted last {} message(s)".format(cur))
        await asyncio.sleep(5)
        
        try:
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
            
def setup(bot):
    bot.add_cog(Utility(bot))