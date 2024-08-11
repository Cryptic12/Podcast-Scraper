
import urllib
from enum import Enum
from mutagen.mp3 import EasyMP3 as MP3
from alive_progress import alive_bar
import feedparser
import os
import string
import json
import time


CONFIG_FILE_PATH = "config.json"


class ConfigFields(Enum):
    NEW_EPISODES_DIR = "new_episodes_dir"
    OLD_EPISODES_DIR = "old_episodes_dir"
    RSS_ADDRESS = "rss_address"
    DATE_LAST_RUN = "date_last_run"
    DATE_FORMAT = "date_format"


class ConfigManager():
    config_path: str = ""
    config_fields: dict = {}

    def __init__(self, config_path):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        config = self._read_config_from_file(self.config_path)
        config_keys = config.keys()

        for key in ConfigFields:
            if key.value not in config_keys:
                raise KeyError(
                    f'Required config {key.value} missing from confing file')

            self.update_value(key.value, config[key.value])

    def _read_config_from_file(self, file_path):
        with open(file_path) as file:
            return json.load(file)

    def update_value(self, field, value):
        self.config_fields[field] = value

    def get_value(self, field):
        return self.config_fields[field]

    def save_config(self):
        with open(self.config_path, 'w') as file:
            json.dump(self.config_fields, file, sort_keys=True, indent=4)


class PodcastFetcher():

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def download_new_podcasts(self):
        rss_data = self.fetch_rss_data()
        new_podcasts = self.identify_new_podcasts(rss_data)
        self.prepare_for_new_downloads()
        if len(new_podcasts) > 0:
            self.download_podcasts(new_podcasts)

    def fetch_rss_data(self):
        return feedparser.parse(self.config_manager.get_value(ConfigFields.RSS_ADDRESS.value))

    def identify_new_podcasts(self, rss_data):
        last_run_timestamp = time.strptime(self.config_manager.get_value(
            ConfigFields.DATE_LAST_RUN.value), self.config_manager.get_value(ConfigFields.DATE_FORMAT.value))
        return list(filter(lambda entry: last_run_timestamp < entry.published_parsed, reversed(rss_data.entries)))

    def prepare_for_new_downloads(self):
        with os.scandir(self.config_manager.get_value(ConfigFields.NEW_EPISODES_DIR.value)) as previously_downloaded_episodes:
            for entry in previously_downloaded_episodes:
                if entry.is_file():
                    self.move_file_from_new_to_old(entry)

    def move_file_from_new_to_old(self, entry):
        os.rename(entry.path, os.path.join(
            self.config_manager.get_value(ConfigFields.OLD_EPISODES_DIR.value), entry.name))

    def download_podcasts(self, podcasts):

        previously_downloaded_count = self.count_previously_downloaded()
        with alive_bar(len(podcasts)) as bar:
            for podcast in podcasts:
                self.download_podcast(podcast)
                bar()

        self.format_new_podcasts(previously_downloaded_count)

    def count_previously_downloaded(self):
        return count_files(self.config_manager.get_value(ConfigFields.OLD_EPISODES_DIR.value))

    def download_podcast(self, podcast):
        url = self.identify_podcast_url(podcast)
        file_path = self.construct_podcast_file_path(podcast)

        if len(url) == 0:
            print("Unable to identify url for :", podcast)
            return

        self.fetch_mp3(url, file_path)
        self.config_manager.update_value(
            ConfigFields.DATE_LAST_RUN.value, podcast["published"])

    def identify_podcast_url(self, podcast):
        for link in podcast.links:
            if link["rel"] == "enclosure":
                return link["href"]

        return ""

    def construct_podcast_file_path(self, podcast):
        file_name = clean_title(podcast.title) + ".mp3"
        return os.path.join(self.config_manager.get_value(ConfigFields.NEW_EPISODES_DIR.value), file_name)

    def fetch_mp3(self, url, file_name):
        urllib.request.urlretrieve(
            url, file_name)

    def format_new_podcasts(self, previously_downloaded_count):
        with os.scandir(self.config_manager.get_value(ConfigFields.NEW_EPISODES_DIR.value)) as new_podcasts:
            new_podcasts_list = list(new_podcasts)
            new_podcasts_list.sort(
                key=lambda podcast: os.path.getctime(podcast))
            for podcast in new_podcasts_list:
                previously_downloaded_count += 1
                self.format_podcast(podcast.path, previously_downloaded_count)

    def format_podcast(self, podcast_path, podcast_number):
        self.update_tags(podcast_path, podcast_number)
        self.rename_podcast(podcast_path, podcast_number)

    def update_tags(self, podcast_path, podcast_number):
        audio = MP3(podcast_path)

        audio.tags['album'] = ['Abroad in Japan']
        audio.tags['artist'] = ['Abroad in Japan']
        audio.tags['albumartist'] = ['Abroad in Japan']
        audio.tags["genre"] = "Podcast"
        audio.tags['tracknumber'] = str(podcast_number)

        audio.save(v2_version=3)

    def rename_podcast(self, podcast_path, podcast_number):
        file_dir, file_name = os.path.split(podcast_path)
        new_file_location = os.path.join(
            file_dir, f'{podcast_number}. {file_name}')
        os.rename(podcast_path, new_file_location)


def count_files(dir):
    count = 0

    with os.scandir(dir) as directory_entries:
        for entry in directory_entries:
            if entry.is_dir():
                count += count_files(entry)
            else:
                count += 1

    return count


def clean_title(title):
    allowed_chars = string.ascii_letters + string.digits + "\"'.! -_"
    return ''.join(
        (filter(lambda x: x in allowed_chars, title)))


def main():
    config_manager = ConfigManager(CONFIG_FILE_PATH)
    podcast_downloader = PodcastFetcher(config_manager)
    podcast_downloader.download_new_podcasts()
    config_manager.save_config()


if __name__ == "__main__":
    main()
