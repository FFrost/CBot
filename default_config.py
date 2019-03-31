DEFAULT_CONFIG = {
    # tracker network api key (for fortnite stats command, https://fortnitetracker.com/site-api)
    "trn_api_key": "",

    # api key for steam (https://steamcommunity.com/dev/apikey)
    "steam_api_key": "",

    # image search options
    "image_search": {
        # time in seconds to wait before removing inactive image searches
        "time_to_wait": 60,

        # cooldown in seconds in between editing the image search embed when scrolling between pages
        "cooldown_between_updates": 1,
    },

    # max number of messages to purge at once
    "max_purge": 20,

    # youtube-dl options
    "youtube-dl": {
        # enable the youtube-dl command to let users download mp3s using the bot
        "enabled": True,

        # max video length in seconds, any video longer than this will be ignored
        "max_video_length": 1800,

        # where to temporarily store the downloaded mp3s
        "download_directory": "/tmp/cbot"
    },

    # can other people use the !invite command to invite the bot to their own servers
    "bot_can_be_invited": True,

    # should the bot insult people who at it
    "should_insult": True,

    # should the bot reply to '^ this'
    "should_this": True,

    # should the bot automatically send embeds
    "embeds": {
        "enabled": True,

        # steam embeds when a profile is linked
        "steam": True,

        # amazon embeds when a product is linked
        "amazon": True
    },

    # siege cog options
    "siege": {
        # how long to keep siege stats cached in seconds
        "cache_time": 120,

        # email and password for uplay account, used to get ticket
        "email": "",
        "password": "",

        # base64 encoded string "email:password" used for ubisoft api
        "ticket": ""
    },

    # admin settings
    "admin": {
        # what channel should the bot send administrative log messages to, leave blank to disable
        "log_channel": "admin",
    }
}
