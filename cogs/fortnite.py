import discord
from discord.ext import commands

from modules import utils

import asyncio
import aiohttp
from http.client import responses
from typing import Optional

class Fortnite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_fortnite_stats(self, name: str, platform: str) -> Optional[dict]:
        headers = {
            "TRN-Api-Key": self.bot.CONFIG["trn_api_key"]
        }

        url = "https://api.fortnitetracker.com/v1/profile/{platform}/{name}".format(platform=platform, name=name)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as r:
                    if (r.status != 200):
                        return r.status

                    return await r.json()

        except Exception:
            return None

    @staticmethod
    def create_fortnite_stats_embed(user: discord.User, stats_data: dict, stats: str, title: str = "") -> discord.Embed:
        embed = discord.Embed(colpr=discord.Color.dark_green())
        
        embed.title = title
        
        embed.set_footer(text="{platform} | {stats} stats | Powered by fortnitetracker.com".format(
                                                                                            platform=stats_data["platformNameLong"],
                                                                                            stats=stats[0].upper() + stats[1:]))
        
        embed.set_author(name=user.name, icon_url=user.avatar_url)

        if (stats == "lifetime"):
            data = utils.list_of_pairs_to_dict(stats_data["lifeTimeStats"])

            embed.add_field(name=":trophy: Wins", value="{:,}".format(int(data["Wins"])))
            embed.add_field(name=":medal: Win %", value=data["Win%"])
            embed.add_field(name=":gun: Kills", value="{:,}".format(int(data["Kills"])))
            embed.add_field(name=":skull_crossbones: K/D", value=data["K/d"])
            embed.add_field(name=":video_game: Matches Played", value=data["Matches Played"])
            
            try:
                rank = stats_data["stats"]["p9"]["trnRating"]["rank"]

            except KeyError:
                pass

            else:
                embed.add_field(name=":military_medal: Ranking", value="{:,}".format(int(rank)))
        else:
            stats_options = {"solo": "p2",
                            "duo": "p10",
                            "squad": "p9"
                            }

            if ("stats" not in stats_data or stats_options[stats] not in stats_data["stats"]):
                return None

            data = stats_data["stats"][stats_options[stats]]

            embed.add_field(name=":trophy: Wins", value="{:,}".format(int(data["top1"]["value"])))
            embed.add_field(name=":medal: Win %", value=(data["winRatio"]["value"] + "%"))
            embed.add_field(name=":gun: Kills", value="{:,}".format(int(data["kills"]["value"])))
            embed.add_field(name=":skull_crossbones: K/D", value=data["kd"]["value"])
            embed.add_field(name=":video_game: Matches Played", value="{:,}".format(int(data["matches"]["value"])))

            if (stats == "solo"):
                embed.add_field(name=":third_place: Top 10", value="{:,}".format(int(data["top10"]["value"])))
            elif (stats == "duo"):
                embed.add_field(name=":third_place: Top 5", value="{:,}".format(int(data["top5"]["value"])))
            elif (stats == "squad"):
                embed.add_field(name=":third_place: Top 3", value="{:,}".format(int(data["top3"]["value"])))
        
        return embed

    @commands.command(description="finds Fortnite stats for a user",
                      brief="finds Fortnite stats for a user",
                      aliases=["fstats"])
    @commands.cooldown(1, 1, commands.BucketType.guild)
    async def fortnite(self, ctx, name: str, stats: str = "lifetime"):
        async with ctx.channel.typing():
            if (not "trn_api_key" in self.bot.CONFIG):
                await ctx.send("No Tracker API key found")
                return

            stats_options = ["lifetime", "solo", "duo", "squad"]
            if (stats not in stats_options):
                await ctx.send(f"{ctx.author.mention} Invalid stat selection `{stats}`, options are: {', '.join('`{}`'.format(s) for s in stats_options)}")
                return

            platforms = ["pc", "xbl", "psn"]

            success = False

            for platform in platforms:
                data = await self.get_fortnite_stats(name, platform)
                await asyncio.sleep(1) # cooldown in between each request, according to the api's guidelines

                if (not data):
                    continue

                if (isinstance(data, int)):
                    self.bot.bot_utils.log_error_to_file("Failed to get Fortnite stats for \"{name}\" ({platform}) failed with status code {code} ({string})".format(
                            name=name,
                            platform=platform,
                            code=data,
                            string=responses[data] if (data in responses) else "unknown"), prefix="Fortnite")
                    continue

                try:
                    data = dict(data)

                except Exception as e:
                    self.bot.bot_utils.log_error_to_file("Failed to find Fortnite stats for \"{}\" ({}) because of exception: {}".format(name, platform, e),
                            prefix="Fortnite")
                    continue

                if ("error" in data):
                    if (data["error"] != "Player Not Found"):
                        self.bot.bot_utils.log_error_to_file("API error for \"{}\" ({}): {}".format(name, platform, data["error"]), prefix="Fortnite")
                    
                    continue

                embed = self.create_fortnite_stats_embed(ctx.message.author,
                                                            data,
                                                            stats,
                                                            title=name)

                if (not embed):
                    await ctx.send(f"{ctx.author.mention} Failed to find `{stats}` Fortnite stats for `{name}`")
                    return

                await ctx.send(embed=embed)
                success = True

            if (not success):
                await ctx.send(f"{ctx.author.mention} Failed to find `{stats}` Fortnite stats for `{name}`")

def setup(bot):
    bot.add_cog(Fortnite(bot))
