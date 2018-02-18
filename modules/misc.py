import aiohttp
from lxml import html

class Misc:
    def __init__(self, bot):
        self.bot = bot
        
    # get insults from insult generator
    # output: string; the insult if found or "fucker"
    async def get_insult(self):
        try:
            conn = aiohttp.TCPConnector(verify_ssl=False) # for https
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get("https://www.insult-generator.org/") as r:
                    if (r.status != 200):
                        return "fucker"
                    
                    tree = html.fromstring(await r.text())            
                    p = tree.xpath("//div[@class='insult-text']/text()")
                    
                    if (isinstance(p, list)):
                        ret = p[0]
                    elif (isinstance(p, str)):
                        ret = p
                    else:
                        return "fucker"
                    
                    ret = ret.strip()
                        
                    if (not ret):
                        return "fucker"
                
                    return ret
        
        except Exception:
            return "fucker"