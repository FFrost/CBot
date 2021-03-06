import discord
from discord.ext import commands

from modules import enums, utils

import os
import time
import ipaddress
import json
import tempfile
import asyncio
import aiohttp
import pytesseract
from lxml import html
from urllib.parse import quote
from collections import OrderedDict
from PIL import Image as Img
from typing import Optional, Union

liquid_command_enabled = True

try:
    import wand, wand.color, wand.drawing

except Exception as e:
    print(f"{e}\nDisabling liquid command.")
    liquid_command_enabled = False

class Image(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.SEARCH_CACHE = OrderedDict()

        self.remove_inactive_image_searches_task = self.bot.loop.create_task(self.remove_inactive_image_searches())

    def cog_unload(self):
        self.remove_inactive_image_searches_task.cancel()

    # find images in message or attachments and pass to liquify function
    @commands.command(description="liquidizes an image",
                      brief="liquidizes an image",
                      enabled=liquid_command_enabled)
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def liquid(self, ctx, url: str = ""):
        try:
            message = ctx.message
            
            if (not url):
                if (message.attachments):
                    url = message.attachments[0].url
                else:
                    last_img = await self.bot.bot_utils.find_last_image(message)
                    
                    if (last_img):
                        url = last_img
                    
            if (not url):
                await ctx.send(f"{ctx.author.mention} No image found")
                return
            
            msg = await ctx.send(f"{ctx.author.mention} Liquidizing image...")
            
            async with ctx.channel.typing():
                path = await self.download_image(url)
                
                if (isinstance(path, enums.ImageCodes)):
                    await self.image_error_message(message, path, url)
                else:
                    code = await self.do_magic(ctx, path)
                    
                    if (code != enums.ImageCodes.SUCCESS):
                        await self.image_error_message(message, code, url)
                
                await msg.delete()
            
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} Failed to liquidize image `{url}`")
            await self.bot.messaging.error_alert(e)
            
    # finds the last image sent from a message
    # input: message, the message the user sent and where to start the search
    # output: path to the downloaded file or None if the download failed
    async def find_and_download_image(self, message: discord.Message) -> Optional[str]:
        url = None

        if (message.attachments):
            url = message.attachments[0].url
        else:
            last_img = await self.bot.bot_utils.find_last_image(message)
            
            if (last_img): 
                url = last_img
                
        if (not url):
            return None
        
        path = await self.download_image(url)
            
        if (isinstance(path, enums.ImageCodes)):
            await self.image_error_message(message, path, url)
            return None
        
        return path
        
    # save an image file with a new filename and upload it to a discord channel
    # input: message, command message
    #        path, path to the original downloaded file
    #        image, edited image file currently open
    #        url, the url of the original image that was downloaded
    async def save_and_upload(self, message: discord.Message, path: str, image: Img, url: str) -> None:
        file_path = os.path.splitext(path)[0]
        edited_file_path = file_path + "_edited.png"
        
        # now save the magickd image
        image.save(edited_file_path, format="PNG")
        
        # upload liquidized image
        if (message.channel.permissions_for(message.author).attach_files):
            await message.channel.send(file=discord.File(edited_file_path))
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
    # input: message, message to reply to
    #        code, the error code
    #        url, the url that was attempted to be liquidized
    async def image_error_message(self, message: discord.Message, code: enums.ImageCodes, url: str = "") -> None:
        if (code == enums.ImageCodes.MISC_ERROR):
            await message.channel.send(f"{message.author.mention} Image error")
        elif (code == enums.ImageCodes.MAX_FILESIZE):
            await message.channel.send(f"{message.author.mention} Image filesize was too large (max filesize: 10mb)")
        elif (code == enums.ImageCodes.INVALID_FORMAT):
            await message.channel.send(f"{message.author.mention} Invalid image format")
        elif (code == enums.ImageCodes.MAX_DIMENSIONS):
            await message.channel.send(f"{message.author.mention} Image dimensions were too large (max dimensions: 3000x3000)")
        elif (code == enums.ImageCodes.BAD_URL):
            await message.channel.send(f"{message.author.mention} Failed to download image")
        elif (code == enums.ImageCodes.NO_PERMISSIONS):
            await message.channel.send(f"{message.author.mention} Missing attach file permissions, can't upload image file")
    
    # download an image from a url and save it as a temp file
    # input: url, image to download
    #        simulate, should the image be downloaded or only checked to see if it's valid
    # output: if successful: string; path to temp file;
    #         if unsuccessful: ImageCodes; error code
    async def download_image(self, url: str, simulate: bool = False) -> Union[str, enums.ImageCodes]:
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
    # input: channel, the channel to send the image in
    #        path, path to the image to liquify
    # output: return code of the operation
    async def do_magic(self, ctx: commands.Context, path: str) -> enums.ImageCodes:
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
            if (ctx.channel.permissions_for(ctx.me).attach_files):
                await ctx.channel.send(file=discord.File(magickd_file_path))
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

    @commands.command(description="first image results from Google Images",
                      brief="first image results from Google Images",
                      aliases=["image", "im"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def img(self, ctx, *, query: str):
        channel = ctx.message.channel
        async with channel.typing():
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
            url = f"https://www.google.com/search?q={quote(query)}&tbm=isch&gs_l=img&safe=on" # escape query for url
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as r:
                    if (r.status != 200):
                        await ctx.send(f"{ctx.author.mention} Query for `{query}` failed (maybe try again)")
                        return
                    
                    text = await r.text()
                    
            if ("did not match any image results" in text):
                await ctx.send(f"{ctx.author.mention} No results found for `{query}`")
                return
        
            tree = html.fromstring(text)
                    
            # count the number of divs that contain images
            path = tree.xpath("//div[@class='rg_meta notranslate']/text()")
            images = []
            
            for p in path:
                extracted_image = self.extract_image_url(p)
                
                if (extracted_image):
                    images.append(extracted_image)

            if (len(images) <= 0):
                await ctx.send(f"{ctx.author.mention} No results found for `{query}`")
                return

            images_copy = images.copy()
            img_msg = None

            for image in images_copy:
                try:
                    valid_image = await self.validate_image(image)

                    if (valid_image is None):
                        images.remove(image)
                        continue

                    embed = utils.create_image_embed(ctx.author, title=f"Search results for {query}", footer="Page 1/{}".format(len(images)), image=valid_image)
                    img_msg = await channel.send(embed=embed)
        
                    await self.bot.messaging.add_img_reactions(img_msg)
                except discord.HTTPException:
                    images.remove(image)
                    continue
                else:
                    break

            if (len(images) <= 0 or not img_msg):
                await ctx.send(f"{ctx.author.mention} No results found for `{query}`")
                return

            # add the tree to the cache
            self.SEARCH_CACHE[img_msg.id] = {"images": images, "index": 0, "time": time.time(), "command_msg": ctx.message, "channel": channel}

    # gets an image url from a dict
    # input: image_dict, dictionary in string form containing info from google image search
    # output: url of the image if valid or None if invalid
    @staticmethod
    def extract_image_url(image_dict: str) -> Optional[str]:
        try:
            image_dict = json.loads(image_dict)
            
        except Exception:
            return None
        
        if (not "ou" in image_dict):
            return None
        
        return image_dict["ou"]
    
    # checks if an image is one discord can embed
    # input: image_url, url of image
    # output: url of the image or None if invalid
    async def validate_image(self, image_url: str) -> Optional[str]:
        result = await self.download_image(image_url, simulate=True)
        
        if (result == enums.ImageCodes.SUCCESS):
            return image_url
        
        return None
                
    # edits a message with the new embed
    # input: user, the user who originally requested the image search
    #        message, the message to edit
    #        i, the index modifier, which direction to display images in, forwards or backwards from current index, can be 1 or -1
    async def update_img_search(self, user: discord.User, message: discord.Message, i: int = 1) -> None:
        if (message.id not in self.SEARCH_CACHE):
            return
        
        cached_msg = self.SEARCH_CACHE[message.id]
        
        last_time = cached_msg["time"]
        
        if (time.time() < last_time + self.bot.CONFIG["image_search"]["cooldown_between_updates"]):
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

        # if image is invalid, remove it from the list and go to the next image
        if (img_url is None):
            self.SEARCH_CACHE[message.id]["images"].remove(images[index])
            await self.update_img_search(user, message, index)
            return
                
        embed = utils.create_image_embed(user, title="Search results", footer="Page {}/{}".format(index + 1, length), image=img_url)
        
        try:
            await message.edit(embed=embed)
            
        except discord.errors.DiscordException:
            return
        
        except Exception as e:
            self.bot.bot_utils.log_error_to_file(e)
            await command_msg.channel.send(f"{command_msg.author.mention} An error occured while updating the image search: `{e}`")
            await self.remove_img_from_cache(message)
            
        else:
            await self.bot.messaging.add_img_reactions(message)
        
            # update cache
            self.SEARCH_CACHE[message.id] = {"images": images, "index": index, "time": time.time(), "command_msg": command_msg, "channel": channel}
        
    # remove an image from the cache and prevent it from being scrolled
    # input: message, message to remove
    async def remove_img_from_cache(self, message: discord.Message) -> None:
        try:
            del self.SEARCH_CACHE[message.id]
        except KeyError:
            pass
        
        try:
            await message.clear_reactions()
        except Exception:
            pass
        
    # deletes an embed and removes it from the cache
    # input: message, the message to delete
    async def remove_img_search(self, message: discord.Message) -> None:
        try:
            await self.SEARCH_CACHE[message.id]["command_msg"].delete()
        except discord.errors.Forbidden:
            pass

        try:
            del self.SEARCH_CACHE[message.id]
        except KeyError:
            pass
        
        await message.delete()
        
    # handles reactions and calls appropriate functions
    # input: reaction, the reaction applied to the message
    #        user, the user that applied the reaction
    async def image_search_reaction_hook(self, reaction: discord.Reaction, user: discord.User) -> None:
        message = reaction.message
          
        if (user == self.bot.user):
            return

        if (message.id not in self.SEARCH_CACHE):
            return
        
        if (message.author == self.bot.user):
            if (message.embeds):
                embed = message.embeds[0].to_dict()

                if ("author" not in embed or "name" not in embed["author"]):
                    return
                        
                if (embed["author"]["name"] == user.name):
                    emoji = reaction.emoji
                    
                    if (message.reactions and reaction in message.reactions and emoji in self.bot.messaging.EMOJI_CHARS.values()):
                        if (message.channel.permissions_for(message.author).manage_emojis):
                            try:
                                await message.remove_reaction(emoji, user) # remove the reaction so the user can react again
                            
                            except Exception:
                                pass
                    
                    if (emoji == self.bot.messaging.EMOJI_CHARS["stop_button"]):
                        await self.remove_img_search(message) # delete message
                    elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_forward"]):
                        await self.update_img_search(user, message, 1) # increment index
                    elif (emoji == self.bot.messaging.EMOJI_CHARS["arrow_backward"]):
                        await self.update_img_search(user, message, -1) # decrement index
                        
    async def remove_inactive_image_searches(self) -> None:
        await self.bot.wait_until_ready()
        
        while (not self.bot.is_closed()):
            try:
                search_cache_copy = self.SEARCH_CACHE.copy()
                
                for message_id, cache in search_cache_copy.items():
                    if (time.time() > cache["time"] + self.bot.CONFIG["image_search"]["time_to_wait"]):
                        try:
                            msg = await cache["channel"].fetch_message(message_id)
                            
                        except Exception as e:
                            self.bot.bot_utils.log_error_to_file(e)
                        
                        await self.remove_img_from_cache(msg)
                
                search_cache_copy.clear()

            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)
            
            #await asyncio.sleep(self.bot.CONFIG["image_search"]["time_to_wait"] // 2)
            await asyncio.sleep(20)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # call image search hook
        await self.image_search_reaction_hook(reaction, user)

    # pixelates image
    # input: message, command message
    #        pixel_size, how much to pixelate the image
    #        url, url of the image to download
    async def do_pixel(self, message: discord.Message, pixel_size: int, url: str) -> None:
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
        
        img = Img.open(path) # filename
        
        if (img.size >= (3000, 3000)):
            utils.remove_file_safe(path)
            await self.image_error_message(message, enums.ImageCodes.MAX_DIMENSIONS, url)
            return
        
        # no animated gifs
        if (img.info and ("loop" in img.info or "duration" in img.info)):
            utils.remove_file_safe(path)
            await message.channel.send(f"{message.author.mention} Can't pixelate animated gifs")
            return
        
        old_size = img.size
        new_size = (old_size[0] // pixel_size, old_size[1] // pixel_size)
        
        if (new_size > (0, 0)):
            img = img.resize(new_size, Img.NEAREST)
            img = img.resize(old_size, Img.NEAREST)
        else:
            utils.remove_file_safe(path)
            await message.channel.send(f"{message.author.mention} Pixel size too large")
            return
        
        await self.save_and_upload(message, path, img, url)
                
    @commands.command(description="pixelates an image",
                      brief="pixelates an image",
                      aliases=["pix", "pixel", "px"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def pixelate(self, ctx, pixel_size: int = 5, *, url: str = "") -> None:
        if (pixel_size < 1):
            await ctx.send(f"{ctx.author.mention} Pixel size must be at least 1")
            return
        
        msg = await ctx.send(f"{ctx.author.mention} Pixelating image...")
        
        await self.do_pixel(ctx.message, pixel_size, url)
        
        await msg.delete()

    @commands.command(description="speeds up a gif",
                      brief="speeds up a gif",
                      aliases=["gpseed"])
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def gspeed(self, ctx, image: str = ""):
        if (not image):
            path = await self.find_and_download_image(ctx.message)
        else:
            path = await self.download_image(image)

        if (not path):
            await ctx.send(f"{ctx.author.mention} No image found")
            return
        elif (isinstance(path, enums.ImageCodes)):
            await self.image_error_message(ctx.message, path)
            return

        async with ctx.channel.typing():
            # process it
            img = Img.open(path)

            if (img.size >= (3000, 3000)):
                utils.remove_file_safe(path)
                await self.image_error_message(ctx.message, enums.ImageCodes.MAX_DIMENSIONS)
                return

            # only animated gifs
            if (img.info and ("loop" not in img.info or "duration" not in img.info)):
                utils.remove_file_safe(path)
                await ctx.send(f"{ctx.author.mention} Image must be an animated gif")
                return

            duration = int(img.info.get("duration", 0))
            img.info["duration"] = max(int(duration / 2), 1) # TODO: remember to change this on july 1st (https://github.com/python-pillow/Pillow/issues/3073#issuecomment-380620206)

            file_path = os.path.splitext(path)[0]
            edited_file_path = file_path + "_edited.gif"

            img.save(edited_file_path, format="gif", save_all=True, optimize=False)

            # upload liquidized image
            if (ctx.channel.permissions_for(ctx.me).attach_files):
                await ctx.channel.send(file=discord.File(edited_file_path))
            else:
                await self.image_error_message(ctx.message, enums.ImageCodes.NO_PERMISSIONS)
            
            # just in case
            await asyncio.sleep(1)
            
            # delete leftover file(s)
            utils.remove_file_safe(path)
            utils.remove_file_safe(edited_file_path)

    # TODO: rotate each frame in a gif
    @commands.command(description="rotates an image",
                      brief="rotates an image")
    @commands.cooldown(2, 5, commands.BucketType.channel)
    async def rotate(self, ctx, degrees: int = 90, image: str = ""):
        async with ctx.channel.typing():
            if (not image):
                path = await self.find_and_download_image(ctx.message)
            else:
                path = await self.download_image(image)

            if (not path):
                await ctx.send(f"{ctx.author.mention} No image found")
                return

            try:
                im = Img.open(path)
                im = im.rotate(degrees, expand=True)
                im.save(path)

                await ctx.channel.send(file=discord.File(path))
            except Exception as e:
                await ctx.send(f"{ctx.author.mention} An error occured processing the image: `{e}`")
            finally:
                utils.remove_file_safe(path)

    @commands.command(description="converts an image to specified format",
                      brief="converts an image to specified format")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def convert(self, ctx, url: str = "", extension = "jpeg"):
        async with ctx.channel.typing():
            if (not url):
                path = await self.find_and_download_image(ctx.message)

                if (not path):
                    await ctx.send(f"{ctx.author.mention} No image found")
                    return
            else:
                path = await self.download_image(url)

                if (isinstance(path, enums.ImageCodes)):
                    await self.image_error_message(ctx.message, path, url)
                    return

            formats = ["jpeg", "png"]

            if (extension not in formats):
                await ctx.send(f"{ctx.author.mention} Invalid format `{extension}`, valid formats are: {utils.format_code_brackets(formats)}")
                return
                
            new_filename = f"{path}.{extension}"

            im = Img.open(path).convert("RGB")
            im.save(new_filename, extension)

            await ctx.channel.send(file=discord.File(new_filename))

            utils.remove_file_safe(new_filename)
            utils.remove_file_safe(path)

    @commands.command(description="extracts text from an image",
                      brief="extracts text from an image")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ocr(self, ctx, *, url: str = ""):
        await ctx.trigger_typing()

        if (not url):
            path = await self.find_and_download_image(ctx.message)

            if (not path):
                await ctx.send(f"{ctx.author.mention} No image found")
                return
        else:
            path = await self.download_image(url)

            if (isinstance(path, enums.ImageCodes)):
                await self.image_error_message(ctx.message, path, url)
                return

        im = Img.open(path).convert("RGB")
        text = pytesseract.image_to_string(im)

        if (not text):
            await ctx.send(f"{ctx.author.mention} No text found")
        else:
            await ctx.send(f"{ctx.author.mention} ```{text}```")

        utils.remove_file_safe(path)

    @commands.command(description="needs more jpeg",
                      brief="needs more jpeg",
                      aliases=["jpg"])
    async def jpeg(self, ctx, quality: int = 1, url: str = ""):
        await ctx.trigger_typing()

        if (quality < 0 or quality > 100):
            await ctx.send(f"{ctx.author.mention} Quality must be between 0 and 100")
            return

        if (not url):
            path = await self.find_and_download_image(ctx.message)

            if (not path):
                await ctx.send(f"{ctx.author.mention} No image found")
                return
        else:
            path = await self.download_image(url)

            if (isinstance(path, enums.ImageCodes)):
                await self.image_error_message(ctx.message, path, url)
                return

        filename, ext = os.path.splitext(path)

        new_filename = f"{filename}_jpegged{ext}"

        im = Img.open(path)
        im = im.convert(im.mode)
        im.save(new_filename, optimize=True, quality=quality)

        await ctx.channel.send(file=discord.File(new_filename))

        utils.remove_file_safe(new_filename)
        utils.remove_file_safe(path)

def setup(bot):
    bot.add_cog(Image(bot))
