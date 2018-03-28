# CBot

[<img src="https://img.shields.io/badge/discord-py-blue.svg">](https://github.com/Rapptz/discord.py)

Work-in-progress Discord bot. Mainly a learning experience. Currently only Linux is supported.

## Requirements

* Python 3.5+
* [discord.py](https://github.com/Rapptz/discord.py)
* All the modules defined in requirements.txt: `pip install -r requirements.txt`

## Running the bot

1. Go to the [Discord applications page](https://discordapp.com/developers/applications/me) and click "New App". If you've already done this and know the Token, skip to step 5
2. Name the app and click "Create App"
3. Scroll down and click "Create a Bot User"
4. Scroll down to the "Bot" section, find "Token" and click to reveal it. Make note of this, you'll need it for the next steps. **Do not share this with anyone.** This is effectively the password for your bot. For an example of how the token will look, see `example.yml`
5. Run CBot.py: `python3 cbot.py` (for a specific version of Python ex 3.5: `python3.5 cbot.py`)
6. CBot will ask for your bot token, enter it now
7. When prompted for your Discord ID, you might not know it yet. If you do, enter it now; if not, leave it blank, and after running CBot, you can find it using the `!info` command. Enter it into the config file (`cbot.yml`) on the line `dev_id: 'enter your id here'`

## Inviting the bot to your server

1. Find the bot's client ID. There are several ways to do this:
	* When you first run CBot, it'll print it's Discord ID and discriminator to the command line: `Logged in as CBot#0000 [101010101010101010]`
	* Or you can simply use the info command and @ CBot to get the bot's info: `!info @CBot` and note the ID: `ID: 101010101010101010`
2. Replace `YOUR_ID_HERE` with the ID you just found: `https://discordapp.com/oauth2/authorize?client_id=YOUR_ID_HERE&scope=bot` and navigate to the page
3. Choose what server you want CBot to join (this will require you to have `Manage Server` permissions on the server, so if a server doesn't show on the list, you probably don't have the proper permissions)
4. Done! CBot doesn't require any special permissions for the most part, but without these some commands won't be fully functional. For a full list of permissions CBot requires, see `permissions.md`

## Troubleshooting

* If you're getting this error when trying to run the bot: `discord.errors.LoginFailure: Improper token has been passed.`, delete `cbot.yml`, run the bot again and reenter your bot token
	* If you're still getting this error even after deleting `cbot.yml`, ensure your config file looks like the sample config (`example.yml`)