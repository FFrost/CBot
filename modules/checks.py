import discord
from discord.ext import commands

class NoVoiceChannel(commands.CommandError):
    pass

owner_id = None
    
def is_owner(ctx):
    return (ctx.message.author.id == owner_id)

# if the channel is private or the user has "manage messages" permissions
def can_manage_messages(ctx):
    if (ctx.message.channel.is_private):
        return True
    elif (ctx.message.author.permissions_in(ctx.message.channel).manage_messages):
        return True
    
    return False

# if the message author is in a voice channel
# TODO: permission check if we can join the channel
def is_in_voice_channel(ctx):
    if (ctx.message.channel.is_private):
        return False
    
    if (ctx.message.author.voice_channel is None):
        raise NoVoiceChannel()
    
    return True