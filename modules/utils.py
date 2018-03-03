import discord

import asyncio
import os, datetime, time, re

class Utils:
    def __init__(self, bot):
        self.bot = bot
       
    # return some info about a user as a formatted string
    # input: user; discord.User; user to lookup
    def get_user_info(self, user):
        info_msg = """
Name: {name}
Discriminator: {disc}
ID: {id}
User created at: {date}
Avatar URL: {avatar}
""".format(name=user.name, disc=user.discriminator, id=user.id, date=str(user.created_at),
                  avatar=(user.avatar_url if user.avatar_url is not None else ""))
        
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
        content = message.clean_content
        server_name = ("[{}]".format(message.server.name)) if message.server else ""
        
        return "{time}{space}{server} [{channel}] {name}: {message}".format(time=self.get_cur_time(),
                                                                        space=(" " if server_name else ""),
                                                                        server=server_name,
                                                                        channel=message.channel,
                                                                        name=message.author,
                                                                        message=content)
    
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
    
    # find last attachment in message
    # input: message; discord.Message; message to search for attachments
    # output: string or None; url of the attachment or None if not found
    def find_attachment(self, message):
        if (message.attachments):
            for attach in message.attachments:
                if (attach):
                    return attach["url"]
                    
        return None
    
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
                            if ("url" in keys and self.youtube_url_validation(embed["url"])):
                                return embed["url"]
    
    # format member name as user#discriminator
    # input: user; discord.User; the user to format
    # output: string; formatted string in the form username#discriminator (ex. CBot#8071)
    def format_member_name(self, user):
        return "{}#{}".format(user.name, user.discriminator)
                
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

    # TODO: discord changes this to type 'rich' and drops the 'video' data entirely after being sent
    # creates a discord.Embed with an embedded YouTube video
    # input: info; dict; youtube-dl dict of extracted info from the video
    # output: embed; discord.Embed; generated video embed
    def create_youtube_embed(self, info):
        if ("entries" in info.keys()):
            info = info["entries"][0]
        
        data = {
                "url": info["webpage_url"],
                "title": info["title"],
                "type": "video",
                "thumbnail": {
                    "url": info["thumbnail"],
                    "height": 360,
                    "width": 480
                    },
                "author": {
                    "name": info["uploader"],
                    "url": info["uploader_url"]
                    },
                "provider": {
                    "url": "https://www.youtube.com/",
                    "name": "YouTube"
                    },
                "video": {
                    "url": info["webpage_url"].replace("watch?v=", "embed/"),
                    "height": 720,
                    "width": 1280
                    },
                "description": info["description"][:140] + ("..." if len(info["description"]) > 140 else "")
               }
        
        embed = discord.Embed().from_data(data)
        
        embed.colour = discord.Colour.dark_blue()
        
        embed.add_field(name=":movie_camera:", value="{:,} views".format(info["view_count"]))
        embed.add_field(name=":watch:", value=time.strftime("%H:%M:%S", time.gmtime(info["duration"])))
        embed.add_field(name=":thumbsup:", value="{:,} likes".format(info["like_count"], inline=True))
        embed.add_field(name=":thumbsdown:", value="{:,} dislikes".format(info["dislike_count"], inline=True))
        embed.add_field(name=":calendar_spiral:", value=datetime.datetime.strptime(info["upload_date"], "%Y%m%d").strftime("%b %-d, %Y"))

        return embed
    
    # check if a url matches a youtube url format
    # thanks to stack overflow (https://stackoverflow.com/a/19161373)
    def youtube_url_validation(self, url):
        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube|youtu|youtube-nocookie)\.(com|be)/'
            '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
        youtube_regex_match = re.match(youtube_regex, url)
        if youtube_regex_match:
            return youtube_regex_match.group(6)
    
        return youtube_regex_match
            
    # 'safely' remove a file
    # TODO: not that safe, sanity check path / dir just to be safe... we don't want people ever abusing this
    #       os.remove only raises OSError?
    # input: filename; string; filename to remove
    def remove_file_safe(self, filename):
        if (os.path.exists(filename)):
            os.remove(filename)
            
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
        num_deleted = 0
    
        async for message in self.bot.logs_from(ctx.message.channel, before=ctx.message, limit=500):
            if (num_deleted >= num_to_delete):
                break
            
            if (not users or message.author in users):
                success = await self.bot.utils.delete_message(message)
                
                if (success):
                    num_deleted += 1
            
        return num_deleted