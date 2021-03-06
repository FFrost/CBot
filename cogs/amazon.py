import discord
from discord.ext import commands

from modules import utils

import aiohttp
import re
from lxml import html
from typing import Optional

class Amazon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.amazon_url_regex = re.compile(r"(https?:\/\/)?(www\.)?(amazon)\.(com|co\.uk|ca|de|fr|co\.jp|br|at|it|es|cn|nl|in)(\.(mx|au))?\/(\S)+", re.IGNORECASE)

    @commands.Cog.listener()
    async def on_message(self, message):
        if (not self.bot.CONFIG["embeds"]["enabled"] or not self.bot.CONFIG["embeds"]["amazon"]):
            return

        try:
            if (not message.content or not message.author):
                return

            url = self.has_amazon_url(message.content)

            if (url):
                embed = await self.create_amazon_embed(message.author, url)

                if (embed):
                    try:
                        await message.channel.send(embed=embed)
                    except discord.errors.HTTPException:
                        pass

        except Exception as e:
            self.bot.bot_utils.log_error_to_file(e, prefix="Amazon")

    def has_amazon_url(self, content: str) -> Optional[str]:
        try:
            return (self.amazon_url_regex.search(content).group(0))
        except Exception:
            return None

        return None

    async def get_item_page(self, url: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    if (r.status != 200):
                        return None

                    return await r.text()

        except Exception:
            return None

    @staticmethod
    def get_element(tree: html.HtmlElement, expression: str) -> Optional[str]:
        path = tree.xpath(expression)

        if (not path):
            return None

        if (isinstance(path, list)):
            path = path[0]

        return path.strip()

    @staticmethod
    def get_description_list(tree: html.HtmlElement) -> Optional[str]:
        path = tree.xpath("//div[@id='feature-bullets']/ul/li")

        if (path is None or not isinstance(path, list) or len(path) < 1):
            return None

        description = []

        for p in path:
            try:
                description.append(p.text_content().strip())

            except AttributeError:
                pass

        if (not description):
            return None

        if (description[0].startswith("Make sure this fits")):
            description.pop(0)

        return "\n".join("- {}".format(d) for d in description)

    async def create_amazon_embed(self, user: discord.User, url: str) -> discord.Embed:
        page = await self.get_item_page(url)

        if (page is None):
            return None

        tree = html.fromstring(page)

        if (tree is None):
            return None

        embed = discord.Embed(color=discord.Color.dark_orange())

        embed.set_author(name=user.name, icon_url=user.avatar_url)

        title = tree.get_element_by_id("productTitle").text_content()

        if (title is None):
            title = "Unknown item"

        embed.title = title

        image = self.get_element(tree, "//img[@id='landingImage']/@data-old-hires")

        if (image is not None):
            embed.set_thumbnail(url=image)
        
        description = self.get_description_list(tree)

        if (not description):
            description = ""
        else:
            description = utils.cap_string_and_ellipsis(description, length=240, num_lines=4)

        embed.description = description

        price = self.get_element(tree, "//span[@id='priceblock_ourprice']/text()")
        buying_price = self.get_element(tree, "//span[@class='buyingPrice']/text()")

        if (price):
            embed.add_field(name=":dollar: Price", value=price)
        elif (buying_price):
            embed.add_field(name=":dollar: Price", value=f"${buying_price}")
        else:
            price = tree.get_element_by_id("priceblock_dealprice").text_content()

            if (price is not None):
                price_element = tree.get_element_by_id("price")

                if (price_element):
                    original_price = price_element.find_class("a-text-strike")

                    if (original_price):
                        if (isinstance(original_price, list)):
                            original_price = original_price[0]

                        original_price = original_price.text_content().strip()
                        embed.add_field(name=":dollar: Price", value=f"~~{original_price}~~")
                
                embed.add_field(name=":money_mouth: Price with deal", value=price)

        rating = self.get_element(tree, "//span[@id='acrPopover']/@title")

        num_reviews = tree.get_element_by_id("acrCustomerReviewText").text_content()

        if (rating is not None):
            embed.add_field(name=":star: Rating", value=rating)

            if (num_reviews is not None):
                embed.add_field(name=":pencil: Number of Reviews", value=num_reviews)

        return embed

def setup(bot):
    bot.add_cog(Amazon(bot))
