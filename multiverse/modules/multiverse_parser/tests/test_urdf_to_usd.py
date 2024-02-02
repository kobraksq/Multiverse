import unittest

import os
import tracemalloc

import numpy

from multiverse_parser import UrdfImporter

from pxr import Usd


class UrdfToUsdTestCase(unittest.TestCase):
    resource_path: str

    @classmethod
    def setUpClass(cls):
        tracemalloc.start()
        cls.resource_path = os.path.join(os.path.dirname(__file__), "..", "resources")

    def test_urdf_to_usd_1(self):
        input_urdf_path = os.path.join(self.resource_path, "input", "tiago_dual", "urdf", "tiago_dual.urdf")
        importer = UrdfImporter(file_path=input_urdf_path,
                                with_physics=True,
                                with_visual=True,
                                with_collision=True,
                                default_rgba=numpy.array([1.0, 0.0, 0.0, 0.1]))
        self.assertEqual(importer.source_file_path, input_urdf_path)
        self.assertEqual(importer._config.model_name, "tiago_dual")

        usd_file_path = importer.import_model()
        self.assertTrue(os.path.exists(usd_file_path))

        stage = Usd.Stage.Open(usd_file_path)
        default_prim = stage.GetDefaultPrim()
        self.assertEqual(default_prim.GetName(), "tiago_dual")

        output_usd_path = os.path.join(self.resource_path, "output", "test_urdf_to_usd", "tiago_dual.usda")
        importer.save_tmp_model(usd_file_path=output_usd_path)
        self.assertTrue(os.path.exists(output_usd_path))

    def test_urdf_to_usd_2(self):
        input_urdf_path = os.path.join(self.resource_path, "input", "ur5e", "urdf", "ur5e.urdf")
        importer = UrdfImporter(file_path=input_urdf_path,
                                with_physics=True,
                                with_visual=True,
                                with_collision=True,
                                default_rgba=numpy.array([1.0, 0.0, 0.0, 0.1]))
        self.assertEqual(importer.source_file_path, input_urdf_path)
        self.assertEqual(importer._config.model_name, "ur5e")

        usd_file_path = importer.import_model()
        self.assertTrue(os.path.exists(usd_file_path))

        stage = Usd.Stage.Open(usd_file_path)
        default_prim = stage.GetDefaultPrim()
        self.assertEqual(default_prim.GetName(), "ur5e")

        output_usd_path = os.path.join(self.resource_path, "output", "test_urdf_to_usd", "ur5e.usda")
        importer.save_tmp_model(usd_file_path=output_usd_path)
        self.assertTrue(os.path.exists(output_usd_path))

    def test_urdf_to_usd_3(self):
        input_urdf_path = os.path.join(self.resource_path, "input", "milk_box", "urdf", "milk_box.urdf")
        importer = UrdfImporter(file_path=input_urdf_path, with_physics=True, with_visual=True,
                                with_collision=True)
        usd_file_path = importer.import_model()

        stage = Usd.Stage.Open(usd_file_path)
        default_prim = stage.GetDefaultPrim()
        self.assertEqual(default_prim.GetName(), "milk_box")

        output_usd_path = os.path.join(self.resource_path, "output", "test_urdf_to_usd", "milk_box.usda")
        importer.save_tmp_model(usd_file_path=output_usd_path)
        self.assertTrue(os.path.exists(output_usd_path))

    def test_urdf_to_usd_with_invalid_file_path(self):
        with self.assertRaises(FileNotFoundError):
            UrdfImporter(file_path="abcxyz", with_physics=True, with_visual=True,
                         with_collision=True)

    @classmethod
    def tearDownClass(cls):
        tracemalloc.stop()


if __name__ == '__main__':
    unittest.main()