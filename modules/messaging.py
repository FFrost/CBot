import discord
from discord.ext import commands

from modules import enums

import asyncio
import inspect
import re
import math
from collections import OrderedDict
from typing import Union, List

class Messaging:
    def __init__(self, bot):
        self.bot = bot

        # emojis for browsing image searches
        self.EMOJI_CHARS = OrderedDict()
        self.EMOJI_CHARS["arrow_backward"] = "\N{BLACK LEFT-POINTING TRIANGLE}"
        self.EMOJI_CHARS["arrow_forward"] = "\N{BLACK RIGHT-POINTING TRIANGLE}"
        self.EMOJI_CHARS["stop_button"] = "\N{BLACK SQUARE FOR STOP}"
    
    # private message the developer
    # input: msg, message to send
    async def message_developer(self, msg: str) -> None:
        if (not self.bot.dev_id):
            return
        
        user = self.bot.get_user(self.bot.dev_id)
            
        if (user is None):
            return
        
        await user.send(msg)
    
    # send message to the "admin" channel if it exists
    # input: msg, content of message to send
    #        guild, guild to send message in
    async def msg_admin_channel(self, msg: str, guild: discord.Guild) -> None:
        if (not self.bot.CONFIG["admin"]["log_channel"]):
            return

        try:
            if (not guild):
                return
            
            channel = discord.utils.find(lambda c: (c.name == self.bot.CONFIG["admin"]["log_channel"]), guild.channels)
            
            if (not channel):
                return
            
            if (not channel.permissions_for(guild.me).send_messages):
                return
    
            await channel.send(msg)

        except discord.errors.HTTPException:
            return
        
        except Exception as e:
            await self.error_alert(e)
            
    # alerts the developer if an error occurs
    # input: e, the error to output
    #        uid, the user's unique id
    #        extra, any extra information to include
    async def error_alert(self, e: Exception, extra: str = "") -> None:              
        function_name = inspect.stack()[1][3]
            
        caller_func = function_name or "NULL_FUNC"
        if (caller_func == "<module>"):
            caller_func = "main"
            
        if (extra):
            extra = f" ({extra})"
    
        err = "{func}{extra}:\n```{error}```".format(func=caller_func,
                                                        error=str(e),
                                                        extra=extra)
        print(err)
        await self.message_developer(err)
            
    # add reaction to message if any keyword is in message
    # input: message, message to react to
    #        keyword, keyword(s) to look for in message content, author name or id
    #        emoji, emoji(s) to react with
    #        partial, should react if partial keywords are found
    async def react(self,
                    message: discord.Message,
                    keyword: Union[str, List[str]],
                    emojis: Union[str, List[str]],
                    partial: bool = True
                    ) -> None:
        if (not message.channel.permissions_for(message.guild.me).add_reactions):
            return
    
        try:
            if (not isinstance(keyword, list)):
                keyword = [keyword]
            
            if (not isinstance(emojis, list)):
                emojis = [emojis]
            
            found = False
            
            if (partial): # search for any occurence of key in message
                for key in keyword:
                    if (key in message.content.lower()):
                        found = True
                        break
                    elif (key in message.author.name.lower()):
                        found = True
                        break
                    elif (key in message.author.id):
                        found = True
                        break
            else: # search for word by itself
                for key in keyword:
                    if (re.match(r"\b" + key + r"\b", message.content.lower())):
                        found = True
                        break
                    elif (key == message.author.name):
                        found = True
                        break
                    elif (key == message.author.id):
                        found = True
                        break
            
            if found:
                # react with custom emojis
                for custom_emoji in self.bot.get_all_emojis():
                    if (custom_emoji.name in emojis and custom_emoji.guild == message.guild):
                        await self.bot.add_reaction(message, custom_emoji)
                
                for e in emojis:
                    # react with normal emojis and ignore custom ones
                    try:
                        await self.bot.add_reaction(message, e)
                    except discord.errors.DiscordException:
                        pass
        
        except Exception as e:
            if ("Reaction blocked" in str(e)):
                return
            
            await self.error_alert(e)
            
    # adds reactions for browsing an image to a message
    # input: message, message to add reactions to
    async def add_img_reactions(self, message: discord.Message) -> None:
        try:
            for name, emoji in self.EMOJI_CHARS.items():
                if (name == "stop_button" and not isinstance(message.channel, discord.abc.PrivateChannel) and not message.channel.permissions_for(message.guild.me).manage_messages): # skip delete if we can't delete messages
                    continue
                
                await message.add_reaction(emoji)
        
        except discord.errors.NotFound:
            pass
        except Exception as e:
            await self.error_alert(e)