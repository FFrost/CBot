"""
TODO:
    - reimplement voice player (with simultaneous cross-server play)
    - split things into different files (learn how to use cogs) (maybe make module for utility functions, etc?)
    - add the ability for server owners to add reactions to messages with specified keywords
    - make a class for the bot and replace global vars w/ member vars
    - add options for developer notification/admin settings/etc
"""

import discord
from discord.ext import commands

import logging, os, datetime, codecs, re, time, inspect, ipaddress, json
import asyncio, aiohttp
import wand, wand.color, wand.drawing
import youtube_dl
from random import randint, uniform
from lxml import html
from urllib.parse import quote

# load opus library for voice
if (not discord.opus.is_loaded()):
    discord.opus.load_opus("opus")

# set up logging
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))

"""/////////////
//    init    //
/////////////"""

description = """CBot 2.0 [CURRENTLY UNDER DEVELOPMENT]
Got feedback? Found a bug? Report it to me: Frost#0261"""
bot = commands.Bot(command_prefix="!", description=description, pm_help=True)

"""////////////////
//    globals    //
////////////////"""

# id to send errors to
DEV_ID = ""

# max filesize for discord
DISCORD_MAX_FILESIZE = 10 * 1024 * 1024

"""//////////////
//    setup    //
//////////////"""

@bot.event
async def on_ready():
    print("Logged in as {name}#{disc} [{uid}]".format(name=bot.user.name, disc=bot.user.discriminator, uid=bot.user.id))
    
    await bot.change_presence(game=discord.Game(name="!help for info"))
    await bot_info()

# print info about where the bot is
async def bot_info():
    print("Connected to:")
    
    for s in bot.servers:
        if (s.unavailable): # can't retrieve info about server, shouldn't usually happen
            print("\t{id} - server is unavailable!".format(id=s.id))
        else:
            print("\t{name} owned by {owner}#{ownerid}".format(name=s.name, owner=s.owner.name, ownerid=s.owner.discriminator))
            
"""//////////////////
//    messaging    //
//////////////////"""

# send a user a message and mention them in it
# input: dest; discord.User, discord.Message, discord.ext.commands.Context, or string; destination to send message to (string should be id of user)
#        msg; string; message to send
# output: discord.Message; the reply message object sent to the user
async def reply(dest, msg):
    if (isinstance(dest, discord.User)):
        destination = user = dest
    elif (isinstance(dest, discord.Message)):
        destination = dest.channel
        user = dest.author
    elif (isinstance(dest, str)):
        user = await find(dest)
        
        if (user):
            destination = user
        else:
            return None
    elif (isinstance(dest, commands.Context)):
        destination = dest.message.channel
        user = dest.message.author
    else:
        return None
        
    return await bot.send_message(destination, "{} {}".format(user.mention, msg))

# private message a user
# input: uid; string; id of user to message
#        msg; string; message content to send
async def private_message(uid, msg):
    user = await find(uid)
        
    if (user is None):
        return
    
    #await bot.send_message(user, msg)
    await reply(user, msg)

# send message to the "admin" channel if it exists
# input: msg; string; content of message to send
#        server; discord.Server; server to send message in
async def msg_admin_channel(msg, server):
    try:
        if (not server):
            return
        
        channel = find_channel("admin", server)
        
        if (not channel):
            return
        
        if (not channel.permissions_for(server.me)):
            return

        await bot.send_message(channel, msg)
    
    except Exception as e:
        await error_alert(e)

# add reaction to message if any keyword is in message
# input: message; discord.Message; message to react to
#        keyword; string or list; keyword(s) to look for in message content, author name or id
#        emoji; string or list; emoji(s) to react with
#        partial; bool=True; should react if partial keywords are found
async def react(message, keyword, emoji, partial=True):
    try:
        if (not isinstance(keyword, list)):
            keyword = [keyword]
        
        if (not isinstance(emoji, list)):
            emoji = [emoji]
        
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
            for e in bot.get_all_emojis():
                if (any(em == e.name for em in emoji) and e.server == message.server):
                    await bot.add_reaction(message, e)
                else:
                    # react with normal emojis and ignore custom ones
                    # TODO: do we really need this try/except?
                    try:
                        await bot.add_reaction(message, e)
                    except Exception:
                        pass
    
    except Exception as e:
        if ("Reaction blocked" in str(e)):
            return
        
        await error_alert(e)
        
