import discord
from discord.ext import commands

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