#!/usr/bin/env/python
# -*- coding: UTF-8 -*-
from __future__ import print_function, division
from sys import argv
from os import remove
from platform import system
from sys import version as py_ver
if int(py_ver[0]) >= 3:
    from urllib.request import Request, urlopen, URLError
else:
    from urllib2 import Request, urlopen, URLError

import time
import pygame
import praw

# Import external settings files:
import settings
import translations


'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' Python based magic mirror application, based on pygame  '
' library as well as Reddit and BOM weather data.         '
' Licensed under MIT license.                             '
'                                                         '
'                              (c) Jackson Sommerich 2016 '
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''


def fetch_weather_info():
    '''
    fetch_weather_info() -> parse_weather_info()
    See _parse_weather_info for more details on return type.

    Fetches weather info and manages request frequency and data saving.
    To get weather info call this function, not _parse_weather_info unless
    you know what you're doing and don't require flood control or saved
    data return.
    '''

    # Planned features:
    #  - Ability to use multiple services

    save_path = settings.saved_weather_data_path
    try:
        with open(save_path, "r") as save_data:
            # Get elapsed time since update and check against update delay:
            time_since_check = time.time() - int(save_data.readline())
            if time_since_check > settings.weather_update_delay:
                # Raises to trigger data update in except clause:
                raise IOError
            else:
                result = str(save_data.read())

    # Exception if weather_data can't be opened:
    except(IOError, FileNotFoundError):
        # Fetch data from a URL and save it to weather_data,
        # then call self:
        with open(save_path, "w") as save_data:
            current_time = str(int(time.time()))
            try:
                bom_data = urlopen(Request(
                    settings.weather_url)).read().decode("utf-8")
            except URLError:
                print("No network connection.")
                save_data.close()
                remove(save_path)
                pygame.quit()
                quit()
            save_data.write("{}\n{}".format(current_time, bom_data))
        return fetch_weather_info()
    except ValueError:
        print("Error in file, deleting and retrying download.")
        remove(save_path)
        return fetch_weather_info()
    # Return resulting weather data after parsing:
    return parse_weather_info(settings.weather_city, result)


def parse_weather_info(city, data):
    '''parse_weather_info(city, data) -> (city, temperature, description, icon)

    Parses bureau of meteorology IDA00100.dat file from their FTP server and
    returns city name, temperature, current conditions and the appropriate
    icon to represent the weather. Call through fetch_weather_info().
    '''

    # Planned features:
    #  - distinguising between night and day
    #  - 7-day forecast

    # Initialise variables, index = position of the city in the string,
    # also acts as the cursor to the string:

    # Capitolise city name (just in case):
    city = city.title()
    string, result, index = "", [], data.find(city)
    while True:
        # Add the next letter to the string and increment the cursor by 1:
        string = string + data[index]
        index += 1

        # "#" is the seperator character in the IDX00100.dat file supplied
        # by the ABS. This seperates each data entry.
        if string[-1] == "#":
            result.append(string[0:-1])
            string = ""
            continue

        # Newline indicaates moving to the next city:
        if string[-1] == "\n":
            break

    # Converts the description (last entry in the IDA00100.dat file) to
    # lower-case, an array of weather conditions is then used to find
    # a single-word descriptor of the current weather for use as a
    # weather icon as none is supplied.
    # Typical...
    description = result[-1].lower()
    condition = [condition for condition in translations.conditions
                 if description.find(condition) != -1]

    # Format the condition for a picture descriptor by looking in a
    # predefined dictionary (located in weather settings), which
    # contains the appropriate icon for the found descriptor
    if len(condition) != 0:
        condition = translations.translation[condition[0]]

    # If the description doesn't contain relevant info then use
    # a gigantic question mark picture because again, no single
    # word weather info is supplied.
    else:
        condition = u""
    temperature, description = result[-2], result[-1].title()

    return (city, temperature, description, condition)