# return some info about a user as a formatted string
# input:    user;  discord.User;  user to lookup
def get_user_info(user):
    info_msg = """
Name: {name}
Discriminator: {disc}
ID: {id}
User created at: {date}
Avatar URL: {avatar}
""".format(name=user.name, disc=user.discriminator, id=user.id, date=str(user.created_at),
              avatar="%s" % (user.avatar_url if user.avatar_url is not None else ""))
    
    return info_msg
            
"""//////////////////////////
//    utility functions    //
//////////////////////////"""

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
    content = message.content.replace(bot.user.id, "{name}#{disc}".format(name=bot.user.name, disc=bot.user.discriminator))
    return "{time} [{channel}] {name}: {message}".format(time=get_cur_time(), channel=message.channel, name=message.author, message=content)

# find a user by full or partial name or id
# input: name; string; keyword to search usernames for
# output: discord.User or None; found user or None if no users were found  
async def find(name):
    return discord.utils.find(lambda m: (m.name.lower().startswith(name) or m.id == name), bot.get_all_members())

# get channel by name
# input: name; string; keyword to search channel names for
#        server; discord.Server; server to search for the channel
# output: discord.Channel or None; channel object matching search or None if no channels were found
def find_channel(name, server):
    if (not server):
        return None
    
    server = str(server)
    return discord.utils.get(bot.get_all_channels(), server__name=server, name=name)

# find last attachment in message
# input: message; discord.Message; message to search for attachments
# output: string or None; url of the attachment or None if not found
def find_attachment(message):
    if (message.attachments):
        for attach in message.attachments:
            if (attach):
                return attach["url"]
                
    return None

# TODO: create enum for embed type? message.embeds returns a dict so maybe not
# find last embed in message
# input: message; discord.Message; message to search for embeds
#        embed_type; string; type of embed to search for, video or image
# output: string or None; url of the embed or None if not found
def find_embed(message, embed_type): # video, image
    if (message.embeds):            
        for embed in message.embeds:                
            if (embed and embed["type"] == embed_type):
                return embed["url"]
                    
    return None

# find last embed in channel
# input: channel; discord.Channel; channel to search for embeds
#        embed_type; string; type of embed to search for, video or image
# output: string or None; url of the embed or None if not found
async def find_last_embed(channel, embed_type):
    async for message in bot.logs_from(channel):
        embed = find_embed(message, embed_type)

        if (embed):
            return embed
        
    return None

# finds last image in channel
# input: channel; discord.Channel; channel to search for images in
# output: string or None; url of image found or None if no images were found
async def find_last_image(channel):
    async for message in bot.logs_from(channel):
        attachments = find_attachment(message)
        
        if (attachments):
            return attachments
        
        embed = find_embed(message, "image")
                
        if (embed):
            return embed
        
    return None

# format member name as user#discriminator
# input: user; discord.User; the user to format
# output: string; formatted string in the form username#discriminator (ex. CBot#8071)
def format_member_name(user):
    return "%s#%s" % (user.name, str(user.discriminator))

# alerts a user if an error occurs, will always alert developer
# input: e; error object; the error to output
#        uid; string=""; the user's unique id
#        extra; string=""; any extra information to include
async def error_alert(e, uid="", extra=""):
    if (not uid):
        uid = DEV_ID
        
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
    await private_message(uid, err)
        
    if (uid != DEV_ID and DEV_ID):
            await private_message(DEV_ID, err)
            
"""///////////////
//    checks    //
///////////////"""

# checks if a user is the listed developer
# input: obj; discord.Member or discord.Message; the user to check or message to extract user from
# output: bool; if the member's ID matches the developer's
def is_dev(obj):
    global DEV_ID
    
    if (isinstance(obj, discord.Member)):
        if (obj.id == DEV_ID):
            return True
    elif (isinstance(obj, discord.Message)):
        if (obj.author.id == DEV_ID):
            return True
        
    return False

"""//////////////////
//    functions    //
//////////////////"""

