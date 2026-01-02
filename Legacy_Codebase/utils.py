import time

def mtime_to_fat(mtime):
    """Convert from the mtime returned by os.stat to rockbox's mtime."""
    year, month, day, hour, minute, second = time.localtime(mtime)[:-3]
    year = year - 1980
    date = 0
    date |= (year << 9)
    date |= (month << 5)
    date |= day
    tim = 0
    tim |= (hour << 11)
    tim |= (minute << 5)
    tim |= second
    total = (date << 16) | tim
    return total

def fat_to_mtime(fat):
    """Convert from rockbox's mtime to the mtime returned by os.stat."""
    date = fat >> 16
    tim = fat & 0x0000FFFF
    year = ((date >> 9) & 0x7F) + 1980
    month = (date >> 5) & 0x0F
    day = date & 0x1F
    hour = (tim >> 11) & 0x1F
    minute = (tim >> 5) & 0x3F
    second = tim & 0x1F
    t = time.mktime((year, month, day, hour, minute, second, -1, -1, -1))
    return t
