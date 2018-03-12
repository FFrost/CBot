from enum import Enum

DISCORD_MAX_FILESIZE = 10 * 1024 * 1024
 
IMAGESEARCH_TIME_TO_WAIT = 5 * 60 # 5 minutes

class ImageCodes(Enum):
    SUCCESS = 1
    MAX_FILESIZE = 2
    INVALID_FORMAT = 3
    MAX_DIMENSIONS = 4
    BAD_URL = 5
    MISC_ERROR = 6
    NO_PERMISSIONS = 7