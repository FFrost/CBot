import discord
from discord.ext import commands

class NoVoiceChannel(commands.CommandError):
    pass

owner_id = None

def is_owner(ctx: commands.Context) -> bool:
    return (ctx.message.author.id == owner_id)

# if the message author is in a voice channel
# TODO: permission check if we can join the channel
def is_in_voice_channel(ctx: commands.Context) -> bool:
    if (isinstance(ctx.channel, discord.abc.PrivateChannel)):
        return False
    
    if (ctx.author.voice.channel is None):
        raise NoVoiceChannel()
    
    return True

def yes_no_check(message: discord.Message) -> bool:
    return (message.content.lower() == "yes")

def is_yes_or_no(message: discord.Message) -> bool:
    return (message.content.lower() in ["yes", "no"])

"""
TODO:
    add groups that can kick while not having discord permissions (ex. specific role that
    can use CBot to kick/ban but not kick themselves)
"""
def can_kick(ctx: commands.Context) -> bool:
    return (ctx.channel.permissions_for(ctx.author).kick_members)

def can_ban(ctx: commands.Context) -> bool:
    return (ctx.channel.permissions_for(ctx.author).ban_members)