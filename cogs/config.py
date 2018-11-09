from discord.ext import commands

from modules import checks

import json

class Config:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(description="reads, edits, and/or updates the config (owner only)",
                    brief="reads, edits, and/or updates the config (owner only)",
                    pass_context=True,
                    hidden=True,
                    aliases=["config"])
    @commands.check(checks.is_owner)
    async def cfg(self, ctx):
        if (not ctx.invoked_subcommand):
            await self.bot.messaging.reply(ctx.message, "Invalid command")

    @cfg.command(description="reloads the bot's config",
                 brief="reloads the bot's config",
                 pass_context=True)
    async def reload(self, ctx):
        await self.bot.send_typing(ctx.message.channel)

        try:
            self.bot.load_config()

        except Exception as e:
            await self.bot.messaging.reply(ctx.message, f"Failed to reload config: `{e}`")

        else:
            await self.bot.messaging.reply(ctx.message, "Reloaded config")

    @cfg.command(description="reports the bot's current config (MAY CONTAIN SENSITIVE INFO)",
                  brief="reports the bot's current config (MAY CONTAIN SENSITIVE INFO)",
                  pass_context=True,
                  name="print")
    async def print_cfg(self, ctx):
        if (not ctx.message.channel.is_private):
            await self.bot.messaging.reply(ctx.message, "This command can only be used in a private message")
            return

        data = json.dumps(self.bot.CONFIG, indent=2)

        await self.bot.messaging.reply(ctx.message, f"```\n{data}\n```")

def setup(bot):
    bot.add_cog(Config(bot))