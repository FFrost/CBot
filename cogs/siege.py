import discord
from discord.ext import commands

import asyncio
import aiohttp
import datetime
import time
import base64
import iso8601
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timezone
from math import ceil

class NoLoginInfo(Exception):
    pass

class LoginFailure(Exception):
    pass

class UnauthorizedError(Exception):
    pass

class RateLimited(Exception):
    pass

class UbisoftAPI:
    def __init__(self, loop, *args, **kwargs):
        if (kwargs.get("ticket")):
            self._initialAuth = f"Basic {kwargs.get('ticket')}"
        elif ("email" in kwargs and "password" in kwargs):
            self._initialAuth = self._generateTicket(kwargs.get("email"), kwargs.get("password"))
        else:
            raise NoLoginInfo("No ticket or email/password combo provided")
        
        self._UBI_APP_ID = "39baebad-39e5-4552-8c25-2c9b919064e2"

        self._headers = {
            "Authorization": self._initialAuth,
            "Ubi-Appid": self._UBI_APP_ID
        }

        self._platforms = {
            "uplay": {
                "id": "5172a557-50b5-4665-b7db-e3f2e8c5041d",
                "name": "PC"
            },
            "psn": {
                "id": "05bfb3f7-6c21-4c42-be1f-97a33fb5cf66",
                "name": "PS4"
            },
            "xbl": {
                "id": "98a601e5-ca91-4440-b1c5-753f601a2c90",
                "name": "XBOXONE"
            }
        }

        self._regions = ["emea", "ncsa", "apac"]

        self._statsTypes = ["ranked", "casual", "overall", "operator"]

        self._statsList = [
            "casualpvp_death",
            "casualpvp_kdratio",
            "casualpvp_kills",
            "casualpvp_matchlost",
            "casualpvp_matchplayed",
            "casualpvp_matchwlratio",
            "casualpvp_matchwon",
            "casualpvp_timeplayed",

            "generalpvp_accuracy",
            "generalpvp_bulletfired",
            "generalpvp_bullethit",
            "generalpvp_death",
            "generalpvp_headshot",
            "generalpvp_kdratio",
            "generalpvp_killassists",
            "generalpvp_kills",
            "generalpvp_matchlost",
            "generalpvp_matchplayed",
            "generalpvp_matchwlratio",
            "generalpvp_matchwon",
            "generalpvp_meleekills",
            "generalpvp_penetrationkills",
            "generalpvp_revive",
            "generalpvp_suicide",
            "generalpvp_timeplayed",

            "rankedpvp_death",
            "rankedpvp_kdratio",
            "rankedpvp_kills",
            "rankedpvp_matchlost",
            "rankedpvp_matchplayed",
            "rankedpvp_matchwlratio",
            "rankedpvp_matchwon",
            "rankedpvp_timeplayed",
            ]

        self._operatorStatsList = [
            "operatorpvp_kills",
            "operatorpvp_death",
            "operatorpvp_roundwon",
            "operatorpvp_roundlost",
            "operatorpvp_meleekills",
            "operatorpvp_headshot",
            "operatorpvp_timeplayed"
        ]

        self.loop = loop
        self._session = aiohttp.ClientSession(loop=loop)

        self._rateLimitCooldown = 120

    async def _post(self, url: str, payload: dict, headers: dict = None) -> dict:
        if (hasattr(self, "rateLimitedTime")):
            if (self.rateLimitedTime > time.time()):
                print(f"Rate limited for {self.rateLimitedTime - time.time():.2f} more seconds")
                return None

        if (self._has_expired()):
            await self.login(relog=True)
        
        async with self._session.post(url, json=payload, headers=(headers if headers is not None else payload)) as r:
            try:
                data = await r.json()
            except Exception:
                return None
            
            if (r.status != 200):
                if (r.status == 401):
                    raise UnauthorizedError(data.get("message", "POST Unauthorized error"))
            
            return data

        return None

    async def _get(self, url: str, payload: dict = None, headers: dict = None) -> dict:
        if (hasattr(self, "rateLimitedTime")):
            if (self.rateLimitedTime > time.time()):
                print(f"Rate limited for {self.rateLimitedTime - time.time():.2f} more seconds")
                return None

        if (payload is None):
            payload = self._headers

        if (self._has_expired()):
            await self.login(relog=True)
        
        async with self._session.get(url, json=payload, headers=(headers if headers is not None else payload)) as r:
            try:
                data = await r.json()
            except Exception:
                return None
            
            if (r.status != 200):
                if (r.status == 401):
                    raise UnauthorizedError(data.get("message", "GET Unauthorized error"))
            
            return data

        return None

    def _parse_expiration(self, expiration: str) -> datetime:
        return iso8601.parse_date(expiration)

    def _has_expired(self) -> bool:
        if (not hasattr(self, "_expiration")):
            return False
        
        return (datetime.now(timezone.utc) > self._expiration)

    def _generateTicket(self, email: str, password: str) -> str:
        return f"Basic {base64.b64encode(bytes(f'{email}:{password}'.encode('ascii'))).decode('ascii')}"

    async def login(self, relog: bool = False) -> None:
        if (relog):
            self._headers.update({"Authorization": self._initialAuth})

        data = await self._post("https://uplayconnect.ubi.com/ubiservices/v2/profiles/sessions", self._headers)

        if ("errorCode" in data):
            if (data["errorCode"] == 1100): # rate limited
                self.rateLimitedTime = time.time() + self._rateLimitCooldown
                self._rateLimitCooldown += 30 # incremement every time we fail to login

                raise RateLimited(f"Rate limited for {self.rateLimitedTime - time.time():.2f} more seconds")

            raise LoginFailure(f"Login error {data['errorCode']}: {data['message']}")

        try:
            self._headers.update({
                "Ubi-SessionId": data["sessionId"],
                "Authorization": data["Authorization"] if "Authorization" in data else f"Ubi_v1 t={data['ticket']}"
                })

            self._expiration = self._parse_expiration(data["expiration"])

            self._rateLimitCooldown = 120 # set back to default on successful login

            if (not hasattr(self, "_operatorData")):
                await self._loadOperatorData()
        except KeyError:
            raise LoginFailure("Recieved unexpected response")

    async def retry(self, retriesRemaining: int = 5) -> bool:
        if (retriesRemaining <= 0):
            return False

        try:
            await self.login(relog=True)
            return True
        except LoginFailure as e:
            print(e)
            return False
        except RateLimited as e:
            print(e)
            await asyncio.sleep(self.rateLimitedTime)
            return await self.retry(retriesRemaining - 1)

    async def getProfile(self, userID: str) -> dict:
        data = await self._get(f"https://public-ubiservices.ubi.com/v2/profiles?userId={userID}")
        return data

    async def searchPlayers(self, username: str, platform: str = "uplay") -> Optional[dict]:
        data = await self._get(f"https://public-ubiservices.ubi.com/v2/profiles?nameOnPlatform={username}&platformType={platform}")

        try:
            return data["profiles"]
        except (KeyError, TypeError):
            return None

    def _getRequestUrl(self, platform: str) -> str:
        return (f"https://public-ubiservices.ubi.com/v1/spaces/{self._platforms[platform]['id']}/sandboxes/"
                f"OSBOR_{self._platforms[platform]['name']}_LNCH_A")

    async def getLevel(self, profile: dict) -> int:
        userID = profile["userId"]
        platform = profile["platformType"]
        url = f"{self._getRequestUrl(platform)}/r6playerprofile/playerprofile/progressions?profile_ids={userID}"
        data = await self._get(url)

        try:
            return int(data["player_profiles"][0]["level"])
        except (KeyError, TypeError):
            return 0

        return 0

    async def getRankData(self, profile: dict, region: str = "ncsa", season: int = -1) -> Optional[dict]:
        userID = profile["userId"]
        platform = profile["platformType"]
        url = f"{self._getRequestUrl(platform)}/r6karma/players?board_id=pvp_ranked&region_id={region}&season_id={season}&profile_ids={userID}"
        data = await self._get(url)

        try:
            return data["players"][userID]
        except (KeyError, TypeError):
            return None

        return None

    async def getStatsData(self, profile: dict) -> Optional[dict]:
        userID = profile["userId"]
        platform = profile["platformType"]
        url = f"{self._getRequestUrl(platform)}/playerstats2/statistics?populations={userID}&statistics={','.join(self._statsList)}"
        data = await self._get(url)

        try:
            return data["results"][userID]
        except KeyError:
            return None

        return None

    def getRankName(self, mmr: int) -> str:
        if (mmr <= 1399):
            return "Copper IV"
        elif (1399 < mmr <= 1499):
            return "Copper III"
        elif (1499 < mmr <= 1599):
            return "Copper II"
        elif (1599 < mmr <= 1699):
            return "Copper I"
        elif (1699 < mmr <= 1799):
            return "Bronze IV"
        elif (1799 < mmr <= 1899):
            return "Bronze III"
        elif (1899 < mmr <= 1999):
            return "Bronze II"
        elif (1999 < mmr <= 2099):
            return "Bronze I"
        elif (2099 < mmr <= 2199):
            return "Silver IV"
        elif (2199 < mmr <= 2299):
            return "Silver III"
        elif (2299 < mmr <= 2399):
            return "Silver II"
        elif (2399 < mmr <= 2499):
            return "Silver I"
        elif (2499 < mmr <= 2699):
            return "Gold IV"
        elif (2699 < mmr <= 2899):
            return "Gold III"
        elif (2899 < mmr <= 3099):
            return "Gold II"
        elif (3099 < mmr <= 3299):
            return "Gold I"
        elif (3299 < mmr <= 3699):
            return "Platinum III"
        elif (3699 < mmr <= 4099):
            return "Platinum II"
        elif (4099 < mmr <= 4499):
            return "Platinum I"
        elif (4499 < mmr):
            return "Diamond"

        return "Unknown"

    async def _loadOperatorData(self) -> Optional[dict]:
        url = "https://ubistatic-a.akamaihd.net/0058/prod/assets/data/operators.3a2655c8.json"
        data = await self._get(url)

        try:
            data["recruit_sas"] = {
                "id": "Recruit (SAS)",
                "index": "1:1",
                "category": "atk_def"
            }

            data["recruit_fbi"] = {
                "id": "Recruit (FBI)",
                "index": "1:2",
                "category": "atk_def"
            }

            data["recruit_gign"] = {
                "id": "Recruit (GIGN)",
                "index": "1:3",
                "category": "atk_def"
            }

            data["recruit_spetsnaz"] = {
                "id": "Recruit (Spetsnaz)",
                "index": "1:4",
                "category": "atk_def"
            }

            data["recruit_gsg"] = {
                "id": "Recruit (GSG 9)",
                "index": "1:5",
                "category": "atk_def"
            }
            
        except (KeyError, TypeError):
            pass

        self._operatorData = data
        return data

    async def getOperatorStats(self, profile: dict) -> Optional[dict]:
        if (not hasattr(self, "_operatorData") or self._operatorData is None):
            await self._loadOperatorData()

        if (self._operatorData is None):
            return None
        
        userID = profile["userId"]
        platform = profile["platformType"]
        url = f"{self._getRequestUrl(platform)}/playerstats2/statistics?populations={userID}&statistics={','.join(self._operatorStatsList)}"
        data = await self._get(url)

        try:
            return data["results"][userID]
        except KeyError:
            return None

        return None

    def sortOperatorData(self, data: dict) -> dict:
        ret = {
            "death": [],
            "headshot": [],
            "kills": [],
            "meleekills": [],
            "roundlost": [],
            "roundwon": [],
            "timeplayed": []
        }

        for stat, value in data.items():
            stat = stat.replace("operatorpvp_", "").replace(":infinite", "")
            split = stat.find(":")

            statName = stat[:split]
            operatorIndex = stat[split + 1:]

            ret[statName].append([operatorIndex, value])

        for key, dataList in ret.items():
            ret[key] = sorted(dataList, key=lambda k: k[1], reverse=True)

        return ret

    def getOperatorName(self, index: str) -> str:
        if (not hasattr(self, "_operatorData") or self._operatorData is None):
            return "Unknown"

        for op, data in self._operatorData.items():
            if (data["index"] == index):
                return op.capitalize()

        return "Unknown"

    def findAtkAndDefOperators(self, opData: list) -> Tuple[Optional[List[Dict[str, int]]], Optional[List[Dict[str, int]]]]:
        mostPlayedAttacker, mostPlayedDefender = None, None

        if (not hasattr(self, "_operatorData") or self._operatorData is None):
            return mostPlayedAttacker, mostPlayedDefender

        for operator in opData:
            for _op, data in self._operatorData.items():
                if (not mostPlayedAttacker and data["index"] == operator[0] and "atk" in data["category"]):
                    mostPlayedAttacker = operator
                elif (not mostPlayedDefender and data["index"] == operator[0] and "def" in data["category"]):
                    mostPlayedDefender = operator
                
                if (mostPlayedAttacker is not None and mostPlayedDefender is not None):
                    return mostPlayedAttacker, mostPlayedDefender

        return mostPlayedAttacker, mostPlayedDefender

