import discord
from discord.ext import commands

import asyncio
import aiohttp
import datetime
import time
from typing import Optional

class Siege:
    def __init__(self, bot):
        self.bot = bot

        self.SIEGE_CACHE = {}
        self.bot.loop.create_task(self.remove_siege_cache())

        self.base_url = "https://api.r6stats.com/api/v1/"

        self.platforms = {"uplay": "Uplay",
                    "xone": "Xbox One",
                    "ps4": "PS4"
                    }

    @commands.command(description="finds Rainbow Six Siege stats for a user",
                      brief="finds Rainbow Six Siege stats for a user",
                      pass_context=True,
                      aliases=["r6s", "r6stats"])
    @commands.cooldown(1, 5, commands.BucketType.server)
    async def siege(self, ctx, username: str, stats_selection: str = "overall", platform: str = "uplay"):
        stats_options = ["overall", "ranked", "casual", "all"]
        if (stats_selection not in stats_options):
            await self.bot.messaging.reply(ctx.message, "Invalid stat selection `{}`, options are: {}".format(stats_selection,
                ", ".join("`{}`".format(s) for s in stats_options)))
            return

        if (platform not in self.platforms.keys()):
            await self.bot.messaging.reply(ctx.message, "Invalid platform selection `{}`, options are: {}".format(platform,
                ", ".join("`{}`".format(s) for s in self.platforms.keys())))
            return

        if (username in self.SIEGE_CACHE):
            stats = self.SIEGE_CACHE[username]["stats"]
            self.SIEGE_CACHE[username]["time"] = time.time()
        else:
            msg = await self.bot.messaging.reply(ctx.message, "Searching for stats (might take a while)...")
            await self.bot.send_typing(ctx.message.channel)

            stats = await self.get_player(username, platform=platform)

            await self.bot.bot_utils.delete_message(msg)

            if (not stats):
                await self.bot.messaging.reply(ctx.message, "Failed to find `{}` stats for `{}` on `{}`".format(stats_selection, username, platform))
                return

            if (not "player" in stats):
                if ("errors" in stats):
                    for error in stats["errors"]:
                        detail = "Unknown error."
                        description = "Unknown."

                        if ("detail" in error):
                            detail = error["detail"]

                        if ("meta" in error and "description" in error["meta"]):
                            description = error["meta"]["description"]

                        await self.bot.messaging.reply(ctx.message, "An error occured searching for `{}` on `{}`: {} {}".format(username,
                            platform,
                            detail,
                            description))

                return

            stats = stats["player"]

        if (stats_selection == "all"):
            stats_option = stats_options[:-1]
        else:
            stats_option = [stats_selection]

        success = False

        for option in stats_option:
            embed = await self.create_siege_embed(ctx.message.author, stats, stats_selection=option)

            if (not embed):
                continue

            success = True
            await self.bot.send_message(ctx.message.channel, embed=embed)

            self.SIEGE_CACHE[username] = {"time": time.time(),
                                          "stats": stats}

        if (not success):
            await self.bot.messaging.reply(ctx.message, "Failed to find `{}` stats for `{}` on `{}`".format(stats_selection, username, platform))

    async def remove_siege_cache(self) -> None:
        await self.bot.wait_until_ready()
        
        while (not self.bot.is_closed):
            try:
                siege_cache_copy = self.SIEGE_CACHE.copy()
                
                for username, cache in siege_cache_copy.items():
                    if (time.time() > cache["time"] + self.bot.CONFIG["SIEGE_CACHE_TIME"]):
                        del self.SIEGE_CACHE[username]
                
                siege_cache_copy.clear()

            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)
            
            #await asyncio.sleep(self.bot.CONFIG["SIEGE_CACHE_TIME"] // 2)
            await asyncio.sleep(10)

    async def get_player(self, username: str, platform: str = "uplay") -> Optional[dict]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url + "players/{}?platform={}".format(username, platform)) as r:
                    return await r.json()
            
        except Exception:
            return None

    async def create_siege_embed(self, user: discord.User, data: dict, stats_selection: str = "overall") -> discord.Embed:
        stats = data["stats"]

        embed = discord.Embed()
        
        embed.title = data["username"]
        
        platform = self.platforms[data["platform"]] or "Unknown"

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

def setup(bot):
    bot.add_cog(Siege(bot))