# get insults from insult generator
# output: string; the insult if found or "fucker"
async def get_insult():
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

"""/////////////////
//    commands    //
/////////////////"""

# find images in message or attachments and pass to liquify function
@bot.command(description="liquidizes an image, can be url or attachment (if attachment, add !liquid as a comment)",
             brief="liquidizes an image, can be url or attachment",
             pass_context=True)
@commands.cooldown(2, 5, commands.BucketType.channel)
async def liquid(ctx, url : str=""):
    try:
        message = ctx.message
        
        urls = []
        
        if (url):
            urls.append(url)
        
        if (message.attachments):
            for attach in message.attachments:
                urls.append(attach["url"])
                
        if (not urls):
            urls.append(await find_last_image(message.channel))
            
            if (not urls):
                return
        
        if (len(urls) > 5):
            urls = urls[:5]
        
        msg = await reply(message, "Liquidizing image%s..." % ("s" if (len(urls) > 1) else ""))
        
        for url in urls:
            code = await do_magic(message.channel, url)
            
            if (not code):
                await reply(message, "Failed to liquidize image: `%s`" % url)
            elif (code == 2):
                await reply(message, "Failed to liquidize image (max filesize: 10mb): `%s`" % url)
            elif (code == 3):
                await reply(message, "Failed to liquidize image (invalid image): `%s`" % url)
            elif (code == 4):
                await reply(message, "Failed to liquidize image (max dimensions: 3000x3000): `%s`" % url)
            elif (code == 5):
                await reply(message, "Failed to liquidize image (could not download url): `%s`" % url)
        
        await bot.delete_message(msg)
        
    except Exception as e:
        await reply(message, "Failed to liquidize image%s." % ("s" if (len(urls) > 1) else ""))
        await error_alert(e)

# liquify image
# input: channel; discord.Channel; the channel to send the image in
#        url; string; the url of the image to download and liquify
# output: int; return code of the operation
async def do_magic(channel, url):
    global DISCORD_MAX_FILESIZE

    ret_codes = {"success": 1, "filesize": 2, "invalid": 3, "dimensions": 4, "bad_url": 5}
    
    try: 
        # check for private ip
        try:
            ip = ipaddress.ip_address(url)
            
            if (ip.is_private):
                return
            
        except Exception: # if it's not an ip (i.e. an actual url like a website)
            pass
        
        if (not url.startswith("http")):
            url = "http://" + url
        
        conn = aiohttp.TCPConnector(verify_ssl=False) # for https
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url) as r:
                if (r.status == 200):
                    if ("Content-Type" in r.headers):
                        content_type = r.headers["Content-Type"]
                    else:
                        return
                    
                    if ("Content-Length" in r.headers):
                        content_length = r.headers["Content-Length"]
                    else:
                        return
                    
                    # check if empty file
                    if (content_length):
                        content_length = int(content_length)
                        
                        if (content_length < 1):
                            return
                        elif (content_length > DISCORD_MAX_FILESIZE):
                            return ret_codes["filesize"]
                    else:
                        return
                    
                    # check for file type
                    if (not content_type):
                        return
                    
                    content_type = content_type.split("/")
                    
                    mime = content_type[0]
                    ext = content_type[1]
                    
                    if (mime.lower() != "image"):
                        return ret_codes["invalid"]
                    
                    filename = "liquid." + ext
                    
                    with (open(filename, "wb")) as f:
                        while True:
                            chunk = await r.content.read(1024)
                            
                            if (not chunk):
                                break
                            
                            f.write(chunk)
                else:
                    return ret_codes["bad_url"]
                        
        # do the magick
        img = wand.image.Image(filename=filename)
        
        if (img.animation): # no animated gifs
            # delete leftover files after
            if (os.path.exists(filename)):
                os.remove(filename)
                
            return ret_codes["invalid"]
        
        img.format = ext
        img.alpha_channel = True
        
        if (img.size >= (3000, 3000)):
            # delete leftover files after
            if (os.path.exists(filename)):
                os.remove(filename)
                
            return ret_codes["dimensions"]
        
        img.transform(resize="800x800>")
        img.liquid_rescale(width=int(img.width * 0.5), height=int(img.height * 0.5), delta_x=1)
        img.liquid_rescale(width=int(img.width * 1.5), height=int(img.height * 1.5), delta_x=2)
        
        magickd = "magickd.%s" % ext
        img.save(filename=magickd)
        
        # check file size
        size = os.stat(filename).st_size # filesize in bytes
        
        if (size > DISCORD_MAX_FILESIZE):
            return ret_codes["filesize"]
        
        # upload liquidized image
        await bot.send_file(channel, magickd)
        
        # just in case
        await asyncio.sleep(1)
        
        # delete leftover files after
        # downloaded image
        if (os.path.exists(filename)):
            os.remove(filename)
        
        # liquidized image
        if (os.path.exists(magickd)):
            os.remove(magickd)
            
        return ret_codes["success"] # good
    
    # TODO: do something with this maybe? convert image to a different format and try again?
    except wand.exceptions.WandException:
        return
    
    except Exception:
        return
    
