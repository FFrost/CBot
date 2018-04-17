import discord
from discord.ext import commands

from modules import checks
import inspect, os, sys, subprocess, psutil
from hurry.filesize import size

class Meta:
    def __init__(self, bot):
        self.bot = bot

    # stolen from https://github.com/Rapptz/RoboDanny/blob/c8fef9f07145cef6c05416dc2421bbe1d05e3d33/cogs/meta.py#L164
    @commands.command(description="bot source code",
                      brief="bot source code",
                      pass_context=True,
                      aliases=["src"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def source(self, ctx, *, command : str=""):
        if (not command):
            await self.bot.messaging.reply(ctx.message, self.bot.source_url)
            return
        
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
        
        for i, s in enumerate(self.bot.servers):
            num = i + 1
            
            if (s.unavailable): # can't retrieve info about server
                msg += "{num}. {id} - server is unavailable!\n".format(num=num, id=s.id)
            else:
                msg += "{num}. {name} owned by {owner}#{ownerid}\n".format(num=num,
                                                                         name=s.name,
                                                                         owner=s.owner.name,
                                                                         ownerid=s.owner.discriminator)
                
        msg += "```"

        await self.bot.messaging.reply(ctx.message, msg)
        
    @cmd.command(description="have the bot leave a server",
                 brief="have the bot leave a server",
                 pass_context=True)
    async def leave(self, ctx, *, search : str):
        server = self.bot.bot_utils.find_server(search)
        
        if (not server):
            await self.bot.messaging.reply(ctx.message, "No server found for `{}`".format(search))
            return
        
        leave_msg = await self.bot.messaging.reply(ctx.message, "Are you sure you want me to leave `{name} [{id}]`? (yes/no)".format(name=server.name,
                                                                                                                       id=server.id))
        msg = await self.bot.wait_for_message(author=ctx.message.author, check=checks.is_yes_or_no, timeout=15)
        
        if (not msg or msg.content.lower() != "yes"):
            await self.bot.bot_utils.delete_message(leave_msg)
            return
        
        await self.bot.leave_server(server)
        await self.bot.messaging.reply(ctx.message, "Left `{name}` [{id}]".format(name=server.name, id=server.id))
        
    @cmd.command(description="resource usage on the bot's server",
                 brief="resource usage on the bot's server",
                 pass_context=True)
    async def usage(self, ctx):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        msg = "CPU: {cpu}%\nMemory: {percent}% ({used}/{total})".format(cpu=cpu,
                                                                        percent=memory.percent,
                                                                        used=size(memory.used),
                                                                        total=size(memory.total))

        await self.bot.messaging.reply(ctx.message, msg)
        
    @cmd.command(description="prints status of cogs",
                 brief="prints status of cogs",
                 pass_context=True)
    async def cogs(self, ctx): 
        loaded_cogs = ""
        unloaded_cogs = ""
        
        for cog, info in self.bot.loaded_cogs.items():
            if (not info["loaded"]):
                unloaded_cogs += cog + "\n"
            else:
                loaded_cogs += cog + "\n"
                
        msg = """Loaded cogs:\n```
{loaded_cogs}```

Unloaded cogs:
```
{unloaded_cogs}```""".format(loaded_cogs=loaded_cogs,
              unloaded_cogs=unloaded_cogs)
  
        await self.bot.messaging.reply(ctx.message, msg)

    @cmd.command(description="load a cog",
                 brief="load a cog",
                 pass_context=True)
    async def load(self, ctx, cog : str):
        if (not cog in self.bot.loaded_cogs):
            await self.bot.messaging.reply(ctx.message, "Cog `{}` not found".format(cog))
            return
        
        try:
            self.bot.load_extension(self.bot.loaded_cogs[cog]["ext"])
        except Exception as e:
            await self.bot.messaging.reply(ctx.message, "Failed to load cog `{}`: ```{}```".format(cog, e))
        else:
            self.bot.loaded_cogs[cog] = {"ext": self.bot.loaded_cogs[cog]["ext"],
                                         "loaded": True}
            
            await self.bot.messaging.reply(ctx.message, "Loaded `{}`".format(cog))
    
    @cmd.command(description="unload a cog",
                 brief="unload a cog",
                 pass_context=True)
    async def unload(self, ctx, cog : str):
        if (not cog in self.bot.loaded_cogs):
            await self.bot.messaging.reply(ctx.message, "Cog `{}` not found".format(cog))
            return
        
        try:
            self.bot.unload_extension(self.bot.loaded_cogs[cog]["ext"])
            
        except Exception as e:
            await self.bot.messaging.reply(ctx.message, "Failed to unload cog `{}`: ```{}```".format(cog, e))
        else:
            self.bot.loaded_cogs[cog] = {"ext": self.bot.loaded_cogs[cog]["ext"],
                                         "loaded": False}
            
            await self.bot.messaging.reply(ctx.message, "Unloaded `{}`".format(cog))
    
    @cmd.command(description="reload a cog",
                 brief="reload a cog",
                 pass_context=True)
    async def reload(self, ctx, cog : str):
        if (not cog in self.bot.loaded_cogs):
            await self.bot.messaging.reply(ctx.message, "Cog `{}` not found".format(cog))
            return
        
        try:
            self.bot.unload_extension(self.bot.loaded_cogs[cog]["ext"])
            self.bot.loaded_cogs[cog] = {"ext": self.bot.loaded_cogs[cog]["ext"],
                                         "loaded": False}
            
            self.bot.load_extension(self.bot.loaded_cogs[cog]["ext"])
            self.bot.loaded_cogs[cog] = {"ext": self.bot.loaded_cogs[cog]["ext"],
                                         "loaded": True}
            
        except Exception as e:
            await self.bot.messaging.reply(ctx.message, "Failed to reload cog `{}`: ```{}```".format(cog, e))
            
        else:
            await self.bot.messaging.reply(ctx.message, "Reloaded `{}`".format(cog))

def setup(bot):
    bot.add_cog(Meta(bot))