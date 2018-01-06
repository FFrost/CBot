"""
TODO now:
    - reimplement voice player (with simultaneous cross-server play)
    - add the ability for server owners to add reactions to messages with specified keywords
    - add options for developer notification/admin settings/etc
    - add a time limit on how long a user can scroll through images (after x mins of inactivity, remove reactions and clear from cache)
    
next:
    - store bot token/other settings/etc in database instead of txt files
"""

import discord
from discord.ext import commands

from modules import utils, enums, messaging

import logging, os, traceback, glob
from random import randint

# load opus library for voice
if (not discord.opus.is_loaded()):
    discord.opus.load_opus("opus")

# set up logging
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))

class CBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("!"),
                         description="CBot 2.0",
                         pm_help=True)
        
        self.source_url = "https://github.com/FFrost/CBot"
        
        self.token = ""
        self.dev_id = ""
        self.REAL_PATH = os.path.dirname(os.path.realpath(__file__))
        self.TOKEN_PATH = self.REAL_PATH + "/cbot.txt"
        self.get_token()
        
        # load all cogs from the directory
        for path in glob.glob(self.REAL_PATH + "/cogs/*.py"):
            ext = "cogs." + os.path.basename(path).replace(".py", "")
            try:
                self.load_extension(ext)
                print("Loaded cog: {}".format(ext))
            except Exception as e:
                print("Failed to load extension \"{}\" ({})".format(ext, e))
            
        self.utils = utils.Utils(self)
        self.enums = enums.Enums()
        self.messaging = messaging.Messaging(self)
        
    def save_token(self):
        token = input("Enter the bot's token: ")
        
        while (not token):
            token = input("Enter the bot's token: ")
            
        self.token = token
        
        dev_id = input("Enter your Discord ID ONLY if you want the bot to message you when events happen (leave blank if you don't): ")
        
        if (not dev_id):
            confirm = input("Are you sure you don't want to enter your Discord ID? (y/n): ").lower() == "y"
            
            if (confirm):
                self.dev_id = ""
            else:
                self.dev_id = input("Enter your Discord ID: ")
        
        with open(self.TOKEN_PATH, "w") as f:
            f.write("{};{}".format(self.token, self.dev_id))
        
    def get_token(self):
        if (not os.path.exists(self.TOKEN_PATH)):
            self.save_token()
        else:
            try:
                with open(self.TOKEN_PATH, "r") as f:
                    r = f.readline().split(";")
                    
                    self.token = r[0]
                    self.dev_id = r[1]        
            except Exception:
                print("Failed to read token from file, please reenter it")
                self.save_token()
    
    async def on_ready(self):
        print("Logged in as {name}#{disc} [{uid}]".format(name=self.user.name, disc=self.user.discriminator, uid=self.user.id))
        
        await self.change_presence(game=discord.Game(name="!help for info"))
        await self.bot_info()
        
        await self.messaging.message_developer("CBot loaded!")
    
    # print info about where the bot is
    async def bot_info(self):
        print("Connected to:")
        
        for s in self.servers:
            if (s.unavailable): # can't retrieve info about server, shouldn't usually happen
                print("\t{id} - server is unavailable!".format(id=s.id))
            else:
                print("\t{name} owned by {owner}#{ownerid}".format(name=s.name, owner=s.owner.name, ownerid=s.owner.discriminator))
    
    async def on_error(self, event, *args, **kwargs):  
        trace = traceback.format_exc()
        
        self.utils.log_error_to_file(trace)
        await self.messaging.error_alert(e=trace)
    
    async def on_command_error(self, error, ctx): 
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
            
        await self.messaging.reply(ctx, error)
    
    async def on_message(self, message):
        try:
            if (not message.content or not message.author):
                return
            
            # print messages
            # don't mess up the flow of the execution if it errors
            try:
                print(self.utils.format_log_message(message))
            
            except Exception as e:
                await self.messaging.error_alert(e, extra="logging")
            
            # don't respond to yourself
            if (message.author == self.user):
                return
            
            # insult anyone who @s us
            # TODO: find a better way to check if command is being run than startswith("!")
            if (self.user in message.mentions and not message.mention_everyone and not message.content.startswith("!")):
                await self.messaging.reply(message, "fuck you, you %s." % await self.utils.get_insult())
            
            # respond to "^ this", "this", "^", etc.
            if (message.content.startswith("^") or message.content.lower() == "this"):
                if (message.content == "^" or "this" in message.content.lower()):
                    this_msg = "^"
                    
                    if (randint(0, 100) < 50):
                        this_msg = "^ this"
                        
                    await self.send_message(message.channel, this_msg)
                    return
                
            # TODO: reactions will go here
            
            # process commands
            await self.process_commands(message)
            
        except Exception as e:        
            await self.messaging.error_alert(e)
    
    async def on_member_join(self, member):
        try:
            if (member == self.user):
                return
            
            await self.messaging.msg_admin_channel("{time} {name} [{uid}] joined".format(time=self.utils.get_cur_time(),
                                                                                         name=self.utils.format_member_name(member),
                                                                                         uid=member.id), member.server)
            
        except Exception as e:
            await self.messaging.error_alert(e)
    
    async def on_member_remove(self, member):
        try:
            if (member == self.user):
                return
            
            await self.messaging.msg_admin_channel("{time} {name} [{uid}] left".format(time=self.utils.get_cur_time(),
                                                                                       name=self.utils.format_member_name(member),
                                                                                       uid=member.id), member.server)
        
        except Exception as e:
            await self.messaging.error_alert(e)
    
    async def on_server_join(self, server):
        try:
            await self.messaging.private_message(self.dev_id, "{time} CBot joined server {name}#{id}".format(time=self.utils.get_cur_time(),
                                                                                         name=server.name,
                                                                                         id=server.id))
        
        except Exception as e:
            await self.messaging.error_alert(e)
    
    async def on_server_remove(self, server):
        try:
            await self.messaging.private_message(self.dev_id, "{time} CBot was removed from server {name}#{id}".format(time=self.utils.get_cur_time(),
                                                                                                   name=server.name,
                                                                                                   id=server.id))
        
        except Exception as e:
            await self.messaging.error_alert(e)
                
    def run(self):
        super().run(self.token)
        
bot = CBot()
bot.run()