def get_news(sub, limit=settings.item_count):
    '''get_news(subreddit: str) -> news: [str]'''
    user_agent = settings.user_agent.format(system(), settings.version)
    reddit, result = praw.Reddit(user_agent=user_agent), {}
    submission = reddit.get_subreddit(sub).get_top_from_day(limit=limit)
    result = []
    for story in submission:
        result.append(story.title)
    return result


def truncate(text, title=False, length=100):
    '''truncate(text, title: bool, length: int, suffix: str) -> unicode'''
    if title:
        text = text.title()
    if len(text) <= length:
        if (text[-1] != "?" or "." or "!" or ":") and not title:
            return u"{}{}".format(text, ".")
        else:
            return u"{}".format(text)
    else:
        return u" ".join(text[:length+1].split(" ")[:-1]) + u"…"


def get_weather_display(font, colour):
    '''returns the imagery and text for the weather display'''
    width, height = settings.resolution
    # fetches data for weather info:
    weather_info = fetch_weather_info()
    # Sets text for weather info, (text, antialiasing, colour, [background]):
    # city_text, temp_text, condition_text, weather_icon then positions
    weather_text = (
        font[5].render(weather_info[3][0], 1, colour[2]),
        font[1].render(weather_info[0], 1, colour[2]),
        font[2].render("{}\xb0c".format(weather_info[1]), 1, colour[2]),
        font[3].render(str(weather_info[2]), 1, colour[2])
        )
    weather_text_pos = (
        weather_text[0].get_rect(left=width/100, top=weather_info[3][1]),
        weather_text[1].get_rect(left=1, top=width*-0.008),
        weather_text[2].get_rect(right=width/4.5, top=height/3.50),
        weather_text[3].get_rect(right=width/4.5, top=height/2.70)
        )
    return (weather_text, weather_text_pos)


def get_alt_news_display(font, colour):
    '''returns news text and rects'''
    width, height = settings.resolution
    subs = settings.subreddits
    news, stories, stories_pos, subreddit, subreddit_pos = [], [], [], [], []
    for sub in subs:
        news = []
        news.extend(get_news(sub))
        for story in news:
            subreddit.append(font[4].render(truncate(sub, title=True), 1, colour[2]))
            subreddit_pos.append(subreddit[-1].get_rect(left=0, bottom=height*0.95))
            stories.append(font[3].render(truncate(story), 1, colour[2]))
            stories_pos.append(stories[-1].get_rect(
                left=10, bottom=height))
            story_right_edge = stories_pos[-1][2]
            # Check if the news item is wider than the screen edge:
            if story_right_edge > width:
                cuts = 0
                # Repeatedly truncate() the text until it fits:
                while story_right_edge > width:
                    stories[-1] = font[3].render(
                        truncate(story, length=len(story)-cuts), 1, colour[2])
                    stories_pos[-1] = stories[-1].get_rect(left=0, bottom=height)
                    story_right_edge = (stories_pos[-1][2] + 10)
                    cuts += 1
    return (subreddit, subreddit_pos, stories, stories_pos)


def get_news_display(font, colour):
    '''returns news text and rects'''
    width, height = settings.resolution
    subs = settings.subreddits
    sub_offset, news, stories, stories_pos = -10, [], [], []
    for sub in subs:
        news = []
        news.extend(get_news(sub))
        sub_offset += int((10/600)*height)
        stories.append(font[4].render(truncate(sub, title=True), 1, colour[2]))
        stories_pos.append(stories[-1].get_rect(left=width/3.6, top=sub_offset))
        sub_offset += int((34/600)*settings.resolution[1])
        for story in news:
            stories.append(font[3].render(truncate(story), 1, colour[2]))
            stories_pos.append(stories[-1].get_rect(
                left=width/3.41, top=sub_offset))
            story_right_edge = (stories_pos[-1][2] + width / 3.41)
            # Check if the news item is wider than the screen edge:
            if story_right_edge > width - width / 40:
                cuts = 0
                # Repeatedly truncate() the text until it fits:
                while story_right_edge > width - width / 40:
                    stories[-1] = font[3].render(
                        truncate(story, length=(len(story)-cuts)), 1, colour[2])
                    stories_pos[-1] = stories[-1].get_rect(
                        left=width/3.41, top=sub_offset)
                    story_right_edge = (stories_pos[-1][2] + width / 3.41)
                    cuts += 1
            sub_offset += int((26/600)*height)
            # Check if the next news item will run off the screen:
            if sub_offset >= height-(26/600)*height+1:
                break
    return (stories, stories_pos)


