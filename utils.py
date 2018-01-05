import discord
from discord.ext import commands

import logging, os, datetime, codecs, re, time, inspect, ipaddress, json, tempfile, traceback
import asyncio, aiohttp
import wand, wand.color, wand.drawing
import youtube_dl
from random import randint, uniform
from lxml import html
from urllib.parse import quote
from collections import OrderedDict
from http.client import responses

class Utils():
    def __init__(self, bot):
        self.bot = bot
       
    # return some info about a user as a formatted string
    # input:    user;  discord.User;  user to lookup
    def get_user_info(self, user):
        info_msg = """
Name: {name}
Discriminator: {disc}
ID: {id}
User created at: {date}
Avatar URL: {avatar}
""".format(name=user.name, disc=user.discriminator, id=user.id, date=str(user.created_at),
                  avatar="%s" % (user.avatar_url if user.avatar_url is not None else ""))
        
        return info_msg
    
    # format current time
    def get_cur_time(self):
        return "{:%m/%d/%y %H:%M:%S}".format(datetime.datetime.now())
    
    # format current date
    def get_date(self):
        return "{:%m-%d-%y}".format(datetime.datetime.now())
    
    # add real filepath to relative filepath when writing a file
    # input: filename; string; filename to write to
    #        mode; string; what mode to open the file in, r, w, or a
    #        string; string; what should be written
    #        add_time; bool; if should the current time be prepended
    def write_to_file(self, filename, mode, string, add_time=False):
        if (add_time):
            string = "[{}] {}".format(self.get_cur_time(), string)
        
        with open(self.bot.REAL_PATH + "/" + filename, mode) as f:            
            f.write(string + "\n")
    
    # logs an error to file
    # input: error; string; the error to write
    def log_error_to_file(self, error):
        self.write_to_file("cbot_errors.txt", "a", error, add_time=True)
    
    # format message to log
    # input: message; discord.Message; message to format to be output
    # output: string; formatted string of message content
    def format_log_message(self, message):
        content = message.content.replace(self.bot.user.id, "{name}#{disc}".format(name=self.bot.user.name, disc=self.bot.user.discriminator))
        server_name = message.server.name if message.server else "Private Message"
        
        return "{time} [{server}] [{channel}] {name}: {message}".format(time=self.get_cur_time(),
                                                                        server=server_name,
                                                                        channel=message.channel,
                                                                        name=message.author,
                                                                        message=content)
    
    # find a user by full or partial name or id
    # input: name; string; keyword to search usernames for
    # output: discord.User or None; found user or None if no users were found  
    async def find(self, name):
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
    
    # find last attachment in message
    # input: message; discord.Message; message to search for attachments
    # output: string or None; url of the attachment or None if not found
    def find_attachment(self, message):
        if (message.attachments):
            for attach in message.attachments:
                if (attach):
                    return attach["url"]
                    
        return None
    
    # TODO: create enum for embed type? message.embeds returns a dict so maybe not
    # find last embed in message
    # input: message; discord.Message; message to search for image embeds
    # output: string or None; url of the embed or None if not found
    def find_image_embed(self, message): # video, image
        if (message.embeds):            
            for embed in message.embeds:
                if (embed):
                    if ("type" in embed and embed["type"] == "image"):
                        return embed["url"]
                    elif ("image" in embed):
                        return embed["image"]["url"]
                        
        return None
    
    # find last embed in channel
    # input: channel; discord.Channel; channel to search for embeds
    #        embed_type; string; type of embed to search for, video or image
    # output: string or None; url of the embed or None if not found
    async def find_last_embed(self, channel, embed_type):
        async for message in self.bot.logs_from(channel):
            embed = self.find_image_embed(message)
    
            if (embed):
                return embed
            
        return None
    
    # finds last image in channel
    # input: message; discord.Message; message from which channel will be extracted and point to search before
    # output: string or None; url of image found or None if no images were found
    async def find_last_image(self, message):
        channel = message.channel
        
        async for message in self.bot.logs_from(channel, before=message):
            attachments = self.find_attachment(message)
            
            if (attachments):
                return attachments
            
            embed = self.find_image_embed(message)
            
            if (embed):
                return embed
            
        return None
    
    # format member name as user#discriminator
    # input: user; discord.User; the user to format
    # output: string; formatted string in the form username#discriminator (ex. CBot#8071)
    def format_member_name(self, user):
        return "%s#%s" % (user.name, str(user.discriminator))
                
    # creates a discord.Embed featuring an image
    # input: user; discord.Member; the author of the embed
    #        title; string=""; the title of the embed
    #        footer; string=""; the footer of the embed
    #        image; string=""; url of the image to embed
    #        color; discord.Color; the color of the embed
    # output: embed; discord.Embed; the generated embed
    def create_image_embed(self, user, title="", description="", footer="", image="", thumbnail="", color=discord.Color.blue()):
        embed = discord.Embed()
        
        embed.title = title
        
        if (description):
            embed.description = description
        
        if (footer):
            embed.set_footer(text=footer)
        
        embed.set_author(name=user.name, icon_url=user.avatar_url)
        
        embed.color = color
        
        if (image):
            embed.set_image(url=image)
            
        if (thumbnail):
            embed.set_thumbnail(url=thumbnail)
        
        return embed
            
    # 'safely' remove a file
    # TODO: not that safe, sanity check path / dir just to be safe... we don't want people ever abusing this
    #       os.remove only raises OSError?
    # input: filename; string; filename to remove
    def remove_file_safe(self, filename):
        if (os.path.exists(filename)):
            os.remove(filename)
    
    # TODO: this is clearly not a utility function, need to find a better place to put this function
    # get insults from insult generator
    # output: string; the insult if found or "fucker"
    async def get_insult(self):
        try:
            conn = aiohttp.TCPConnector(verify_ssl=False) # for https
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get("https://www.insult-generator.org/") as r:
                    if (r.status != 200):
                        return "fucker"
                    
                    tree = html.fromstring(await r.text())            
                    p = tree.xpath("//div[@class='insult-text']/text()")
                    
                    if (isinstance(p, list)):
                        ret = p[0]
                    elif (isinstance(p, str)):
                        ret = p
                    else:
                        return "fucker"
                    
                    ret = ret.strip()
                        
                    if (not ret):
                        return "fucker"
                
                    return ret
        
        except Exception:
            return "fucker"