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
    if (ctx.message.channel.is_private):
        return False
    
    if (ctx.message.author.voice_channel is None):
        raise NoVoiceChannel()
    
    return True

def yes_no_check(message: discord.Message) -> bool:
    return (message.content.lower() == "yes")

def is_yes_or_no(message: discord.Message) -> bool:
    return (message.content.lower() in ["yes", "no"])