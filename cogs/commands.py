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

class Utility:
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(description="info about a Discord user", brief="info about a Discord user", pass_context=True)
    async def info(self, ctx, *, name : str=""):
        if (ctx.message.mentions):
            info_msg = self.bot.utils.get_user_info(ctx.message.mentions[0])
        elif (name):
            user = await self.bot.utils.find(name)
                    
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `%s`" % name)
                return
                    
            info_msg = self.bot.utils.get_user_info(user)
        else:
            info_msg = self.bot.utils.get_user_info(ctx.message.author)
    
        await self.bot.messaging.reply(ctx, info_msg)
        
    @commands.command(description="get a user's avatar", brief="get a user's avatar", pass_context=True)
    async def avatar(self, ctx, *, name : str=""):
        if (ctx.message.mentions):
            users = ctx.message.mentions
        elif (name):
            user = await self.bot.utils.find(name)
            
            if (not user):
                await self.bot.messaging.reply(ctx, "Failed to find user `{}`".format(name))
                return
            else:
                users = [user]
        else:
            users = [ctx.message.author]
        
        for user in users:
            embed = self.bot.utils.create_image_embed(user, image=user.avatar_url)
            await self.bot.send_message(ctx.message.channel, embed=embed)
            
    @commands.command(description="undo bot's last message(s)", brief="undo bot's last message(s)", pass_context=True)    
    async def undo(self, ctx, num_to_delete=1):
        cur = 0
    
        async for message in self.bot.logs_from(ctx.message.channel):
            if (cur >= num_to_delete):
                break
            
            if (message.author == self.bot.user):
                await self.bot.delete_message(message)
                cur += 1
        
        # TODO: check if we have perms to do this
        try:
            await self.bot.delete_message(ctx.message)
        except Exception:
            pass
        
        temp = await self.bot.say("Deleted last {} message(s)".format(cur))
        await asyncio.sleep(5)
        
        if (temp):
            await self.bot.delete_message(temp)
            
    @commands.command(description="source code", brief="source code", pass_context=True, aliases=["src"])
    async def source(self, ctx):
        await self.bot.messaging.reply(ctx.message, "https://github.com/FFrost/cbot")

