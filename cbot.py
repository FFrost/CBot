import discord
from discord.ext import commands

import default_config
from modules import bot_utils, utils, messaging, misc, checks

import logging
import os
import traceback
import glob
import yaml
import sys
import atexit
import psutil
import importlib
import aiohttp
import sqlite3
from random import randint
from datetime import datetime
from googletrans import Translator

# set up logger
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))

class CBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!",
                         description="CBot rewrite",
                         intents=discord.Intents.all()) # TODO: ownerid here, help formatter that DMs help message

        self.source_url = "https://github.com/FFrost/CBot"
        
        self.bot_restart_arg = "-restarted"
        self.bot_manager_arg = "-manager"

        self.REQUIRED_PERMISSIONS = ["add_reactions", "attach_files", "embed_links", "read_message_history",
                                    "read_messages", "send_messages"]
        self.VOICE_PERMISSIONS = ["connect", "speak"]
        self.OPTIONAL_PERMISSIONS = ["manage_messages", "move_members"]
        
        self.token = ""
        self.dev_id: int = None
        self.REAL_FILE = os.path.realpath(__file__)
        self.REAL_PATH = os.path.dirname(self.REAL_FILE)
        self.TOKEN_PATH = f"{self.REAL_PATH}/cbot.yml"

        self.ERROR_FILEPATH = f"{self.REAL_PATH}/error.log"

        self.TEMP_DIR = "/tmp/cbot"
        if (not os.path.exists(self.TEMP_DIR)):
            os.makedirs(self.TEMP_DIR)
        
        # check if cbot exited properly on last run
        self.PID_FILEPATH = f"{self.TEMP_DIR}/cbot.pid"

        if (os.path.exists(self.PID_FILEPATH)):
            with open(self.PID_FILEPATH, "r") as f:
                pid = int(f.read())
            
            if (psutil.pid_exists(pid)):
                print("Another instance of CBot is already running, exiting...")
                sys.exit()
            else:
                print("CBot may have crashed on last run, see error log at", self.ERROR_FILEPATH)
                os.unlink(self.PID_FILEPATH)

        # cleanup temp dir
        for f in glob.glob(self.TEMP_DIR + "/*"):
            os.remove(f)

        with open(self.PID_FILEPATH, "w") as f:
            f.write(str(os.getpid()))
        
        print("Created PID file at", self.PID_FILEPATH)

        self.get_token()

        self.CONFIG = {}
        self.CONFIG_PATH = self.REAL_PATH + "/config.yml"
        
        self.load_config()

        # connect to database
        self.DATABASE_FILEPATH = f"{self.REAL_PATH}/cbot_database.db"
        self.db = sqlite3.connect(self.DATABASE_FILEPATH)

        # remove any leftover files in the youtubedl download directory
        self.cleanup_youtubedl_directory()

        checks.owner_id = self.dev_id

        self.session = aiohttp.ClientSession(loop=self.loop)
        
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

        atexit.register(self.on_exit)

        self.translator = Translator()

    # called when the script terminates
    def on_exit(self):
        print("Unlinking PID file...")
        os.unlink(self.PID_FILEPATH)
        
    # save bot token and optional developer id to file
    def save_token(self):
        token = input("Enter the bot's token: ")
        
        while (not token):
            token = input("Enter the bot's token: ")
            
        self.token = token
        
        self.dev_id = int(input("Enter your Discord ID ONLY if you want the bot to message you when events happen (leave blank if you don't): "))
        
        if (not self.dev_id):
            confirm = input("Are you sure you don't want to enter your Discord ID? (y/n): ").lower() == "y"
            
            if (confirm):
                self.dev_id: int = None
            else:
                self.dev_id = int(input("Enter your Discord ID: "))
        
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
                    config = yaml.safe_load(f)
                    
                    self.token = config["token"]
                    self.dev_id = config["dev_id"]
                    
                    print("Loaded token from file")
            
            except Exception:
                print("Failed to read token from file, please reenter it")
                self.save_token()

    def get_all_keys(self, d: dict, parent: str=""):
        keys = {}

        for k, v in d.items():
            if (isinstance(v, dict) and k not in keys):
                keys.update({k: {}})
                keys.update(self.get_all_keys(v, parent=f"{k}."))

            keys.update({f"{parent}{k}": v})

        return keys

    # creates a config file if it doesn't exist,
    # updates it if needed,
    # and loads it
    def load_config(self):
        importlib.reload(default_config)

        data = default_config.DEFAULT_CONFIG

        if (not os.path.exists(self.CONFIG_PATH)):
            print("Saving config file to {}".format(self.CONFIG_PATH))
        else:
            # saved config exists, read it
            disk_config = self.get_config()

            if (not disk_config):
                print("Failed to load disk config, falling back to default config")
                self.CONFIG = default_config.DEFAULT_CONFIG
                return

            # check if the saved config is up to date (do the keys match?)
            # if they do, no need to update it
            disk_dicts = self.get_all_keys(disk_config)
            default_dicts = self.get_all_keys(data)

            if (set(default_dicts.keys()) == set(disk_dicts.keys())):
                self.CONFIG = disk_config
                print("Loaded config from file")
                return

            # it's outdated
            print("Updating config....")

            # update the new config with the old values if they exist
            for k, v in disk_dicts.items():
                # if the disk config has an outdated key, discard it
                if (k not in default_dicts.keys()):
                    continue
                
                # otherwise, try to save the old value
                if ("." in k):
                    try:
                        utils.nested_set(data, k.split("."), v)
                    except KeyError as e:
                        print(e)
                        continue
                else:
                    data[k] = v
        
        with open(self.CONFIG_PATH, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        self.CONFIG = data

        print("Saved config")

    # gets the config from disk
    def get_config(self):
        try:
            with open(self.CONFIG_PATH, "r") as f:
                return yaml.safe_load(f)

        except yaml.scanner.ScannerError as e:
            print("Config file could not be loaded (scanner error), make sure config.yml is formatted properly: {}".format(e))
            return None

        except Exception as e:
            print("Config file could not be loaded (general error): {}".format(e))
            return None

    def save_config(self) -> bool:
        try:
            with open(self.CONFIG_PATH, "w") as f:
                yaml.dump(self.CONFIG, f, default_flow_style=False)

            return True
        except Exception as e:
            print(e)
        
        return False

    def cleanup_youtubedl_directory(self):
        path = self.CONFIG["youtube-dl"]["download_directory"]

        if (not path):
            return

        if (not os.path.exists(path)):
            return

        if (path[-1] != "/" and path[-1] != "\\"):
            path += "/"

        if (path == "/"):
            return

        for f in glob.glob(path + "*.mp3"):
            os.remove(f)
    
    async def on_ready(self):
        if (not hasattr(self, "uptime")):
            self.uptime = datetime.utcnow()

        print("Logged in as {name}#{disc} [{uid}]".format(name=self.user.name, disc=self.user.discriminator, uid=self.user.id))
        
        await self.change_presence(activity=discord.Game(name="!help for info"))
        await self.print_bot_info()

        print("CBot ready!")
        
        if (self.bot_restart_arg in sys.argv):
            await self.messaging.message_developer("CBot restarted successfully")
        elif (self.bot_manager_arg in sys.argv):
            await self.messaging.message_developer("CBot was restarted by the manager")

        self.invite_url = f"https://discordapp.com/oauth2/authorize?client_id={self.user.id}&scope=bot"
        print(f"Invite url: {self.invite_url}")
    
    # print info about where the bot is
    async def print_bot_info(self):
        print(f"Connected to {len(self.guilds)} guilds:")
        
        for s in self.guilds:
            if (s.unavailable): # can't retrieve info about guild
                print("\t{id} - guild is unavailable!".format(id=s.id))
            else:
                owned_by = f" owned by {s.owner.name}#{s.owner.discriminator}" if s.owner else ""
                print(f"\t{s.name}{owned_by}")
    
    async def on_error(self, event, *args, **kwargs):
        trace = traceback.format_exc()
        
        self.bot_utils.log_error_to_file(trace)
        await self.messaging.error_alert(e=trace)
    
    async def on_command_error(self, ctx, error):
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
            await ctx.send(f"{ctx.author.mention} You must be in a voice channel to use this command")
            return
        elif (isinstance(error, commands.CheckFailure)):
            await ctx.send(f"{ctx.author.mention} You don't have permissions for this command")
            return
        elif (isinstance(error, commands.NoPrivateMessage)):
            await ctx.send(f"{ctx.author.mention} This command can't be used in private messages")
            return
        elif (hasattr(error, "original") and isinstance(error.original, discord.errors.Forbidden)):
            await ctx.send(f"{ctx.author.mention} Forbidden action: `{error.original.text}`")
            return
            
        await ctx.send(f"{ctx.author.mention} {error}")
    
    # only output command messages
    async def on_command(self, ctx):
        if (ctx.command.name == "eval" and checks.is_owner(ctx)):
            return

        await self.bot_utils.output_log(ctx.message)
            
    # TODO: track completed commands for !stats
    async def on_command_completion(self, ctx):
        pass
    
    async def on_message(self, message):
        try:
            if (not message.content or not message.author):
                return
            
            # don't respond to ourselves
            if (message.author == self.user):
                #await self.bot_utils.output_log(message)
                return

            # ignore other bots
            if (message.author.bot):
                return
                
            # TODO: reactions will go here
            
            # process commands
            await self.process_commands(message)

        except discord.errors.Forbidden as e:
            if (e.code == 50013): # missing permissions
                return

            await self.messaging.error_alert(e)

        except Exception as e:
            await self.messaging.error_alert(e)
                
    def run(self):
        super().run(self.token)
        
bot = CBot()
bot.run()
