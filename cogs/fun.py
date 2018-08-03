import discord
from discord.ext import commands

from modules import enums, utils, checks

import os, re, time, ipaddress, json, tempfile, random
import asyncio, aiohttp
from random import randint, uniform
from lxml import html
from urllib.parse import quote
from collections import OrderedDict
from http.client import responses
from PIL import Image

liquid_command_enabled = True

try:
    import wand, wand.color, wand.drawing

except Exception as e:
    print("{}\nDisabling liquid command.".format(e))
    liquid_command_enabled = False

class Fun:
    def __init__(self, bot):
        self.bot = bot
        
        self.SEARCH_CACHE = OrderedDict()
        
        self.bot.loop.create_task(self.remove_inactive_image_searches())
        
        self.magic8ball_choices = ["It is certain", "It is decidedly so",
                                   "Without a doubt", "Yes definitely",
                                   "You may rely on it", "As I see it, yes",
                                   "Most likely", "Outlook good", "Yep",
                                   "Signs point to yes", "Reply hazy try again",
                                   "Ask again later", "Better not tell you now",
                                   "Cannot predict now", "Concentrate and ask again",
                                   "Don't count on it", "My reply is no",
                                   "My sources say no", "Outlook not so good",
                                   "Very doubtful"
                                   ]

    # find images in message or attachments and pass to liquify function
    @commands.command(description="liquidizes an image",
                      brief="liquidizes an image",
                      pass_context=True,
                      enabled=liquid_command_enabled)
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def liquid(self, ctx, url : str=""):
        try:
            message = ctx.message
            
            if (not url):        
                if (message.attachments):
                    url = message.attachments[0]["url"]
                else:
                    last_img = await self.bot.bot_utils.find_last_image(message)
                    
                    if (last_img): 
                        url = last_img
                    
            if (not url):
                await self.bot.messaging.reply(message, "No image found")
                return
            
            msg = await self.bot.messaging.reply(message, "Liquidizing image...")
            
            await self.bot.send_typing(message.channel)
            
            path = await self.download_image(url)
            
            if (isinstance(path, enums.ImageCodes)):
                await self.image_error_message(message, path, url)
            else:
                code = await self.do_magic(message.channel, path)
                
                if (code != enums.ImageCodes.SUCCESS):
                    await self.image_error_message(message, code, url)
            
            await self.bot.bot_utils.delete_message(msg)
            
        except Exception as e:
            await self.bot.messaging.reply(message, "Failed to liquidize image `{}`".format(url))
            await self.bot.messaging.error_alert(e)
            
    # finds the last image sent from a message
    # input: message; discord.Message; the message the user sent and where to start the search
    # output: str or None; path to the downloaded file or none if the download failed
    async def find_and_download_image(self, message):       
        if (message.attachments):
            url = message.attachments[0]["url"]
        else:
            last_img = await self.bot.bot_utils.find_last_image(message)
            
            if (last_img): 
                url = last_img
                
        if (not url):
            await self.bot.messaging.reply(message, "No image found")
            return
        
        path = await self.download_image(url)
            
        if (isinstance(path, enums.ImageCodes)):
            await self.image_error_message(message, path, url)
            return
        else:
            return path
        
    # save an image file with a new filename and upload it to a discord channel
    # input: message; discord.Message; command message
    #        path; str; path to the original downloaded file
    #        image; PIL.Image; edited image file currently open
    #        url; str; the url of the original image that was downloaded
    async def save_and_upload(self, message, path, image, url):
        file_path = os.path.splitext(path)[0]
        edited_file_path = file_path + "_edited.png"
        
        # now save the magickd image
        image.save(edited_file_path, format="PNG")
        
        # upload liquidized image
        if (self.bot.bot_utils.get_permissions(message.channel).attach_files):
            await self.bot.send_file(message.channel, edited_file_path)
        else:
            utils.remove_file_safe(path)
            utils.remove_file_safe(edited_file_path)
            await self.image_error_message(message, enums.ImageCodes.NO_PERMISSIONS, url)
            return
        
        # just in case
        await asyncio.sleep(1)
        
        # delete leftover file(s)
        utils.remove_file_safe(path)
        utils.remove_file_safe(edited_file_path)
            
    # message the user an error if liquidizing fails
    # input: message; discord.Message; message to reply to
    #        code; ImageCodes; the error code
    #        url; string; the url that was attempted to be liquidized
    async def image_error_message(self, message, code, url=""):
        if (code == enums.ImageCodes.MISC_ERROR):
            await self.bot.messaging.reply(message, "Image error")
        elif (code == enums.ImageCodes.MAX_FILESIZE):
            await self.bot.messaging.reply(message, "Image filesize was too large (max filesize: 10mb)")
        elif (code == enums.ImageCodes.INVALID_FORMAT):
            await self.bot.messaging.reply(message, "Invalid image format")
        elif (code == enums.ImageCodes.MAX_DIMENSIONS):
            await self.bot.messaging.reply(message, "Image dimensions were too large (max dimensions: 3000x3000)")
        elif (code == enums.ImageCodes.BAD_URL):
            await self.bot.messaging.reply(message, "Failed to download image")
        elif (code == enums.ImageCodes.NO_PERMISSIONS):
            await self.bot.messaging.reply(message, "Missing attach file permissions, can't upload image file")
    
    # download an image from a url and save it as a temp file
    # input: url; string; image to download
    #        simulate; bool=False; should the image be downloaded or only checked to see if it's valid
    # output: if successful: string; path to temp file;
    #         if unsuccessful: ImageCodes; error code
    async def download_image(self, url, simulate=False):
        # check for private ip
        try:
            ip = ipaddress.ip_address(url)
            
            if (ip.is_private):
                return enums.ImageCodes.BAD_URL
            
        except Exception: # if it's not an ip (i.e. an actual url like a website)
            pass
        
        if (not url.startswith("http")):
            url = "http://" + url
        
        try:
            conn = aiohttp.TCPConnector(verify_ssl=False) # for https
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get(url, timeout=10) as r:
                    if (r.status == 200):
                        if ("Content-Type" in r.headers):
                            content_type = r.headers["Content-Type"]
                        else:
                            return enums.ImageCodes.BAD_URL
                        
                        if ("Content-Length" in r.headers):
                            content_length = r.headers["Content-Length"]
                        else:
                            return enums.ImageCodes.BAD_URL
                        
                        # check if empty file
                        if (content_length):
                            content_length = int(content_length)
                            
                            if (content_length < 1):
                                return enums.ImageCodes.BAD_URL
                            elif (content_length > enums.DISCORD_MAX_FILESIZE):
                                return enums.ImageCodes.MAX_FILESIZE
                        else:
                            return enums.ImageCodes.BAD_URL
                        
                        # check for file type
                        if (not content_type):
                            return enums.ImageCodes.BAD_URL
                        
                        content_type = content_type.split("/")
                        
                        mime = content_type[0]
                        ext = content_type[1]
                        
                        if (mime.lower() != "image"):
                            return enums.ImageCodes.INVALID_FORMAT
                        
                        # return if the simulation reached this far
                        if (simulate):
                            return enums.ImageCodes.SUCCESS
        
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
                        return enums.ImageCodes.BAD_URL
                    
        except aiohttp.ClientError as e:
            return enums.ImageCodes.BAD_URL
        
        except Exception as e:
            self.bot.bot_utils.log_error_to_file(e)
            return enums.ImageCodes.MISC_ERROR
                
        return enums.ImageCodes.MISC_ERROR
    
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
                utils.remove_file_safe(path)
                return enums.ImageCodes.INVALID_FORMAT
            
            # image dimensions too large
            if (img.size >= (3000, 3000)):
                utils.remove_file_safe(path)
                return enums.ImageCodes.MAX_DIMENSIONS
            
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
            
            if (len(img_blob) > enums.DISCORD_MAX_FILESIZE):
                utils.remove_file_safe(path)
                return enums.ImageCodes.MAX_FILESIZE
                
            magickd_file_path = file_path + "_magickd" + ext
                
            # now save the magickd image
            img.save(filename=magickd_file_path)
            
            # upload liquidized image
            if (self.bot.bot_utils.get_permissions(channel).attach_files):
                await self.bot.send_file(channel, magickd_file_path)
            else:
                utils.remove_file_safe(path)
                utils.remove_file_safe(magickd_file_path)
                return self.bot.enum.ImageCodes.NO_PERMISSIONS
            
            # just in case
            await asyncio.sleep(1)
            
            # delete leftover file(s)
            utils.remove_file_safe(path)
            utils.remove_file_safe(magickd_file_path)
                
            return enums.ImageCodes.SUCCESS
        
        # TODO: do something with this maybe? convert image to a different format and try again?
        except wand.exceptions.WandException as e:
            print("wand exception", e)
            return enums.ImageCodes.INVALID_FORMAT
        
        except Exception as e:
            print(e)
            return enums.ImageCodes.MISC_ERROR
        
    @commands.command(description="random number generator, supports hexadecimal and floats",
                      brief="random number generator, supports hex/floats",
                      pass_context=True)
    @commands.cooldown(2, 5, commands.BucketType.channel)
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
            await self.bot.messaging.reply(message, "rolled a {}".format(low))
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
            result = r
                
        await self.bot.messaging.reply(ctx, "rolled a {}".format(result))
    
    @commands.command(description="first image results from Google Images",
                      brief="first image results from Google Images",
                      pass_context=True,
                      aliases=["image"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
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
        path = tree.xpath("//div[@class='rg_meta notranslate']/text()")
        images = []
        
        for p in path:
            extracted_image = self.extract_image_url(p)
            
            if (extracted_image):
                images.append(extracted_image)
        
        length = len(images)
        
        if (length < 1):
            await self.bot.messaging.reply(ctx, "No results found for `{}`".format(query))
            return

        first_image = await self.validate_image(images[0])
        
        embed = utils.create_image_embed(ctx.message.author, title="Search results", footer="Page 1/{}".format(length), image=first_image)
        
        img_msg = await self.bot.send_message(channel, embed=embed)
    
        await self.bot.messaging.add_img_reactions(img_msg)
                
        # add the tree to the cache
        self.SEARCH_CACHE[img_msg.id] = {"images": images, "index": 0, "time": time.time(), "command_msg": ctx.message, "channel": channel}

    # gets an image url from a dict
    # input: image_dict; str; dictionary in string form containing info from google image search
    # output: str or None; url of the image if valid or None if invalid
    def extract_image_url(self, image_dict):
        try:
            image_dict = json.loads(image_dict)
            
        except Exception:
            return None
        
        if (not "ou" in image_dict):
            return None
        
        return image_dict["ou"]
    
    # checks if an image is one discord can embed
    # input: image_url; str; url of image
    # output: str or None; url of the image or None if invalid
    async def validate_image(self, image_url):
        result = await self.download_image(image_url, simulate=True)
        
        if (result == enums.ImageCodes.SUCCESS):
            return image_url
        
        return None
                
    # edits a message with the new embed
    # input: user; discord.Member; the user who originally requested the image search
    #        message; discord.Message; the message to edit
    #        i; int=1; the index modifier, which direction to display images in, forwards or backwards from current index, can be 1 or -1
    async def update_img_search(self, user, message, i=1):
        if (message.id not in self.SEARCH_CACHE):
            return
        
        cached_msg = self.SEARCH_CACHE[message.id]
        
        last_time = cached_msg["time"]
        
        if (time.time() < last_time + self.bot.CONFIG["IMAGESEARCH_COOLDOWN_BETWEEN_UPDATES"]):
            return
        
        images = cached_msg["images"]
        index = cached_msg["index"] + i
        length = len(images)
        command_msg = cached_msg["command_msg"]
        channel = cached_msg["channel"]
        
        if (index < 0):
            index = length - 1
        
        if (index > length - 1):
            index = 0
        
        img_url = await self.validate_image(images[index])
                
        embed = utils.create_image_embed(user, title="Search results", footer="Page {}/{}".format(index + 1, length), image=img_url)
        
        try:
            msg = await self.bot.edit_message(message, embed=embed)
            
        except discord.errors.DiscordException:
            return
        
        except Exception as e:
            self.bot.bot_utils.log_error_to_file(e)
            await self.bot.messaging.reply(command_msg, "An error occured while updating the image search: `{}`".format(e))
            await self.remove_img_from_cache(message)
            
        else:
            await self.bot.messaging.add_img_reactions(msg)
        
            # update cache
            self.SEARCH_CACHE[msg.id] = {"images": images, "index": index, "time": time.time(), "command_msg": command_msg, "channel": channel}
        
    # remove an image from the cache and prevent it from being scrolled
    # input: message; discord.Message; message to clear
    async def remove_img_from_cache(self, message):
        try:
            del self.SEARCH_CACHE[message.id]
        except KeyError:
            pass
        
        try:
            await self.bot.clear_reactions(message)
        except Exception:
            pass
        
    # deletes an embed and removes it from the cache
    # input: message; discord.Message; the message to delete
    async def remove_img_search(self, message):
        try:
            await self.bot.bot_utils.delete_message(self.SEARCH_CACHE[message.id]["command_msg"])
            del self.SEARCH_CACHE[message.id]
        
        except KeyError:
            pass
        
        await self.bot.bot_utils.delete_message(message)
        
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
                        if (self.bot.bot_utils.get_permissions(message.channel).manage_emojis):
                            try:
                                await self.bot.remove_reaction(message, emoji, user) # remove the reaction so the user can react again
                            
                            except Exception:
                                pass
                    
                    if (emoji == self.bot.messaging.EMOJI_CHARS["stop_button"]):
                        await self.remove_img_search(message) # delete message
                    elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_forward"]):
                        await self.update_img_search(user, message, 1) # increment index
                    elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_backward"]):
                        await self.update_img_search(user, message, -1) # decrement index
                        
    async def remove_inactive_image_searches(self):
        await self.bot.wait_until_ready()
        
        while (not self.bot.is_closed):
            try:
                search_cache_copy = self.SEARCH_CACHE.copy()
                
                for message_id, cache in search_cache_copy.items():
                    if (time.time() > cache["time"] + self.bot.CONFIG["IMAGESEARCH_TIME_TO_WAIT"]):
                        try:
                            msg = await self.bot.get_message(cache["channel"], message_id)
                            
                        except Exception as e:
                            self.bot.bot_utils.log_error_to_file(e)
                        
                        await self.remove_img_from_cache(msg)
                
                search_cache_copy.clear()

            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)
            
            #await asyncio.sleep(self.bot.CONFIG["IMAGESEARCH_TIME_TO_WAIT"] // 2)
            await asyncio.sleep(20)
                        
    async def on_reaction_add(self, reaction, user):
        # call image search hook
        await self.image_search_reaction_hook(reaction, user)
        
    # TODO: reenable this if we find a workaround for rate limits
    @commands.command(description="reverse image search",
                      brief="reverse image search",
                      pass_context=True,
                      aliases=["rev"],
                      enabled=False)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def reverse(self, ctx, *, query : str=""):
        message = ctx.message
        
        await self.bot.send_typing(message.channel)
        
        if (not query):        
            if (message.attachments):
                query = message.attachments[0]["url"]
            else:
                query = await self.bot.bot_utils.find_last_image(message)
                
        if (not query):
            await self.bot.messaging.reply(message, "No image found")
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
                    
                embed = utils.create_image_embed(message.author,
                                                          title="Best guess for this image:",
                                                          description=path,
                                                          thumbnail=query,
                                                          color=discord.Color.green())
                
                await self.bot.messaging.bot.send_message(message.channel, embed=embed)
                
    # pixelates image
    # input: message; discord.Message, command message
    #        pixel_size; inthow much to pixelate the image
    #        url; str; url of the image to download
    async def do_pixel(self, message, pixel_size, url):
        if (not url):
            path = await self.find_and_download_image(message)
        else:
            path = await self.download_image(url)
        
        if (isinstance(path, enums.ImageCodes)):
            await self.image_error_message(message, path, url)
            return  
        elif (not path):
            await self.image_error_message(message, enums.ImageCodes.BAD_URL, url)
            return
        
        img = Image.open(path) # filename
        
        if (img.size >= (3000, 3000)):
            utils.remove_file_safe(path)
            await self.image_error_message(message, enums.ImageCodes.MAX_DIMENSIONS, url)
            return
        
        # no animated gifs
        if (img.info and ("loop" in img.info or "duration" in img.info)):
            utils.remove_file_safe(path)
            await self.bot.messaging.reply(message, "Can't pixelate animated gifs")
            return
        
        old_size = img.size
        new_size = (old_size[0] // pixel_size, old_size[1] // pixel_size)
        
        if (new_size > (0, 0)):
            img = img.resize(new_size, Image.NEAREST)
            img = img.resize(old_size, Image.NEAREST)
        else:
            utils.remove_file_safe(path)
            await self.bot.messaging.reply(message, "Pixel size too large")
            return
        
        await self.save_and_upload(message, path, img, url)
                
    @commands.command(description="pixelates an image",
                      brief="pixelates an image",
                      pass_context=True,
                      aliases=["pix"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def pixelate(self, ctx, pixel_size : int=5, *, url : str=""):
        if (pixel_size < 1):
            await self.bot.messaging.reply(ctx.message, "Pixel size must be at least 1")
            return
        
        msg = await self.bot.messaging.reply(ctx.message, "Pixelating image...")
        
        await self.do_pixel(ctx.message, pixel_size, url)
        
        await self.bot.bot_utils.delete_message(msg)
        
    @commands.command(description="ask the magic 8 ball something",
                      brief="ask the magic 8 ball something",
                      pass_context=True,
                      aliases=["8b", "8", "8ball"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def magic8ball(self, ctx):
        choice = random.choice(self.magic8ball_choices)
        await self.bot.messaging.reply(ctx.message, choice)

    @commands.command(description="speeds up a gif",
                      brief="speeds up a gif",
                      pass_context=True,
                      aliases=["gpseed"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def gspeed(self, ctx, image : str=""):
        if (not image):
            path = await self.find_and_download_image(ctx.message)
        else:
            path = await self.download_image(image)

        if (not path):
            return

        await self.bot.send_typing(ctx.message.channel)

        # process it
        img = Image.open(path)

        if (img.size >= (3000, 3000)):
            utils.remove_file_safe(path)
            await self.image_error_message(ctx.message, enums.ImageCodes.MAX_DIMENSIONS)
            return

        # only animated gifs
        if (img.info and ("loop" not in img.info or "duration" not in img.info)):
            utils.remove_file_safe(path)
            await self.bot.messaging.reply(ctx.message, "Image must be an animated gif")
            return

        duration = int(img.info["duration"])
        img.info["duration"] = max(int(duration / 2), 1) # TODO: remember to change this on july 1st (https://github.com/python-pillow/Pillow/issues/3073#issuecomment-380620206)

        file_path = os.path.splitext(path)[0]
        edited_file_path = file_path + "_edited.gif"

        img.save(edited_file_path, format="gif", save_all=True, optimize=False)

        # upload liquidized image
        if (self.bot.bot_utils.get_permissions(ctx.message.channel).attach_files):
            await self.bot.send_file(ctx.message.channel, edited_file_path)
        else:
            await self.image_error_message(ctx.message, enums.ImageCodes.NO_PERMISSIONS)
        
        # just in case
        await asyncio.sleep(1)
        
        # delete leftover file(s)
        utils.remove_file_safe(path)
        utils.remove_file_safe(edited_file_path)

    @commands.command(description="annoys someone (owner only)",
                    brief="annoys someone (owner only)",
                    pass_context=True)
    @commands.check(checks.is_owner)
    async def annoy(self, ctx, user : discord.User, amount : int=10):
        await self.bot.bot_utils.delete_message(ctx.message)

        for _i in range(amount):
            msg = await self.bot.send_message(ctx.message.channel, "{.mention}".format(user))
            await self.bot.bot_utils.delete_message(msg)

    @commands.command(description="scrambles someone out of a voice channel (owner only)",
                      brief="scrambles someone out of a voice channel (owner only)",
                      pass_context=True)
    @commands.check(checks.is_owner)
    async def scramble(self, ctx, user : discord.User, amount : int=5):
        await self.bot.bot_utils.delete_message(ctx.message)

        old_channel = user.voice_channel

        if (not old_channel):
            return

        channels = list(filter(lambda chan: chan.type == discord.ChannelType.voice, ctx.message.server.channels))

        for _i in range(amount):
            try:
                await self.bot.move_member(user, random.choice(channels))
            
            except Exception:
                pass

        await self.bot.move_member(user, old_channel)

    @commands.group(description="ask the bot something",
                      brief="ask the bot something",
                      pass_context=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def what(self, ctx):
        if (not ctx.invoked_subcommand):
            await self.bot.messaging.reply("Invalid command")
       
def setup(bot):
    bot.add_cog(Fun(bot))