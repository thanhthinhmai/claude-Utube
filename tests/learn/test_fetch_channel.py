import shutil
import sys
import types
import unittest

from helpers import FX, Project, need_fixtures
from sl import fetch, refset

CHANNEL = "https://www.youtube.com/@demo"
TABS = {CHANNEL + "/videos": ["v1", "v2", "v3"], CHANNEL + "/shorts": ["s1", "s2", "s3"]}


def fake_yt_dlp(downloads: list, src):
    class YoutubeDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            if url == CHANNEL:                                   # home page: a playlist of tabs, not videos
                return {"_type": "playlist", "entries": [
                    {"_type": "url", "ie_key": "YoutubeTab", "url": t} for t in TABS]}
            if url in TABS:
                return {"_type": "playlist", "entries": [
                    {"_type": "url", "ie_key": "Youtube", "url": f"https://www.youtube.com/watch?v={i}"} for i in TABS[url]]}
            assert download, "videos are only fetched one by one with download=True"
            vid = url.rsplit("=", 1)[1]
            out = self.opts["outtmpl"].replace("%(id)s", vid).replace("%(ext)s", "mp4")
            shutil.copy(src, out)
            downloads.append(vid)
            return {"webpage_url": url, "title": f"Title {vid}", "channel": "Demo Channel",
                    "requested_downloads": [{"filepath": out}],
                    "formats": [{"vcodec": "none", "acodec": "opus", "language": "en"}],
                    "requested_formats": [{"vcodec": "none", "acodec": "opus", "language": "en", "format_note": "medium"}]}
    return types.SimpleNamespace(YoutubeDL=YoutubeDL)


class ChannelFetch(unittest.TestCase):
    def setUp(self):
        need_fixtures(self)
        self.p = Project()
        self.saved = sys.modules.get("yt_dlp")
        self.downloads = []
        sys.modules["yt_dlp"] = fake_yt_dlp(self.downloads, FX / "flat.mp4")

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("yt_dlp", None)
        else:
            sys.modules["yt_dlp"] = self.saved
        self.p.close()

    def test_channel_home_takes_exactly_count_across_tabs(self):
        data = fetch.fetch_urls("chan-set", "channel", [CHANNEL], count=4, log=lambda *_: None)
        self.assertEqual(self.downloads, ["v1", "v2", "v3", "s1"])          # Videos tab first, then Shorts
        self.assertEqual([v["id"] for v in data["videos"]], ["v01", "v02", "v03", "v04"])
        for v in data["videos"]:
            self.assertTrue(refset.video_path("chan-set", v).exists())
            self.assertTrue(v["audio_original"])                            # one audio language
        self.assertFalse(list((refset.set_dir("chan-set") / "videos").glob("dl_*")))

    def test_tab_url_and_rerun_skip(self):
        fetch.fetch_urls("tab-set", "channel", [CHANNEL + "/shorts"], count=3, log=lambda *_: None)
        self.assertEqual(self.downloads, ["s1", "s2", "s3"])
        data = fetch.fetch_urls("tab-set", "channel", [CHANNEL + "/shorts"], count=3, log=lambda *_: None)
        self.assertEqual(len(data["videos"]), 3)                           # nothing registered twice
        self.assertEqual(self.downloads, ["s1", "s2", "s3"])               # and nothing downloaded twice
        self.assertEqual(fetch.video_id("https://www.youtube.com/shorts/AbC_12-xyz"), "AbC_12-xyz")


if __name__ == "__main__":
    unittest.main()
