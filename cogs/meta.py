import discord
from discord.ext import commands

from modules import checks, utils
import inspect
import os
import sys
import psutil
import importlib
import io
import textwrap
import traceback
import humanize
from contextlib import redirect_stdout
from datetime import datetime

class Meta:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    # stolen from https://github.com/Rapptz/RoboDanny/blob/c8fef9f07145cef6c05416dc2421bbe1d05e3d33/cogs/meta.py#L164
    @commands.command(description="bot source code",
                      brief="bot source code",
                      pass_context=True,
                      aliases=["src"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def source(self, ctx, *, command: str = ""):
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
        
        location = obj.callback.__module__.replace(".", "/") + ".py"
        
        url = "{source_url}/blob/master/{location}#L{firstlineno}-L{end}".format(source_url=self.bot.source_url,
                                                         location=location,
                                                         firstlineno=firstlineno,
                                                         end=(firstlineno + len(lines) - 1))
        
        await self.bot.messaging.reply(ctx.message, url)
            
    @commands.group(description="run commands on the bot (owner only)",
                    brief="run commands on the bot (owner only)",
                    pass_context=True,
                    hidden=True,
                    aliases=["command"])
    @commands.check(checks.is_owner)
    async def cmd(self, ctx):
        if (not ctx.invoked_subcommand):
            await self.bot.messaging.reply(ctx.message, "Invalid command")
    
    @cmd.command(description="stops the bot",
                 brief="stops the bot",
                 pass_context=True,
                 aliases=["logout"])
    async def stop(self, ctx):
        await self.bot.messaging.reply(ctx.message, "Shutting down...")
        await self.bot.logout()
        
    @cmd.command(description="makes the bot say something",
                 brief="makes the bot say something")
    async def say(self, *, msg: str):
        await self.bot.say(msg)
        
    @cmd.command(description="changes the bot's status",
                 brief="changes the bot's status",
                 pass_context=True)
    async def status(self, ctx, *, status: str):
        await self.bot.change_presence(game=discord.Game(name=status))
        await self.bot.messaging.reply(ctx.message, "Set status to `{}`".format(status))
        
    # TODO: convert to paginator
    @commands.command(description="what servers the bot is in",
                 brief="what servers the bot is in",
                 pass_context=True)
    @commands.check(checks.is_owner)
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
    async def leave(self, ctx, *, search: str):
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
    async def load(self, ctx, cog: str):
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
    async def unload(self, ctx, cog: str):
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
    
    @cmd.command(description="reload a cog or module",
                 brief="reload a cog or module",
                 pass_context=True)
    async def reload(self, ctx, name: str):
        # reload cog
        if (name in self.bot.loaded_cogs):
            try:
                self.bot.unload_extension(self.bot.loaded_cogs[name]["ext"])
                self.bot.loaded_cogs[name] = {"ext": self.bot.loaded_cogs[name]["ext"],
                                            "loaded": False}
                
                self.bot.load_extension(self.bot.loaded_cogs[name]["ext"])
                self.bot.loaded_cogs[name] = {"ext": self.bot.loaded_cogs[name]["ext"],
                                            "loaded": True}
                
            except Exception as e:
                await self.bot.say(f"Failed to reload cog `{name}`: ```{e}```")
                
            else:
                await self.bot.say(f"Reloaded cog `{name}`")
        # reload module
        elif (f"modules.{name}" in sys.modules.keys()):
            try:
                importlib.reload(sys.modules[f"modules.{name}"])

            except Exception as e:
                await self.bot.say(f"Failed to reload module `{name}`: ```{e}```")

            else:
                await self.bot.say(f"Reloaded module `{name}`")
        # it's neither
        else:
            await self.bot.say(f"No cog or module found named `{name}`")

    @commands.command(description="generates an invite link to invite the bot to your server",
                      brief="generates an invite link to invite the bot to your server",
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def invite(self, ctx):
        if (not ctx.message.channel.is_private):
            await self.bot.send_message(ctx.message.author, "This command can only be used in a private message")
            return

        if (not self.bot.CONFIG["bot_can_be_invited"] and ctx.message.author.id != checks.owner_id):
            await self.bot.say("Sorry, the owner has disabled invitations")
            return

        full_perms = 3271744
        no_2fa_perms = 3263552

        url = f"https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot"

        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)

        embed.description = """There are several options for inviting the bot:

1. Inviting the bot with no permissions and manually adding the ones you want.

2. Inviting the bot with full permissions. __**This requires Two-Factor Authentication (2FA) to be enabled on your account.**__
See the list of required permissions below. For more information on 2FA, see: https://support.discordapp.com/hc/en-us/articles/219576828-Setting-up-Two-Factor-Authentication

3. Inviting the bot without 2FA-required permissions, and then manually adding the required permissions afterwards.

You need to have Manage Server permissions on the server you want to invite the bot to in order to invite it to that server.
If you don't see the server on the list of servers after clicking the link, you don't have those permissions.

Permissions the bot requires:
Manage Messages **(2FA)**, Read Messages, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Connect, Speak
"""

        embed.add_field(name=":negative_squared_cross_mark: No permissions", value=url, inline=False)
        embed.add_field(name=":white_check_mark: Full permissions", value=f"{url}&permissions={full_perms}", inline=False)
        embed.add_field(name=":no_mobile_phones: No Two-Factor Authentication permissions", value=f"{url}&permissions={no_2fa_perms}", inline=False)

        await self.bot.send_message(ctx.message.author, embed=embed)

    # eval command stolen from ItWasAllIntended - https://gist.github.com/ItWasAllIntended/905500623d772d1a153049715e3e68b7
    @staticmethod
    def cleanup_code(content: str) -> str:
        """Automatically removes code blocks from the code."""
        # Remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        
        return content

    @commands.command(pass_context=True, hidden=True, name='eval', aliases=["ev"])
    @commands.check(checks.is_owner)
    async def _eval(self, ctx, *, body: str):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'server': ctx.message.server,
            'message': ctx.message,
            '_': self._last_result,
            "say": self.bot.say
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            try:
                await self.bot.add_reaction(ctx.message, "\N{NEGATIVE SQUARED CROSS MARK}")
            except discord.errors.DiscordException:
                pass

            return await self.bot.say(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await self.bot.say(f'```py\n{value}{traceback.format_exc()}\n```')

            try:
                await self.bot.add_reaction(ctx.message, "\N{NEGATIVE SQUARED CROSS MARK}")
            except discord.errors.DiscordException:
                pass
        else:
            value = stdout.getvalue()
            try:
                await self.bot.add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")
            except:
                pass

            if ret is None:
                if value:
                    await self.bot.say(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await self.bot.say(f'```py\n{value}{ret}\n```')

    @commands.command(description="information about the bot",
                      brief="information about the bot",
                      pass_context=True)
    async def about(self, ctx):
        embed = discord.Embed(title=f"About {self.bot.user.name}#{self.bot.user.discriminator}", color=discord.Color.blue())

        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)

        embed.add_field(name="ID", value=f"{self.bot.user.id}")

        if (self.bot.user.display_name != self.bot.user.name):
            embed.add_field(name="Nickname", value=f"")

        if (ctx.message.server is not None):
            embed.add_field(name="Joined the server at", value=f"{utils.format_time(ctx.message.server.me.joined_at)}",)
        
        embed.add_field(name="Created at", value=f"{utils.format_time(self.bot.user.created_at)}")
        embed.add_field(name="Servers", value=f"{len(self.bot.servers)}")
        embed.add_field(name="Users", value=f"{len([member for member in self.bot.get_all_members()])}")

        cbot_process = psutil.Process(os.getpid())
        embed.add_field(name="CPU used", value=f"{cbot_process.cpu_percent(0.1)}%")
        embed.add_field(name="Memory used", value=f"{humanize.naturalsize(cbot_process.memory_info().rss)}")

        if (hasattr(self.bot, "uptime")):
            embed.add_field(name="Uptime", value=utils.get_uptime(self.bot.uptime))

        embed.set_footer(text=f"Requested at {utils.format_time(datetime.now())}")

        await self.bot.say(embed=embed)

    @commands.command(description="invoke a command and delete the message",
                      brief="invoke a command and delete the message",
                      pass_context=True,
                      aliases=["cmd_del", "cd"])
    async def cmd_delete(self, ctx, command: str):
        command_obj = self.bot.commands.get(command)

        if (not command_obj):
            await self.bot.messaging.reply(ctx.message, f"Command `{command}` not found")
            return

        await self.bot.bot_utils.delete_message(ctx.message)
        await command_obj.invoke(ctx)

def setup(bot):
    bot.add_cog(Meta(bot))