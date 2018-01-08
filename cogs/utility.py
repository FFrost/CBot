import discord
from discord.ext import commands

import os, inspect
import asyncio

class Utility:
    def __init__(self, bot):
        self.bot = bot
        
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
    
        async for message in self.bot.logs_from(ctx.message.channel):
            if (cur >= num_to_delete):
                break
            
            if (message.author == self.bot.user):
                await self.bot.delete_message(message)
                cur += 1
        
        # TODO: check if we have perms to do this
        try:
            await self.bot.delete_message(ctx.message)
        except Exception:
            pass
        
        temp = await self.bot.say("Deleted last {} message(s)".format(cur))
        await asyncio.sleep(5)
        
        if (temp):
            await self.bot.delete_message(temp)
    
    # stolen from https://github.com/Rapptz/RoboDanny/blob/c8fef9f07145cef6c05416dc2421bbe1d05e3d33/cogs/meta.py#L164
    @commands.command(description="source code", brief="source code", pass_context=True, aliases=["src"])
    async def source(self, ctx, *, command : str=""):
        if (not command):
            await self.bot.messaging.reply(ctx.message, self.bot.source_url)
        else:            
            obj = self.bot.get_command(command.replace(".", " "))
            
            if (not obj):
                await self.bot.messaging.reply(ctx.message, "Failed to find command {}".format(command))
                return
            
            src = obj.callback.__code__
            lines, firstlineno = inspect.getsourcelines(src)
            
            if (obj.callback.__module__.startswith("discord")):
                await self.bot.messaging.reply(ctx.message, "Can't get source code of built-in commands")
                return
            
            location = os.path.relpath(src.co_filename).replace("\\", "/").replace("cbot/", "")
                
            url = "{source_url}/blob/master/{location}#L{firstlineno}-L{end}".format(source_url=self.bot.source_url,
                                                             location=location,
                                                             firstlineno=firstlineno,
                                                             end=(firstlineno + len(lines) - 1))
            
            await self.bot.messaging.reply(ctx.message, url)
            
def setup(bot):
    bot.add_cog(Utility(bot))