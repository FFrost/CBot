import discord

import os
import datetime
import time
import re
import asyncio
import aiohttp
from youtube_dl import utils as ytutils
from typing import Optional, Union

"""
this file is for utility functions that do NOT require access to discord,
e.g. general utility functions
"""

# format current time
def get_cur_time() -> str:
    return "{:%m/%d/%y %H:%M:%S}".format(datetime.datetime.now())

# format current date
def get_date() -> str:
    return "{:%m-%d-%y}".format(datetime.datetime.now())

def format_time(datetime_obj: datetime.datetime) -> str:
    return datetime_obj.strftime("%H:%M on %-m/%-d/%Y")

# format message to log
# input: message, message to format to be output
# output: formatted string of message content
def format_log_message(message: discord.Message) -> str:
    content = message.clean_content
    server_name = ("[{}]".format(message.server.name)) if message.server else ""
    
    return "{time}{space}{server} [{channel}] {name}: {message}".format(time=get_cur_time(),
                                                                    space=(" " if server_name else ""),
                                                                    server=server_name,
                                                                    channel=message.channel,
                                                                    name=message.author,
                                                                    message=content)
    
# find last attachment in message
# input: message, message to search for attachments
# output: url of the attachment or None if not found
def find_attachment(message: discord.Message) -> Optional[str]:
    if (message.attachments):
        for attach in message.attachments:
            if (attach):
                return attach["url"]
                
    return None

# find last embed in message
# input: message, message to search for image embeds
# output: url of the embed or None if not found
def find_image_embed(message: discord.Message) -> Optional[str]:
    if (message.embeds):            
        for embed in message.embeds:
            if (embed):
                if ("type" in embed and embed["type"] == "image"):
                    return embed["url"]
                elif ("image" in embed):
                    return embed["image"]["url"]
                    
    return None

# format member name as user#discriminator
# input: user, the user to format
# output: formatted string in the form username#discriminator (ex. CBot#8071)
def format_member_name(user: discord.User) -> str:
    return "{}#{}".format(user.name, user.discriminator)
            
# creates an embed featuring an image
# input: user, the author of the embed
#        title, the title of the embed
#        footer, the footer of the embed
#        image, url of the image to embed
#        color, the color of the embed
# output: the generated embed
def create_image_embed(user: discord.Member,
                       title: str = "",
                       description: str = "",
                       footer: str ="",
                       image: str ="",
                       thumbnail: str ="",
                       color: discord.Color = discord.Color.blue()
                       ) -> discord.Embed:
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

# creates an embed with info about a youtube video
# input: info, youtube-dl dict of extracted info from the video
#        user, the user who requested the video
# output: the generated embed
def create_youtube_embed(info: dict, user: discord.User = None) -> discord.Embed:
    if ("entries" in info.keys()):
        info = info["entries"][0]
    
    data = {
            "url": info["webpage_url"],
            "title": info["title"],
            "type": "rich",
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
                "url": info["webpage_url"],
                "height": 720,
                "width": 1280
                },
            "description": cap_string_and_ellipsis(info["description"])
           }
    
    embed = discord.Embed().from_data(data)
    
    embed.colour = discord.Colour.red()
    
    if (user):
        embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.add_field(name=":thumbsup:", value="{:,} likes".format(info["like_count"]))
    embed.add_field(name=":thumbsdown:", value="{:,} dislikes".format(info["dislike_count"]))
    embed.add_field(name=":movie_camera:", value="{:,} views".format(info["view_count"]))
    embed.add_field(name=":watch:", value=time.strftime("%H:%M:%S", time.gmtime(info["duration"])))
    embed.add_field(name=":desktop:", value=info["uploader"])
    embed.add_field(name=":calendar_spiral:", value=datetime.datetime.strptime(info["upload_date"], "%Y%m%d").strftime("%b %-d, %Y"))

    return embed

