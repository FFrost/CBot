import discord

from . import utils

import asyncio, aiohttp
import re
from lxml import html

amazon_url_regex = re.compile(r"(https?:\/\/)?(www\.)?(amazon)\.(com|co\.uk|ca|de|fr|co\.jp|br|at|it|es|cn|nl|in)(\.(mx|au))?\/(\S)+", re.IGNORECASE)

def is_amazon_url(url):
    return (amazon_url_regex.match(url) is not None)

async def get_item_page(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if (r.status != 200):
                    return None

                return await r.text()

    except Exception:
        return None

def get_element(tree, expression):
    path = tree.xpath(expression)

    if (not path):
        return None

    if (isinstance(path, list)):
        path = path[0]

    return path.strip()

def get_description_list(tree):
    path = tree.xpath("//div[@id='feature-bullets']/ul/li")

    if (path is None or not isinstance(path, list) or len(path) < 1):
        return None

    description = []

    for p in path:
        try:
            description.append(p.text_content().strip())

        except Exception:
            continue

    if (not description):
        return None

    return "\n".join("- {}".format(d) for d in description)

async def create_amazon_embed(user, url):
    page = await get_item_page(url)

    if (page is None):
        return None

    tree = html.fromstring(page)

    if (tree is None):
        return None

    embed = discord.Embed()

    embed.set_author(name=user.name, icon_url=user.avatar_url)
    
    embed.color = discord.Color.dark_orange()

    title = get_element(tree, "//span[@id='productTitle']/text()")

    if (title is None):
        title = "Unknown item"

    embed.title = title

    image = get_element(tree, "//img[@id='landingImage']/@data-old-hires")

    if (image is not None):
        embed.set_thumbnail(url=image)
    
    description = get_description_list(tree)

    if (not description):
        description = ""
    else:
        description = utils.cap_string_and_ellipsis(description, length=240, num_lines=4)

    embed.description = description

    price = get_element(tree, "//span[@id='priceblock_ourprice']/text()")

    if (price is None):
        price = "$???"

    embed.add_field(name=":dollar: Price", value=price)

    rating = get_element(tree, "//span[@id='acrPopover']/@title")

    num_reviews = get_element(tree, "//span[@id='acrCustomerReviewText']/text()")

    if (rating is not None):
        embed.add_field(name=":star: Rating", value=rating)

        if (num_reviews is not None):
            embed.add_field(name=":pencil: Number of Reviews", value=num_reviews)

    return embed