import discord

import asyncio, aiohttp
import datetime

base_url = "https://api.r6stats.com/api/v1/"

platforms = {"uplay": "Uplay",
             "xone": "Xbox One",
             "ps4": "PS4"
            }

async def get_player(username, platform="uplay"):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url + "players/{}?platform={}".format(username, platform)) as r:
                return await r.json()
        
    except Exception:
        return None

async def create_siege_embed(user, data, stats_selection="overall"):
    stats = data["stats"]

    embed = discord.Embed()
    
    embed.title = data["username"]
    
    platform = platforms[data["platform"]] or "Unknown"

    date = datetime.datetime.strptime(data["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%b %-d, %Y")

    embed.set_footer(text="{platform} | {stats} stats | Updated on {date} | Powered by r6stats.com".format(
                                                                                platform=platform,
                                                                                stats=stats_selection[0].upper() + stats_selection[1:],
                                                                                date=date))
    
    embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.color = discord.Color.blue()

    stats_data = stats[stats_selection]

    if (stats_selection == "overall"):
        embed.add_field(name=":gun: Accuracy", value="{:.2%}".format((stats_data["bullets_hit"] / stats_data["bullets_fired"]) if stats_data["bullets_fired"] else 0))
        embed.add_field(name=":skull_crossbones: Headshot %", value="{:.2%}".format((stats_data["headshots"] / stats_data["bullets_hit"]) if stats_data["bullets_hit"] else 0))
        embed.add_field(name="Penetration Kills", value="{:,}".format(stats_data["penetration_kills"]))
        embed.add_field(name=":skull: Suicides", value="{:,}".format(stats_data["suicides"]))
        embed.add_field(name=":syringe: Revives", value="{:,}".format(stats_data["revives"]))
        embed.add_field(name=":handshake: Assists", value="{:,}".format(stats_data["assists"]))
        embed.add_field(name=":knife: Melee Kills", value="{:,}".format(stats_data["melee_kills"]))
        embed.add_field(name=":military_medal: Level", value="{:,}".format(stats["progression"]["level"]))
    else:
        embed.add_field(name=":medal: Win/Loss Ratio", value="{:.2f}".format(stats_data["wlr"]))
        embed.add_field(name=":trophy: Wins", value="{:,}".format(stats_data["wins"]))
        embed.add_field(name=":second_place: Losses", value="{:,}".format(stats_data["losses"]))
        embed.add_field(name=":skull_crossbones: K/D Ratio", value="{:.2f}".format(stats_data["kd"]))
        embed.add_field(name=":gun: Kills", value="{:,}".format(stats_data["kills"]))
        embed.add_field(name=":skull: Deaths", value="{:,}".format(stats_data["deaths"]))
        embed.add_field(name=":video_game: Matches Played", value="{:,}".format(stats_data["wins"] + stats_data["losses"]))
        embed.add_field(name=":stopwatch: Playtime", value="{:,} hours".format(round(stats_data["playtime"] / 60 / 60)))

    return embed