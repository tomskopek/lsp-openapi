#!/usr/bin/env python3
"""Tests for server.py. Zero dependencies — run with: python3 -m unittest"""

import unittest

from server import camel_to_snake


class TestCamelToSnake(unittest.TestCase):
    def test_simple_camel_case(self):
        self.assertEqual(camel_to_snake("getUser"), "get_user")
        self.assertEqual(camel_to_snake("postGenerateImage"), "post_generate_image")

    def test_single_word(self):
        self.assertEqual(camel_to_snake("health"), "health")

    def test_trailing_digits_stay_attached(self):
        self.assertEqual(
            camel_to_snake("postGenerateImageV45Async"),
            "post_generate_image_v45_async",
        )
        self.assertEqual(
            camel_to_snake("postGenerateImageV4CfgDistilled"),
            "post_generate_image_v4_cfg_distilled",
        )

    def test_capital_run_splits_before_last_capital(self):
        # "PImage" is "P" + "Image": a capital run ends where the next word
        # starts. The naive lookbehind regex glued this into "pimage".
        self.assertEqual(
            camel_to_snake("postGenerateImagePImageIdeogram"),
            "post_generate_image_p_image_ideogram",
        )
        self.assertEqual(
            camel_to_snake("postGenerateImagePImageIdeogramAsync"),
            "post_generate_image_p_image_ideogram_async",
        )


if __name__ == "__main__":
    unittest.main()
