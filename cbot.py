import discord
from discord.ext import commands

import default_config
from modules import bot_utils, utils, enums, messaging, misc, checks

import logging, os, traceback, glob, yaml, sys, atexit, psutil, importlib
from random import randint
from datetime import datetime

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
        
        self.bot_restart_arg = "-restarted"
        self.bot_manager_arg = "-manager"

        self.REQUIRED_PERMISSIONS = ["add_reactions", "attach_files", "embed_links", "read_message_history",
                                    "read_messages", "send_messages"]
        self.VOICE_PERMISSIONS = ["connect", "speak"]
        self.OPTIONAL_PERMISSIONS = ["manage_messages", "move_members"]
        
        self.token = ""
        self.dev_id = ""
        self.REAL_FILE = os.path.realpath(__file__)
        self.REAL_PATH = os.path.dirname(self.REAL_FILE)
        self.TOKEN_PATH = f"{self.REAL_PATH}/cbot.yml"

        self.ERROR_FILEPATH = f"{self.REAL_PATH}/cbot_errors.txt"

        # check if cbot exited properly on last run
        self.PID_FILEPATH = "/tmp/cbot.pid"

        if (os.path.exists(self.PID_FILEPATH)):
            with open(self.PID_FILEPATH, "r") as f:
                pid = int(f.read())
            
            if (psutil.pid_exists(pid)):
                print("Another instance of CBot is already running, exiting...")
                sys.exit()
            else:
                print("CBot crashed on last run, see error log at", self.ERROR_FILEPATH)
                os.unlink(self.PID_FILEPATH)

        with open(self.PID_FILEPATH, "w") as f:
            f.write(str(os.getpid()))
        
        print("Created PID file at", self.PID_FILEPATH)

        self.get_token()

        self.CONFIG = {}
        self.CONFIG_PATH = self.REAL_PATH + "/config.yml"
        
        self.load_config()

        # remove any leftover files in the youtubedl download directory
        self.cleanup_youtubedl_directory()

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

        atexit.register(self.on_exit)

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
            if (set(data.keys()) == set(disk_config.keys())):
                self.CONFIG = disk_config
                print("Loaded config from file")
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
        try:
            with open(self.CONFIG_PATH, "r") as f:  
                return yaml.load(f)

        except yaml.scanner.ScannerError as e:
            print("Config file could not be loaded (scanner error), make sure config.yml is formatted properly: {}".format(e))
            return None

        except Exception as e:
            print("Config file could not be loaded (general error): {}".format(e))
            return None

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
            self.uptime = datetime.now()

        print("Logged in as {name}#{disc} [{uid}]".format(name=self.user.name, disc=self.user.discriminator, uid=self.user.id))
        
        await self.change_presence(game=discord.Game(name="!help for info"))
        await self.print_bot_info()
        
        print("CBot ready!")
        
        if (self.bot_restart_arg in sys.argv):
            await self.messaging.message_developer("CBot restarted successfully")
        elif (self.bot_manager_arg in sys.argv):
            await self.messaging.message_developer("CBot was restarted by the manager")
    
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
        elif (isinstance(error, commands.NoPrivateMessage)):
            await self.messaging.reply(ctx.message, "This command can't be used in private messages")
            return
        elif (hasattr(error, "original") and isinstance(error.original, discord.errors.Forbidden)):
            await self.messaging.reply(ctx.message, f"Forbidden action: `{error.original.text}`")
            return
            
        await self.messaging.reply(ctx, error)
    
    # only output command messages
    async def on_command(self, command, ctx):
        if (command.name == "eval" and checks.is_owner(ctx)):
            return

        await self.bot_utils.output_log(ctx.message)
            
    # TODO: track completed commands for !stats
    async def on_command_completion(self, command, ctx):
        pass
    
    async def on_message(self, message):
        try:
            if (not message.content or not message.author):
                return
            
            # don't respond to ourselves
            if (message.author == self.user):
                #await self.bot_utils.output_log(message)
                return
            
            # insult anyone who @s us
            if (self.user in message.mentions and not message.mention_everyone and not message.content.startswith("!")):
                await self.bot_utils.output_log(message)
                
                if (self.CONFIG["should_insult"]):
                    insult = await self.misc.get_insult()
                    an = "an" if (insult[0].lower() in "aeiou") else "a"
                    await self.messaging.reply(message, "you're {an} {insult}.".format(an=an, insult=insult))
            
            # respond to "^ this", "this", "^", etc.
            if (self.CONFIG["should_this"]):
                if (message.content.startswith("^") or message.content.lower() == "this"):
                    if (message.content == "^" or "this" in message.content.lower()):
                        this_msg = "^"
                        
                        if (randint(0, 100) < 50):
                            this_msg = "^ this"
                        
                        await self.bot_utils.output_log(message)
                        await self.send_message(message.channel, this_msg)
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

            perms = dict(server.me.server_permissions)
            all_perms = self.REQUIRED_PERMISSIONS + self.VOICE_PERMISSIONS + self.OPTIONAL_PERMISSIONS
            perms_we_dont_have = []

            for perm in all_perms:
                if (not perms[perm]):
                    perms_we_dont_have.append(perm)

            msg = f"Hi, thanks for adding me to your server `{server.name}`. The minimum permissions I need to function are " \
                  f"{', '.join([f'`{p}`' for p in self.REQUIRED_PERMISSIONS]).replace('_', ' ')}.\n" \
                  f"For voice support, I need {', '.join([f'`{p}`' for p in self.VOICE_PERMISSIONS]).replace('_', ' ')} in the voice channel you want me to join.\n" \
                  f"For additional commands, I need {', '.join([f'`{p}`' for p in self.OPTIONAL_PERMISSIONS]).replace('_', ' ')}\n"

            msg += (f"I currently don't have `{', '.join(perms_we_dont_have).replace('_', ' ')}` permissions."
                    if (len(perms_we_dont_have) > 0) else
                    "I have all the permissions I need. Thanks!")

            await self.send_message(server.owner, msg)
        
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
