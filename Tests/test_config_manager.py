
from asyncio import sleep
import os
import json
import unittest
import tempfile
from main_refactored import ConfigFields, ConfigManager


class TestConfigManager(unittest.TestCase):
    TEMP_DIR = "Tests/Temp"

    def setUp(self):
        self.test_base = os.path.dirname(os.path.realpath(__file__))
        self.abs_config_path = os.path.join(
            self.test_base, 'Configs/test_config_normal.json')
        self.config_manager = ConfigManager(self.abs_config_path)

    def test_all_fields_loaded_from_config_file(self):
        for field in ConfigFields:
            self.assertGreater(
                len(self.config_manager.get_value(field.value)), 0)

    def test_invalid_field_throws_key_error(self):
        with self.assertRaises(KeyError):
            self.config_manager.get_value("invalid value")

    def test_value_is_updated(self):
        TEST_VALUE = "test value"
        self.config_manager.update_value(
            ConfigFields.DATE_LAST_RUN.value, TEST_VALUE)
        self.assertEqual(self.config_manager.get_value(
            ConfigFields.DATE_LAST_RUN.value), TEST_VALUE)

    def test_config_saves_corrrectly(self):

        TEST_VALUE = "TEST_VAUE"

        tmp_config_file, tmp_config_path = tempfile.mkstemp(
            dir=self.TEMP_DIR, text=True)

        with open(self.abs_config_path) as default_config:
            default_json = json.load(default_config)
            print("I am here ", default_json)

            with os.fdopen(tmp_config_file, "w") as file:
                json.dump(default_json, file)

        self.config_manager = ConfigManager(tmp_config_path)
        for field in ConfigFields:
            self.config_manager.update_value(
                field.value, TEST_VALUE)

        self.config_manager.save_config()

        self.config_manager = ConfigManager(tmp_config_path)
        for field in ConfigFields:
            self.assertEquals(
                TEST_VALUE, self.config_manager.get_value(field.value))

        os.remove(tmp_config_path)


if __name__ == '__main__':
    unittest.main()
