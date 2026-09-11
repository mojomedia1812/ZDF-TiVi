# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import urllib.request
import zipfile


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, ROOT)

from updater import (  # noqa: E402
    check_for_update,
    install_update,
    is_newer_version,
    latest_release_info,
    should_prompt_for_update,
    validate_update_zip,
)


ADDON_ID = "plugin.video.zdf-tivi"


class FakeVfs:
    def __init__(self, root):
        self.root = root

    def translatePath(self, path):
        mapping = {
            "special://home/addons": os.path.join(self.root, "home", "addons"),
            "special://home/addons/packages": os.path.join(self.root, "home", "addons", "packages"),
            "special://profile/addon_data/{0}".format(ADDON_ID): os.path.join(
                self.root,
                "profile",
                "addon_data",
                ADDON_ID,
            ),
        }
        return mapping[path]


class FakeXbmc:
    LOGDEBUG = 0
    LOGWARNING = 1

    def __init__(self):
        self.builtins = []

    def executebuiltin(self, command, wait=False):
        self.builtins.append((command, wait))


def local_file_url(path):
    return "file:///" + urllib.request.pathname2url(os.path.abspath(path)).lstrip("/")


def build_fake_update_zip(path, version):
    addon_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{0}" name="ZDF-TIVI" version="{1}" provider-name="m0j01812">
    <requires>
        <import addon="xbmc.python" version="3.0.0"/>
    </requires>
    <extension point="xbmc.python.pluginsource" library="default.py">
        <provides>video</provides>
    </extension>
</addon>
""".format(ADDON_ID, version)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("{0}/".format(ADDON_ID), "")
        archive.writestr("{0}/addon.xml".format(ADDON_ID), addon_xml)
        archive.writestr("{0}/default.py".format(ADDON_ID), "# test\n")


def main():
    fake_release = {
        "tag_name": "2026.09.11.4",
        "html_url": "https://example.invalid/release",
        "assets": [
            {
                "name": "{0}-2026.09.11.4.zip".format(ADDON_ID),
                "browser_download_url": "https://example.invalid/addon.zip",
            }
        ],
    }

    assert is_newer_version("2026.09.11.4", "2026.09.11.3")
    assert not is_newer_version("2026.09.11.3", "2026.09.11.3")
    assert check_for_update("2026.09.11.3", fake_release)["version"] == "2026.09.11.4"
    assert check_for_update("2026.09.11.4", fake_release) is None

    with tempfile.TemporaryDirectory() as directory:
        fake_vfs = FakeVfs(directory)
        fake_xbmc = FakeXbmc()
        zip_path = os.path.join(directory, "{0}-2026.09.11.5.zip".format(ADDON_ID))
        build_fake_update_zip(zip_path, "2026.09.11.5")
        validate_update_zip(zip_path, "2026.09.11.5")
        assert should_prompt_for_update(
            fake_vfs,
            {"version": "2026.09.11.5"},
        )
        install_update(
            {
                "version": "2026.09.11.5",
                "filename": os.path.basename(zip_path),
                "download_url": local_file_url(zip_path),
            },
            fake_vfs,
            fake_xbmc,
        )
        installed_xml = os.path.join(
            directory,
            "home",
            "addons",
            ADDON_ID,
            "addon.xml",
        )
        assert os.path.isfile(installed_xml)
        assert ("UpdateLocalAddons", True) in fake_xbmc.builtins

    latest = latest_release_info()
    if latest:
        print("Latest GitHub release:", latest["version"])
        print("Release asset:", latest["filename"])
    print("Update-Test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
