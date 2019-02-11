import discord
from discord.ext import commands
import time

from typing import List

class Paginator:
    def __init__(self, bot: commands.Bot, ctx: commands.Context, embeds: List[discord.Embed], *args, **kwargs):
        self.bot = bot
        self.ctx = ctx # context the paginator was invoked in

        self.index = 0
        self.max_index = len(embeds)

        self.embeds = embeds

        self.last_updated = time.time()

        self.message = None # embed message

        # kwargs
        self.expiry_time = kwargs.get("expiry_time", 120) # time until the embed expires
        self.paging_cooldown = kwargs.get("paging_cooldown", 1) # 1 second cooldown in between paging

    # can the paginator be updated anymore
    def has_expired(self) -> bool:
        return (time.time() > self.last_updated + self.expiry_time)

    # spam protection
    def can_be_updated(self) -> bool:
        return (time.time() > self.last_updated + self.paging_cooldown)

    # pages forwards or backwards
    async def page(self, forward: bool = True):
        if (not self.can_be_updated()):
            return
        
        direction = 1 if forward else -1

        self.index += direction

        if (self.index < 0):
            self.index = self.max_index - 1
        elif (self.index >= self.max_index):
            self.index = 0

        embed = self.embeds[self.index]

        await self.update(embed)

    # updates the message with the new embed
    async def update(self, embed: discord.Embed = None):
        if (embed is None):
            embed = self.embeds[self.index]
        
        if (not self.message):
            self.message = await self.bot.send_message(self.ctx.message.channel, embed=embed)
            
            await self.bot.messaging.add_img_reactions(self.message)
        else:
            await self.bot.edit_message(self.message, embed=embed)

        self.last_updated = time.time()

    # call when the embed has passed its expiry time
    async def clear_reactions(self):
        if (not self.message):
            return
        
        await self.bot.clear_reactions(self.message)

    # deletes the embed message and the command message
    async def delete(self):
        if (not self.message):
            return
        
        await self.bot.bot_utils.delete_message(self.ctx.message)
        await self.bot.bot_utils.delete_message(self.message)
        self.message = None

    # call in on_reaction_add to update the paginator on reactions
    async def reaction_hook(self, reaction: discord.Reaction, user: discord.User):
        if (not self.message):
            return
        
        message = reaction.message

        if (user == self.bot.user):
            return

        if (message.id != self.message.id):
            return

        if (self.ctx.message.author != user):
            return

        emoji = reaction.emoji

        if (message.reactions and reaction in message.reactions):
            if (self.bot.bot_utils.get_permissions(message.channel).manage_emojis):
                try:
                    await self.bot.remove_reaction(message, emoji, user) # remove the reaction so the user can react again
                except discord.DiscordException:
                    pass

        if (not self.can_be_updated()):
            return
        
        if (emoji == self.bot.messaging.EMOJI_CHARS["stop_button"]):
            await self.delete()
        elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_forward"]):
            await self.page(forward = True)
        elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_backward"]):
            await self.page(forward = False)

async def create_paginator(bot: commands.Bot, ctx: commands.Context, embeds: List[discord.Embed], *args, **kwargs) -> Paginator:
    pager = Paginator(bot, ctx, embeds, *args, **kwargs)
    await pager.update()
    
    return pager
