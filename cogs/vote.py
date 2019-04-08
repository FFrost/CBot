import discord
from discord.ext import commands

import asyncio
import time
from enum import Enum

class VoteTypes(Enum):
    POLL = 1
    MUTE = 2

class Vote:
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

    def __unload(self):
        self.vote_task.cancel()

    @commands.group(description="starts a vote",
                    brief="starts a vote",
                    pass_context=True,
                    no_pm=True)
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
                  brief="starts a vote to mute a user",
                  pass_context=True)
    async def mute(self, ctx, user: discord.Member):
        if (user == ctx.message.server.me):
            await self.bot.messaging.reply(ctx.message, "nice try")
            return
        
        embed = self.make_mute_embed(ctx.message.author, user, self.MUTE_TIME)

        vote_message = await self.bot.send_message(ctx.message.channel, embed=embed)
        
        for emoji in self.emojis.values():
            await self.bot.add_reaction(vote_message, emoji)

        # add vote to vote list
        self.votes[vote_message.id] = {
            "time": time.time() + self.MUTE_TIME,
            "votes": 0,
            "message": vote_message,
            "author": ctx.message.author,
            "target": user,
            "type": VoteTypes.MUTE
        }

    def is_valid_reaction(self, emoji: str, message: discord.Message, user: discord.User) -> bool:
        if (user == self.bot.user):
            return False

        if (message.id not in self.votes):
            return False

        if (emoji not in self.emojis.values()):
            return False

        return True

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        message = reaction.message
        emoji = reaction.emoji

        if (not self.is_valid_reaction(emoji, message, user)):
            return

        if (emoji == self.emojis["yes"]):
            self.votes[message.id]["votes"] += 1
        elif (emoji == self.emojis["no"]):
            self.votes[message.id]["votes"] -= 1

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
            await self.bot.clear_reactions(vote["message"])
            total = vote["votes"]

            del self.votes[message_id]

            embed = self.make_mute_embed(vote["author"], vote["target"], -1)
            await self.bot.edit_message(vote["message"], embed=embed)

            if (total > 0):
                await self.bot.send_message(vote["message"].channel,
                    f"{vote['author'].mention}'s vote to mute {vote['target'].mention} passed, muting them for {self.MUTE_TIME} seconds")

                try:
                    await self.bot.server_voice_state(vote["target"], mute=True)
                except discord.Forbidden:
                    await self.bot.send_message(vote["message"].channel, "I don't have permissions to mute")
                except discord.HTTPException as e:
                    await self.bot.send_message(vote["message"].channel, f"HTTPException: `{e}`")

                self.muted_members[vote["target"].id] = {
                    "time": time.time() + self.MUTE_TIME,
                    "channel": vote["message"].channel,
                    "member": vote["target"]
                }
            elif (total < 0):
                await self.bot.send_message(vote["message"].channel,
                    f"{vote['author'].mention}'s vote to mute {vote['target'].mention} failed, no action taken")
            else:
                await self.bot.send_message(vote["message"].channel,
                    f"{vote['author'].mention}'s vote to mute {vote['target'].mention} tied, no action taken")
        else:
            embed = self.make_mute_embed(vote["author"], vote["target"], int(vote["time"] - time.time()))
            await self.bot.edit_message(vote["message"], embed=embed)

    async def vote_think(self):
        await self.bot.wait_until_ready()

        while (not self.bot.is_closed):
            try:
                vote_copy = self.votes.copy()

                for message_id, vote in vote_copy.items():
                    if (vote["type"] == VoteTypes.MUTE):
                        await self.handle_mute(message_id, vote)

                vote_copy.clear()

                muted_members = self.muted_members.copy()

                for member_id, muted_dict in muted_members.items():
                    if (muted_dict["time"] < time.time()):
                        await self.bot.send_message(muted_dict["channel"], f"{muted_dict['member'].mention}'s mute expired, unmuting")

                        try:
                            await self.bot.server_voice_state(vote["target"], mute=False)
                        except discord.Forbidden:
                            await self.bot.send_message(muted_dict["channel"], "I don't have permissions to unmute")
                        except discord.HTTPException as e:
                            await self.bot.send_message(muted_dict["channel"], f"HTTPException: `{e}`")

                        del self.muted_members[member_id]
            except Exception as e:
                self.bot.bot_utils.log_error_to_file(e)

            await asyncio.sleep(10)

def setup(bot):
    bot.add_cog(Vote(bot))