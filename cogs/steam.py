import discord
from discord.ext import commands

from modules import utils

import asyncio, aiohttp
import re
import random
from lxml import html
from datetime import datetime

class Steam:
    def __init__(self, bot):
        self.bot = bot
        self.steam_api_key = self.bot.CONFIG["steam_api_key"]

        self.steam_url_regex = re.compile(r"((https?:\/\/)(www.)?)?(steamcommunity.com\/(?P<type>id|profiles)\/(?P<id>[A-Za-z0-9]{2,32}))")

    async def on_message(self, message):
        try:
            if (not message.content or not message.author):
                return

            if (self.steam_api_key and self.is_steam_url(message.content.lower())):
                embed = await self.create_steam_embed(message.author, message.content.lower())

                if (embed):
                    await self.bot.send_message(message.channel, embed=embed)

        except Exception as e:
            await self.bot.bot_utils.log_error_to_file(e, prefix="Steam")

    @commands.command(description="game recommendations from your steam profile",
                  brief="game recommendations from your steam profile",
                  pass_context=True)
    async def game(self, ctx, url : str):
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

    async def resolve_vanity_url(self, sid):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=%s&vanityurl=%s" % (self.steam_api_key, sid)) as r:
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

    async def get_profile_summary(self, id64):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=%s&steamids=%s" % (self.steam_api_key, id64)) as r:
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

    async def is_profile_public(self, id64):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=%s&steamids=%s" % (self.steam_api_key, id64)) as r:
                    if (r.status != 200):
                        return False
                        
                    data = await r.json()

                    if ("response" not in data):
                        return False

                    if ("players" not in data["response"]):
                        return False

                    if (len(data["response"]["players"]) == 0):
                        return False

                    summary = data["response"]["players"][0]

                    if ("communityvisibilitystate" not in summary):
                        return False

                    return (summary["communityvisibilitystate"] == 3)
        
        except Exception:
            return False

        return False

    async def get_profile_page(self, id64):
        if (not await self.is_profile_public(id64)):
            return None
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://steamcommunity.com/profiles/%s" % id64) as r:
                if (r.status != 200):
                    return None

                return await r.text()

    async def get_profile_description(self, id64, page=None):
        try:
            if (not page):
                page = await self.get_profile_page(id64)

            if (not page):
                return None
            
            tree = html.fromstring(page)

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

    async def get_friends(self, id64, page=None):
        try:
            if (not page):
                page = await self.get_profile_page(id64)

            if (not page):
                return None
            
            tree = html.fromstring(page)

            path = tree.xpath("//span[@class='profile_count_link_total']/text()")

            if (not path):
                return None

            if (isinstance(path, list)):
                path = path[-1]

            return path.strip()

        except Exception:
            return None

    async def get_games(self, id64):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=%s&steamid=%s&format=json" % (self.steam_api_key, id64)) as r:
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

    async def get_game_name(self, appid):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key=%s&appid=%s" % (self.steam_api_key, appid)) as r:
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

    async def get_game_name_from_store(self, appid):
        game_url = "http://store.steampowered.com/app/" + str(appid)

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

    async def get_num_bans(self, id64):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key=%s&steamids=%s" % (self.steam_api_key, id64)) as r: 
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
    def steamid64_to_32(self, id64):
        y = int(id64) - 76561197960265728
        x = y % 2 
        return "STEAM_0:{}:{}".format(x, (y - x) // 2)

    async def get_account_age(self, id64):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://steamcommunity.com/profiles/%s/badges/1" % id64) as r:
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

    async def get_level(self, id64, page=None):
        try:
            if (not page):
                page = await self.get_profile_page(id64)

            if (not page):
                return None
            
            tree = html.fromstring(page)

            path = tree.xpath("//span[@class='friendPlayerLevelNum']/text()")

            if (not path):
                return None

            if (isinstance(path, list)):
                path = path[0]

            return path.strip()

        except Exception:
            return None

    def is_steam_url(self, string):
        return (self.steam_url_regex.match(string) is not None)

    async def extract_id64(self, url):
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

    async def create_steam_embed(self, user, url):
        id64 = await self.extract_id64(url)

        if (not id64):
            return None

        # get 32-bit steamid
        id32 = self.steamid64_to_32(id64)

        # get profile summary
        profile_summary = await self.get_profile_summary(id64) # profile name gives us "avatarfull" (url to avatar) and "personaname" (username)

        # get profile username
        if ("personaname" in profile_summary):
            username = profile_summary["personaname"]
        else:
            username = "unknown"

        # load profile page
        profile_page = await self.get_profile_page(id64)

        # get profile description
        description = await self.get_profile_description(id64, page=profile_page) # gives us description

        # get number of friends
        num_friends = await self.get_friends(id64, page=profile_page)

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

        level = await self.get_level(id64, page=profile_page)

        # create the embed
        embed = discord.Embed()

        embed.title = username
            
        embed.set_author(name=user.name, icon_url=user.avatar_url)
        
        embed.color = discord.Color.blue()

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

        if (not await self.is_profile_public(id64)):
            embed.set_footer(text="Private profile")

        return embed

def setup(bot):
    bot.add_cog(Steam(bot))