import discord
from discord.ext import commands

import asyncio
import time
from enum import Enum

class VoteType(Enum):
    POLL = 1
    MUTE = 2

class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.emojis = {
            "yes": "\N{WHITE HEAVY CHECK MARK}",
            "no": "\N{NEGATIVE SQUARED CROSS MARK}"
        }

        # votes currently running
        self.votes = {}

        # dict of muted members where the id is the key
        # and the time to unmute is the value
        self.muted_members = {}

        # background task to check when votes expire and when to unmute users
        self.vote_task = self.bot.loop.create_task(self.vote_think())

        # time in seconds to mute users
        self.MUTE_TIME = 60

    def cog_unload(self):
        self.vote_task.cancel()

    @commands.group(description="starts a vote",
                    brief="starts a vote")
    async def vote(self, ctx):
        if (not ctx.invoked_subcommand):
            return

    def make_mute_embed(self, author: discord.Member, target: discord.User, time: int):
        embed = discord.Embed()

        embed.title = f"Vote to mute {target}"
        embed.color = discord.Color.red()
        embed.set_author(name=author.name, icon_url=author.avatar_url)
        embed.set_thumbnail(url=target.avatar_url)

        if (time > 0):
            embed.set_footer(text=f"Time remaining: {time}s")
        else:
            embed.set_footer(text="Time remaining: expired")

        return embed

    @vote.command(description="starts a vote to mute a user",
                  brief="starts a vote to mute a user")
    async def mute(self, ctx, user: discord.Member):
        if (user == ctx.me):
            await ctx.send(f"{ctx.author.mention} nice try")
            return
        
        embed = self.make_mute_embed(ctx.author, user, self.MUTE_TIME)

        vote_message = await ctx.channel.send(embed=embed)
        
        for emoji in self.emojis.values():
            await vote_message.add_reaction(emoji)

        # add vote to vote list
        self.votes[vote_message.id] = {
            "time": time.time() + self.MUTE_TIME,
            "votes": 0,
            "message": vote_message,
            "author": ctx.author,
            "target": user,
            "type": VoteType.MUTE
        }

    def is_valid_reaction(self, emoji: str, message: discord.Message, user: discord.User) -> bool:
        if (user == self.bot.user):
            return False

        if (message.id not in self.votes):
            return False

        if (emoji not in self.emojis.values()):
            return False

        return True

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        message = reaction.message
        emoji = reaction.emoji

        if (not self.is_valid_reaction(emoji, message, user)):
            return

        if (emoji == self.emojis["yes"]):
            self.votes[message.id]["votes"] += 1
        elif (emoji == self.emojis["no"]):
            self.votes[message.id]["votes"] -= 1

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User):
        message = reaction.message
        emoji = reaction.emoji

        if (not self.is_valid_reaction(emoji, message, user)):
            return

        # if the reaction is removed, reverse the vote
        if (emoji == self.emojis["yes"]):
            self.votes[message.id]["votes"] -= 1
        elif (emoji == self.emojis["no"]):
            self.votes[message.id]["votes"] += 1

    async def handle_mute(self, message_id: str, vote: dict):
        if (vote["time"] < time.time()):
            await vote["message"].clear_reactions()
            total = vote["votes"]

            del self.votes[message_id]

            embed = self.make_mute_embed(vote["author"], vote["target"], -1)
            await vote["message"].edit(embed=embed)

            if (total > 0):
                await vote["message"].channel.send(f"{vote['author'].mention}'s vote to mute {vote['target'].mention} passed, muting them for {self.MUTE_TIME} seconds")

                try:
                    await vote["target"].edit(mute=True)
                except discord.Forbidden:
                    await vote["message"].channel.send("I don't have permissions to mute")
                except discord.HTTPException as e:
                    await vote["message"].channel.send(f"HTTPException: `{e}`")

                self.muted_members[vote["target"].id] = {
                    "time": time.time() + self.MUTE_TIME,
                    "channel": vote["message"].channel,
                    "member": vote["target"]
                }
            elif (total < 0):
                await vote["message"].channel.send(f"{vote['author'].mention}'s vote to mute {vote['target'].mention} failed, no action taken")
            else:
                await vote["message"].channel.send(f"{vote['author'].mention}'s vote to mute {vote['target'].mention} tied, no action taken")
        else:
            embed = self.make_mute_embed(vote["author"], vote["target"], int(vote["time"] - time.time()))
            await vote["message"].edit(embed=embed)

    async def vote_think(self):
        await self.bot.wait_until_ready()

        while (not self.bot.is_closed()):
            try:
                vote_copy = self.votes.copy()

                for message_id, vote in vote_copy.items():
                    if (vote["type"] == VoteType.MUTE):
                        await self.handle_mute(message_id, vote)

                vote_copy.clear()

                muted_members = self.muted_members.copy()

                for member_id, muted_dict in muted_members.items():
                    if (muted_dict["time"] < time.time()):
                        await muted_dict["channel"].send(f"{muted_dict['member'].mention}'s mute expired, unmuting")

                        try:
                            await vote["target"].edit(mute=False)
                        except discord.Forbidden:
                            await muted_dict["channel"].send("I don't have permissions to unmute")
                        except discord.HTTPException as e:
                            await muted_dict["channel"].send(f"HTTPException: `{e}`")
                        except Exception as e:
                            await muted_dict["channel"].send(f"An error occured unmuting {vote['target']}: ```{e}```")

                        del self.muted_members[member_id]
            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)

            await asyncio.sleep(10)

def setup(bot):
    bot.add_cog(Vote(bot))
