# CBot

[<img src="https://img.shields.io/badge/discord-py-blue.svg">](https://github.com/Rapptz/discord.py)

Work-in-progress Discord bot. Mainly a learning experience. Currently only Linux is supported.
For general questions, feel free to contact me on Discord: Frost#0261

## Requirements

* Python 3.6
* [discord.py](https://github.com/Rapptz/discord.py)
* All the modules defined in requirements.txt: `pip install -r requirements.txt`
* [FFmpeg](https://www.ffmpeg.org)
* [ImageMagick](https://www.imagemagick.org)

## Creating the bot

1. Go the to [Discord Applications Page](https://discordapp.com/developers/applications) and click "Create an application". If you've already created a bot and know the Token, [skip to the next section](#running-the-bot).
2. Name your application, it can be anything, and click "Save Changes" at the bottom of the page.
3. On the left under "Settings", click the "Bot" tab.
4. Click "Add Bot"
5. Under the username box you'll see your token, copy it, you'll need it to run the bot. **Do not share this with anyone.** This is effectively the password for your bot. For an example of how the token will look, see [example.yml](https://github.com/FFrost/CBot/blob/master/example.yml)

## Running the bot

1. Run CBot.py: `python3 cbot.py`
2. CBot will ask for your bot token, enter it now
3. When prompted for your Discord ID, you might not know it yet. If you do, enter it now; if not, leave it blank, and after running CBot, you can find it using the `!info` command. Enter it into the config file (`cbot.yml`) on the line `dev_id: 'enter your id here'`

## Inviting the bot to your server

0. If you can message the bot, using the `!invite` command is the easiest way to invite the bot to a server. Otherwise, follow the rest of the steps.
1. Find the bot's client ID. There are several ways to do this:
	* The easiest way is to go back to the [Discord applications page](https://discordapp.com/developers/applications) and select your bot application
		* Under the `General Information` tab, find the `Client ID`
	* When you run CBot, it'll print its Discord ID and discriminator to the command line: `Logged in as CBot#0000 [101010101010101010]`
	* Or you can use the info command and @ CBot to get the bot's info: `!info @CBot` and note the ID: `ID: 101010101010101010`
2. Replace `YOUR_ID_HERE` with the ID you just found: `https://discordapp.com/oauth2/authorize?client_id=YOUR_ID_HERE&scope=bot` and navigate to the page
	* If you want to invite the bot with the permissions already applied, use this link instead: `https://discordapp.com/oauth2/authorize?client_id=YOUR_ID_HERE&scope=bot&permissions=3271744`, however you will need to have [2-Factor Authentication](https://support.discordapp.com/hc/en-us/articles/219576828-Setting-up-Two-Factor-Authentication) enabled on your Discord account, as the `Manage Messages` permission requires it. 
	* If you don't want to enable 2FA, change the permissions to `permissions=3263552` and apply the `Manage Messages` permissions after the bot has joined your server.
3. Choose what server you want CBot to join (this will require you to have `Manage Server` permissions on the server, so if a server doesn't show on the list, you probably don't have the proper permissions)
4. Done! CBot doesn't require any special permissions for the most part, but without them some commands won't be fully functional. For a full list of permissions CBot requires, see `permissions.md`

## Troubleshooting

* If you're getting this error when trying to run the bot: `discord.errors.LoginFailure: Improper token has been passed.`, delete `cbot.yml`, run the bot again and reenter your bot token
	* If you're still getting this error even after deleting `cbot.yml`, ensure your config file looks like the sample config [example.yml](https://github.com/FFrost/CBot/blob/master/example.yml)