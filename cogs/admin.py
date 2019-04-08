import discord
from discord.ext import commands

from modules import checks

class Admin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="kicks a user from the server",
                      brief="kicks a user from the server",
                      pass_context=True,
                      no_pm=True,
                      enabled=False)
    @commands.cooldown(1, 10, commands.BucketType.server)
    @commands.check(checks.can_kick)
    async def kick(self, ctx, member: discord.Member, reason: str=""):
        if (not ctx.message.server.me.server_permissions.kick_members):
            await self.bot.messaging.reply(ctx.message, "I don't have kick permissions")
            return

        if (member == ctx.message.server.me):
            await self.bot.messaging.reply(ctx.message, "nice try")
            return
        
        try:
            await self.bot.kick(member)
        except discord.Forbidden as e:
            await self.bot.messaging.reply(ctx.message, f"I can't kick `{member}`: `{e}`")
        except discord.HTTPException as e:
            await self.bot.messaging.reply(ctx.message, f"Failed to kick `{member}`: `{e}`")
        else:
            # log
            pass

    @commands.command(description="""bans a user from the server\n
delete_message_days = The number of days worth of messages to delete
from the user in the server. The minimum is 0 and the maximum is 7.""",
                      brief="bans a user from the server",
                      pass_context=True,
                      no_pm=True,
                      enabled=False)
    @commands.cooldown(1, 10, commands.BucketType.server)
    @commands.check(checks.can_ban)
    async def ban(self, ctx, member: discord.Member, reason: str, delete_message_days: int=1):
        # await self.bot.ban(member, delete_message_days)
        pass

def setup(bot):
    bot.add_cog(Admin(bot))