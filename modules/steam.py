import asyncio, aiohttp
from lxml import html
from datetime import datetime

steam_api_key = ""

async def resolve_vanity_url(sid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=%s&vanityurl=%s" % (steam_api_key, sid)) as r:
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

async def get_profile_summary(id64):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=%s&steamids=%s" % (steam_api_key, id64)) as r:
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

async def is_profile_public(id64):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=%s&steamids=%s" % (steam_api_key, id64)) as r:
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

async def get_profile_page(id64):
    if (not await is_profile_public(id64)):
        return None
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://steamcommunity.com/profiles/%s" % id64) as r:
            if (r.status != 200):
                return None

            return await r.text()

async def get_profile_description(id64, page=None):
    try:
        if (not page):
            page = await get_profile_page(id64)

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

async def get_friends(id64, page=None):
    try:
        if (not page):
            page = await get_profile_page(id64)

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

async def get_games(id64):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=%s&steamid=%s&format=json" % (steam_api_key, id64)) as r:
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

async def get_game_name(appid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key=%s&appid=%s" % (steam_api_key, appid)) as r:
                if (r.status != 200):
                    return await get_game_name_from_store(appid)
                
                data = await r.json()
        
                if data is not None:
                    if ("game" not in data):
                        return await get_game_name_from_store(appid)
                    
                    if ("gameName" not in data["game"]):
                        return await get_game_name_from_store(appid)

                    if (data["game"]["gameName"] == ""):
                        return await get_game_name_from_store(appid)
                    
                    if (data["game"]["gameName"].startswith("ValveTestApp")):
                        return await get_game_name_from_store(appid)
                    
                    return data["game"]["gameName"]

    except Exception:
        return await get_game_name_from_store(appid)

async def get_game_name_from_store(appid):
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

async def get_num_bans(id64):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key=%s&steamids=%s" % (steam_api_key, id64)) as r: 
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
def steamid64_to_32(id64):
    y = int(id64) - 76561197960265728
    x = y % 2 
    return "STEAM_0:{}:{}".format(x, (y - x) // 2)

async def get_account_age(id64):
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

async def get_level(id64, page=None):
    try:
        if (not page):
            page = await get_profile_page(id64)

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