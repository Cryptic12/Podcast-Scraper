import sys
import tempfile
import os
from time import sleep
import flask
import unittest
from multiprocessing import Process
from main_refactored import ConfigFields, ConfigManager, PodcastFetcher
from server import TestServer


def configure_server():
    test_server = TestServer()
    test_server.start()


class TestPodcastFetcher(unittest.TestCase):
    BASE_CONFIG = "Tests/basic_config.json"
    TEMP_DIR = "Tests/Temp"

    @classmethod
    def setUpClass(self):
        print("Starting Server")
        self.server = Process(target=configure_server)
        self.server.start()

        # Allow server to start up
        sleep(3)

    def setUp(self):
        # Need to create temporary directories for the tests to download into
        CWD = os.getcwd()
        self.config_manager = ConfigManager(self.BASE_CONFIG)
        old_podcasts_dir_path = os.path.join(
            CWD, tempfile.mkdtemp(dir=self.TEMP_DIR))
        self.config_manager.update_value(
            ConfigFields.OLD_EPISODES_DIR.value, old_podcasts_dir_path)
        new_podcasts_dir_path = os.path.join(
            CWD, tempfile.mkdtemp(dir=old_podcasts_dir_path))
        self.config_manager.update_value(
            ConfigFields.NEW_EPISODES_DIR.value, new_podcasts_dir_path)

    def test_all_new_podcasts(self):
        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", "Fri, 1 Jan 2021 00:00:00 GMT")

        self.download_podcasts()

        self.check_expected_podcasts(
            [], ["1. Podcast 1.mp3", "2. Podcast 2.mp3", "3. Podcast 3.mp3"])

    def test_no_new_podcasts(self):
        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", "Sun, 2 Jan 2022 00:00:00 GMT")

        self.download_podcasts()
        self.check_expected_podcasts([], [])

    def test_some_new_podcasts(self):
        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", "Sat, 1 Jan 2022 00:00:01 GMT")

        self.download_podcasts()
        self.check_expected_podcasts(
            [], ["1. Podcast 2.mp3", "2. Podcast 3.mp3"])

    def test_podcast_with_disallowed_chars(self):
        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_2.xml", "Sat, 1 Jan 2022 00:00:00 GMT")

        self.download_podcasts()
        self.check_expected_podcasts(
            [], ["1. Disallowed Chars Start  End.mp3"])

    def test_old_podcasts_moved_from_new_dir_to_old_dir(self):
        FIRST_PODCAST_BATCH = ["1. Podcast 1.mp3",
                               "2. Podcast 2.mp3", "3. Podcast 3.mp3"]
        SECOND_PODCAST_BATCH = []

        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", "Fri, 1 Jan 2021 00:00:00 GMT")
        self.download_podcasts()

        self.check_expected_podcasts(
            [], FIRST_PODCAST_BATCH)

        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", "Sat, 1 Jan 2022 00:00:10 GMT")
        self.download_podcasts()

        self.check_expected_podcasts(
            FIRST_PODCAST_BATCH, SECOND_PODCAST_BATCH)

    def test_duplicate_podcasts_downloaded(self):
        FIRST_PODCAST_BATCH = ["1. Podcast 1.mp3",
                               "2. Podcast 2.mp3", "3. Podcast 3.mp3"]
        SECOND_PODCAST_BATCH = ["4. Podcast 1.mp3",
                                "5. Podcast 2.mp3", "6. Podcast 3.mp3"]
        THIRD_PODCAST_BATCH = ["7. Podcast 1.mp3",
                               "8. Podcast 2.mp3", "9. Podcast 3.mp3"]
        TIME_STAMP = "Fri, 1 Jan 2021 00:00:00 GMT"

        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", TIME_STAMP)
        self.download_podcasts()
        self.check_expected_podcasts(
            [], FIRST_PODCAST_BATCH)

        self.config_manager.update_value(
            ConfigFields.DATE_LAST_RUN.value, TIME_STAMP)
        self.download_podcasts()
        self.check_expected_podcasts(
            FIRST_PODCAST_BATCH, SECOND_PODCAST_BATCH)

        self.config_manager.update_value(
            ConfigFields.DATE_LAST_RUN.value, TIME_STAMP)
        self.download_podcasts()
        self.check_expected_podcasts(
            FIRST_PODCAST_BATCH + SECOND_PODCAST_BATCH, THIRD_PODCAST_BATCH)

    def test_date_last_run_updated(self):
        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_1.xml", "Fri, 1 Jan 2021 00:00:00 GMT")
        self.download_podcasts()

        self.assertEquals(self.config_manager.get_value(
            ConfigFields.DATE_LAST_RUN.value), "Sat, 1 Jan 2022 00:00:03 GMT")

        self.configure_test(
            "http://127.0.0.1:5000/resource/test_rss_2.xml", "Fri, 1 Jan 2021 00:00:00 GMT")
        self.download_podcasts()

        self.assertEquals(self.config_manager.get_value(
            ConfigFields.DATE_LAST_RUN.value), "Sat, 1 Jan 2022 00:00:01 GMT")

    def tearDown(self):
        self.clean_and_remove_dir(self.config_manager.get_value(
            ConfigFields.NEW_EPISODES_DIR.value))
        self.clean_and_remove_dir(self.config_manager.get_value(
            ConfigFields.OLD_EPISODES_DIR.value))

    @classmethod
    def tearDownClass(self):
        print("\nTearing Down Server")
        self.server.terminate()
        self.server.join()

    def configure_test(self, rss_url, last_run_timestamp):
        self.config_manager.update_value(
            ConfigFields.RSS_ADDRESS.value, rss_url)
        self.config_manager.update_value(
            ConfigFields.DATE_LAST_RUN.value, last_run_timestamp)

    def download_podcasts(self):
        podcast_fetcher = PodcastFetcher(self.config_manager)
        podcast_fetcher.download_new_podcasts()

    def check_expected_podcasts(self, old_episodes, new_episodes):
        self.check_expected_podcasts_in_dir(self.config_manager.get_value(
            ConfigFields.OLD_EPISODES_DIR.value), old_episodes)
        self.check_expected_podcasts_in_dir(self.config_manager.get_value(
            ConfigFields.NEW_EPISODES_DIR.value), new_episodes)

    def check_expected_podcasts_in_dir(self, dir, expected_podcasts):
        podcasts = self.get_file_names_from_dir(dir)
        self.assertCountEqual(expected_podcasts, podcasts)
        self.assertListEqual(expected_podcasts, podcasts)

    def get_file_names_from_dir(self, dir):
        podcasts = []
        with os.scandir(dir) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    podcasts.append(entry.name)
        return podcasts

    def clean_and_remove_dir(self, dir_path):
        for entry in os.scandir(dir_path):
            if entry.is_file():
                os.remove(entry)
        os.rmdir(dir_path)


def main():
    # Makes a temporary directory
    dir_path = tempfile.mkdtemp(dir="Tests/Temp")
    cwd = os.getcwd()
    print(os.path.join(cwd, dir_path))


if __name__ == '__main__':
    unittest.main()
    # main()
