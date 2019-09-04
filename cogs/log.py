import discord
from discord.ext import commands

import asyncio
import datetime
from modules import checks, utils

class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.COOLDOWN = 10 # seconds

        self.update_task = self.bot.loop.create_task(self.update_log())

        self.logs = {}

    def cog_unload(self):
        self.update_task.cancel()

    async def update_log(self):
        await self.bot.wait_until_ready()

        while (not self.bot.is_closed()):
            sent_ids = []

            for gid, msgs in self.logs.items():
                guild = self.bot.get_guild(gid)

                chan = discord.utils.find(lambda c: (c.name == self.bot.CONFIG["log"]["channel_name"]), guild.channels) or None

                if (not chan):
                    return

                if (not chan.permissions_for(guild.me).send_messages):
                    return

                await chan.send("\n".join(msgs[:10]))
                await asyncio.sleep(1)

                msgs_copy = msgs.copy()

                for _i in range(0, (10 if len(msgs_copy) > 10 else len(msgs_copy))):
                    del self.logs[gid][0]
                
                sent_ids.append(gid)

            for gid in sent_ids:
                if (len(self.logs[gid]) == 0):
                    del self.logs[gid]

            await asyncio.sleep(self.COOLDOWN)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if (not self.bot.CONFIG["log"]["enabled"] ):
            return
        
        chan = discord.utils.find(lambda c: (c.name == self.bot.CONFIG["log"]["channel_name"]), member.guild.channels) or None

        if (not chan):
            return

        if (not chan.permissions_for(member.guild.me).send_messages):
            return

        time = datetime.datetime.now().strftime("%-I:%M:%S %p")

        if (before.channel is None):
            s = f"[{time}] {member} joined {after.channel.mention}"
        elif (after.channel is None):
            s = f"[{time}] {member} left {before.channel.mention}"
        elif (before.channel == after.channel): # ignore muting/unmuting
            return
        elif (after.channel == member.guild.afk_channel):
            s = f"[{time}] {member} was moved to afk channel {member.guild.afk_channel.mention}"
        elif (before.channel is not None and after.channel is not None):
            s = f"[{time}] {member} switched from {before.channel.mention} to {after.channel.mention}"

        if (member.guild.id in self.logs):
            self.logs[member.guild.id] += [s]
        else:
            self.logs[member.guild.id] = [s]

def setup(bot):
    bot.add_cog(Log(bot))
