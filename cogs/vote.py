import discord
from discord.ext import commands

class Vote:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(description="starts a vote",
                    brief="starts a vote",
                    pass_context=True)
    async def vote(self, ctx, title: str, *options):
        if (ctx.invoked_subcommand):
            return

        # start a poll

    @vote.command(description="start a vote to mute a user",
                  brief="start a vote to mute a user",
                  pass_context=True)
    async def mute(self, ctx, user: discord.User):
        pass

def setup(bot):
    bot.add_cog(Vote(bot))