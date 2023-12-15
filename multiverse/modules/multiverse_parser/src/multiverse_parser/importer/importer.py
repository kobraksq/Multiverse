#!/usr/bin/env python3

import atexit
import os
import random
import shutil
import string
import subprocess
from typing import Optional, Dict, Tuple

from ..factory.config import Configuration
from ..utils import (import_obj, import_stl, import_dae,
                     export_obj, export_stl, export_dae, export_usd)


def copy_and_overwrite(source_folder: str, destination_folder: str) -> None:
    os.makedirs(name=destination_folder, exist_ok=True)

    # Iterate through all files and folders in the source folder
    for item in os.listdir(source_folder):
        source_item = os.path.join(source_folder, item)
        destination_item = os.path.join(destination_folder, item)

        # If item is a folder, call the function recursively
        if os.path.isdir(source_item):
            if os.path.exists(destination_item):
                shutil.rmtree(destination_item)
            shutil.copytree(source_item, destination_item)
        # If item is a file, simply copy it
        else:
            shutil.copy2(source_item, destination_item)


class Importer:
    source_file_path: str
    config: Configuration
    tmp_meshdir_path: str
    tmp_file_path: str
    _tmp_file_name: str = "tmp"
    _mesh_file_paths: Dict[str, Tuple[str, str]] = {}

    def __init__(self, file_path: str, config: Configuration = Configuration()):
        self._source_file_path = file_path
        self._tmp_file_path, self._tmp_meshdir_path = self._create_tmp_paths()
        self._config = config
        atexit.register(self.clean_up)

    def _create_tmp_paths(self) -> Tuple[str, str]:
        """
        Create temporary paths for the USD file and the mesh directory.
        :return: Tuple of the temporary USD file path and the temporary mesh directory path.
        """
        tmp_dir = os.path.join("/tmp",
                               "cache",
                               "".join(random.choices(string.ascii_letters + string.digits, k=10)))
        tmp_file_path = os.path.join(tmp_dir, f"{self._tmp_file_name}.usda")
        tmp_mesh_dir = os.path.join(tmp_dir, self._tmp_file_name, "usd")
        os.makedirs(name=tmp_dir, exist_ok=True)
        os.makedirs(name=tmp_mesh_dir, exist_ok=True)
        print(f"Create {tmp_dir} and {tmp_mesh_dir}.")
        return tmp_file_path, tmp_mesh_dir

    def import_model(self, save_file_path: Optional[str] = None) -> str:
        """
        Import the model from the source file path to the temporary file path.
        :param save_file_path: Optional path to save the USD file to.
        :return: If save_file_path is None, return the temporary file path. Otherwise, return the save_file_path.
        """
        raise NotImplementedError

    def import_mesh(self, mesh_file_path: str) -> Tuple[str, str]:
        """
        Import the mesh from the mesh file path to the temporary mesh directory path.
        :param mesh_file_path: Path to the mesh file.
        :return: Paths to the imported mesh.
        """
        if mesh_file_path in self.mesh_file_paths:
            return self.mesh_file_paths[mesh_file_path]

        file_name = os.path.basename(mesh_file_path).split(".")[0]
        file_extension = os.path.splitext(mesh_file_path)[1]
        tmp_origin_file_path = os.path.join(os.path.dirname(self.tmp_meshdir_path),
                                            file_extension[1:],
                                            f"{file_name}{file_extension}")
        tmp_usd_file_path = os.path.join(self.tmp_meshdir_path,
                                         f"from_{file_extension[1:]}",
                                         f"{file_name}.usda")

        if file_extension == ".obj":
            cmd = import_obj(mesh_file_path) + export_obj(tmp_origin_file_path) + export_usd(tmp_usd_file_path)
        elif file_extension == ".stl":
            cmd = import_stl(mesh_file_path) + export_stl(tmp_origin_file_path) + export_usd(tmp_usd_file_path)
        elif file_extension == ".dae":
            cmd = import_dae(mesh_file_path) + export_dae(tmp_origin_file_path) + export_usd(tmp_usd_file_path)
        else:
            raise ValueError(f"Unsupported file extension {file_extension}.")

        cmd = ["blender",
               "--background",
               "--python-expr",
               f"import bpy"
               f"{cmd}"]

        process = subprocess.Popen(cmd)
        process.wait()

        self.mesh_file_paths[mesh_file_path] = tmp_usd_file_path, tmp_origin_file_path

        return tmp_usd_file_path, tmp_origin_file_path

    def save_tmp_model(self, file_path: str) -> None:
        file_name = os.path.basename(file_path).split(".")[0]
        file_dir = os.path.dirname(file_path)
        tmp_file_dir = os.path.dirname(self.tmp_file_path)
        new_file_path = os.path.join(file_dir, os.path.basename(self.tmp_file_path))

        copy_and_overwrite(source_folder=tmp_file_dir, destination_folder=file_dir)

        os.rename(new_file_path, file_path)

        new_mesh_dir = os.path.join(file_dir, file_name)
        if os.path.exists(new_mesh_dir):
            shutil.rmtree(new_mesh_dir)

        tmp_meshdir = os.path.join(file_dir, self._tmp_file_name)
        if os.path.exists(tmp_meshdir):
            os.rename(tmp_meshdir, new_mesh_dir)

            with open(file_path, encoding="utf-8") as file:
                file_contents = file.read()

            tmp_path = os.path.dirname(self._tmp_meshdir_path)
            new_path = file_name
            file_contents = file_contents.replace(tmp_path, new_path)

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(file_contents)

    def clean_up(self) -> None:
        """
        Remove the temporary directory.
        :return: None
        """
        tmp_dir_path = os.path.dirname(self.tmp_file_path)
        if os.path.exists(tmp_dir_path):
            print(f"Remove {tmp_dir_path}.")
            shutil.rmtree(tmp_dir_path)

    @property
    def tmp_file_path(self) -> str:
        return self._tmp_file_path

    @property
    def tmp_meshdir_path(self) -> str:
        return self._tmp_meshdir_path

    @property
    def mesh_file_paths(self) -> Dict[str, Tuple[str, str]]:
        return self._mesh_file_paths

    @property
    def source_file_path(self) -> str:
        return self._source_file_path

    @source_file_path.setter
    def source_file_path(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")
        self._source_file_path = file_path

    @property
    def config(self) -> Configuration:
        return self._config

    @config.setter
    def config(self, config: Configuration) -> None:
        if not isinstance(config, Configuration):
            raise TypeError(f"Expected {Configuration}, got {type(config)}")
        self._config = config
