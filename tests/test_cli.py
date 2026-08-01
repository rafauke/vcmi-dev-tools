from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from vcmi_portrait_tools.cli import SIZES, build_portrait, normalized_resource


class PortraitToolsTests(unittest.TestCase):
    def test_resource_is_normalized(self) -> None:
        self.assertEqual(normalized_resource("003sh"), "003SH")

    def test_builds_all_large_sizes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            master = root / "large.png"
            output = root / "content"
            Image.new("RGB", (290, 320), "red").save(master)

            build_portrait(master, "HPL", "003SH", output)

            for data_dir, dimensions in SIZES.items():
                result = output / data_dir / "HPL003SH.png"
                self.assertTrue(result.is_file())
                with Image.open(result) as image:
                    self.assertEqual(image.size, dimensions["HPL"])


if __name__ == "__main__":
    unittest.main()

