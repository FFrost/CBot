import discord
from discord.ext import commands

from modules import utils

import aiohttp
import re
import random
from lxml import html
from datetime import datetime
from typing import Optional, List

class Steam:
    def __init__(self, bot):
        self.bot = bot
        self.steam_api_key = self.bot.CONFIG["steam_api_key"]

        self.steam_url_regex = re.compile(r"((https?:\/\/)(www.)?)?(steamcommunity.com\/(?P<type>id|profiles)\/(?P<id>[A-Za-z0-9_-]{2,32}))")
        self.steam_workshop_regex = re.compile(r"((https?:\/\/)(www.)?)?(steamcommunity.com\/sharedfiles\/filedetails\/\?id=([0-9]{10}))")

    async def on_message(self, message: discord.Message):
        if (not self.bot.CONFIG["embeds"]["enabled"] or not self.bot.CONFIG["embeds"]["steam"]):
            return

        try:
            if (not message.content or not message.author):
                return

            content = message.content.lower()

            # steam profiles
            if (self.steam_api_key and self.is_steam_url(content)):
                embed = await self.create_steam_embed(message.author, content)

                if (embed):
                    await self.bot.send_message(message.channel, embed=embed)

            # workshop item
            if (self.steam_workshop_regex.match(content) is not None):
                workshop_id = self.steam_workshop_regex.search(content).group(5)

                if (not workshop_id):
                    return

                embed = await self.create_workshop_embed(message.author, workshop_id)

                if (embed):
                    await self.bot.send_message(message.channel, embed=embed)

        except Exception as e:
            self.bot.bot_utils.log_error_to_file(e, prefix="Steam")

    async def create_workshop_embed(self, author: discord.User, workshop_id: str) -> discord.Embed:
        data = await self.get_workshop_details(workshop_id)

        if (not data):
            return None

        embed = discord.Embed(color=discord.Colour.blue())

        try:
            embed.title = data.get("title", "Untitled")

            embed.description = utils.cap_string_and_ellipsis(data.get("description", ""))

            embed.url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}"

            embed.set_thumbnail(url=data["preview_url"]) # TODO: discord doesn't want to embed steam images

            embed.add_field(name=":star: Subscriptions", value=f"{data.get('subscriptions', 0):,}")
            embed.add_field(name=":heart: Favorites", value=f"{data.get('favorited', 0):,}")
            embed.add_field(name=":movie_camera: Views", value=f"{data.get('views', 0):,}")

            upload_time = datetime.fromtimestamp(data.get("time_created"))
            embed.add_field(name=":calendar_spiral: Uploaded", value=utils.format_time(upload_time))

            update_time = datetime.fromtimestamp(data.get("time_updated"))

            if (update_time != upload_time):
                embed.add_field(name=":pencil: Updated", value=utils.format_time(update_time))
            
        except KeyError:
            return None

        return embed

    async def get_workshop_details(self, workshop_id: str) -> dict:
        url = f"https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"

        data = {
            "itemcount": 1,
            "publishedfileids[0]": workshop_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as r:
                    if (r.status != 200):
                        return None
                    
                    summary = await r.json()
                    
                    if (summary is None):
                        return None

                    try:
                        return summary["response"]["publishedfiledetails"][0]

                    except KeyError:
                        return None
        except Exception:
            return None

    @commands.command(description="game recommendations from your steam profile",
                  brief="game recommendations from your steam profile",
                  pass_context=True)
    async def game(self, ctx, url: str):
        if (not self.is_steam_url(url)):
            await self.bot.messaging.reply(ctx.message, "Invalid Steam url")
            return

        id64 = await self.extract_id64(url)

        if (not id64):
            await self.bot.messaging.reply(ctx.message, "Invalid Steam url")
            return

        games = await self.get_games(id64)

        if (not games):
            await self.bot.messaging.reply(ctx.message, "Failed to find games")
            return

        random_game = str(random.choice(games["games"])["appid"])
        random_game_name = await self.get_game_name(random_game)
        game_url = "http://store.steampowered.com/app/" + str(random_game)

        await self.bot.messaging.reply(ctx.message, "You should play **{}**\n{}".format(random_game_name, game_url))

    async def resolve_vanity_url(self, sid: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={self.steam_api_key}&vanityurl={sid}") as r:
                    if (r.status != 200):
                        return None
                    
                    summary = await r.json()
                    
                    if (summary is not None):
                        if ("response" not in summary):
                            return None
                        
                        if ("steamid" not in summary["response"]):
                            return None
                        
                        return summary["response"]["steamid"]
            
        except Exception:
            return None

    async def get_profile_summary(self, id64: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.steam_api_key}&steamids={id64}") as r:
                    if (r.status != 200):
                        return None
                    
                    summary = await r.json()
            
                    if summary is not None:
                        if ("response" not in summary):
                            return None
                        
                        if ("players" not in summary["response"]):
                            return None
                        
                        if (len(summary["response"]["players"][0]) <= 0):
                            return None
            
                        return summary["response"]["players"][0]

        except Exception:
            return None

    @staticmethod
    def is_profile_public(profile_summary: dict) -> bool:
        if (profile_summary is None):
            return False
        
        if ("communityvisibilitystate" not in profile_summary):
            return False

        return (profile_summary["communityvisibilitystate"] == 3)

    async def get_profile_page(self, id64: str) -> Optional[str]:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://steamcommunity.com/profiles/%s" % id64) as r:
                if (r.status != 200):
                    return None

                return await r.text()

    async def get_profile_description(self, id64: str, tree: html.HtmlElement) -> Optional[str]:
        try:
            # replace line breaks with newlines
            for br in tree.xpath("*//br"):
                br.tail = "\n" + br.tail if br.tail else "\n"

            # div class can be "profile_summary" or "profile_summary noexpand"
            path = tree.xpath("//div[starts-with(@class, 'profile_summary')]")
            
            if (not path):
                return None

            if (isinstance(path, list)):
                path = path[0]

            return path.text_content().strip()

        except Exception:
            return None

    async def get_friends(self, id64: str, tree: html.HtmlElement) -> Optional[str]:
        try:
            path = tree.xpath("//span[@class='profile_count_link_total']/text()")

            if (not path):
                return None

            if (isinstance(path, list)):
                path = path[-1]

            return path.strip()

        except Exception:
            return None

    async def get_games(self, id64: str) -> Optional[List[dict]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.steam_api_key}&steamid={id64}&format=json") as r:
                    if (r.status != 200):
                        return None
                    
                    games = await r.json()
            
                    if games is not None:
                        if ("response" not in games):
                            return None
                        
                        if ("game_count" not in games["response"] or "games" not in games["response"]):
                            return None

                        return games["response"]

        except Exception:
            return None

    async def get_game_name(self, appid: int) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key={self.steam_api_key}&appid={appid}") as r:
                    if (r.status != 200):
                        return await self.get_game_name_from_store(appid)
                    
                    data = await r.json()
            
                    if data is not None:
                        if ("game" not in data):
                            return await self.get_game_name_from_store(appid)
                        
                        if ("gameName" not in data["game"]):
                            return await self.get_game_name_from_store(appid)

                        if (data["game"]["gameName"] == ""):
                            return await self.get_game_name_from_store(appid)
                        
                        if (data["game"]["gameName"].startswith("ValveTestApp")):
                            return await self.get_game_name_from_store(appid)
                        
                        return data["game"]["gameName"]

        except Exception:
            return await self.get_game_name_from_store(appid)

    async def get_game_name_from_store(self, appid: int) -> str:
        game_url = f"http://store.steampowered.com/app/{appid}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(game_url) as r:
                    if (r.status != 200):
                        return "unknown"

                    tree = html.fromstring(await r.text())

                    path = tree.xpath("//title/text()")
                    
                    if (not path):
                        return "unknown"
                    
                    if (isinstance(path, list)):
                        path = path[0]

                    return path.strip().replace(" on Steam", "")

        except Exception:
            return "unknown"

    async def get_num_bans(self, id64: str) -> int:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={self.steam_api_key}&steamids={id64}") as r:
                    if (r.status != 200):
                        return 0
                    
                    bans = await r.json()
            
                    if (bans is None):
                        return 0
                    
                    if (not "players" in bans):
                        return 0
                    
                    if (len(bans) < 1):
                        return 0
                    
                    data = bans["players"][0]
                    
                    num_game_bans = int(data["NumberOfGameBans"])
                    num_vac_bans = int(data["NumberOfVACBans"])
                            
                    return (num_game_bans + num_vac_bans)
        
        except Exception:
            return 0

    # thanks to https://stackoverflow.com/a/36472887
    @staticmethod
    def steamid64_to_32(id64: str) -> str:
        y = int(id64) - 76561197960265728
        x = y % 2
        return "STEAM_0:{}:{}".format(x, (y - x) // 2)

    async def get_account_age(self, id64: str) -> Optional[int]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://steamcommunity.com/profiles/{id64}/badges/1") as r:
                    if (r.status != 200):
                        return None
                    
                    tree = html.fromstring(await r.text())

                    path = tree.xpath("//div[@class='badge_description']/text()")

                    if (not path):
                        return None

                    if (isinstance(path, list)):
                        path = path[0]

                    date = path.strip().replace("Member since ", "")[:-1]
                    
                    now = datetime.now()
                    age = datetime.strptime(date, "%d %B, %Y")
                    
                    return (now.year - age.year) - (1 if now.month < age.month else 0)
        
        except Exception:
            return None

    async def get_level(self, id64: str, tree: html.HtmlElement) -> Optional[str]:
        try:
            path = tree.xpath("//span[@class='friendPlayerLevelNum']/text()")

            if (not path):
                return None

            if (isinstance(path, list)):
                path = path[0]

            return path.strip()

        except Exception:
            return None

    def is_steam_url(self, string: str) -> bool:
        return (self.steam_url_regex.match(string) is not None)

    async def extract_id64(self, url: str) -> Optional[str]:
        search = self.steam_url_regex.search(url)
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
            id64 = await self.resolve_vanity_url(url_id)

        return id64

    async def create_steam_embed(self, user: discord.User, url: str) -> discord.Embed:
        id64 = await self.extract_id64(url)

        if (not id64):
            return None

        # get 32-bit steamid
        id32 = self.steamid64_to_32(id64)

        # get profile summary
        profile_summary = await self.get_profile_summary(id64) # profile name gives us "avatarfull" (url to avatar) and "personaname" (username)

        # get profile username
        if (profile_summary is not None and "personaname" in profile_summary):
            username = profile_summary["personaname"]
        else:
            username = "unknown"

        profile_is_visible = self.is_profile_public(profile_summary)

        description = None
        num_friends = None
        level = None

        # we can only see this if the profile is public
        if (profile_is_visible):
            # load profile page
            profile_page = await self.get_profile_page(id64)

            tree = html.fromstring(profile_page)

            # get profile description
            description = await self.get_profile_description(id64, tree) # gives us description

            # get number of friends
            num_friends = await self.get_friends(id64, tree)

            # account level
            level = await self.get_level(id64, tree)

        # get number of games
        games = await self.get_games(id64)

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
                    game_name = await self.get_game_name(most_played_game)
            
            except Exception:
                game_name = None
                most_played_game_time = 0

        # find number of bans
        num_bans = await self.get_num_bans(id64)

        if (not num_bans):
            num_bans = 0
        else:
            num_bans = int(num_bans)

        # get account age
        account_age = await self.get_account_age(id64)

        # create the embed
        embed = discord.Embed(color=discord.Color.blue())

        embed.title = username
            
        embed.set_author(name=user.name, icon_url=user.avatar_url)

        embed.url = f"https://steamcommunity.com/profiles/{id64}"

        if (description):
            embed.description = utils.cap_string_and_ellipsis(description, 240)

        if ("avatarfull" in profile_summary):
            embed.set_thumbnail(url=profile_summary["avatarfull"])

        embed.add_field(name="SteamID64", value=id64)
        embed.add_field(name="SteamID32", value=id32)

        if (num_friends):
            embed.add_field(name="Friends", value=num_friends)

        if (num_games):
            embed.add_field(name="Games Owned", value="{:,}".format(int(num_games)))

        if (game_name):
            embed.add_field(name="Most Played Game", value=utils.cap_string_and_ellipsis(game_name, 32, 1))
            embed.add_field(name="Hours", value="{:,}".format(most_played_game_time))
        
        if (account_age):
            plural = "year" + ("" if account_age == 1 else "s")
            embed.add_field(name="Account Age", value="{:,} {}".format(account_age, plural))

        if (num_bans > 0):
            embed.add_field(name="Bans", value="{:,}".format(num_bans))

        if (level):
            embed.add_field(name="Level", value="{:,}".format(int(level)))

        if (not profile_is_visible):
            embed.set_footer(text="Private profile")

        return embed

def setup(bot):
    bot.add_cog(Steam(bot))