import discord
from discord.ext import commands

from modules import bot_utils, utils, enums, messaging, misc, checks, steam

import logging, os, traceback, glob, yaml, sys
from random import randint

# set up logger
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))

class CBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!",
                         description="CBot 2.0 by Frost#0261",
                         pm_help=True)
        
        self.source_url = "https://github.com/FFrost/CBot"

        self.DEFAULT_CONFIG = {
                "trn_api_key": "", # tracker network api key (for fortnite stats command, https://fortnitetracker.com/site-api)
                "steam_api_key": "", # api key for steam (https://steamcommunity.com/dev/apikey)
                "IMAGESEARCH_TIME_TO_WAIT": 60, # time in seconds to wait before removing inactive image searches
                "IMAGESEARCH_COOLDOWN_BETWEEN_UPDATES": 1 # cooldown in seconds in between editing the image search embed when scrolling between pages
               }
        
        self.bot_restart_arg = "-restarted"
        
        self.token = ""
        self.dev_id = ""
        self.REAL_FILE = os.path.realpath(__file__)
        self.REAL_PATH = os.path.dirname(self.REAL_FILE)
        self.TOKEN_PATH = self.REAL_PATH + "/cbot.yml"

        self.get_token()

        self.CONFIG = {}
        self.CONFIG_PATH = self.REAL_PATH + "/config.yml"
        
        self.load_config()
        self.get_config()

        steam.steam_api_key = self.CONFIG["steam_api_key"]
        
        checks.owner_id = self.dev_id
        
        print("Loading modules...")
        
        self.bot_utils = bot_utils.BotUtils(self)
        self.messaging = messaging.Messaging(self)
        self.misc = misc.Misc(self)
        
        print("Loaded modules")
        
        print("Loading cogs...")
        
        self.loaded_cogs = {}
        
        self.cog_path = self.REAL_PATH + "/cogs/"
        cogs = glob.glob(self.cog_path + "*.py")
              
        # load all cogs from the directory
        for i, path in enumerate(cogs):
            cog_name = os.path.basename(path).replace(".py", "")
            ext = "cogs." + cog_name
            
            try:
                self.load_extension(ext)
            except Exception as e:
                print("\tFailed to load cog \"{}\" ({})".format(ext, e))
                self.loaded_cogs[cog_name] = {"ext": ext, "loaded": False}
            else:
                print("\tLoaded cog {}/{}: {}".format(i + 1, len(cogs), ext))
                self.loaded_cogs[cog_name] = {"ext": ext, "loaded": True}
                
        print("Finished loading cogs")
        
        print("CBot initialized")
        
    # save bot token and optional developer id to file
    def save_token(self):
        token = input("Enter the bot's token: ")
        
        while (not token):
            token = input("Enter the bot's token: ")
            
        self.token = token
        
        self.dev_id = input("Enter your Discord ID ONLY if you want the bot to message you when events happen (leave blank if you don't): ")
        
        if (not self.dev_id):
            confirm = input("Are you sure you don't want to enter your Discord ID? (y/n): ").lower() == "y"
            
            if (confirm):
                self.dev_id = ""
            else:
                self.dev_id = input("Enter your Discord ID: ")
        
        data = {
                "token": self.token,
                "dev_id": self.dev_id
               }
        
        with open(self.TOKEN_PATH, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
            
        print("Saved token to file")
        
    # load token and dev id from file or prompt user if they don't exist
    def get_token(self):
        if (not os.path.exists(self.TOKEN_PATH)):
            self.save_token()
        else:
            try:
                with open(self.TOKEN_PATH, "r") as f:  
                    config = yaml.load(f)
                    
                    self.token = config["token"]
                    self.dev_id = config["dev_id"]
                    
                    print("Loaded token from file")
            
            except Exception:
                print("Failed to read token from file, please reenter it")
                self.save_token()

    # creates a config file if it doesn't exist,
    # updates it if needed,
    # and loads it
    def load_config(self):
        data = self.DEFAULT_CONFIG

        if (not os.path.exists(self.CONFIG_PATH)):
            print("Saving config file to {}".format(self.CONFIG_PATH))
        else:
            # saved config exists, read it
            with open(self.CONFIG_PATH, "r") as f:
                disk_config = yaml.load(f)

            # check if the saved config is up to date (do the keys match?)
            # if they do, no need to update it
            if (set(data.keys()) == set(disk_config.keys())):
                self.CONFIG = self.get_config()
                return

            # it's outdated
            print("Updating config....")

            # update the new config with the old values if they exist
            for key, value in disk_config.items():
                if (key in data):
                    data[key] = value
        
        with open(self.CONFIG_PATH, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        self.CONFIG = data

        print("Saved config")

    # gets the config from disk
    def get_config(self):
        if (not os.path.exists(self.CONFIG_PATH)):
            self.save_config()

        with open(self.CONFIG_PATH, "r") as f:  
            self.CONFIG = yaml.load(f)

        print("Loaded config from file")
    
    async def on_ready(self):
        print("Logged in as {name}#{disc} [{uid}]".format(name=self.user.name, disc=self.user.discriminator, uid=self.user.id))
        
        await self.change_presence(game=discord.Game(name="!help for info"))
        await self.print_bot_info()
        
        print("CBot ready!")
        
        if (self.bot_restart_arg in sys.argv):
            await self.messaging.message_developer("CBot restarted successfully")
    
    # print info about where the bot is
    async def print_bot_info(self):
        print("Connected to:")
        
        for s in self.servers:
            if (s.unavailable): # can't retrieve info about server
                print("\t{id} - server is unavailable!".format(id=s.id))
            else:
                print("\t{name} owned by {owner}#{ownerid}".format(name=s.name, owner=s.owner.name, ownerid=s.owner.discriminator))
    
    async def on_error(self, event, *args, **kwargs):
        trace = traceback.format_exc()
        
        self.bot_utils.log_error_to_file(trace)
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
        elif (isinstance(error, checks.NoVoiceChannel)):
            await self.messaging.reply(ctx.message, "You must be in a voice channel to use this command")
            return
        elif (isinstance(error, commands.CheckFailure)):
            await self.messaging.reply(ctx.message, "You don't have permissions for this command")
            return
            
        await self.messaging.reply(ctx, error)
    
    # only output command messages
    async def on_command(self, command, ctx):
        await self.bot_utils.output_log(ctx.message)
            
    # TODO: track completed commands for !stats
    async def on_command_completion(self, command, ctx):
        pass
    
    async def on_message(self, message):
        try:
            if (not message.content or not message.author):
                return
            
            # don't respond to ourself
            if (message.author == self.user):
                await self.bot_utils.output_log(message)
                return
            
            # insult anyone who @s us
            if (self.user in message.mentions and not message.mention_everyone and not message.content.startswith("!")):
                await self.bot_utils.output_log(message)
                
                insult = await self.misc.get_insult()
                an = "an" if (insult[0].lower() in "aeiou") else "a"
                await self.messaging.reply(message, "you're {an} {insult}.".format(an=an, insult=insult))
            
            # respond to "^ this", "this", "^", etc.
            if (message.content.startswith("^") or message.content.lower() == "this"):
                if (message.content == "^" or "this" in message.content.lower()):
                    this_msg = "^"
                    
                    if (randint(0, 100) < 50):
                        this_msg = "^ this"
                        
                    await self.send_message(message.channel, this_msg)
                    return
                
            if (message.content.lower().startswith("same")):
                await self.send_message(message.channel, "same")
                return

            if (self.CONFIG["steam_api_key"] and utils.is_steam_url(message.content.lower())):
                embed = await utils.create_steam_embed(message.author, message.content.lower())

                if (embed):
                    await self.send_message(message.channel, embed=embed)
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
            
            await self.messaging.msg_admin_channel("{time} {name} [{uid}] joined".format(time=utils.get_cur_time(),
                                                                                         name=utils.format_member_name(member),
                                                                                         uid=member.id),
                                                                                         member.server)
            
        except Exception as e:
            await self.messaging.error_alert(e)
    
    async def on_member_remove(self, member):
        try:
            if (member == self.user):
                return
            
            await self.messaging.msg_admin_channel("{time} {name} [{uid}] left".format(time=utils.get_cur_time(),
                                                                                       name=utils.format_member_name(member),
                                                                                       uid=member.id),
                                                                                       member.server)
        
        except Exception as e:
            await self.messaging.error_alert(e)
    
    async def on_server_join(self, server):
        try:
            await self.messaging.private_message(self.dev_id, "{time} CBot joined server {name}#{id}".format(time=utils.get_cur_time(),
                                                                                                             name=server.name,
                                                                                                             id=server.id))
        
        except Exception as e:
            await self.messaging.error_alert(e)
    
    async def on_server_remove(self, server):
        try:
            await self.messaging.private_message(self.dev_id, "{time} CBot was removed from server {name}#{id}".format(time=utils.get_cur_time(),
                                                                                                                       name=server.name,
                                                                                                                       id=server.id))
        
        except Exception as e:
            await self.messaging.error_alert(e)
                
    def run(self):
        super().run(self.token)
        
bot = CBot()
bot.run()
