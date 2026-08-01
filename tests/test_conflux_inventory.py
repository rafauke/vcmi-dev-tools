import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from vcmi_dev_tools.conflux_extract import load_selection
from vcmi_dev_tools.conflux_inventory import archive_name, collect_references
from vcmi_dev_tools.conflux_pack import validate_d32, write_d32


class ConfluxInventoryTests(unittest.TestCase):
    def test_normalizes_vcmi_bitmap_names_to_pcx(self) -> None:
        self.assertEqual(archive_name("TBELBACK.bmp"), "tbelback.pcx")
        self.assertEqual(archive_name("TBELMAGE.def"), "tbelmage.def")

    def test_collects_and_deduplicates_references(self) -> None:
        config = {
            "conflux": {
                "town": {
                    "townBackground": "TBELBACK.bmp",
                    "structures": {
                        "mageGuild1": {
                            "animation": "TBELMAGE.def",
                            "border": "TOELMAGE.bmp",
                        },
                        "mageGuild2": {
                            "animation": "TBELMAGE.def",
                        },
                    },
                }
            }
        }
        resources = collect_references(config)
        self.assertEqual(
            set(resources), {"tbelback.pcx", "tbelmage.def", "toelmage.pcx"}
        )
        self.assertEqual(
            resources["tbelmage.def"]["structures"],
            ["mageGuild1", "mageGuild2"],
        )

    def test_validates_extraction_selection(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "selection.json"
            path.write_text(
                '{"resources": [{"archiveEntry": "TBELTVRN.DEF", '
                '"runtimeName": "TBELTVRN.def", "role": "building"}]}',
                encoding="utf-8",
            )
            selection = load_selection(path)
        self.assertEqual(selection[0]["archiveEntry"], "tbeltvrn.def")

    def test_d32_round_trip_preserves_groups_and_pixels(self) -> None:
        groups = {
            0: [
                ("first.pcx", Image.new("RGBA", (3, 2), (10, 20, 30, 40))),
                ("second.pcx", Image.new("RGBA", (3, 2), (50, 60, 70, 80))),
            ]
        }
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.def"
            write_d32(groups, path)
            validate_d32(path, groups)


if __name__ == "__main__":
    unittest.main()
