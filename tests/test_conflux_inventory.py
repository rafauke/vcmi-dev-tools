import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vcmi_dev_tools.conflux_extract import load_selection
from vcmi_dev_tools.conflux_export import frame_output_name
from vcmi_dev_tools.conflux_inventory import archive_name, collect_references


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

    def test_maps_def_frame_name_to_hd_png(self) -> None:
        self.assertEqual(frame_output_name("TBELtvrn.pcx"), "TBELtvrn.png")


if __name__ == "__main__":
    unittest.main()
