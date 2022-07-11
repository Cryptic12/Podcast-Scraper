from enum import Enum
import feedparser
import os
import string
import json
import time
from alive_progress import alive_bar
from mutagen.mp3 import EasyMP3 as MP3
import urllib


CONFIG = "config.json"


class ConfigFields(Enum):
    NEW_EPISODES_DIR = "new_episodes_dir"
    OLD_EPISODES_DIR = "old_episodes_dir"
    RSS_ADDRESS = "rss_address"
    DATE_LAST_RUN = "date_last_run"
    DATE_FORMAT = "date_format"


def get_config():
    with open(CONFIG) as file:
        return json.load(file)


def parse_timestamp(config):
    return time.strptime(config[ConfigFields.DATE_LAST_RUN.value], config[ConfigFields.DATE_FORMAT.value])


def get_rss_data(config):
    """ Fetches the RSS file """
    # RSS_FILE = "Data/test.xml"
    # return feedparser.parse(RSS_FILE)
    print(
        f"Downloading RSS file from {config[ConfigFields.RSS_ADDRESS.value]}")
    return feedparser.parse(config[ConfigFields.RSS_ADDRESS.value])


def identify_new_podcasts(rss_data, timestamp):
    """ Identify the podcasts that have been added since the last time checked """
    new_podcasts = []

    for entry in rss_data.entries:
        if timestamp < entry.published_parsed:
            new_podcasts.append(entry)

    # Return the podcasts ordered oldest to newest
    new_podcasts.reverse()

    return new_podcasts


def cleanup_previous_batch(config):
    """ Moves the previous batch of podcasts into the location all others are stored """
    print("Cleaning up previously downloaded batch")
    previous_episodes = os.scandir(config[ConfigFields.NEW_EPISODES_DIR.value])
    for entry in previous_episodes:
        if entry.is_file():
            os.rename(entry.path, os.path.join(
                config[ConfigFields.OLD_EPISODES_DIR.value], entry.name))


def clean_title(title):
    allowed_chars = string.ascii_letters + string.digits + "\"'.! -_"
    return ''.join(
        (filter(lambda x: x in allowed_chars, title)))


def fetch_mp3(url, file_name):
    urllib.request.urlretrieve(
        url, file_name)


def count_files(dir):
    """ Count the number of files found in the given directory """
    count = 0
    list = os.scandir(dir)
    for location in list:
        if location.is_dir():
            count += count_files(location)
        else:
            count += 1

    return count


def format_podcast(file_location, count):
    audio = MP3(file_location)
    audio.tags['album'] = ['Abroad in Japan']
    audio.tags['artist'] = ['Abroad in Japan']
    audio.tags['albumartist'] = ['Abroad in Japan']
    audio.tags["genre"] = "Podcast"
    audio.tags['tracknumber'] = str(count)

    audio.save(v2_version=3)

    file_dir, file_name = os.path.split(file_location)
    new_file_location = os.path.join(file_dir, f'{count}. {file_name}')
    os.rename(file_location, new_file_location)


def download_podcasts(config, podcasts_to_download):
    cleanup_previous_batch(config)

    file_count = count_files(config[ConfigFields.OLD_EPISODES_DIR.value])
    print("Downloading new podcasts")

    with alive_bar(len(podcasts_to_download)) as bar:
        for podcast in podcasts_to_download:
            file_count += 1
            file_name = clean_title(podcast.title) + ".mp3"
            file_path = os.path.join(
                config[ConfigFields.NEW_EPISODES_DIR.value], file_name)

            url = ""
            for link in podcast.links:
                if link["rel"] == "enclosure":
                    url = link["href"]

            if len(url) == 0:
                print("Unable to identify url for :", podcast)

            fetch_mp3(url, file_path)
            format_podcast(file_path, file_count)
            bar()

    print("Downloading complete!")


def update_config(config, podcast):
    print("Updating config with most recent episodes release time")
    config[ConfigFields.DATE_LAST_RUN.value] = podcast["published"]
    with open(CONFIG, 'w') as f:
        json.dump(config, f, sort_keys=True, indent=4)


def main():

    config = get_config()
    TIMESTAMP = parse_timestamp(config)
    RSS_DATA = get_rss_data(config)
    NEW_PODCASTS = identify_new_podcasts(RSS_DATA, TIMESTAMP)

    if len(NEW_PODCASTS) == 0:
        print("No new podcasts found.")
        exit()

    print(f'{len(NEW_PODCASTS)} new podcast(s) found!')
    download_podcasts(config, NEW_PODCASTS)

    latest_podcast = NEW_PODCASTS[len(NEW_PODCASTS) - 1]
    update_config(config, latest_podcast)

    print("Finished")


if __name__ == "__main__":
    main()
