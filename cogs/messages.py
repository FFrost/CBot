import discord
from discord.ext import commands

from random import randint

import time

class Messages:
    def __init__(self, bot):
        self.bot = bot

        self.times = {}
        self.cooldown = 2

    async def on_message(self, message):
        if (not message.content or not message.author):
            return
        
        # don't respond to ourselves
        if (message.author == self.bot.user):
            return

        # ignore other bots
        if (message.author.bot):
            return

        # cooldown
        author_id = message.author.id

        if (author_id not in self.times):
            self.times[author_id] = 0
        
        if (self.times[author_id] > time.time()):
            return

        self.times[author_id] = time.time() + self.cooldown

        # insult anyone who @s us
        if (self.bot.user in message.mentions and not message.mention_everyone and not message.content.startswith("!")):
            await self.bot.bot_utils.output_log(message)
            
            if (self.bot.CONFIG["should_insult"]):
                insult = await self.bot.misc.get_insult()
                an = "an" if (insult[0].lower() in "aeiou") else "a"
                await self.bot.messaging.reply(message, "you're {an} {insult}.".format(an=an, insult=insult))
                return
        
        # respond to "^ this", "this", "^", etc.
        if (self.bot.CONFIG["should_this"]):
            if (message.content.startswith("^") or message.content.lower() == "this"):
                if (message.content == "^" or "this" in message.content.lower()):
                    this_msg = "^"
                    
                    if (randint(0, 100) < 50):
                        this_msg = "^ this"
                    
                    await self.bot.bot_utils.output_log(message)
                    await self.bot.send_message(message.channel, this_msg)
                    return

        if (message.content.lower() == "f"):
            await self.bot.send_message(message.channel, "F")
            return

        if ("thanks for the invite" in message.content.lower()):
            await self.bot.messaging.reply(message, "shut the fuck up")
            return

        if (message.content.lower() == "a"):
            await self.bot.messaging.reply(message, "shut up dex")
            return

def setup(bot):
    bot.add_cog(Messages(bot))