import discord
from discord.ext import commands

from modules import utils

from typing import Optional, List

# this file is for utility functions that require access to discord

class BotUtils:
    def __init__(self, bot):
        self.bot = bot

    # writes to a file
    # input: filename, filename to write to
    #        mode, what mode to open the file in, r, w, or a
    #        string, what should be written
    #        add_time, if should the current time be prepended
    @staticmethod
    def write_to_file(filename: str, mode: str, string: str, add_time: bool = False) -> None:
        if (add_time):
            string = f"[{utils.get_cur_time()}] {string}"
        
        with open(filename, mode) as f:
            f.write(f"{string}\n")
        
    # logs an error to file
    def log_error_to_file(self, error: str, prefix: str = "") -> None:
        if (prefix):
            error = f"[{prefix}] {error}"

        self.write_to_file(self.bot.ERROR_FILEPATH, "a", error, add_time=True)
        
    # prints a message
    async def output_log(self, message: discord.Message) -> None:
        try:
            print(utils.format_log_message(message))
        
        except Exception as e:
            await self.bot.messaging.error_alert(e, extra="on_command")
    
    # finds a user by full or partial name or id
    # input: name, keyword to search usernames for
    # output: found user or None if no users were found
    async def find(self, name: str) -> Optional[discord.User]:
        if (not name):
            return None
        
        return discord.utils.find(lambda m: (m.name.lower().startswith(name.lower()) or m.id == name), self.bot.get_all_members())
    
    # gets a channel by name
    # input: name, keyword to search channel names for
    #        guild,  guild to search for the channel
    # output: channel object matching search or None if no channels were found
    def find_channel(self, name: str, guild: discord.Guild) -> Optional[discord.abc.GuildChannel]:
        if (not guild):
            return None
        
        guild = str(guild)
        return discord.utils.get(self.bot.get_all_channels(), guild__name=guild, name=name)
    
    # find last embed in channel
    # input: channel, channel to search for embeds
    #        embed_type, type of embed to search for, video or image
    # output: url of the embed or None if not found
    async def find_last_embed(self, channel: discord.abc.GuildChannel) -> Optional[str]:
        async for message in channel.history():
            embed = utils.find_image_embed(message)
    
            if (embed):
                return embed
            
        return None
    
    # finds last image in channel
    # input: message, message from which channel will be extracted and point to search before
    # output: url of image found or None if no images were found
    async def find_last_image(self, message: discord.Message) -> Optional[str]:        
        async for message in message.channel.history(before=message):
            attachments = utils.find_attachment(message)
            
            if (attachments):
                return attachments
            
            embed = utils.find_image_embed(message)
            
            if (embed):
                return embed
            
        return None
    
    # finds last text message in channel
    # input: message, message from which channel will be used as point to search before
    # output: text of message or None if no text messages were found
    async def find_last_text(self, message: discord.Message) -> Optional[str]:
        async for message in message.channel.history(before=message):
            if (message.content):
                return message.content
            
    # finds last youtube video embed in channel
    # input: message, message from which channel will be used as point to search before
    # output: url of youtube embed or None if no youtube video embeds were found
    async def find_last_youtube_embed(self, message: discord.Message) -> Optional[str]:
        async for message in message.channel.history(before=message, limit=50):
            if (message.embeds):
                for embed in message.embeds:                    
                    if (embed.type == "video" or embed.video):
                        if (embed.provider.name == "YouTube"):
                            return embed.url
                    elif (utils.youtube_url_validation(embed.url)):
                        return embed.url

    # finds the last message sent before the command message
    # input: message, the message to search before
    # output: the message if found or None
    async def find_last_message(self, message: discord.Message) -> Optional[discord.Message]:
        async for message in message.channel.history(before=message, limit=1):
            return message

        return None
    
    # deletes a message if the bot has permission to do so
    # input: message, message to delete
    # output: success of the operation
    async def delete_message(self, message: discord.Message) -> bool:
        channel = message.channel
                
        if (isinstance(channel, discord.abc.PrivateChannel) and message.author != self.bot.user):
            return False
        elif (channel.permissions_for(message.guild.me).manage_messages):
            try:
                await message.delete()
                return True
            
            except Exception:
                return False
        
        return False
            
    # deletes a number messages from a channel by user
    # input: ctx, context to reference
    #        num_to_delete, number of messages to delete
    #        users, list of users to delete messages from or None to delete regardless of author
    # output: number of messages successfully deleted
    async def purge(self, ctx: commands.Context, num_to_delete: int, users: List[discord.User]) -> int:
        num_to_delete = abs(num_to_delete)
        num_deleted = 0
    
        async for message in ctx.channel.history(before=ctx.message, limit=500):
            if (num_deleted >= num_to_delete):
                break
            
            if (not users or message.author in users):
                success = await self.delete_message(message)
                
                if (success):
                    num_deleted += 1
            
        return num_deleted
    
    # find a guild from the ones we are currently in
    # input: search, string to search for, either part/all of guild name or index in list of guilds
    # output: the guild if found or None
    def find_guild(self, search: str) -> Optional[discord.Guild]:
        guilds = list(self.bot.guilds)
        guild = None
        
        try:
            index = int(search)
            
        except ValueError: # if it's not an index, search by name
            guild = discord.utils.find(lambda s: search.lower() in s.name.lower(), guilds)
        
        else:
            index -= 1
            
            if (index >= 0 and index < len(guilds)):
                guild = guilds[index]
            else: # search in the guild name
                guild = discord.utils.find(lambda s: search.lower() in s.name.lower(), guilds)

        return guild
