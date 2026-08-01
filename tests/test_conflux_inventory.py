import unittest

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


if __name__ == "__main__":
    unittest.main()

