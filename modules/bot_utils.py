import discord

from modules import utils

import asyncio

"""
this file is for utility functions that require access to discord
"""

class BotUtils:
    def __init__(self, bot):
        self.bot = bot
    
    # add real filepath to relative filepath when writing a file
    # input: filename; string; filename to write to
    #        mode; string; what mode to open the file in, r, w, or a
    #        string; string; what should be written
    #        add_time; bool; if should the current time be prepended
    def write_to_file(self, filename, mode, string, add_time=False):
        if (add_time):
            string = "[{}] {}".format(utils.get_cur_time(), string)
        
        with open(self.bot.REAL_PATH + "/" + filename, mode) as f:            
            f.write(string + "\n")
        
    # logs an error to file
    # input: error; string; the error to write
    def log_error_to_file(self, error, prefix=""):
        if (prefix):
            error = "[{}] {}".format(prefix, error)

        self.write_to_file("cbot_errors.txt", "a", error, add_time=True)
        
    # prints message
    # input: message; discord.Message; message to print
    async def output_log(self, message):
        try:
            print(utils.format_log_message(message))
        
        except Exception as e:
            await self.bot.messaging.error_alert(e, extra="on_command")
    
    # find a user by full or partial name or id
    # input: name; string; keyword to search usernames for
    # output: discord.User or None; found user or None if no users were found  
    async def find(self, name):
        if (not name):
            return
        
        return discord.utils.find(lambda m: (m.name.lower().startswith(name.lower()) or m.id == name), self.bot.get_all_members())
    
    # get channel by name
    # input: name; string; keyword to search channel names for
    #        server; discord.Server; server to search for the channel
    # output: discord.Channel or None; channel object matching search or None if no channels were found
    def find_channel(self, name, server):
        if (not server):
            return None
        
        server = str(server)
        return discord.utils.get(self.bot.get_all_channels(), server__name=server, name=name)
    
    # find last embed in channel
    # input: channel; discord.Channel; channel to search for embeds
    #        embed_type; string; type of embed to search for, video or image
    # output: string or None; url of the embed or None if not found
    async def find_last_embed(self, channel, embed_type):
        async for message in self.bot.logs_from(channel):
            embed = utils.find_image_embed(message)
    
            if (embed):
                return embed
            
        return None
    
    # finds last image in channel
    # input: message; discord.Message; message from which channel will be extracted and point to search before
    # output: string or None; url of image found or None if no images were found
    async def find_last_image(self, message):
        channel = message.channel
        
        async for message in self.bot.logs_from(channel, before=message):
            attachments = utils.find_attachment(message)
            
            if (attachments):
                return attachments
            
            embed = utils.find_image_embed(message)
            
            if (embed):
                return embed
            
        return None
    
    # finds last text message in channel
    # input: message; discord.Message; message from which channel will be used as point to search before
    # output: string or None; text of message or None if no text messages were found
    async def find_last_text(self, message):
        async for message in self.bot.logs_from(message.channel, before=message):
            if (message.content):
                return message.content
            
    # finds last youtube video embed in channel
    # input: message; discord.Message; message from which channel will be used as point to search before
    # output: string or None; url of youtube embed or None if no youtube video embeds were found
    async def find_last_youtube_embed(self, message):
        async for message in self.bot.logs_from(message.channel, before=message, limit=50):
            if (message.embeds):            
                for embed in message.embeds:
                    keys = embed.keys()
                    
                    if ("video" in keys or ("type" in keys and embed["type"] == "video")):  
                        if ("provider" in keys and "name" in embed["provider"].keys() and embed["provider"]["name"] == "YouTube"):
                            if ("url" in keys and utils.youtube_url_validation(embed["url"])):
                                return embed["url"]
            
    # get bot's permissions in a channel
    # input: channel; discord.Channel; channel to get permissions from
    # output: discord.Permissions; permissions in the channel
    def get_permissions(self, channel, user=None):
        if (channel.is_private):
            return discord.Permissions.all_channel()
        
        if (user == self.bot.user or not user):
            user = channel.server.me # needs member version of bot
        
        return user.permissions_in(channel)
    
    # deletes a message if the bot has permission to do so
    # input: message; discord.Message; message to delete
    async def delete_message(self, message):
        channel = message.channel
                
        if (channel.is_private and message.author != self.bot.user):
            return False
        elif (self.get_permissions(channel, self.bot.user).manage_messages):
            try:
                await self.bot.delete_message(message)
                return True
            
            except Exception:
                return False
        
        return False
            
    # deletes a number messages from a channel by user
    # input: ctx; discord.Context; context to reference
    #        num_to_delete; int; number of messages to delete
    #        users; list or None; list of users to delete messages from or None to delete regardless of author
    # output: int; number of messages successfully deleted
    async def purge(self, ctx, num_to_delete, users):
        num_to_delete = abs(num_to_delete)
        num_deleted = 0
    
        async for message in self.bot.logs_from(ctx.message.channel, before=ctx.message, limit=500):
            if (num_deleted >= num_to_delete):
                break
            
            if (not users or message.author in users):
                success = await self.delete_message(message)
                
                if (success):
                    num_deleted += 1
            
        return num_deleted
    
    # find a server from the ones we are currently in
    # input: search; str; string to search for, either part/all of server name or index in list of servers
    # output: discord.Server or None; the server if found or None
    def find_server(self, search):
        servers = list(self.bot.servers)
        server = None
        
        try:
            index = int(search)
            
        except ValueError: # if it's not an index, search by name
            server = discord.utils.find(lambda s: search.lower() in s.name.lower(), servers)
        
        else:
            index -= 1
            
            if (index >= 0 and index < len(servers)):
                server = servers[index]
            else: # search in the server name
                server = discord.utils.find(lambda s: search.lower() in s.name.lower(), servers)

        return server