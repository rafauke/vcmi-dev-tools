import json
from collections import Counter
from pathlib import Path
import unittest


class ManifestTests(unittest.TestCase):
    def test_hd_expansion_portrait_roster(self) -> None:
        path = (
            Path(__file__).parents[1]
            / "manifests"
            / "hd-expansion-portraits.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        heroes = data["heroes"]

        self.assertEqual(len(heroes), data["initialScope"])
        self.assertEqual(len({hero["slug"] for hero in heroes}), len(heroes))
        self.assertEqual(len({hero["resource"] for hero in heroes}), len(heroes))
        self.assertEqual(
            Counter(hero["release"] for hero in heroes),
            {
                "armageddons-blade": 27,
                "shadow-of-death": 5,
                "restoration-of-erathia": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
