from enum import Enum

DISCORD_MAX_FILESIZE = 10 * 1024 * 1024
 
IMAGESEARCH_TIME_TO_WAIT = 5 * 60 # 5 minutes

# how long to wait in between editing the image search embed when scrolling
# between pages, 1 second
IMAGESEARCH_COOLDOWN_BETWEEN_UPDATES = 1

DISCORD_MAX_MESSAGE_LENGTH = 2000 # max characters in a discord message
DISCORD_MAX_MENTION_LENGTH = 21 # max length a mention of a user can be ("<@id>") where id is the 18 digit id of the user

class ImageCodes(Enum):
    SUCCESS = 1
    MAX_FILESIZE = 2
    INVALID_FORMAT = 3
    MAX_DIMENSIONS = 4
    BAD_URL = 5
    MISC_ERROR = 6
    NO_PERMISSIONS = 7