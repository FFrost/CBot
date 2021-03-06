import discord
from discord.ext import commands

from modules import utils, paginator

import asyncio
import aiohttp
import time
import base64
import iso8601
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timezone
from math import ceil, floor, inf

class UbisoftAPIError(Exception):
    pass

class NoLoginInfo(UbisoftAPIError):
    pass

class LoginFailure(UbisoftAPIError):
    pass

class UnauthorizedError(UbisoftAPIError):
    pass

class RateLimited(UbisoftAPIError):
    pass

class UbisoftAPI:
    def __init__(self, session, *args, **kwargs):
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

        self._regions = {
            "ncsa": "North America",
            "emea": "Europe",
            "apac": "Asia"
        }

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

        self._ranks = [
            "Unranked",
            "Copper V",
            "Copper IV",
            "Copper III",
            "Copper II",
            "Copper I",
            "Bronze V",
            "Bronze IV",
            "Bronze III",
            "Bronze II",
            "Bronze I",
            "Silver V",
            "Silver IV",
            "Silver III",
            "Silver II",
            "Silver I",
            "Gold III",
            "Gold II",
            "Gold I",
            "Platinum III",
            "Platinum II",
            "Platinum I",
            "Diamond",
            "Champion"
        ]

        self._rankImages = [
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank4.5105339d.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank3.f204dd6e.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank2.f2bc8224.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank1.79a2af3a.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank8.d08a99eb.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank7.ba63ea85.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank6.fc40a107.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank5.5b0b90e9.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank12.c432740e.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank11.2fffcd0a.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank10.cce1c8c4.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank9.4196c329.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank16.9950a890.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank15.e8ddab14.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank14.1e94c7f0.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank13.42fb03b4.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank19.5cc86715.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank18.0942a2f2.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank17.27fbc796.svg",
            "https://ubistatic-a.akamaihd.net/0058/prod/assets/styles/images/hd-rank20.da30b73c.svg"
        ]

        self.rateLimitedTime: float = 0

        self._session = session

        self._rateLimitCooldown = 120

    async def _post(self, url: str, payload: dict, headers: dict = None, is_login: bool = False) -> dict:
        if (self.rateLimitedTime > time.time()):
            print(f"Rate limited for {self.rateLimitedTime - time.time():.2f} more seconds")
            return None

        if (self._has_expired() and not is_login):
            await self.login(relog=True)
        
        async with self._session.post(url, json=payload, headers=(headers if headers is not None else payload)) as r:
            try:
                data = await r.json()
            except Exception:
                return None
            
            if (r.status == 401):
                raise UnauthorizedError(data.get("message", "POST Unauthorized error"))
            
            return data

        return None

    async def _get(self, url: str, payload: dict = None, headers: dict = None) -> dict:
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
            
            if (r.status == 401):
                raise UnauthorizedError(data.get("message", "GET Unauthorized error"))
            
            return data

        return None

    @staticmethod
    def _parse_expiration(expiration: str) -> datetime:
        return iso8601.parse_date(expiration)

    def _has_expired(self) -> bool:
        if (not hasattr(self, "_expiration")):
            return False
        
        return (datetime.now(timezone.utc) > self._expiration)

    @staticmethod
    def _generateTicket(email: str, password: str) -> str:
        return f"Basic {base64.b64encode(bytes(f'{email}:{password}'.encode('ascii'))).decode('ascii')}"

    async def login(self, relog: bool = False) -> None:
        if (relog):
            self._headers.update({"Authorization": self._initialAuth})

        data = await self._post("https://public-ubiservices.ubi.com/v3/profiles/sessions", self._headers, is_login=relog)

        if (not data):
            raise LoginFailure("Failed to get data from Ubisoft services")

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
        except KeyError:
            raise LoginFailure("Recieved unexpected response")
        else:
            self._rateLimitCooldown = 120 # set back to default on successful login

            if (not hasattr(self, "_operatorData")):
                await self._loadOperatorData()

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

        return False

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
        except KeyError:
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

    def getRankName(self, rank: int) -> str:
        if (0 <= rank < len(self._ranks)):
            return self._ranks[rank]

        return "Unranked"

    def mmrToRankName(self, mmr: int) -> str:
        rank = 0

        mmr_ranks = [
            0,      # unranked
            1200,   # copper V
            1300,   # IV
            1400,   # III
            1500,   # II
            1600,   # I
            1700,   # bronze V
            1800,   # IV
            1900,   # III
            2000,   # II
            2100,   # I
            2200,   # silver V
            2300,   # IV
            2400,   # III
            2500,   # II
            2600,   # I
            2800,   # gold III
            3000,   # II
            3200,   # I
            3600,   # plat III
            4000,   # II
            4400,   # I
            5000,   # diamond
            inf     # champion
        ]

        for i in range(1, len(mmr_ranks)):
            prev = i - 1
            lower = mmr_ranks[prev] # lower bound of rank
            upper = mmr_ranks[i] # upper bound of rank

            if (lower <= mmr < upper):
                rank = prev
                break

        return self.getRankName(rank)

    async def _loadOperatorData(self) -> Optional[dict]:
        url = "https://game-rainbow6.ubi.com/assets/data/operators.caa95d86.json"

        async with self._session.get(url) as r:
            try:
                data = await r.json()
            except Exception:
                return None

        if (not data or not isinstance(data, dict)):
            return None

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

    @staticmethod
    def sortOperatorData(data: dict) -> dict:
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

    async def _loadSeasonsData(self):
        url = "https://game-rainbow6.ubi.com/assets/data/seasons.c77d84ac.json"

        async with self._session.get(url) as r:
            try:
                data = await r.json()
            except Exception:
                return None

        if (not data or not isinstance(data, dict)):
            return None

        self._seasonsData = data
        return data

    async def getPastSeasonsData(self, profile: dict, region: str="ncsa") -> List[Dict]:
        if (not hasattr(self, "_seasonsData") or self._seasonsData is None):
            await self._loadSeasonsData()

        if (self._seasonsData is None):
            return None

        if (not "seasons" in self._seasonsData):
            return None

        userID = profile["userId"]
        platform = profile["platformType"]

        seasons = []

        for season in self._seasonsData["seasons"]:
            season_name = self._seasonsData["seasons"][season]["name"]
            url = f"{self._getRequestUrl(platform)}/r6karma/players?board_id=pvp_ranked&region_id={region}&season_id={season}&profile_ids={userID}"
            data = await self._get(url)

            if (not data):
                continue

            if ("errorCode" in data):
                break

            # if max_mmr is 0, they were not ranked that season, so we should ignore that data
            if (not "players" in data or not userID in data["players"] or not "max_mmr" in data["players"][userID]):
                continue

            if (data["players"][userID]["max_mmr"] == 0.0):
                continue

            data["season_name"] = season_name
            seasons.append(data)

        return seasons

