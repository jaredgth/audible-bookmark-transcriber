import math


def format_time(milliseconds):
    hours = math.floor(milliseconds / (1000 * 60 * 60))
    minutes = math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
    seconds = math.floor(((milliseconds % (1000 * 60 * 60)) % (1000 * 60)) / 1000)
    millis = milliseconds % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"
