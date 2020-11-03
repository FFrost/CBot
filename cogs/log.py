import discord
from discord.ext import commands

import asyncio
import datetime
from modules import checks, utils
from random import randint

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

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            if (member == self.bot.user):
                return
            
            await self.bot.messaging.msg_admin_channel("{time} {name} [{uid}] joined".format(time=utils.get_cur_time(),
                                                                                         name=utils.format_member_name(member),
                                                                                         uid=member.id),
                                                                                         member.guild)
            
        except Exception as e:
            await self.bot.messaging.error_alert(e)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            if (member == self.bot.user):
                return

            msg = f"{utils.get_cur_time()} {utils.format_member_name(member)} [{member.id}] left"

            if (randint(0, 5) == 0):
                msg = f"{utils.get_cur_time()} \N{CRAB} {utils.format_member_name(member)} [{member.id}] is gone \N{CRAB}"
            
            await self.bot.messaging.msg_admin_channel(msg, member.guild)
        
        except Exception as e:
            await self.bot.messaging.error_alert(e)
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            await self.bot.messaging.message_developer("{time} CBot joined guild {name}#{id}".format(time=utils.get_cur_time(),
                                                                                                             name=guild.name,
                                                                                                             id=guild.id))

            perms = dict(guild.me.guild_permissions)
            all_perms = self.bot.REQUIRED_PERMISSIONS + self.bot.VOICE_PERMISSIONS + self.bot.OPTIONAL_PERMISSIONS
            perms_we_dont_have = []

            for perm in all_perms:
                if (not perms[perm]):
                    perms_we_dont_have.append(perm)

            msg = f"Hi, thanks for adding me to your guild `{guild.name}`. The minimum permissions I need to function are " \
                  f"{utils.format_code_brackets(self.bot.REQUIRED_PERMISSIONS).replace('_', ' ')}.\n" \
                  f"For voice support, I need {utils.format_code_brackets(self.bot.VOICE_PERMISSIONS).replace('_', ' ')} in the voice channel you want me to join.\n" \
                  f"For additional commands, I need {utils.format_code_brackets(self.bot.OPTIONAL_PERMISSIONS).replace('_', ' ')}\n"

            msg += (f"I currently don't have {utils.format_code_brackets(perms_we_dont_have).replace('_', ' ')} permissions."
                    if (len(perms_we_dont_have) > 0) else
                    "I have all the permissions I need. Thanks!")

            try:
                await guild.owner.send(msg)
            except discord.errors.Forbidden:
                pass
        
        except Exception as e:
            await self.bot.messaging.error_alert(e)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            await self.bot.messaging.message_developer("{time} CBot was removed from guild {name}#{id}".format(time=utils.get_cur_time(),
                                                                                                                       name=guild.name,
                                                                                                                       id=guild.id))
        
        except Exception as e:
            await self.bot.messaging.error_alert(e)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if (before.nick is None and after.nick is not None):
            await self.bot.messaging.msg_admin_channel(f"{before} added a nickname {after.display_name}", before.guild)
        elif (before.nick is not None and after.nick is None):
            await self.bot.messaging.msg_admin_channel(f"{after} removed their nickname of {before.display_name}", before.guild)
        elif (before.nick != after.nick):
            await self.bot.messaging.msg_admin_channel(f"{before} changed their nickname to {after.display_name}", before.guild)

    """@commands.Cog.listener()
    async def on_user_update(self, before, after):
        if (before.name != after.name):
            print(f"{before} changed their username to {after}")
            await self.bot.messaging.message_developer(f"{before} changed their username to {after}")"""

def setup(bot):
    bot.add_cog(Log(bot))