class Siege:
    def __init__(self, bot):
        self.bot = bot

        self.SIEGE_CACHE = {}
        self.remove_siege_cache_task = self.bot.loop.create_task(self.remove_siege_cache())

        try:
            email = self.bot.CONFIG["siege"].get("email")
            password = self.bot.CONFIG["siege"].get("password")
            ticket = self.bot.CONFIG["siege"].get("ticket")

            if (not email and not password and not ticket):
                raise NoLoginInfo

            self.ubi = UbisoftAPI(self.bot.loop, email=email, password=password, ticket=ticket)
            self._login_task = self.bot.loop.run_until_complete(self.ubi.login())
        except NoLoginInfo:
            print("No Ubisoft login info provided for Siege stats command, disabling command")
            self.siege.enabled = False
        except LoginFailure as e:
            print(f"Failed to log in to Ubisoft servers: {e}")
            result = self.bot.loop.run_until_complete(self.ubi.retry())
            self.siege.enabled = result
        except UnauthorizedError as e:
            print(f"Failed to log in to Ubisoft servers: {e}")
            self.siege.enabled = False

    def __unload(self):
        self.bot.loop.create_task(self.ubi._session.close())
        self.remove_siege_cache_task.cancel()

    def create_siege_embed(self, user: discord.User, profile: dict, statsType: str, stats: dict, rankedData: dict, level: int, operatorData: dict) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=user.name, icon_url=user.avatar_url)
        embed.title = profile["nameOnPlatform"]
        embed.set_footer(text=f"{self.ubi._platforms[profile['platformType']]['name']} | {statsType.capitalize()} stats | UserID: {profile['userId']}")

        if (statsType == "ranked"):
            embed.add_field(name=":medal: Win/Loss Ratio", value=f"{stats['rankedpvp_matchwon:infinite'] / (stats['rankedpvp_matchlost:infinite'] + stats['rankedpvp_matchwon:infinite']):.2%}")
            embed.add_field(name=":trophy: Wins", value=f"{stats['rankedpvp_matchwon:infinite']:,}")
            embed.add_field(name=":second_place: Losses", value=f"{stats['rankedpvp_matchlost:infinite']:,}")
            embed.add_field(name=":skull_crossbones: K/D Ratio", value=f"{stats['rankedpvp_kills:infinite'] / stats['rankedpvp_death:infinite']:.2f}")
            embed.add_field(name=":gun: Kills", value=f"{stats['rankedpvp_kills:infinite']:,}")
            embed.add_field(name=":skull: Deaths", value=f"{stats['rankedpvp_death:infinite']:,}")
            embed.add_field(name="MMR", value=f"{ceil(rankedData['mmr'])}")
            embed.add_field(name="Max MMR", value=f"{ceil(rankedData['max_mmr'])}")
            embed.add_field(name="Rank", value=f"{self.ubi.getRankName(ceil(rankedData['mmr']))}")
            embed.add_field(name="Max Rank", value=f"{self.ubi.getRankName(ceil(rankedData['max_mmr']))}")
            embed.add_field(name=":video_game: Matches Played", value=f"{stats['rankedpvp_matchplayed:infinite']:,}")
            embed.add_field(name=":stopwatch: Playtime", value=f"{stats['rankedpvp_timeplayed:infinite'] / 3600:,.0f} hours")
        elif (statsType == "casual"):
            embed.add_field(name=":medal: Win/Loss Ratio", value=f"{stats['casualpvp_matchwon:infinite'] / (stats['casualpvp_matchlost:infinite'] + stats['casualpvp_matchwon:infinite']):.2%}")
            embed.add_field(name=":trophy: Wins", value=f"{stats['casualpvp_matchwon:infinite']:,}")
            embed.add_field(name=":second_place: Losses", value=f"{stats['casualpvp_matchlost:infinite']:,}")
            embed.add_field(name=":skull_crossbones: K/D Ratio", value=f"{stats['casualpvp_kills:infinite'] / stats['casualpvp_death:infinite']:.2f}")
            embed.add_field(name=":gun: Kills", value=f"{stats['casualpvp_kills:infinite']:,}")
            embed.add_field(name=":skull: Deaths", value=f"{stats['casualpvp_death:infinite']:,}")
            embed.add_field(name=":video_game: Matches Played", value=f"{stats['casualpvp_matchplayed:infinite']:,}")
            embed.add_field(name=":stopwatch: Playtime", value=f"{stats['casualpvp_timeplayed:infinite'] / 3600:,.0f} hours")
        elif (statsType == "overall"):
            embed.add_field(name=":gun: Accuracy", value=f"{stats['generalpvp_bullethit:infinite'] / stats['generalpvp_bulletfired:infinite']:.2%}")
            embed.add_field(name=":skull_crossbones: Headshot %", value=f"{stats['generalpvp_headshot:infinite'] / stats['generalpvp_bulletfired:infinite']:.2%}")
            embed.add_field(name="Penetration Kills", value=f"{stats['generalpvp_penetrationkills:infinite']:,}")
            embed.add_field(name=":skull: Suicides", value=f"{stats['generalpvp_suicide:infinite']:,}")
            embed.add_field(name=":syringe: Revives", value=f"{stats['generalpvp_revive:infinite']:,}")
            embed.add_field(name=":handshake: Assists", value=f"{stats['generalpvp_killassists:infinite']:,}")
            embed.add_field(name=":knife: Melee Kills", value=f"{stats['generalpvp_meleekills:infinite']:,}")
            embed.add_field(name=":military_medal: Level", value=f"{level:,}")
            embed.add_field(name=":video_game: Total Playtime", value=f"{stats['generalpvp_timeplayed:infinite'] // 3600:,.0f} hours")
        elif (statsType == "operator"):
            opData = self.ubi.sortOperatorData(operatorData)

            mostPlayedAttacker, mostPlayedDefender = self.ubi.findAtkAndDefOperators(opData["timeplayed"])

            if (not mostPlayedAttacker):
                mostPlayedAttacker = (["1:1"], 0)
            
            if (not mostPlayedDefender):
                mostPlayedDefender = (["1:2"], 0)

            mostKills = opData["kills"][0]
            mostDeaths = opData["death"][0]
            mostHeadshots = opData["headshot"][0]
            mostMeleeKills = opData["meleekills"][0]
            mostRoundsWon = opData["roundwon"][0]
            mostRoundsLost = opData["roundlost"][0]

            embed.add_field(name="Most Played Attacker", value=f"{self.ubi.getOperatorName(mostPlayedAttacker[0])} ({mostPlayedAttacker[1] / 3600:,.0f} hours)")
            embed.add_field(name="Most Played Defender", value=f"{self.ubi.getOperatorName(mostPlayedDefender[0])} ({mostPlayedDefender[1] / 3600:,.0f} hours)")
            embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")
            embed.add_field(name="Most Kills", value=f"{self.ubi.getOperatorName(mostKills[0])} ({mostKills[1]:,})")
            embed.add_field(name="Most Deaths", value=f"{self.ubi.getOperatorName(mostDeaths[0])} ({mostDeaths[1]:,})")
            embed.add_field(name="Most Headshots", value=f"{self.ubi.getOperatorName(mostHeadshots[0])} ({mostHeadshots[1]:,})")
            embed.add_field(name="Most Melee Kills", value=f"{self.ubi.getOperatorName(mostMeleeKills[0])} ({mostMeleeKills[1]:,})")
            embed.add_field(name="Most Rounds Won", value=f"{self.ubi.getOperatorName(mostRoundsWon[0])} ({mostRoundsWon[1]:,})")
            embed.add_field(name="Most Rounds Lost", value=f"{self.ubi.getOperatorName(mostRoundsLost[0])} ({mostRoundsLost[1]:,})")

        return embed

    @commands.command(description="finds Rainbow Six: Siege stats for a user",
                      brief="finds Rainbow Six: Siege stats for a user",
                      pass_context=True,
                      aliases=["r6s", "r6stats"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def siege(self, ctx, username: str, statsType: str = "ranked", platform: str = "uplay", region: str = "ncsa"):
        await self.bot.send_typing(ctx.message.channel)

        if (statsType not in self.ubi._statsTypes):
            await self.bot.messaging.reply(ctx.message, f"Invalid platform, options are: `{', '.join(self.ubi._statsTypes)}`")
            return

        if (platform.lower() not in self.ubi._platforms.keys()):
            await self.bot.messaging.reply(ctx.message, f"Invalid platform, options are: `{', '.join(self.ubi._platforms.keys())}`")
            return

        if (region.lower() not in self.ubi._regions):
            await self.bot.messaging.reply(ctx.message, f"Invalid platform, options are: `{', '.join(self.ubi._regions)}`")
            return

        if (hasattr(self.ubi, "rateLimitedTime")):
            if (self.ubi.rateLimitedTime > time.time()):
                await self.bot.messaging.reply(ctx.message, f"Can't fetch stats, rate limited by Ubisoft for {self.ubi.rateLimitedTime - time.time():.2f} more seconds")
                return

        if (username in self.SIEGE_CACHE and platform in self.SIEGE_CACHE[username]):
            data = self.SIEGE_CACHE[username][platform]
            profile = data["profile"]
            level = data["level"]

            if (region in data):
                rankedData = data[region]
            else:
                try:
                    rankedData = await self.ubi.getRankData(profile, region)
                except (UnauthorizedError, LoginFailure) as e:
                    await self.bot.messaging.reply(ctx.message, f"An error occured getting stats for player `{username}` on `{platform}`: {e}")
                    return

            statsData = data["statsData"]

            operatorData = data["operatorData"]

            self.SIEGE_CACHE[username]["time"] = time.time()
        else:
            try:
                profiles = await self.ubi.searchPlayers(username, platform)
            
                if (not profiles):
                    await self.bot.messaging.reply(ctx.message, f"Failed to find player `{username}` on `{platform}`")
                    return

                profile = profiles[0] # TODO: show list?

                level = await self.ubi.getLevel(profile)

                rankedData = await self.ubi.getRankData(profile, region)

                statsData = await self.ubi.getStatsData(profile)

                operatorData = await self.ubi.getOperatorStats(profile)
            except (UnauthorizedError, LoginFailure) as e:
                await self.bot.messaging.reply(ctx.message, f"An error occured getting stats for player `{username}` on `{platform}`: {e}")
                return

        if (not rankedData or not statsData):
            await self.bot.messaging.reply(ctx.message, f"Failed to find stats for `{username}` on `{platform}`")
            return

        embed = self.create_siege_embed(ctx.message.author, profile, statsType, statsData, rankedData, level, operatorData)
        await self.bot.say(embed=embed)

        self.SIEGE_CACHE[username] = {
            platform: {
                "profile": profile,
                "level": level,
                region: rankedData,
                "statsData": statsData,
                "operatorData": operatorData
            },
            "time": time.time()
        }

    async def remove_siege_cache(self) -> None:
        await self.bot.wait_until_ready()
        
        while (not self.bot.is_closed):
            try:
                siege_cache_copy = self.SIEGE_CACHE.copy()
                
                for username, cache in siege_cache_copy.items():
                    if (time.time() > cache["time"] + self.bot.CONFIG["siege"]["cache_time"]):
                        del self.SIEGE_CACHE[username]
                
                siege_cache_copy.clear()

            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)
            
            await asyncio.sleep(10)

def setup(bot):
    bot.add_cog(Siege(bot))