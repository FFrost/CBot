# CBot

[<img src="https://img.shields.io/badge/discord-py-blue.svg">](https://github.com/Rapptz/discord.py)
[![PyPI](https://img.shields.io/pypi/pyversions/discord.py.svg)](https://pypi.python.org/pypi/discord.py/)

Work-in-progress Discord bot. Mainly a learning experience. Currently only Linux is supported.

## Requirements

* Python 3.4+
* [discord.py](https://github.com/Rapptz/discord.py)
* All the modules defined in requirements.txt: `pip install -r requirements.txt`

## Running the bot

1. Go to the [Discord applications page](https://discordapp.com/developers/applications/me) and click "New App"
2. Name the app and click "Create App"
3. Scroll down and click on "Create a Bot User"
4. Make note of the token (looks like a string of numbers and letters, you'll need to click on it to reveal it)
5. Run CBot.py: `python3 cbot.py` (for a specific version of Python ex 3.5: `python3.5 cbot.py`)
6. CBot will ask for your bot token, enter it now
7. When prompted for your Discord ID, you might not know it. If you do, enter it now; if not, leave it blank, and after running CBot, you can find it by typing !info to the bot. Enter it into the config file (`cbot.yml`) on the line `dev_id: 'enter your id here'`

## Troubleshooting

* If you're getting this error when trying to run the bot: `discord.errors.LoginFailure: Improper token has been passed.`, delete cbot.yml and reenter your token