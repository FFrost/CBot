import discord
from discord.ext import commands

owner_id = None
    
def is_owner(ctx):
    return (ctx.message.author.id == owner_id)