class Siege(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.SIEGE_CACHE = {}
        self.siege_think_task = self.bot.loop.create_task(self.siege_think())

        self.paginators = []

        try:
            email = self.bot.CONFIG["siege"].get("email")
            password = self.bot.CONFIG["siege"].get("password")
            ticket = self.bot.CONFIG["siege"].get("ticket")

            if (not email and not password and not ticket):
                raise NoLoginInfo

            self.ubi = UbisoftAPI(self.bot.session, email=email, password=password, ticket=ticket)
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

    def cog_unload(self):
        self.bot.loop.create_task(self.ubi._session.close())
        self.siege_think_task.cancel()

    def create_ranked_embed(self, user: discord.User, profile: dict, rankedData: dict, stats: dict, region_name: str, level: int) -> discord.Embed:
        ranked_embed = discord.Embed(color=discord.Color.red())
        ranked_embed.set_author(name=user.name, icon_url=user.avatar_url)
        ranked_embed.title = profile["nameOnPlatform"]
        ranked_embed.set_footer(text=f"{self.ubi._platforms[profile['platformType']]['name']} | Ranked stats | {region_name} | UserID: {profile['userId']}")

        rank_num = rankedData.get("rank", 0)

        if (0 < rank_num < len(self.ubi._rankImages)):
            thumb_url = self.ubi._rankImages[rank_num]
            ranked_embed.set_thumbnail(url=thumb_url) # TODO: discord doesn't embed .svg
        
        wl_ratio = utils.safe_div(stats.get('rankedpvp_matchwon:infinite', 0), stats.get('rankedpvp_matchlost:infinite', 0))

        ranked_embed.add_field(name=":medal: Win/Loss Ratio", value=f"{wl_ratio:.2f}")
        ranked_embed.add_field(name=":trophy: Wins", value=f"{stats.get('rankedpvp_matchwon:infinite', 0):,}")
        ranked_embed.add_field(name=":second_place: Losses", value=f"{stats.get('rankedpvp_matchlost:infinite', 0):,}")

        kd_ratio = utils.safe_div(stats.get('rankedpvp_kills:infinite', 0), stats.get('rankedpvp_death:infinite', 0))

        ranked_embed.add_field(name=":skull_crossbones: K/D Ratio", value=f"{kd_ratio:.2f}")
        ranked_embed.add_field(name=":gun: Kills", value=f"{stats.get('rankedpvp_kills:infinite', 0):,}")
        ranked_embed.add_field(name=":skull: Deaths", value=f"{stats.get('rankedpvp_death:infinite', 0):,}")

        highest_rank = rankedData.get("max_rank", 0)

        if (highest_rank > 0):
            ranked_embed.add_field(name="MMR", value=f"{int(rankedData['mmr'])}")
            ranked_embed.add_field(name="Rank", value=f"{self.ubi.getRankName(rank_num)}")

            ranked_embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")

            ranked_embed.add_field(name="Highest MMR", value=f"{ceil(rankedData['max_mmr'])}")
            ranked_embed.add_field(name="Highest Rank", value=f"{self.ubi.getRankName(highest_rank)}")

            ranked_embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")
        else:
            ranked_embed.add_field(name="Rank", value="Unranked")
        
        ranked_embed.add_field(name=":military_medal: Level", value=f"{level:,}")
        ranked_embed.add_field(name=":video_game: Matches Played", value=f"{stats.get('rankedpvp_matchplayed:infinite', 0):,}")
        ranked_embed.add_field(name=":stopwatch: Playtime", value=f"{stats.get('rankedpvp_timeplayed:infinite', 0) / 3600:,.0f} hours")

        return ranked_embed

    def create_casual_embed(self, user: discord.User, profile: dict, stats: dict, region_name: str) -> discord.Embed:
        casual_embed = discord.Embed(color=discord.Color.blue())
        casual_embed.set_author(name=user.name, icon_url=user.avatar_url)
        casual_embed.title = profile["nameOnPlatform"]
        casual_embed.set_footer(text=f"{self.ubi._platforms[profile['platformType']]['name']} | Casual stats | {region_name} | UserID: {profile['userId']}")
        wl_ratio = utils.safe_div(stats.get('casualpvp_matchwon:infinite', 0),
            (stats.get('casualpvp_matchlost:infinite', 1) + stats.get('casualpvp_matchwon:infinite', 0)))
        
        casual_embed.add_field(name=":medal: Win/Loss Ratio", value=f"{wl_ratio:.2%}")
        casual_embed.add_field(name=":trophy: Wins", value=f"{stats.get('casualpvp_matchwon:infinite', 0):,}")
        casual_embed.add_field(name=":second_place: Losses", value=f"{stats.get('casualpvp_matchlost:infinite', 0):,}")

        kd_ratio = utils.safe_div(stats.get('casualpvp_kills:infinite', 0), stats.get('casualpvp_death:infinite', 0))

        casual_embed.add_field(name=":skull_crossbones: K/D Ratio", value=f"{kd_ratio:.2f}")
        casual_embed.add_field(name=":gun: Kills", value=f"{stats.get('casualpvp_kills:infinite', 0):,}")
        casual_embed.add_field(name=":skull: Deaths", value=f"{stats.get('casualpvp_death:infinite', 0):,}")
        casual_embed.add_field(name=":video_game: Matches Played", value=f"{stats.get('casualpvp_matchplayed:infinite', 0):,}")
        casual_embed.add_field(name=":stopwatch: Playtime", value=f"{stats.get('casualpvp_timeplayed:infinite', 0) / 3600:,.0f} hours")
        casual_embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")

        return casual_embed

    def create_overall_embed(self, user: discord.User, profile: dict, stats: dict, level: int) -> discord.Embed:
        overall_embed = discord.Embed(color=discord.Color.green())
        overall_embed.set_author(name=user.name, icon_url=user.avatar_url)
        overall_embed.title = profile["nameOnPlatform"]
        overall_embed.set_footer(text=f"{self.ubi._platforms[profile['platformType']]['name']} | Overall stats | UserID: {profile['userId']}")
        accuracy = utils.safe_div(stats.get('generalpvp_bullethit:infinite', 0), stats.get('generalpvp_bulletfired:infinite', 0))

        overall_embed.add_field(name=":gun: Accuracy", value=f"{accuracy:.2%}")

        headshot_ratio = utils.safe_div(stats.get('generalpvp_headshot:infinite', 0), stats.get('generalpvp_bulletfired:infinite', 0))

        overall_embed.add_field(name=":skull_crossbones: Headshot %", value=f"{headshot_ratio:.2%}")
        overall_embed.add_field(name="Penetration Kills", value=f"{stats.get('generalpvp_penetrationkills:infinite', 0):,}")
        overall_embed.add_field(name=":skull: Suicides", value=f"{stats.get('generalpvp_suicide:infinite', 0):,}")
        overall_embed.add_field(name=":syringe: Revives", value=f"{stats.get('generalpvp_revive:infinite', 0):,}")
        overall_embed.add_field(name=":handshake: Assists", value=f"{stats.get('generalpvp_killassists:infinite', 0):,}")
        overall_embed.add_field(name=":knife: Melee Kills", value=f"{stats.get('generalpvp_meleekills:infinite', 0):,}")
        overall_embed.add_field(name=":military_medal: Level", value=f"{level:,}")
        overall_embed.add_field(name=":video_game: Total Playtime", value=f"{stats.get('generalpvp_timeplayed:infinite', 0) // 3600:,.0f} hours")

        return overall_embed
    
    def create_operator_embed(self, user: discord.User, profile: dict, operatorData: dict):
        operator_embed = discord.Embed(color=discord.Color.light_grey())
        operator_embed.set_author(name=user.name, icon_url=user.avatar_url)
        operator_embed.title = profile["nameOnPlatform"]
        operator_embed.set_footer(text=f"{self.ubi._platforms[profile['platformType']]['name']} | Operator stats | UserID: {profile['userId']}")
        opData = self.ubi.sortOperatorData(operatorData)

        mostPlayedAttacker, mostPlayedDefender = self.ubi.findAtkAndDefOperators(opData["timeplayed"])

        if (not mostPlayedAttacker):
            mostPlayedAttacker = (["1:1"], 0)
        
        if (not mostPlayedDefender):
            mostPlayedDefender = (["1:1"], 0)

        mostKills = utils.safe_list_get(opData.get("kills"), 0)
        mostDeaths = utils.safe_list_get(opData.get("death"), 0)
        mostHeadshots = utils.safe_list_get(opData.get("headshot"), 0)
        mostMeleeKills = utils.safe_list_get(opData.get("meleekills"), 0)
        mostRoundsWon = utils.safe_list_get(opData.get("roundwon"), 0)
        mostRoundsLost = utils.safe_list_get(opData.get("roundlost"), 0)

        operator_embed.add_field(name="Most Played Attacker", value=f"{self.ubi.getOperatorName(mostPlayedAttacker[0])} ({mostPlayedAttacker[1] / 3600:,.0f} hours)")
        operator_embed.add_field(name="Most Played Defender", value=f"{self.ubi.getOperatorName(mostPlayedDefender[0])} ({mostPlayedDefender[1] / 3600:,.0f} hours)")
        operator_embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")
        
        if (mostKills):
            operator_embed.add_field(name="Most Kills", value=f"{self.ubi.getOperatorName(mostKills[0])} ({mostKills[1]:,})")
        
        if (mostDeaths):
            operator_embed.add_field(name="Most Deaths", value=f"{self.ubi.getOperatorName(mostDeaths[0])} ({mostDeaths[1]:,})")
        
        if (mostHeadshots):
            operator_embed.add_field(name="Most Headshots", value=f"{self.ubi.getOperatorName(mostHeadshots[0])} ({mostHeadshots[1]:,})")
        
        if (mostMeleeKills):
            operator_embed.add_field(name="Most Melee Kills", value=f"{self.ubi.getOperatorName(mostMeleeKills[0])} ({mostMeleeKills[1]:,})")
        
        if (mostRoundsWon):
            operator_embed.add_field(name="Most Rounds Won", value=f"{self.ubi.getOperatorName(mostRoundsWon[0])} ({mostRoundsWon[1]:,})")
        
        if (mostRoundsLost):
            operator_embed.add_field(name="Most Rounds Lost", value=f"{self.ubi.getOperatorName(mostRoundsLost[0])} ({mostRoundsLost[1]:,})")

        return operator_embed

    def create_past_seasons_embed(self, user: discord.User, profile: dict, past_seasons: List[Dict], region_name: str) -> discord.Embed:
        embed = discord.Embed(colors=discord.Color.blurple())
        embed.title = profile["nameOnPlatform"]
        embed.set_footer(text=f"{self.ubi._platforms[profile['platformType']]['name']} | Past Seasons stats | {region_name} | UserID: {profile['userId']}")

        total_mmr = 0
        total_max_mmr = 0

        total_kills, total_deaths = 0, 0
        total_wins, total_losses = 0, 0

        for season in past_seasons:
            season = season["players"][profile["userId"]]

            total_mmr += season["mmr"]
            total_max_mmr += season["max_mmr"]

            total_kills += season["kills"]
            total_deaths += season["deaths"]

            total_wins += season["wins"]
            total_losses += season["losses"]

        avg_mmr = int(total_mmr / len(past_seasons))
        avg_max_mmr = int(total_max_mmr / len(past_seasons))

        avg_kd = utils.safe_div(total_kills, total_deaths)
        avg_wl = utils.safe_div(total_wins, total_losses)

        embed.add_field(name="Average MMR", value=f"{avg_mmr}")

        avg_rank_name = self.ubi.mmrToRankName(avg_mmr)
        embed.add_field(name="Average Rank", value=f"{avg_rank_name}")

        embed.add_field(name="Average Highest MMR", value=f"{avg_max_mmr}")

        embed.add_field(name="Average K/D", value=f"{avg_kd:.2f}")
        embed.add_field(name="Average Win/Loss", value=f"{avg_wl:.2f}")

        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")
        
        return embed

    @commands.command(description="finds Rainbow Six: Siege stats for a user",
                      brief="finds Rainbow Six: Siege stats for a user",
                      aliases=["sg", "r6", "r6s", "r6stats"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def siege(self, ctx, username: str, platform: str = "uplay"):
        async with ctx.channel.typing():
            if (platform.lower() not in self.ubi._platforms.keys()):
                await ctx.send(f"{ctx.author.mention} Invalid platform, options are: {utils.format_code_brackets(self.ubi._platforms.keys())}")
                return

            if (self.ubi.rateLimitedTime > time.time()):
                await ctx.send(f"{ctx.author.mention} Can't fetch stats, rate limited by Ubisoft for {self.ubi.rateLimitedTime - time.time():.2f} more seconds")
                return

            if (username in self.SIEGE_CACHE and platform in self.SIEGE_CACHE[username]):
                data = self.SIEGE_CACHE[username][platform]
                profile = data["profile"]
                level = data["level"]
                rankedData = data["rankedData"]
                statsData = data["statsData"]
                operatorData = data["operatorData"]
                pastSeasonsData = data["pastSeasonsData"]

                self.SIEGE_CACHE[username]["time"] = time.time()
            else:
                try:
                    profiles = await self.ubi.searchPlayers(username, platform)
                
                    if (not profiles):
                        await ctx.send(f"{ctx.author.mention} Failed to find player `{username}` on `{platform}`")
                        return

                    profile = profiles[0] # TODO: show list?

                    level = await self.ubi.getLevel(profile)

                    rankedData = {}
                    pastSeasonsData = {}

                    for region in self.ubi._regions:
                        rankedData[region] = await self.ubi.getRankData(profile, region)
                        pastSeasonsData[region] = await self.ubi.getPastSeasonsData(profile, region)

                    statsData = await self.ubi.getStatsData(profile)

                    operatorData = await self.ubi.getOperatorStats(profile)
                except (UnauthorizedError, LoginFailure) as e:
                    await ctx.send(f"{ctx.author.mention} An error occured getting stats for player `{username}` on `{platform}`: {e}")
                    return

            if (not rankedData or not statsData):
                await ctx.send(f"{ctx.author.mention} Failed to find stats for `{username}` on `{platform}`")
                return

            embeds = {}

            for region in self.ubi._regions:
                region_name = self.ubi._regions.get(region)
                regionalRankedData = rankedData[region]

                ranked_embed = self.create_ranked_embed(ctx.author, profile, regionalRankedData, statsData, region_name, level)
                casual_embed = self.create_casual_embed(ctx.author, profile, statsData, region_name)
                overall_embed = self.create_overall_embed(ctx.author, profile, statsData, level)
                operator_embed = self.create_operator_embed(ctx.author, profile, operatorData)

                embeds[region] = [ranked_embed, casual_embed, overall_embed, operator_embed]

                # ex. new account?
                regionalPastSeasonsData = pastSeasonsData[region]
                if (regionalPastSeasonsData):
                    past_seasons_embed = self.create_past_seasons_embed(ctx.author, profile, regionalPastSeasonsData, region_name)
                    embeds[region] += [past_seasons_embed]

            flags = {
                "us": "\N{Regional Indicator Symbol Letter U}\N{Regional Indicator Symbol Letter S}",
                "eu": "\N{Regional Indicator Symbol Letter E}\N{Regional Indicator Symbol Letter U}",
                "as": "\N{Regional Indicator Symbol Letter J}\N{Regional Indicator Symbol Letter P}"
            }
            
            pager = await paginator.create_paginator(
                self.bot,
                ctx,
                embeds[list(embeds.keys())[0]],
                extra_embeds=embeds,
                table={
                    flags["us"]: "ncsa",
                    flags["eu"]: "emea",
                    flags["as"]: "apac"
                },
                expiry_time=60
            )

            self.paginators.append(pager)

            self.SIEGE_CACHE[username] = {
                platform: {
                    "profile": profile,
                    "level": level,
                    "rankedData": rankedData,
                    "statsData": statsData,
                    "operatorData": operatorData,
                    "pastSeasonsData": pastSeasonsData
                },
                "time": time.time()
            }

    async def siege_think(self) -> None:
        await self.bot.wait_until_ready()
        
        while (not self.bot.is_closed()):
            try:
                # cache
                siege_cache_copy = self.SIEGE_CACHE.copy()
                
                for username, cache in siege_cache_copy.items():
                    if (time.time() > cache["time"] + self.bot.CONFIG["siege"]["cache_time"]):
                        del self.SIEGE_CACHE[username]
                
                siege_cache_copy.clear()

                # paginator
                paginator_copy = self.paginators.copy()

                for pager in paginator_copy:
                    if (pager.has_expired()):
                        try:
                            await pager.clear_reactions()
                        except discord.DiscordException:
                            pass
                        
                        self.paginators.remove(pager)

                paginator_copy.clear()

            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)
            
            await asyncio.sleep(10)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for pager in self.paginators:
            await pager.reaction_hook(reaction, user)

def setup(bot):
    bot.add_cog(Siege(bot))
