import discord
from discord.ext import commands

import inspect, re
from collections import OrderedDict

class Messaging:
    def __init__(self, bot):
        self.bot = bot
        
        # emojis for browsing image searches
        self.EMOJI_CHARS = OrderedDict()
        self.EMOJI_CHARS["arrow_backward"] = "◀"
        self.EMOJI_CHARS["arrow_forward"] = "▶"
        self.EMOJI_CHARS["stop_button"] = "⏹"
        
    # send a user a message and mention them in it
    # input: dest; discord.User, discord.Message, discord.ext.commands.Context, or string; destination to send message to (string should be id of user)
    #        msg; string; message to send
    # output: discord.Message; the reply message object sent to the user
    async def reply(self, dest, msg, channel=None):
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
            user = await self.bot.utils.find(dest)
            
            if (user):
                destination = user
            else:
                return None
        elif (isinstance(dest, commands.Context)):
            destination = dest.message.channel
            user = dest.message.author
        else:
            return None
            
        return await self.bot.send_message(destination, "{} {}".format(user.mention, msg))
    
    # private message the developer
    # input: msg; string; message to send
    async def message_developer(self, msg):
        if (not self.bot.dev_id):
            return
        
        user = await self.bot.utils.find(self.bot.dev_id)
            
        if (user is None):
            return
        
        await self.reply(user, msg)
    
    # private message a user
    # input: uid; string; id of user to message
    #        msg; string; message content to send
    async def private_message(self, uid, msg):
        user = await self.bot.utils.find(uid)
            
        if (user is None):
            return
        
        await self.reply(user, msg)
    
    # send message to the "admin" channel if it exists
    # input: msg; string; content of message to send
    #        server; discord.Server; server to send message in
    async def msg_admin_channel(self, msg, server):
        try:
            if (not server):
                return
            
            channel = self.bot.utils.find_channel("admin", server)
            
            if (not channel):
                return
            
            if (not channel.permissions_for(server.me)):
                return
    
            await self.bot.send_message(channel, msg)
        
        except Exception as e:
            await self.bot.utils.error_alert(e)
            
    # alerts a user if an error occurs, will always alert developer
    # input: e; error object; the error to output
    #        uid; string=""; the user's unique id
    #        extra; string=""; any extra information to include
    async def error_alert(self, e, uid="", extra=""):
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
    # input: message; discord.Message; message to react to
    #        keyword; string or list; keyword(s) to look for in message content, author name or id
    #        emoji; string or list; emoji(s) to react with
    #        partial; bool=True; should react if partial keywords are found
    async def react(self, message, keyword, emojis, partial=True):
        if (not self.bot.utils.get_permissions(message.channel).add_reactions):
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
                for custom_emoji in self.get_all_emojis():
                    if (custom_emoji.name in emojis and custom_emoji.server == message.server):
                        await self.add_reaction(message, custom_emoji)
                
                for e in emojis:                
                    # react with normal emojis and ignore custom ones
                    # TODO: do we really need this try/except?
                    try:
                        await self.bot.add_reaction(message, e)
                    except Exception:
                        pass
        
        except Exception as e:
            if ("Reaction blocked" in str(e)):
                return
            
            await self.error_alert(e)
            
    # adds reactions for browsing an image to a message
    # input: message; discord.Message; message to add reactions to
    async def add_img_reactions(self, message):
        try:
            for name, emoji in self.EMOJI_CHARS.items():
                if (name == "stop_button" and not self.bot.utils.get_permissions(message.channel).manage_messages): # skip delete if we can't delete messages
                    continue
                
                await self.bot.add_reaction(message, emoji)
        
        except discord.errors.NotFound:
            pass
        except Exception as e:
            await self.error_alert(e)