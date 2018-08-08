DEFAULT_CONFIG = {
    # tracker network api key (for fortnite stats command, https://fortnitetracker.com/site-api)
    "trn_api_key": "",

    # api key for steam (https://steamcommunity.com/dev/apikey)
    "steam_api_key": "",

    # time in seconds to wait before removing inactive image searches
    "IMAGESEARCH_TIME_TO_WAIT": 60,

    # cooldown in seconds in between editing the image search embed when scrolling between pages
    "IMAGESEARCH_COOLDOWN_BETWEEN_UPDATES": 1,

    # max number of messages to purge at once
    "MAX_PURGE": 20,

    # how long to keep siege stats cached in seconds
    "SIEGE_CACHE_TIME": 120,

    # youtube-dl options
    "YOUTUBEDL": {
        # enable the youtube-dl command to let users download mp3s using the bot
        "ENABLED": True,

        # max video length in seconds, any video longer than this will be ignored
        "MAX_VIDEO_LENGTH": 1800,

        # where to temporarily store the downloaded mp3s
        "DOWNLOAD_DIRECTORY": "/tmp/cbot"
    },

    # can other people use the !invite command to invite the bot to their own servers
    "BOT_CAN_BE_INVITED": True
}