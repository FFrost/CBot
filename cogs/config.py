import discord
from discord.ext import commands

from modules import checks, utils

import json
import strconv

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(description="reads, edits, and/or updates the config (owner only)",
                    brief="reads, edits, and/or updates the config (owner only)",
                    hidden=True,
                    aliases=["config"])
    @commands.check(checks.is_owner)
    async def cfg(self, ctx):
        if (not ctx.invoked_subcommand):
            await ctx.invoke(self.print_cfg)

    @cfg.command(description="reloads the bot's config",
                 brief="reloads the bot's config")
    async def reload(self, ctx):
        await ctx.trigger_typing()
    
        try:
            self.bot.load_config()
        except Exception as e:
            await ctx.send(f"Failed to reload config: `{e}`")
        else:
            await ctx.send("Reloaded config")

    @cfg.command(description="reports the bot's current config (MAY CONTAIN SENSITIVE INFO)",
                  brief="reports the bot's current config (MAY CONTAIN SENSITIVE INFO)",
                  name="print")
    async def print_cfg(self, ctx):
        if (ctx.guild):
            await ctx.send(f"{ctx.author.mention} This command can only be used in a private message")
            return

        data = json.dumps(self.bot.CONFIG, indent=2)

        await ctx.send(f"```\n{data}\n```")

    @cfg.command(description="edits a value in the config and reloads it\n" \
                             "to edit a subvalue (embeds -> enabled), type the key as embeds.enabled\n" \
                             "ex: !cfg edit embeds.enabled False",
                 brief="edits a value in the config and reloads it")
    async def edit(self, ctx, key: str, *, value):
        # convert the string to the python type
        try:
            literal_val = strconv.convert(value)
        except ValueError:
            await ctx.send(f"Invalid value `{value}`")
            return

        key_list = key.split(".")

        # check if the key exists
        d = self.bot.CONFIG.copy()

        for k in key_list:
            try:
                d = d[k]
            except KeyError:
                await ctx.send(f"Key `{key}` not found")
                return
        
        # set value
        old_val = utils.nested_set(self.bot.CONFIG, key_list, literal_val)

        # reload
        ctx.invoke(self.reload)

        # save to disk
        self.bot.save_config()

        await ctx.send(f"Set `{key}`: `{literal_val}` (old value: `{old_val}`)")

def setup(bot):
    bot.add_cog(Config(bot))
