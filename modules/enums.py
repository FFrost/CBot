from enum import Enum

class Enums:
    DISCORD_MAX_FILESIZE = 10 * 1024 * 1024
     
    class LiquidCodes(Enum):
        SUCCESS = 1
        MAX_FILESIZE = 2
        INVALID_FORMAT = 3
        MAX_DIMENSIONS = 4
        BAD_URL = 5
        MISC_ERROR = 6