@bot.command(description="random number generator, supports hexadecimal and floats", brief="random number generator, supports hex/floats", pass_context=True)
async def random(ctx, low : str, high : str):
    message = ctx.message
            
    base = 10
            
    hex_exp = "0[xX][0-9a-fA-F]+" # hex number regex (0x0 to 0xF)
    alpha_exp = "[a-zA-Z]" # alphabet regex (a to Z)
            
    is_float = (any("." in t for t in [low, high]))
            
    for n in [low, high]:
        if (re.search(alpha_exp, n)):
            if (re.search(hex_exp, n)):
                base = 16
            else:
                await reply(message, "format: !random low high")
                return
            
    try:
        if (base == 16):
            low = int(low, base)
            high = int(high, base)
        else:
            if (is_float):
                low = float(low)
                high = float(high)
            else:
                low = int(low, base)
                high = int(high, base)
                
    except Exception:
        await reply(message, "!random: low and high must be numbers")
        return
            
    if (low == high):
        await reply(message, "!random: numbers can't be equal")
        return
            
    if (low > high):
        temp_high = high
        high = low
        low = temp_high
            
    if (is_float):
        r = uniform(low, high)
    else:
        r = randint(low, high)
            
    result = ""
    
    if (base == 16):
        hex_result = hex(r).upper()
        hex_result = hex_result.replace("X", "x")
                
        result = hex_result
    else:    
        result = str(r)
            
    await reply(ctx, "rolled a %s" % result)

@bot.command(description="info of a Discord user", brief="info of a Discord user", pass_context=True)
async def info(ctx, *, name : str=""):
    if (name):
        user = await find(name)
                
        if (not user):
            await reply(ctx, "Failed to find user `%s`" % name)
            return
                
        info_msg = get_user_info(user)
    else:
        info_msg = get_user_info(ctx.message.author)

    await reply(ctx, info_msg)
    
@bot.command(description="make the bot say something (OWNER ONLY)", brief="make the bot say something (OWNER ONLY)", pass_context=True)
@commands.check(lambda ctx: is_dev(ctx.message))
async def say(ctx, *, msg : str):
    await bot.say(msg)
    
# TODO: get multiple images and allow browsing through results
@bot.command(description="first result from Google Images", brief="first image result from Google Images", pass_context=True)
async def img(ctx, *, query : str):
    query = quote(query)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    url = "https://www.google.com/search?q={}&tbm=isch&gs_l=img".format(query)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:              
            if (r.status != 200):
                await reply(ctx, "Query for `{}` failed (maybe try again)".format(query))
                return
            
            text = await r.text()
            
            if ("did not match any image results" in text):
                await reply(ctx, "No results found for `{}`".format(query))
                return

            tree = html.fromstring(text)
            
            path = tree.xpath("//div[@data-async-rclass='search']/div[@data-ri='0']/div/text()") # data-ri=image_num (0 = first image, 1 = second, etc)
            
            if (not path):
                await reply(ctx, "Query for `{}` failed (maybe try again)".format(query))
                
            if (isinstance(path, list)):
                path = path[0].strip()
            elif (isinstance(path, str)):
                path = path.strip()
                
            path = json.loads(path) # convert to dict
            img_url = path["ou"]
            
            embed = discord.Embed()
            embed.title = "Search results"
            embed.set_footer(text="Page 1/1 (1 entries)") # TODO: make this dynamic
            embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
            embed.color = discord.Color.blue()
            embed.set_image(url=img_url)
            
            await bot.send_message(ctx.message.channel, embed=embed)
                

