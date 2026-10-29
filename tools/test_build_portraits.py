"""Geometry, error handling, compositing and reproducibility regression checks."""

import contextlib
import csv
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import build_portraits as pipeline


class PipelineTests(unittest.TestCase):
    def test_npc_table_is_separate_validated_and_selectable(self):
        path = self.root / 'data/npc_portraits.csv'
        path.write_text('id,bg_id,x_offset,height_scale\nqing_npc_lvying,bg_test,0,0.93\n')
        rows = pipeline.read_records(self.root, 'qing_npc_lvying')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['portrait_kind'], 'npc')
        self.assertEqual(rows[0]['rarity'], 'N')
        self.assertEqual(len(pipeline.read_records(self.root, None)), 2)
        path.write_text('id,bg_id,x_offset,height_scale\nqing_npc_lvying,bg_test,0,0.96\n')
        with self.assertRaises(pipeline.AssetError):
            pipeline.read_records(self.root, 'tp_test')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for folder in ("data", "assets/raw/characters", "assets/raw/backgrounds", "assets/raw/fx"):
            (self.root / folder).mkdir(parents=True)
        self.row = {"id": "tp_test", "bg_id": "bg_test", "x_offset": "0", "rarity_draft": "SR"}
        self.write_table([self.row])

    def tearDown(self):
        self.temp.cleanup()

    def write_table(self, rows):
        with (self.root / "data/characters.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.row))
            writer.writeheader()
            writer.writerows(rows)

    def source(self, box=(300, 150, 900, 1550), size=(1200, 1700), mode="RGBA"):
        image = Image.new(mode, size, (0, 0, 0, 0) if mode == "RGBA" else "white")
        ImageDraw.Draw(image).rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill="crimson")
        image.save(self.root / "assets/raw/characters/tp_test.png")
        return image

    def background(self, size=pipeline.SIZE):
        image = Image.new("RGB", size, "#708090")
        image.save(self.root / "assets/raw/backgrounds/bg_test.png")

    def process(self, **kwargs):
        return pipeline.process(self.root, self.row, tolerance=12, **kwargs)

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return pipeline.main(["--root", str(self.root), *args])

    def hashes(self, folder):
        return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in folder.rglob("*") if p.is_file()}

    def test_lab_and_corner_key(self):
        white, black = pipeline.rgb_to_lab(np.array([[255, 255, 255], [0, 0, 0]]))
        np.testing.assert_allclose(white, [100, 0, 0], atol=0.001)
        np.testing.assert_allclose(black, [0, 0, 0], atol=0.001)
        image = Image.new("RGB", (12, 12), "white")
        ImageDraw.Draw(image).rectangle((3, 3, 9, 9), fill=(190, 0, 0))
        keyed = pipeline.color_key(image, 12)
        self.assertEqual(keyed.getpixel((0, 0))[3], 0)
        self.assertEqual(keyed.getpixel((6, 6))[3], 255)

    def test_color_key_preserves_near_background_interior_after_composition(self):
        background_color = (240, 240, 240)
        interior_color = (238, 237, 239)
        distance = np.linalg.norm(pipeline.rgb_to_lab(np.array(interior_color))
                                  - pipeline.rgb_to_lab(np.array(background_color)))
        self.assertLess(distance, 5)
        image = Image.new("RGB", (1200, 1700), background_color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((300, 150, 899, 1549), fill="crimson")
        draw.rectangle((500, 750, 699, 949), fill=interior_color)
        image.save(self.root / "assets/raw/characters/tp_test.png")
        self.background()
        keyed = pipeline.color_key(image, 12)
        self.assertTrue(np.all(np.asarray(keyed)[750:950, 500:700, 3] == 255))
        self.assertEqual(keyed.getpixel((0, 0))[3], 0)
        result = self.process()
        self.assertIsNotNone(result.preview)
        pixel = result.preview.getpixel((512, 1392 - result.metrics["final_h"] // 2))
        self.assertEqual(pixel[3], 255)
        # An opaque final background alone would make an alpha-only assertion
        # vacuous: also verify the interior color survived the full composite.
        self.assertEqual(pixel[:3], interior_color)

    def test_color_key_flood_starts_from_all_four_edges(self):
        image = Image.new("RGB", (80, 80), "crimson")
        draw = ImageDraw.Draw(image)
        for box in ((30, 0, 49, 10), (30, 69, 49, 79),
                    (0, 30, 10, 49), (69, 30, 79, 49)):
            draw.rectangle(box, fill="white")
        # Corners are isolated from all four matching edge patches.
        for corner in ((0, 0), (0, 79), (79, 0), (79, 79)):
            image.putpixel(corner, (255, 255, 255))
        draw.rectangle((30, 30, 49, 49), fill="white")
        keyed = pipeline.color_key(image, 12)
        for point in ((40, 5), (40, 74), (5, 40), (74, 40)):
            self.assertEqual(keyed.getpixel(point)[3], 0)
        self.assertEqual(keyed.getpixel((40, 40))[3], 255)

    def test_color_key_feathers_only_outer_silhouette_by_two_pixels(self):
        image = Image.new("RGB", (40, 40), "white")
        ImageDraw.Draw(image).rectangle((10, 10, 29, 29), fill="crimson")
        keyed = pipeline.color_key(image, 12)
        alpha = np.asarray(keyed)[20, :, 3]
        np.testing.assert_array_equal(alpha[9:14], [0, 85, 170, 255, 255])
        self.assertTrue(np.all(alpha[:10] == 0))
        self.assertTrue(np.all(alpha[30:] == 0))
        self.assertTrue(np.all(np.asarray(keyed)[12:28, 12:28, 3] == 255))
        # Retained edge RGB is unchanged, so no pale keyed RGB is introduced.
        self.assertEqual(keyed.getpixel((10, 20))[:3], (220, 20, 60))
        self.assertEqual(keyed.tobytes(), pipeline.color_key(image, 12).tobytes())

    def test_color_key_four_connectivity_and_open_background_channel(self):
        mask = np.zeros((8, 8), dtype=bool)
        mask[0, 0] = mask[1, 1] = True
        connected = pipeline.edge_connected(mask)
        self.assertTrue(connected[0, 0])
        self.assertFalse(connected[1, 1], "Diagonal contact is not a four-connected path")
        image = Image.new("RGB", (60, 60), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 49, 49), fill="crimson")
        draw.rectangle((20, 20, 39, 39), fill="white")
        # A narrow opening connects the otherwise enclosed matching region.
        draw.rectangle((0, 25, 20, 27), fill="white")
        keyed = pipeline.color_key(image, 12)
        self.assertEqual(keyed.getpixel((30, 30))[3], 0)

    def test_alpha_threshold_and_edge_distance(self):
        image = Image.new("RGBA", (100, 100))
        image.putpixel((0, 0), (255, 0, 0, 16))
        image.putpixel((4, 5), (255, 0, 0, 17))
        self.assertEqual(pipeline.alpha_bbox(image), (4, 5, 5, 6))
        self.assertEqual(pipeline.alpha_bbox(image, 0), (0, 0, 5, 6))
        self.source(box=(3, 100, 700, 1500))
        self.assertIn("EDGE_CUT", self.process().warnings)

    def test_whole_source_fit_baseline_and_offset(self):
        source = self.source()
        box = pipeline.alpha_bbox(source)
        fitted, scale, bounds = pipeline.fit_foreground(source, box)
        # The resized canvas still contains original transparent padding.
        self.assertEqual(fitted.size, (int(source.width * scale), int(source.height * scale)))
        self.assertGreater(bounds[0], 0)
        self.assertGreater(bounds[1], 0)
        self.assertLessEqual(bounds[3] - bounds[1], 1248)
        self.assertLessEqual(abs((bounds[3] - bounds[1]) - 1248), 2)
        self.background()
        self.row["x_offset"] = "17"
        result = self.process()
        self.assertFalse(result.warnings)
        self.assertEqual(result.preview.size, pipeline.SIZE)
        # Detect red subject independently of background/shadow to verify alignment.
        pixels = np.asarray(result.preview)
        red = (pixels[..., 0] > 180) & (pixels[..., 1] < 50) & (pixels[..., 2] < 90)
        ys, xs = np.nonzero(red)
        # The specification uses alpha>16, while this color threshold detects
        # the opaque red core; Lanczos fringe can extend 1–2px below that core.
        self.assertLessEqual(abs((ys.max() + 1) - 1392), 2)
        self.assertEqual(result.silhouette.getbbox()[3], 1392)
        self.assertGreaterEqual(ys.min(), 92)
        self.assertAlmostEqual((xs.min() + xs.max() + 1) / 2, 529, delta=0.5)

    def test_wide_foreground_and_upscale(self):
        self.source(box=(100, 400, 1100, 1200))
        result = self.process()
        self.assertIn("WIDE", result.warnings)
        self.assertLess(result.metrics["final_h"], 1248)
        self.assertLessEqual(float(result.metrics["scale"]), 896 / 1000)
        self.source(box=(100, 100, 200, 500))
        self.assertIn("UPSCALE", self.process().warnings)

    def test_missing_inputs_and_stale_output_are_not_used(self):
        stale = self.root / "assets/characters/tp_test"
        stale.mkdir(parents=True)
        Image.new("RGB", (400, 600), "green").save(stale / "card.webp")
        result = self.process()
        self.assertEqual(result.warnings, ["SRC_MISSING", "BG_MISSING"])
        self.assertIsNone(result.preview)
        self.assertEqual(self.cli(), 1)
        with (self.root / "assets/reports/pipeline_report.csv").open(encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["src_w"], "")
        self.assertEqual(row["warnings"], "SRC_MISSING;BG_MISSING")
        self.assertFalse((stale / "full.png").exists())

    def test_background_size_error_does_not_resize_or_write(self):
        self.source()
        self.background((512, 768))
        original = (self.root / "assets/raw/backgrounds/bg_test.png").read_bytes()
        self.assertEqual(self.cli(), 1)
        self.assertFalse((self.root / "assets/characters/tp_test/full.png").exists())
        self.assertEqual((self.root / "assets/raw/backgrounds/bg_test.png").read_bytes(), original)
        self.assertIn("BG_INVALID", self.process().warnings)

    def test_fallback_and_empty_foreground(self):
        self.source(mode="RGB")
        result = self.process()
        self.assertIn("NO_ALPHA_FALLBACK", result.warnings)
        self.assertIn("BG_MISSING", result.warnings)
        self.assertIsNotNone(result.preview)
        Image.new("RGB", (100, 100), "white").save(self.root / "assets/raw/characters/tp_test.png")
        self.assertIn("NO_FOREGROUND", self.process().warnings)

    def test_no_visible_pixels_are_silently_clipped(self):
        self.source()
        self.row["x_offset"] = "1000"
        result = self.process()
        self.assertIn("PLACEMENT_INVALID", result.warnings)
        self.assertIsNone(result.preview)

    def test_screen_alpha_and_ssr_gate(self):
        base = Image.new("RGBA", (2, 2), (100, 50, 0, 255))
        overlay = Image.new("RGBA", (2, 2), (0, 0, 255, 128))
        overlay.putpixel((0, 0), (255, 255, 255, 0))
        screened = pipeline.screen_blend(base, overlay)
        self.assertEqual(screened.getpixel((0, 0)), (100, 50, 0, 255))
        self.assertEqual(screened.getpixel((1, 1)), (100, 50, 128, 255))
        self.source()
        self.background()
        reference = self.process().preview.tobytes()
        Image.new("RGBA", pipeline.SIZE, (255, 255, 255, 128)).save(
            self.root / "assets/raw/fx/tp_test.png")
        self.assertEqual(self.process().preview.tobytes(), reference)
        self.row["rarity_draft"] = "SSR"
        self.assertNotEqual(self.process().preview.tobytes(), reference)
        Image.new("RGBA", (4, 4)).save(self.root / "assets/raw/fx/tp_test.png")
        self.assertIn("FX_INVALID", self.process().warnings)

    def test_rembg_switch_only_for_opaque_input(self):
        self.source(mode="RGB")
        calls = []
        def remove(image):
            calls.append(image.size)
            return pipeline.color_key(image, 12)
        result = self.process(remove_background=remove)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("NO_ALPHA_FALLBACK", result.warnings)
        self.assertIsNotNone(result.preview)
        self.source()
        self.process(remove_background=remove)
        self.assertEqual(len(calls), 1)

    def test_reproducibility_dimensions_and_check_nonmutation(self):
        self.source()
        self.background()
        self.assertEqual(self.cli(), 0)
        first = self.hashes(self.root / "assets")
        self.assertEqual(self.cli(), 0)
        self.assertEqual(self.hashes(self.root / "assets"), first)
        folder = self.root / "assets/characters/tp_test"
        with Image.open(folder / "full.png") as full:
            self.assertEqual(full.size, pipeline.SIZE)
            for name, dimensions in pipeline.DERIVATIVES.items():
                with Image.open(folder / f"{name}.webp") as thumbnail:
                    self.assertEqual(thumbnail.size, dimensions)
                    self.assertEqual(thumbnail.width * 3, thumbnail.height * 2)
                    expected = full.resize(dimensions, Image.Resampling.LANCZOS).convert("RGB")
                    error = np.abs(np.asarray(expected).astype(float) - np.asarray(thumbnail).astype(float)).mean()
                    self.assertLess(error, 3, "Derivative must preserve the whole-frame composition")
        original = self.hashes(folder)
        self.assertEqual(self.cli("--check"), 0)
        self.assertEqual(self.hashes(folder), original)
        for path in folder.iterdir():
            path.unlink()
        folder.rmdir()
        self.assertEqual(self.cli("--check"), 0)
        self.assertFalse(folder.exists())

    def test_id_filter_and_table_validation(self):
        other = dict(self.row, id="qing_test")
        self.write_table([self.row, other])
        self.assertEqual(self.cli("--id", "qing_test"), 1)
        with (self.root / "assets/reports/pipeline_report.csv").open(encoding="utf-8-sig") as f:
            self.assertEqual([r["id"] for r in csv.DictReader(f)], ["qing_test"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.cli("--id", "tp_nonexistent"), 2)
            self.write_table([self.row, self.row])
            self.assertEqual(self.cli(), 2)

    def test_batch_ids_keep_requested_order_without_duplicates(self):
        self.write_table([self.row, dict(self.row, id="qing_test")])
        self.assertEqual(self.cli("--id", "qing_test", "--id", "tp_test", "--id", "qing_test"), 1)
        with (self.root / "assets/reports/pipeline_report.csv").open(encoding="utf-8-sig") as f:
            self.assertEqual([row["id"] for row in csv.DictReader(f)], ["qing_test", "tp_test"])

    def test_shared_background_override_preserves_csv(self):
        self.source()
        self.background()
        original_table = (self.root / "data/characters.csv").read_bytes()
        bg_folder = self.root / "assets/raw/backgrounds"
        (bg_folder / "bg_test.png").rename(bg_folder / "bg_review.png")
        self.assertEqual(self.cli("--id", "tp_test", "--background", "bg_review"), 0)
        self.assertEqual((self.root / "data/characters.csv").read_bytes(), original_table)
        summary = (self.root / "assets/reports/pipeline_summary.md").read_text()
        self.assertIn("Review background override: bg_review", summary)
        self.assertIn("planned scene preserved in CSV: bg_test", summary)
        self.assertNotIn("BG_MISSING", summary)

    def test_height_scale_defaults_for_legacy_column_missing_and_blank(self):
        self.source()
        self.background()
        # Existing CSV without the column remains usable, with the NEW default.
        records = pipeline.read_records(self.root, None)
        self.assertEqual(records[0]["height_scale"], "0.96")
        self.assertEqual(self.cli(), 0)
        with (self.root / "assets/reports/pipeline_report.csv").open(encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(list(row), pipeline.REPORT_FIELDS)
        self.assertEqual(row["height_scale"], "0.96")
        self.assertLessEqual(abs(int(row["final_h"]) - 1248), 2)
        for value in (None, "", "   "):
            with self.subTest(value=value):
                self.assertEqual(pipeline.parse_height_scale(value), 0.96)
        self.row["height_scale"] = "   "
        self.write_table([self.row])
        self.assertEqual(self.cli(), 0)

    def test_height_scale_targets_and_measured_foot_baseline(self):
        self.source()
        self.background()
        expected_heights = {"0.90": 1170, "0.92": 1196, "0.93": 1209,
                            "0.95": 1235, "0.96": 1248, "0.99": 1287,
                            "1.00": 1300, "0.951": 1236}
        heights = []
        for coefficient, expected in expected_heights.items():
            with self.subTest(height_scale=coefficient):
                self.row["height_scale"] = coefficient
                result = self.process()
                self.assertFalse(result.warnings)
                self.assertEqual(pipeline.target_height(coefficient), expected)
                self.assertEqual(float(result.metrics["height_scale"]), float(coefficient))
                self.assertLessEqual(abs(result.metrics["final_h"] - expected), 2)
                box = result.silhouette.getbbox()
                self.assertEqual(box[3], 1392)
                self.assertGreaterEqual(box[1], 1392 - expected)
                self.assertLessEqual(abs((box[3] - box[1]) - expected), 2)
                self.assertGreaterEqual(box[0], 64)
                self.assertLessEqual(box[2], 960)
                heights.append(result.metrics["final_h"])
        self.assertLess(heights[0], heights[4])
        self.assertLess(heights[4], heights[6])

    def test_invalid_height_scale_is_table_error_before_any_output_changes(self):
        self.source()
        self.background()
        self.row["height_scale"] = "0.96"
        self.write_table([self.row])
        self.assertEqual(self.cli(), 0)
        original_outputs = self.hashes(self.root / "assets")
        invalid = ("0", "0.8999", "1.0001", "nan", "NaN", "inf", "-inf", "bad", "96%")
        for value in invalid:
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                self.row["height_scale"] = value
                self.write_table([self.row])
                self.assertEqual(self.cli(), 2)
                self.assertEqual(self.hashes(self.root / "assets"), original_outputs)

    def test_invalid_height_scale_in_unselected_row_still_rejects_table(self):
        self.row["height_scale"] = "0.96"
        self.write_table([self.row, dict(self.row, id="qing_test", height_scale="1.1")])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.cli("--id", "tp_test"), 2)
        self.assertFalse((self.root / "assets/reports").exists())

    def test_wide_and_upscale_thresholds_use_height_scale(self):
        self.background()
        self.source(box=(100, 100, 800, 1100))
        self.row["height_scale"] = "0.96"
        self.assertNotIn("WIDE", self.process().warnings)
        self.row["height_scale"] = "1.00"
        wide = self.process()
        self.assertIn("WIDE", wide.warnings)
        self.assertLess(wide.metrics["final_h"], 1300)
        box = wide.silhouette.getbbox()
        self.assertLessEqual(box[2] - box[0], 896)
        self.assertEqual(box[3], 1392)
        self.source(box=(100, 100, 400, 1100))
        self.row["height_scale"] = "0.96"
        self.assertNotIn("UPSCALE", self.process().warnings)
        self.row["height_scale"] = "1.00"
        self.assertIn("UPSCALE", self.process().warnings)

    def test_silhouette_excludes_background_shadow_and_ssr_effects(self):
        self.source()
        self.background()
        self.row.update(height_scale="0.92", rarity_draft="SSR")
        result = self.process()
        original = result.silhouette.tobytes()
        self.assertEqual(result.silhouette.mode, "L")
        self.assertEqual(result.silhouette.getpixel((512, 1392)), 0, "Cast shadow must not enter silhouette")
        Image.new("RGBA", pipeline.SIZE, (255, 255, 255, 200)).save(self.root / "assets/raw/fx/tp_test.png")
        with_fx = self.process()
        self.assertEqual(with_fx.silhouette.tobytes(), original)
        self.assertNotEqual(with_fx.preview.tobytes(), result.preview.tobytes())
        self.write_table([self.row])
        self.assertEqual(self.cli("--check"), 0)
        self.assertTrue((self.root / "assets/reports/silhouette_sheet.png").exists())
        self.assertFalse((self.root / "assets/characters/tp_test").exists())

    def test_silhouette_groups_preserve_order_and_count_dual_only_once(self):
        records = [
            {"id": "qing_first", "faction": "qing"},
            {"id": "tp_first", "faction": "taiping"},
            {"id": "qing_dual", "faction": "dual"},
            {"id": "tp_second", "faction": "taiping"},
        ]
        results = [pipeline.Result(row) for row in records]
        groups = pipeline.silhouette_groups(results)
        self.assertEqual([[r.record["id"] for r in members] for _, members in groups],
                         [["tp_first", "tp_second"], ["qing_first", "qing_dual"]])
        self.assertEqual(sum(len(members) for _, members in groups), len(results))
        # Old tables without the faction column still group by their id prefix.
        legacy = [pipeline.Result({"id": "tp_legacy"}), pipeline.Result({"id": "qing_legacy"})]
        self.assertEqual([len(members) for _, members in pipeline.silhouette_groups(legacy)], [1, 1])

    def test_silhouette_sheet_two_rows_keep_common_scale_and_foot_baseline(self):
        mask = Image.new("L", pipeline.SIZE, 0)
        ImageDraw.Draw(mask).rectangle((400, 200, 623, 1391), fill=255)
        results = [pipeline.Result({"id": "qing_test", "faction": "dual", "name": "清"}, silhouette=mask),
                   pipeline.Result({"id": "tp_test", "faction": "taiping", "name": "太平"}, silhouette=mask)]
        sheet = pipeline.silhouette_sheet(results)
        self.assertEqual(sheet.size, (720, 884))
        first_y, second_y = 136, 516
        for y in (first_y, second_y):
            self.assertEqual(sheet.getpixel((104, y + 100)), (0, 0, 0))
            baseline = y + round(1392 / 1536 * 240)
            self.assertEqual(sheet.getpixel((104, baseline)), (218, 48, 43))
            self.assertEqual(sheet.getpixel((104, baseline + 4)), (237, 227, 204))
        self.assertEqual(sheet.crop((24, first_y, 184, first_y + 240)).tobytes(),
                         sheet.crop((24, second_y, 184, second_y + 240)).tobytes())
        self.assertEqual(sheet.tobytes(), pipeline.silhouette_sheet(results).tobytes())

    def test_different_heights_reproduce_bytes_and_preserve_whole_derivatives(self):
        self.source()
        self.background()
        self.row["height_scale"] = "0.93"
        self.write_table([self.row])
        self.assertEqual(self.cli(), 0)
        first = self.hashes(self.root / "assets")
        self.assertEqual(self.cli(), 0)
        self.assertEqual(self.hashes(self.root / "assets"), first)
        folder = self.root / "assets/characters/tp_test"
        with Image.open(folder / "full.png") as full:
            self.assertEqual(full.size, (1024, 1536))
            for name, dimensions in pipeline.DERIVATIVES.items():
                with Image.open(folder / f"{name}.webp") as derivative:
                    self.assertEqual(derivative.size, dimensions)
                    expected = np.asarray(full.resize(dimensions, Image.Resampling.LANCZOS).convert("RGB"))
                    error = np.abs(expected.astype(float) - np.asarray(derivative).astype(float)).mean()
                    self.assertLess(error, 3)


class NameFontTests(unittest.TestCase):
    @unittest.skipUnless(Path("/System/Library/Fonts/Supplemental/Songti.ttc").exists(),
                         "macOS Songti collection is not installed")
    def test_report_font_covers_lindley_and_liang_name_variants(self):
        font = pipeline.name_font(40)
        missing = bytes(font.getmask("\uffff"))
        for char in "呤唎张国梁樑":
            self.assertIsNotNone(font.getmask(char).getbbox(), char)
            self.assertNotEqual(bytes(font.getmask(char)), missing, char)


if __name__ == "__main__":
    unittest.main()
