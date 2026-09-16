"""
Picking the content URL, with no network access.

A video asset answers with the MP4's URL and its thumbnail's as well. Keeping
the first one downloaded a 46 KB PNG instead of the video.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flow_provider import api

VIDEO = "https://flow-content.google/video/11111111-1111-1111-1111-111111111111?Expires=1"
THUMBNAIL = "https://flow-content.google/image/22222222-2222-2222-2222-222222222222?Expires=1"
IMAGE = "https://flow-content.google/image/33333333-3333-3333-3333-333333333333?Expires=1"


class PickUrlTest(unittest.TestCase):
    def test_video_does_not_pick_the_thumbnail(self):
        # Flow returns the thumbnail first, which is why urls[0] is wrong.
        urls = [THUMBNAIL, VIDEO]
        self.assertEqual(api.pick_url(urls, "video"), VIDEO)

    def test_image_picks_the_image(self):
        self.assertEqual(api.pick_url([IMAGE], "image"), IMAGE)

    def test_without_a_kind_it_prefers_the_video(self):
        self.assertEqual(api.pick_url([THUMBNAIL, VIDEO], None), VIDEO)

    def test_no_urls_returns_none(self):
        self.assertIsNone(api.pick_url([], "video"))

    def test_unmatched_kind_falls_back_to_the_first(self):
        self.assertEqual(api.pick_url([IMAGE], "video"), IMAGE)

    def test_collects_every_url_in_order(self):
        raw = ["id", [None, [THUMBNAIL]], [[VIDEO]], "otro"]
        self.assertEqual(api.find_content_urls(raw), [THUMBNAIL, VIDEO])

    def test_ignores_urls_that_are_not_content(self):
        raw = ["https://flow.google.com/asb/token", THUMBNAIL]
        self.assertEqual(api.find_content_urls(raw), [THUMBNAIL])


if __name__ == "__main__":
    unittest.main()