"""///////////////////////
//    error handling    //
///////////////////////"""

@bot.event
async def on_command_error(error, ctx): 
    # TODO: handle what we need to
    """
    commands.UserInputError, commands.CommandNotFound, commands.MissingRequiredArgument,
    commands.TooManyArguments, commands.BadArgument, commands.NoPrivateMessage,
    commands.CheckFailure, commands.DisabledCommand, commands.CommandInvokeError,
    commands.CommandOnCooldown
    """
        
    if (isinstance(error, commands.CommandNotFound)):
        return
    
    if (isinstance(error, commands.CheckFailure)):
        return
        
    await reply(ctx, error)
        
"""//////////////
//    hooks    //
//////////////"""

@bot.event
async def on_message(message):
    global playing_queue, player
    
    try:
        if (not message.content or not message.author):
            return
        
        # print messages
        # don't mess up the flow of the execution if it errors
        try:
            print(format_log_message(message))
        
        except Exception as e:
            await error_alert(e, extra="logging")
        
        # don't respond to yourself
        if (message.author == bot.user):
            return
        
        # insult anyone who @s us
        if (bot.user in message.mentions and not message.mention_everyone):
            await reply(message, "fuck you, you %s." % await get_insult())
        
        # respond to "^ this", "this", "^", etc.
        if (message.content.startswith("^") or message.content.lower() == "this"):
            if (message.content == "^" or "this" in message.content.lower()):
                this_msg = "^"
                
                if (randint(0, 100) < 50):
                    this_msg = "^ this"
                    
                await bot.send_message(message.channel, this_msg)
                return
            
        # TODO: reactions will go here
        
        # process commands
        await bot.process_commands(message)
        
    except Exception as e:        
        await error_alert(e)

# called when a user joins the server
@bot.event
async def on_member_join(member):
    try:
        if (member == bot.user):
            return
        
        await msg_admin_channel("{time} {name} [{uid}] joined".format(time=get_cur_time(), name=format_member_name(member), uid=member.id), member.server)
        
    except Exception as e:
        await error_alert(e)

# called when a user leaves the server
@bot.event
async def on_member_remove(member):
    try:
        if (member == bot.user):
            return
        
        await msg_admin_channel("{time} {name} [{uid}] left".format(time=get_cur_time(), name=format_member_name(member), uid=member.id), member.server)
    
    except Exception as e:
        await error_alert(e)

# called when the bot joins a server
@bot.event
async def on_server_join(server):
    try:
        await private_message(DEV_ID, "{time} CBot joined server {name}#{id}".format(time=get_cur_time(), name=server.name, id=server.id))
    
    except Exception as e:
        await error_alert(e)

# called when the bot leaves a server
@bot.event
async def on_server_remove(server):
    try:
        await private_message(DEV_ID, "{time} CBot was removed from server {name}#{id}".format(time=get_cur_time(), name=server.name, id=server.id))
    
    except Exception as e:
        await error_alert(e)

"""////////////////////////
//    running the bot    //
////////////////////////"""

# prompts user to input bot token and optional user id for event messaging and saves to "cbot.txt" in the format token;devid
def bot_init():
    global DEV_ID
    
    token = input("Enter the bot's token: ")
    DEV_ID = input("Enter your Discord ID ONLY if you want the bot to message you when events happen (leave blank if you don't): ")
    
    with open("cbot.txt", "w") as f:
        f.write("{};{}".format(token, DEV_ID))
        
    return token

if (not os.path.exists("cbot.txt")):
    token = bot_init()
else:
    token = ""
    tries = 0
    
    while (not token and tries < 5):
        if (tries > 5):
            print("[Error] CBot tried 5 times to get token and failed!")
            exit()
            
        tries += 1
        
        try:
            with open("cbot.txt", "r") as f:
                r = f.readline().split(";")
                
                token = r[0]
                DEV_ID = r[1]
            
            break
        
        except Exception:
            token = bot_init()

bot.run(token)