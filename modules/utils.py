import discord

from . import steam

import os, datetime, time, re
import asyncio, aiohttp

"""
this file is for utility functions that do NOT require access to discord,
e.g. general utility functions
"""

# return some info about a user as a formatted string
# input: user; discord.User; user to lookup
def get_user_info(user):
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
def get_cur_time():
    return "{:%m/%d/%y %H:%M:%S}".format(datetime.datetime.now())

# format current date
def get_date():
    return "{:%m-%d-%y}".format(datetime.datetime.now())

# format message to log
# input: message; discord.Message; message to format to be output
# output: string; formatted string of message content
def format_log_message(message):
    content = message.clean_content
    server_name = ("[{}]".format(message.server.name)) if message.server else ""
    
    return "{time}{space}{server} [{channel}] {name}: {message}".format(time=get_cur_time(),
                                                                    space=(" " if server_name else ""),
                                                                    server=server_name,
                                                                    channel=message.channel,
                                                                    name=message.author,
                                                                    message=content)
    
# find last attachment in message
# input: message; discord.Message; message to search for attachments
# output: string or None; url of the attachment or None if not found
def find_attachment(message):
    if (message.attachments):
        for attach in message.attachments:
            if (attach):
                return attach["url"]
                
    return None

# find last embed in message
# input: message; discord.Message; message to search for image embeds
# output: string or None; url of the embed or None if not found
def find_image_embed(message): # video, image
    if (message.embeds):            
        for embed in message.embeds:
            if (embed):
                if ("type" in embed and embed["type"] == "image"):
                    return embed["url"]
                elif ("image" in embed):
                    return embed["image"]["url"]
                    
    return None

# format member name as user#discriminator
# input: user; discord.User; the user to format
# output: string; formatted string in the form username#discriminator (ex. CBot#8071)
def format_member_name(user):
    return "{}#{}".format(user.name, user.discriminator)
            
# creates a discord.Embed featuring an image
# input: user; discord.Member; the author of the embed
#        title; string=""; the title of the embed
#        footer; string=""; the footer of the embed
#        image; string=""; url of the image to embed
#        color; discord.Color; the color of the embed
# output: embed; discord.Embed; the generated embed
def create_image_embed(user, title="", description="", footer="", image="", thumbnail="", color=discord.Color.blue()):
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

# creates a discord.Embed with an embedded YouTube video
# input: info; dict; youtube-dl dict of extracted info from the video
#        user; discord.User; the user who requested the video
# output: embed; discord.Embed; generated video embed
def create_youtube_embed(info, user=None):
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

