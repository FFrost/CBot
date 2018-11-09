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
        
    # send a user a message and mention them in it
    # input: dest, destination to send message to (string should be id of user)
    #        msg, message to send
    # output: the reply message object sent to the user
    async def reply(self,
                    dest: Union[discord.User, discord.Message, commands.Context, str],
                    msg: str,
                    channel: discord.Channel = None
                    ) -> discord.Message:

        try:
            msg = str(msg)
        except Exception:
            pass
        
        # find the destination of the reply
        if (isinstance(dest, discord.User)):
            if (not channel):
                destination = user = dest
            else:
                destination = channel
                user = dest
        elif (isinstance(dest, discord.Message)):
            destination = dest.channel
            user = dest.author
        elif (isinstance(dest, str)):
            user = await self.bot.bot_utils.find(dest)
            
            if (user):
                destination = user
            else:
                return None
        elif (isinstance(dest, commands.Context)):
            destination = dest.message.channel
            user = dest.message.author
        else:
            return None

        # check if we have send message permissions
        perms = None

        if (channel):
            perms = self.bot.bot_utils.get_permissions(channel)
        elif (isinstance(destination, discord.Channel)):
            perms = self.bot.bot_utils.get_permissions(destination)

        if (perms and not perms.send_messages):
            return
        
        # split the message into multiple replies if necessary
        max_message_length = enums.DISCORD_MAX_MESSAGE_LENGTH - enums.DISCORD_MAX_MENTION_LENGTH - 1 # 1 for the space between mention and message
        
        if (len(msg) > max_message_length):
            code_blocks = ""
            
            if (msg.startswith("```")):
                max_message_length -= 6 # start and end each split with "```"
                code_blocks = "```"
            elif (msg.startswith("`")):
                max_message_length -= 2 # start and end each split with "`"
                code_blocks = "`"
            
            num_messages = math.ceil(len(msg) / max_message_length)
            
            for i in range(num_messages):
                split_msg = msg[i * max_message_length : (i + 1) * max_message_length]
                
                if (not split_msg.startswith("`") and code_blocks is not None):
                    split_msg = code_blocks + split_msg
                if (not split_msg.endswith("`") and code_blocks is not None):
                    split_msg += code_blocks
                
                await self.bot.send_message(destination, "{} {}".format(user.mention, split_msg))
                await asyncio.sleep(1)
                
            return None # TODO: return a list of sent messages?
        else:
            return await self.bot.send_message(destination, "{} {}".format(user.mention, msg))
    
    # private message the developer
    # input: msg, message to send
    async def message_developer(self, msg: str) -> None:
        if (not self.bot.dev_id):
            return
        
        user = await self.bot.bot_utils.find(self.bot.dev_id)
            
        if (user is None):
            return
        
        await self.reply(user, msg)
    
    # private message a user
    # input: uid, id of user to message
    #        msg, message content to send
    async def private_message(self, uid: str, msg: str) -> None:
        user = await self.bot.bot_utils.find(uid)
            
        if (user is None):
            return
        
        await self.reply(user, msg)
    
    # send message to the "admin" channel if it exists
    # input: msg, content of message to send
    #        server, server to send message in
    async def msg_admin_channel(self, msg: str, server: discord.Server) -> None:
        if (not self.bot.CONFIG["log_channel"]):
            return

        try:
            if (not server):
                return
            
            channel = discord.utils.get(server.channels, name=self.bot.CONFIG["log_channel"], type=discord.ChannelType.text)
            
            if (not channel):
                return
            
            if (not channel.permissions_for(server.me)):
                return
    
            await self.bot.send_message(channel, msg)

        except discord.errors.HTTPException:
            return
        
        except Exception as e:
            await self.error_alert(e)
            
    # alerts a user if an error occurs, will always alert developer
    # input: e, the error to output
    #        uid, the user's unique id
    #        extra, any extra information to include
    async def error_alert(self, e: Exception, uid: str = "", extra: str = "") -> None:
        if (not uid):
            if (not self.bot.dev_id):
                return
            
            uid = self.bot.dev_id
            
        function_name = inspect.stack()[1][3]
            
        caller_func = function_name or "NULL_FUNC"
        if (caller_func == "<module>"):
            caller_func = "main"
            
        if (extra):
            extra = " (" + extra + ")"
    
        err = "{func}{extra}:\n```{error}```".format(func=caller_func,
                                                        error=str(e),
                                                        extra=extra)
        print(err)
        await self.private_message(uid, err)
            
        if (uid != self.bot.dev_id and self.bot.dev_id):
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
        if (not self.bot.bot_utils.get_permissions(message.channel).add_reactions):
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
                    if (custom_emoji.name in emojis and custom_emoji.server == message.server):
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
                if (name == "stop_button" and not self.bot.bot_utils.get_permissions(message.channel).manage_messages): # skip delete if we can't delete messages
                    continue
                
                await self.bot.add_reaction(message, emoji)
        
        except discord.errors.NotFound:
            pass
        except Exception as e:
            await self.error_alert(e)