def get_display_mode():
    '''returns the desired display mode integer'''
    try:
        mode = argv[1]
    except IndexError:
        return translations.modes[settings.def_disp_mode]
    try:
        return translations.modes[mode]
    except KeyError:
        print(translations.disp_err_str.format(mode, settings.def_disp_mode))
        return translations.modes[settings.def_disp_mode]


def get_framerate(font, clock):
    '''Returns framerate font item and rect item'''
    fps = font[3].render(
        "{} fps. Press Esc to quit.".format(
            int(clock.get_fps())), 1, translations.colour[1]
        )
    fps_pos = fps.get_rect(right=settings.resolution[0], top=0)
    return (fps, fps_pos)


def check_events(events):
    '''Checks for keyboard events and quits if necessary'''
    for event in events:
        # 2 = pygame.KEYDOWN, 27 = pygame.K_ESCAPE
        if event.type == 2 and event.key == 27:
            pygame.quit()
            quit()


def main():
    '''main() -> None
    UI of the program, calls all other modules.
    '''

    # Planned features:
    #  - Multiple weather sources
    #  - Icons to text (using OW font)
    #  - Automatic on/off based on motion/light sensor

    pygame.init()
    refresh, last_refresh_time = True, 0
    # Resoltion, hardcoded, don't change, will probably break things:
    width, height = settings.resolution
    # Initialise the fonts and colours from translations.py:
    colour = translations.colour
    font = [pygame.font.Font(ttf, size) for ttf, size in translations.fonts]
    # Enables clock, used for frame rate limiter:
    game_clock = pygame.time.Clock()
    # Initialises the display
    screen = pygame.display.set_mode((width, height), get_display_mode())
    pygame.mouse.set_visible(settings.mouse_visible)
    screen.fill(colour[0])
    load_str = font[0].render(translations.loading_text, 1, colour[2])
    screen.blit(load_str, load_str.get_rect(centerx=width/2, centery=height/2))
    pygame.display.flip()
    while True:
        time_since_refresh = int(time.time()) - last_refresh_time
        # Sets the framerate (located in settings.py), 0 = no limit:
        if settings.fps_limit != 0:
            game_clock.tick(settings.fps_limit)
        else:
            game_clock.tick()
        # Checks to see if the information needs to be refreshed:
        if refresh:
            # Gets the weather
            weather, weather_pos = get_weather_display(font, colour)
            # Gets the news
            if settings.bottom_feed:
                sub, sub_pos, story, story_pos = get_alt_news_display(font, colour)
                story_number, story_disp_time = 0, time.time()
            else:
                story, story_pos = get_news_display(font, colour)
            refresh = False
            last_refresh_time = int(time.time())
        # Checks for keyboard events (quit), no return:
        check_events(pygame.event.get())
        # Draws the background:
        screen.fill(colour[0])
        # Blits each element to the screen:
        for item, item_pos in zip(weather, weather_pos):
            screen.blit(item, item_pos)
        if settings.bottom_feed:
            screen.blit(sub[story_number], sub_pos[story_number])
            screen.blit(story[story_number], story_pos[story_number])
            if time.time() - story_disp_time >= settings.refresh_time:
                story_number = (story_number + 1) % settings.item_count
                story_disp_time = time.time()
        else:
            for item, item_pos in zip(story, story_pos):
                screen.blit(item, item_pos)
        # Renders the fps counter:
        if settings.display_framerate is True:
            fps, fps_pos = get_framerate(font, game_clock)
            screen.blit(fps, fps_pos)
        # Renders the total display:
        pygame.display.flip()
        if time_since_refresh >= settings.update_delay:
            refresh = True


if __name__ == '__main__':
    main()
