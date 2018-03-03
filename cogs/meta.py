import discord
from discord.ext import commands

from modules import checks

import inspect, os, sys, subprocess, time

class Meta:
    def __init__(self, bot):
        self.bot = bot

    # stolen from https://github.com/Rapptz/RoboDanny/blob/c8fef9f07145cef6c05416dc2421bbe1d05e3d33/cogs/meta.py#L164
    @commands.command(description="bot source code", brief="bot source code", pass_context=True, aliases=["src"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
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
            
    @commands.group(description="run commands on the bot (owner only)",
                    brief="run commands on the bot (owner only)",
                    pass_context=True,
                    aliases=["command"])
    @commands.check(checks.is_owner)
    async def cmd(self, ctx):
        if (not ctx.invoked_subcommand):
            await self.bot.messaging.reply(ctx.message, "Invalid command")
        
    @cmd.command(description="restarts the bot",
                 brief="restarts the bot",
                 pass_context=True)
    async def restart(self, ctx):
        path_to_cbot = self.bot.REAL_FILE
        
        await self.bot.messaging.reply(ctx.message, "Restarting...")
        
        args = ["python3", path_to_cbot] + sys.argv[1:]
        
        if (self.bot.bot_restart_arg not in args):
            args += [self.bot.bot_restart_arg]
        
        await self.bot.logout()
        subprocess.call(args)
    
    @cmd.command(description="stops the bot",
                 brief="stops the bot",
                 pass_context=True)
    async def stop(self, ctx):
        await self.bot.messaging.reply(ctx.message, "Shutting down...")
        await self.bot.logout()
        
    @cmd.command(description="makes the bot say something",
                 brief="makes the bot say something")
    async def say(self, *, msg : str):
        await self.bot.say(msg)
        
    @cmd.command(description="changes the bot's status",
                 brief="changes the bot's status",
                 pass_context=True)
    async def status(self, ctx, *, status : str):
        await self.bot.change_presence(game=discord.Game(name=status))
        await self.bot.messaging.reply(ctx.message, "Set status to `{}`".format(status))
        
    @cmd.command(description="what servers the bot is in",
                 brief="what servers the bot is in",
                 pass_context=True)
    async def where(self, ctx):
        msg = "\n```"
        
        for s in self.bot.servers:
            if (s.unavailable): # can't retrieve info about server
                msg += "{id} - server is unavailable!\n".format(id=s.id)
            else:
                msg += "{name} owned by {owner}#{ownerid}\n".format(name=s.name, owner=s.owner.name, ownerid=s.owner.discriminator)
                
        msg += "```"

        await self.bot.messaging.reply(ctx.message, msg)

def setup(bot):
    bot.add_cog(Meta(bot))