class Fun:
    def __init__(self, bot):
        self.bot = bot
        
        self.SEARCH_CACHE = OrderedDict()
 
    # find images in message or attachments and pass to liquify function
    @commands.command(description="liquidizes an image", brief="liquidizes an image", pass_context=True)
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def liquid(self, ctx, url : str=""):
        try:
            message = ctx.message
            
            if (not url):        
                if (message.attachments):
                    url = message.attachments[0]["url"]
                else:
                    last_img = await self.bot.utils.find_last_image(message)
                    
                    if (last_img): 
                        url = last_img
                    
            if (not url):
                await self.bot.messaging.reply("No image found")
                return
            
            msg = await self.bot.messaging.reply(message, "Liquidizing image...")
            
            path = await self.download_image(url)
            
            if (isinstance(path, str)):
                code = await self.do_magic(message.channel, path)
                
                if (code != self.bot.enums.LiquidCodes.SUCCESS):
                    await self.liquid_error_message(message, code, url)
            else:
                await self.liquid_error_message(message, path, url)
            
            await self.bot.delete_message(msg)
            
        except Exception as e:
            await self.bot.messaging.reply(message, "Failed to liquidize image `{}`".format(url))
            await self.bot.messaging.error_alert(e)
            
    # message the user an error if liquidizing fails
    # input: message; discord.Message; message to reply to
    #        code; LiquidCodes; the error code
    #        url; string; the url that was attempted to be liquidized
    async def liquid_error_message(self, message, code, url):
        if (code == self.bot.enums.LiquidCodes.MISC_ERROR):
            await self.bot.messaging.reply(message, "Failed to liquidize image: `{}`".format(url))
        elif (code == self.bot.enums.LiquidCodes.MAX_FILESIZE):
            await self.bot.messaging.reply(message, "Failed to liquidize image (max filesize: 10mb): `{}`".format(url))
        elif (code == self.bot.enums.LiquidCodes.INVALID_FORMAT):
            await self.bot.messaging.reply(message, "Failed to liquidize image (invalid image): `{}`".format(url))
        elif (code == self.bot.enums.LiquidCodes.MAX_DIMENSIONS):
            await self.bot.messaging.reply(message, "Failed to liquidize image (max dimensions: 3000x3000): `{}`".format(url))
        elif (code == self.bot.enums.LiquidCodes.BAD_URL):
            await self.bot.messaging.reply(message, "Failed to liquidize image (could not download url): `{}`".format(url))
    
    # download an image from a url and save it as a temp file
    # input: url; string; image to download
    # output: if successful: string; path to temp file;
    #         if unsuccessful: LiquidCodes; error code
    async def download_image(self, url):
        # check for private ip
        try:
            ip = ipaddress.ip_address(url)
            
            if (ip.is_private):
                return self.bot.enums.LiquidCodes.BAD_URL
            
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
                        return self.bot.enums.LiquidCodes.BAD_URL
                    
                    if ("Content-Length" in r.headers):
                        content_length = r.headers["Content-Length"]
                    else:
                        return self.bot.enums.LiquidCodes.BAD_URL
                    
                    # check if empty file
                    if (content_length):
                        content_length = int(content_length)
                        
                        if (content_length < 1):
                            return self.bot.enums.LiquidCodes.BAD_URL
                        elif (content_length > self.bot.enums.DISCORD_MAX_FILESIZE):
                            return self.bot.enums.LiquidCodes.MAX_FILESIZE
                    else:
                        return self.bot.enums.LiquidCodes.BAD_URL
                    
                    # check for file type
                    if (not content_type):
                        return self.bot.enums.LiquidCodes.BAD_URL
                    
                    content_type = content_type.split("/")
                    
                    mime = content_type[0]
                    ext = content_type[1]
                    
                    if (mime.lower() != "image"):
                        return self.bot.enums.LiquidCodes.INVALID_FORMAT
    
                    # make a new 'unique' tmp file with the correct extension
                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix="." + ext)
                    tmp_file_path = tmp_file.name
    
                    # write bytes to tmp file
                    with tmp_file as f:
                        while True:
                            chunk = await r.content.read(1024)
                            
                            if (not chunk):
                                break
                            
                            f.write(chunk)
                            
                    return tmp_file_path
                else:
                    return self.bot.enums.LiquidCodes.BAD_URL
                
        return self.bot.enums.LiquidCodes.MISC_ERROR
    
    # liquify image
    # input: channel; discord.Channel; the channel to send the image in
    #        url; string; the url of the image to download and liquify
    # output: int; return code of the operation
    async def do_magic(self, channel, path):
        try:
            # get a wand image object
            img = wand.image.Image(filename=path)
            
            # no animated gifs
            # TODO: run gif magic code here too
            #       be careful of alpha channel though... just in case
            if (img.animation):
                self.bot.utils.remove_file_safe(path)
                return self.bot.enums.LiquidCodes.INVALID_FORMAT
            
            # image dimensions too large
            if (img.size >= (3000, 3000)):
                self.bot.utils.remove_file_safe(path)
                return self.bot.enums.LiquidCodes.MAX_DIMENSIONS
            
            file_path, ext = os.path.splitext(path)
            
            # TODO: is it worth converting the image to a better format (like png)?
            img.format = ext[1:] # drop the "."
            img.alpha_channel = True
            
            # do the magick
            img.transform(resize="800x800>")
            img.liquid_rescale(width=int(img.width * 0.5), height=int(img.height * 0.5), delta_x=1)
            img.liquid_rescale(width=int(img.width * 1.5), height=int(img.height * 1.5), delta_x=2)
            
            # before saving, check the size of the output file
            # note - dex: on windows, this seems to be 'size' instead of 'size on disk'... 
            #             not sure if that matters when it comes to discord's max filesize
            img_blob = img.make_blob()
            
            if (len(img_blob) > self.bot.enums.DISCORD_MAX_FILESIZE):
                self.bot.utils.remove_file_safe(path)
                return self.bot.enums.LiquidCodes.MAX_FILESIZE
                
            magickd_file_path = file_path + "_magickd" + ext
                
            # now save the magickd image
            img.save(filename=magickd_file_path)
            
            # upload liquidized image
            await self.bot.send_file(channel, magickd_file_path)
            
            # just in case
            await asyncio.sleep(1)
            
            # delete leftover file(s)
            self.bot.utils.remove_file_safe(path)
            self.bot.utils.remove_file_safe(magickd_file_path)
                
            return self.bot.enums.LiquidCodes.SUCCESS
        
        # TODO: do something with this maybe? convert image to a different format and try again?
        except wand.exceptions.WandException as e:
            print("wand exception", e)
            return self.bot.enums.LiquidCodes.INVALID_FORMAT
        
        except Exception as e:
            print(e)
            return self.bot.enums.LiquidCodes.MISC_ERROR
        
    @commands.command(description="random number generator, supports hexadecimal and floats",
                      brief="random number generator, supports hex/floats",
                      pass_context=True)
    async def random(self, ctx, low : str, high : str):
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
                    await self.bot.messaging.reply(message, "format: !random low high")
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
            await self.bot.messaging.reply(message, "!random: low and high must be numbers")
            return
                
        if (low == high):
            await self.bot.messaging.reply(message, "!random: numbers can't be equal")
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
                
        await self.bot.messaging.reply(ctx, "rolled a %s" % result)
        
    # TODO: fix checks
    """  
    @commands.command(description="make the bot say something (OWNER ONLY)", brief="make the bot say something (OWNER ONLY)", pass_context=True)
    @commands.check(lambda ctx: is_dev(ctx.message))
    async def say(self, ctx, *, msg : str):
        await self.bot.say(msg)
    """
    
    @commands.command(description="first result from Google Images",
                      brief="first image result from Google Images",
                      pass_context=True,
                      aliases=["image"])
    async def img(self, ctx, *, query : str):
        channel = ctx.message.channel
        await self.bot.send_typing(channel)
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
        url = "https://www.google.com/search?q={}&tbm=isch&gs_l=img&safe=on".format(quote(query)) # escape query for url
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:              
                if (r.status != 200):
                    await self.bot.messaging.reply(ctx, "Query for `{}` failed (maybe try again)".format(query))
                    return
                
                text = await r.text()
                
        if ("did not match any image results" in text):
            await self.bot.messaging.reply(ctx, "No results found for `{}`".format(query))
            return
    
        tree = html.fromstring(text)
                
        # count the number of divs that contain images
        path = tree.xpath("//div[@data-async-rclass='search']/div")
        max_index = len(path)
                
        img_url = self.get_img_url_from_tree(tree, 0)
                
        embed = self.bot.utils.create_image_embed(ctx.message.author, title="Search results", footer="Page 1/{}".format(max_index), image=img_url)
                
        img_msg = await self.bot.send_message(channel, embed=embed)
    
        await self.bot.messaging.add_img_reactions(img_msg)
                
        # add the tree to the cache
        self.SEARCH_CACHE[img_msg.id] = {"tree": tree, "index": 0, "max": max_index, "time": time.time(), "command_msg": ctx.message}
                
    # searches a tree for a div matching google images's image element and grabs the image url from it
    # input: tree; lxml.etree._Element; a tree element of the google images page to parse
    #        index; int=0; the index of the image to display, 0 being the first image on the page
    # output: img_url; string; url of the image at the specified index
    def get_img_url_from_tree(self, tree, index=0):
        path = tree.xpath("//div[@data-async-rclass='search']/div[@data-ri='{}']/div/text()".format(index)) # data-ri=image_num (0 = first image, 1 = second, etc)
            
        if (isinstance(path, list)):
            path = path[0].strip()
        elif (isinstance(path, str)):
            path = path.strip()
                    
        path = json.loads(path) # convert to dict
        img_url = path["ou"]
        
        return img_url
                
    # edits a message with the new embed
    # input: user; discord.Member; the user who originally requested the image search
    #        message; discord.Message; the message to edit
    #        i; int=1; the index modifier, which direction to display images in, forwards or backwards from current index, can be 1 or -1
    async def update_img_search(self, user, message, i=1):
        cached_msg = self.SEARCH_CACHE[message.id]
        tree = cached_msg["tree"]
        index = cached_msg["index"] + i
        max_index = cached_msg["max"]
        command_msg = cached_msg["command_msg"]
        
        if (index < 0):
            index = max_index - 1
        
        if (index > max_index - 1):
            index = 0
        
        img_url = self.get_img_url_from_tree(tree, index)
                
        embed = self.bot.utils.create_image_embed(user, title="Search results", footer="Page {}/{}".format(index + 1, max_index), image=img_url)
        
        msg = await self.bot.edit_message(message, embed=embed)
         
        await self.bot.messaging.add_img_reactions(msg)
        
        # update cache
        self.SEARCH_CACHE[msg.id] = {"tree": tree, "index": index, "max": max_index, "time": time.time(), "command_msg": command_msg}
        
    # TODO: check every ~minute and clear searches that have been inactive for > 5 mins
    # remove an image from the cache and prevent it from being scrolled
    # input: message; discord.Message; message to clear
    async def remove_img_from_cache(self, message):
        del self.SEARCH_CACHE[message.id]
        
        try:
            await self.bot.clear_reactions(message)
        except Exception:
            pass
        
    # deletes an embed and removes it from the cache
    # input: message; discord.Message; the message to delete
    async def remove_img_search(self, message, index=0):
        # TODO: check if we have permission to do this
        try:
            await self.bot.delete_message(self.SEARCH_CACHE[message.id]["command_msg"])
            
        except Exception:
            pass
        
        del self.SEARCH_CACHE[message.id]
        await self.bot.delete_message(message)
        
    # handles reactions and calls appropriate functions
    # input: reaction; discord.Reaction; the reaction applied to the message
    #        user; discord.Member; the user that applied the reaction
    async def image_search_reaction_hook(self, reaction, user):
        message = reaction.message
          
        if (user == self.bot.user):
            return
        
        if (message.author == self.bot.user):
            if (message.embeds):
                embed = message.embeds[0]
                        
                if (embed["author"]["name"] == user.name):
                    emoji = reaction.emoji
                    
                    if (message.reactions and reaction in message.reactions):
                        await self.bot.remove_reaction(message, emoji, user) # remove the reaction so the user can react again
                                    
                    if (emoji == self.bot.messaging.EMOJI_CHARS["stop_button"]):
                        await self.remove_img_search(message) # delete message
                    elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_forward"]):
                        await self.update_img_search(user, message, 1) # increment index
                    elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_backward"]):
                        await self.update_img_search(user, message, -1) # decrement index
                        
    async def on_reaction_add(self, reaction, user):
        # call image search hook
        await self.image_search_reaction_hook(reaction, user)
        
    # TODO: reenable this if we find a workaround for rate limits
    @commands.command(description="reverse image search",
                      brief="reverse image search",
                      pass_context=True,
                      aliases=["rev"],
                      enabled=False)
    @commands.cooldown(3, 5, commands.BucketType.channel)
    async def reverse(self, ctx, *, query : str=""):
        message = ctx.message
        
        await self.bot.send_typing(message.channel)
        
        if (not query):        
            if (message.attachments):
                query = message.attachments[0]["url"]
            else:
                query = await self.bot.utils.find_last_image(message)
                
        if (not query):
            await self.bot.messaging.reply("No image found")
            return
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
        url = "https://images.google.com/searchbyimage?image_url={}&encoded_image=&image_content=&filename=&hl=en".format(quote(query))
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:              
                if (r.status != 200):
                    await self.bot.messaging.reply(ctx, "Query for `{query}` failed with status code `{code} ({string})` (maybe try again)".format(
                        query=query,
                        code=r.status,
                        string=responses[r.status]))
                    return
                
                text = await r.text()
    
                tree = html.fromstring(text)
                
                path = tree.xpath("//div[@class='_hUb']/a/text()")
                
                if (not path):
                    await self.bot.messaging.reply(ctx, "Query for `{}` failed (maybe try again)".format(query))
                    return
                    
                if (isinstance(path, list)):
                    path = path[0].strip()
                elif (isinstance(path, str)):
                    path = path.strip()
                    
                embed = self.bot.utils.create_image_embed(message.author,
                                                          title="Best guess for this image:",
                                                          description=path,
                                                          thumbnail=query,
                                                          color=discord.Color.green())
                
                await self.bot.messaging.bot.send_message(message.channel, embed=embed)

def setup(bot):
    bot.add_cog(Fun(bot))
    bot.add_cog(Utility(bot))