# creates a discord embed from a youtube-dl extractor dict
# input: info; dict; youtube-dl dict of extracted info from the song
#        user; discord.User; the user who requested the song
# output: embed; discord.Embed; formatted song info embed
def create_soundcloud_embed(info, user=None):
    if ("entries" in info.keys()):
        info = info["entries"][0]

    data = {
            "url": info["webpage_url"],
            "title": info["title"],
            "thumbnail": {
                "url": info["thumbnail"]
                },
            #"description": "\n".join(info["description"][:140].split("\n")[:3]).strip() + ("..." if len(info["description"]) > 140 else "")
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
# input: info; dict; custom dict created from Utility.game that contains info from a google search
#        user; discord.User; user who requested the search
# output: discord.Embed; the formatted embed
def create_game_info_embed(info, user=None):
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
def youtube_url_validation(url):
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
def remove_file_safe(filename):
    if (os.path.exists(filename)):
        os.remove(filename)
        
# format youtube_dl error to inform user of what occured
# input: e; str; the error
# output: str; formatted error removing "YouTube said: " or original error
def extract_yt_error(e):
    e = str(e)    
    err_to_look_for = "YouTube said:"
    
    index = e.find(err_to_look_for)
    
    if (index < 0):
        return e
    
    index += len(err_to_look_for) + 1 # space
    
    ret = e[index:]
    
    return ret

# limits the length of a string and appends "..." if the string is longer than the length
# if the string is
# input: s; str; the string
#        length; int; the length to cap the string at
#        num_lines; int; the number of lines to use if the string is more than 1 line
# output: str; capped string
# sample input: "hello i am an example string", 20
# sample output: "hello i am an exampl..."
def cap_string_and_ellipsis(s, length=140, num_lines=3):
    return "\n".join(s[:length].split("\n")[:num_lines]).strip() + ("..." if len(s) > length else "")

def list_of_pairs_to_dict(obj):
    ret = {}

    for pair in obj:
        data = dict(pair)
        ret[data["key"]] = data["value"]

    return ret

def create_fortnite_stats_embed(user, stats_data, stats, title=""):
    embed = discord.Embed()
    
    embed.title = title
    
    embed.set_footer(text=(stats[0].upper() + stats[1:]) + " stats | Powered by fortnitetracker.com")
    
    embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.color = discord.Color.dark_green()

    if (stats == "lifetime"):
        data = list_of_pairs_to_dict(stats_data["lifeTimeStats"])

        embed.add_field(name=":trophy: Wins", value="{:,}".format(int(data["Wins"])))
        embed.add_field(name=":medal: Win %", value=data["Win%"])
        embed.add_field(name=":gun: Kills", value="{:,}".format(int(data["Kills"])))
        embed.add_field(name=":skull_crossbones: K/D", value=data["K/d"])
        embed.add_field(name=":video_game: Matches Played", value=data["Matches Played"])
        
        try:
            rank = stats_data["stats"]["p9"]["trnRating"]["rank"]

        except Exception:
            pass

        else:
            embed.add_field(name="Ranking", value="{:,}".format(int(rank)))
    else:
        stats_options = {"solo": "p2",
                         "duo": "p10",
                         "squad": "p9"
                         }

        data = stats_data["stats"][stats_options[stats]]

        embed.add_field(name=":trophy: Wins", value="{:,}".format(int(data["top1"]["value"])))
        embed.add_field(name=":medal: Win %", value=(data["winRatio"]["value"] + "%"))
        embed.add_field(name=":gun: Kills", value="{:,}".format(int(data["kills"]["value"])))
        embed.add_field(name=":skull_crossbones: K/D", value=data["kd"]["value"])
        embed.add_field(name=":video_game: Matches Played", value="{:,}".format(int(data["matches"]["value"])))

        if (stats == "solo"):
            embed.add_field(name=":third_place: Top 10", value="{:,}".format(int(data["top10"]["value"])))
        elif (stats == "duo"):
            embed.add_field(name=":third_place: Top 5", value="{:,}".format(int(data["top5"]["value"])))
        elif (stats == "squad"):
            embed.add_field(name=":third_place: Top 3", value="{:,}".format(int(data["top3"]["value"])))
    
    return embed

steam_url_regex = re.compile(r"((https?:\/\/)(www.)?)?(steamcommunity.com\/(?P<type>id|profiles)\/(?P<id>[A-Za-z0-9]{2,32}))")
def is_steam_url(string):
    return (steam_url_regex.match(string) is not None)

async def create_steam_embed(user, url):
    search = steam_url_regex.search(url)
    url_id = search.group("id")
    url_type = search.group("type")

    if (not url_id):
        return None

    if (url_type == "profiles"):
        try:
            int(url_id) # steamid64 will be a number

        except Exception:
            return None

        else:
            id64 = url_id
    else:
        # resolve vanity url
        id64 = await steam.resolve_vanity_url(url_id)

    # profile doesn't exist
    if (not id64):
        return None

    # get 32-bit steamid
    id32 = steam.steamid64_to_32(id64)

    # get profile summary
    profile_summary = await steam.get_profile_summary(id64) # profile name gives us "avatarfull" (url to avatar) and "personaname" (username)

    # get profile username
    if ("personaname" in profile_summary):
        username = profile_summary["personaname"]
    else:
        username = "unknown"

    # load profile page
    profile_page = await steam.get_profile_page(id64)

    # get profile description
    description = await steam.get_profile_description(id64, page=profile_page) # gives us description

    # get number of friends
    num_friends = await steam.get_friends(id64, page=profile_page)

    # get number of games
    games = await steam.get_games(id64)

    game_name = None
    most_played_game_time = 0
    num_games = None

    if (games):
        # number of games owned
        if ("game_count" in games):
            num_games = games["game_count"]

        # find most played  game
        try:
            for game in games["games"]:
                if (int(game["playtime_forever"]) > most_played_game_time):
                    most_played_game = game["appid"]
                    most_played_game_time = int(game["playtime_forever"])

            most_played_game_time = round(most_played_game_time / 60) # minutes to hours

            if (most_played_game == 730): # csgo shows as ValveTestApp260 for some reason
                game_name = "Counter-Strike: Global Offensive"
            else:
                game_name = await steam.get_game_name(most_played_game)
        
        except Exception:
            game_name = None
            most_played_game_time = 0

    # find number of bans
    num_bans = await steam.get_num_bans(id64)

    if (not num_bans):
        num_bans = 0
    else:
        num_bans = int(num_bans)

    # get account age
    account_age = await steam.get_account_age(id64)

    # create the embed
    embed = discord.Embed()

    embed.title = username
        
    embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.color = discord.Color.blue()

    if (description):
        embed.description = cap_string_and_ellipsis(description, 240)

    if ("avatarfull" in profile_summary):
        embed.set_image(url=profile_summary["avatarfull"])

    embed.add_field(name="SteamID64", value=id64)
    embed.add_field(name="SteamID32", value=id32)

    if (num_friends):
        embed.add_field(name="Friends", value=num_friends)

    if (num_games):
        embed.add_field(name="Games Owned", value="{:,}".format(int(num_games)))

    if (game_name):
        embed.add_field(name="Most Played Game", value=game_name)
        embed.add_field(name="Hours", value="{:,}".format(most_played_game_time))
    
    if (account_age):
        plural = "year" + ("" if account_age == 1 else "s")
        embed.add_field(name="Account Age", value="{:,} {}".format(account_age, plural))

    if (num_bans > 0):
        embed.add_field(name="Bans", value="{:,}".format(num_bans))

    return embed