# creates an embed from a youtube-dl extractor dict containing info about a soundcloud song
# input: info, youtube-dl dict of extracted info from the song
#        user, the user who requested the song
# output: formatted song info embed
def create_soundcloud_embed(info: dict, user: discord.User = None) -> discord.Embed:
    if ("entries" in info.keys()):
        info = info["entries"][0]

    data = {
            "url": info["webpage_url"],
            "title": info["title"],
            "thumbnail": {
                "url": info["thumbnail"]
                },
            "description": cap_string_and_ellipsis(info["description"])
           }
    
    embed = discord.Embed().from_data(data)
    
    if (user):
        embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.add_field(name=":desktop:", value=info["uploader"])
    embed.add_field(name=":watch:", value=time.strftime("%H:%M:%S", time.gmtime(info["duration"])))
    embed.add_field(name=":calendar_spiral:", value=datetime.datetime.strptime(info["upload_date"], "%Y%m%d").strftime("%b %-d, %Y"))
    
    return embed

# creates an embed with information about a game
# input: info, custom dict created from Utility.game that contains info from a google search
#        user, user who requested the search
# output: the generated embed
def create_game_info_embed(info: dict, user: discord.User = None) -> discord.Embed:
    embed = discord.Embed()
    
    embed.title = info["title"]
    embed.description = info["body"]
    embed.url = info["wiki"]
    
    if (user):
        embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.color = discord.Colour.green()
    
    embed.set_thumbnail(url=info["image"])
    
    for entry in info["content"]:
        index = entry.find(":")
        header = entry[:index].strip()
        value = entry[index + 1:].strip()
        
        embed.add_field(name=header, value=value)
    
    return embed

# check if a url matches a youtube url format
# thanks to stack overflow (https://stackoverflow.com/a/19161373)
def youtube_url_validation(url: str) -> Union[str, re.match, None]:
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, url)
    if youtube_regex_match:
        return youtube_regex_match.group(6)

    return youtube_regex_match
        
# 'safely' remove a file
# TODO: not that safe, sanity check path / dir just to be safe... we don't want people ever abusing this
#       os.remove only raises OSError?
# input: filename, filename to remove
def remove_file_safe(filename: str) -> None:
    if (os.path.exists(filename)):
        os.remove(filename)
        
# format youtube_dl error to inform user of what occured
# input: e, the error
# output: formatted error removing "YouTube said: " or original error
def extract_yt_error(e: ytutils.YoutubeDLError) -> str:
    if (isinstance(e, ytutils.UnsupportedError)):
        return "Unsupported URL"
    elif (isinstance(e, ytutils.RegexNotFoundError)):
        return "Regex not found"
    elif (isinstance(e, ytutils.GeoRestrictedError)):
        return "Geographic restriction, video is not available"
    elif (isinstance(e, ytutils.ExtractorError)):
        return "Info extractor error"
    elif (isinstance(e, ytutils.DownloadError)):
        return "Error downloading the video"
    elif (isinstance(e, ytutils.SameFileError)):
        return "Can't download the multiple files to the same file"
    elif (isinstance(e, ytutils.PostProcessingError)):
        return "Post processing exception"
    elif (isinstance(e, ytutils.MaxDownloadsReached)):
        return "Max download limit has been reached"
    elif (isinstance(e, ytutils.UnavailableVideoError)):
        return "Video is unavailable in the requested format"
    elif (isinstance(e, ytutils.ContentTooShortError)):
        return "File is too small compared to what the server said, connection was probably interrupted"
    elif (isinstance(e, ytutils.XAttrMetadataError)):
        return "XAttrMetadata error"
    elif (isinstance(e, ytutils.XAttrUnavailableError)):
        return "XAttrUnavailable error"

    return "General YoutubeDL error"

# limits the length of a string and appends "..." if the string is longer than the length
# if the string is
# input: s, the string
#        length, the length to cap the string at
#        num_lines, the number of lines to use if the string is more than 1 line
# output: capped string
# sample input: "hello i am an example string", 20
# sample output: "hello i am an exampl..."
def cap_string_and_ellipsis(s: str, length: int = 140, num_lines: int = 3) -> str:
    return "\n".join(s[:length].split("\n")[:num_lines]).strip() + ("..." if len(s) > length else "")

def list_of_pairs_to_dict(obj: list) -> dict:
    ret = {}

    for pair in obj:
        data = dict(pair)
        ret[data["key"]] = data["value"]

    return ret

# thanks to https://stackoverflow.com/a/27317596
def safe_div(x, y):
    if y == 0:
        return 0
    
    return x / y