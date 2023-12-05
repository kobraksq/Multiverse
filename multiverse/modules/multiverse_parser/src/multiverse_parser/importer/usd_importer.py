#!/usr/bin/env python3.10

import os
import shutil
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, Sdf, Gf
from multiverse_parser import WorldBuilder, GeomType, JointType
from multiverse_parser.factory.body_builder import body_dict
from multiverse_parser.utils import xform_cache
from multiverse_parser.utils import import_usd, export_usd
from multiverse_parser.utils import clear_meshes, copy_prim


class UsdImporter:
    def __init__(
            self,
            usd_file_path: str,
            with_physics: bool,
            with_visual: bool,
            with_collision: bool,
    ) -> None:
        self.usd_file_path = usd_file_path
        self.with_physics = with_physics
        self.with_visual = with_visual
        self.with_collision = with_collision

        self.world_builder = WorldBuilder()

        self.stage = Usd.Stage.Open(self.usd_file_path)

        self.clean_up()

        root_prim = self.stage.GetDefaultPrim()
        self.world_builder.add_body(root_prim.GetName())

        self.parent_map = {}

        self.usd_mesh_path_dict = {}

        for joint_prim in [joint_prim for joint_prim in self.stage.Traverse() if joint_prim.IsA(UsdPhysics.Joint)]:
            parent_prim = self.stage.GetPrimAtPath(UsdPhysics.Joint(joint_prim).GetBody0Rel().GetTargets()[0])
            child_prim = self.stage.GetPrimAtPath(UsdPhysics.Joint(joint_prim).GetBody1Rel().GetTargets()[0])
            self.parent_map[child_prim] = parent_prim

        self.build_body(root_prim)

        if self.with_physics:
            self.build_joint(root_prim)

    def clean_up(self):
        xform_root_prims = [prim for prim in self.stage.GetPseudoRoot().GetChildren() if prim.IsA(UsdGeom.Xform)]
        if len(xform_root_prims) > 1:
            print("Multiple root prim found, add a default root prim")
            world_prim = UsdGeom.Xform.Define(self.stage, "/world").GetPrim()
            self.stage.SetDefaultPrim(world_prim)
            for xform_root_prim in xform_root_prims:
                xform_prim = UsdGeom.Xform.Define(self.stage,
                                                  world_prim.GetPath().AppendPath(xform_root_prim.GetName())).GetPrim()
                copy_prim(xform_root_prim, xform_prim, world_prim.GetPath())
                self.stage.RemovePrim(xform_root_prim.GetPath())

        geom_prims_to_add_xform = {}
        for prim in [prim for prim in self.stage.Traverse() if prim.IsA(UsdGeom.Xform)]:
            geom_prims = [geom_prim for geom_prim in prim.GetChildren() if geom_prim.IsA(UsdGeom.Gprim)]
            xform_prims = [xform_prim for xform_prim in prim.GetChildren() if
                           xform_prim.IsA(UsdGeom.Xform) and not xform_prim.IsA(UsdGeom.Gprim)]

            if len(geom_prims) > 0 and len(xform_prims) > 0:
                geom_prims_to_add_xform[prim.GetName()] = geom_prims

        for geom_prim_name, geom_prims in geom_prims_to_add_xform.items():
            for i, geom_prim in enumerate(geom_prims):
                new_xform_path = geom_prim.GetParent().GetPath().AppendPath(f"{geom_prim_name}_visual_{str(i)}")
                new_xform_prim = UsdGeom.Xform.Define(self.stage, new_xform_path)

                for xform_op in UsdGeom.Xformable(geom_prim).GetOrderedXformOps():
                    new_xform_prim.AddXformOp(op=xform_op.GetOpType(), precision=xform_op.GetPrecision()).Set(
                        value=xform_op.Get())

                new_geom_path = new_xform_path.AppendPath(geom_prim.GetName())
                new_geom_prim = self.stage.DefinePrim(new_geom_path, geom_prim.GetTypeName())

                copy_prim(geom_prim, new_geom_prim)

                self.stage.RemovePrim(geom_prim.GetPath())

    def build_body(self, parent_prim):
        for xform_prim in [xform_prim for xform_prim in parent_prim.GetChildren() if xform_prim.IsA(UsdGeom.Xform)]:
            child_geom_prims = [geom_prim for geom_prim in xform_prim.GetChildren() if geom_prim.IsA(UsdGeom.Gprim)]
            if len(child_geom_prims) == 0:
                if self.with_physics or self.parent_map.get(xform_prim) is None:
                    body_builder = self.world_builder.add_body(
                        body_name=xform_prim.GetName(),
                        parent_body_name=parent_prim.GetName(),
                    )
                    xform_local_transformation, _ = xform_cache.ComputeRelativeTransform(xform_prim, parent_prim)
                    body_builder.xform.AddTransformOp().Set(xform_local_transformation)
                elif self.parent_map.get(xform_prim) is not None:
                    body_builder = self.world_builder.add_body(
                        body_name=xform_prim.GetName(),
                        parent_body_name=parent_prim.GetName(),
                    )
                    xform_local_transformation, _ = xform_cache.ComputeRelativeTransform(xform_prim,
                                                                                         self.parent_map[xform_prim])
                    body_builder.xform.AddTransformOp().Set(xform_local_transformation)

                self.build_body(xform_prim)

            else:
                if len(child_geom_prims) > 1:
                    print(f"More than one child geom for {xform_prim.GetName()} exist, take the first one.")
                geom_prim = child_geom_prims[0]

                is_visual = not geom_prim.HasAPI(UsdPhysics.CollisionAPI)

                if (is_visual and self.with_visual) or (not is_visual and self.with_collision):
                    if geom_prim.IsA(UsdGeom.Cube):
                        geom_type = GeomType.CUBE
                    elif geom_prim.IsA(UsdGeom.Sphere):
                        geom_type = GeomType.SPHERE
                    elif geom_prim.IsA(UsdGeom.Cylinder):
                        geom_type = GeomType.CYLINDER
                    elif geom_prim.IsA(UsdGeom.Mesh):
                        geom_type = GeomType.MESH
                    else:
                        print(f"Geom type {geom_prim} not supported.")
                        continue

                    body_builder = body_dict[parent_prim.GetName()]
                    body_has_mass = body_builder.xform.GetPrim().HasAPI(UsdPhysics.MassAPI)

                    if body_has_mass and self.with_physics:
                        physics_mass_api = UsdPhysics.MassAPI(body_builder.xform)
                        mass = physics_mass_api.GetMassAttr().Get()
                        com = physics_mass_api.GetCenterOfMassAttr().Get()
                        diagonal_inertia = physics_mass_api.GetDiagonalInertiaAttr().Get()

                        body_builder.set_inertial(mass=mass, com=com, diagonal_inertia=diagonal_inertia)

                    geom_builder = body_builder.add_geom(
                        geom_name=xform_prim.GetName(),
                        geom_type=geom_type,
                        is_visual=is_visual,
                    )
                    geom_local_transformation = UsdGeom.Xform(xform_prim).GetLocalTransformation()
                    geom_builder.xform.AddTransformOp().Set(geom_local_transformation)

                    if geom_prim.IsA(UsdGeom.Sphere):
                        geom_builder.set_attribute(radius=UsdGeom.Sphere(geom_prim).GetRadiusAttr().Get())
                    elif geom_prim.IsA(UsdGeom.Cylinder):
                        geom_builder.set_attribute(radius=UsdGeom.Cylinder(geom_prim).GetRadiusAttr().Get())
                        geom_builder.set_attribute(height=UsdGeom.Cylinder(geom_prim).GetHeightAttr().Get() / 2)
                    elif geom_type == GeomType.MESH:
                        from multiverse_parser.factory import TMP_USD_MESH_PATH

                        xform_prepended_items = xform_prim.GetPrim().GetPrimStack()[0].referenceList.prependedItems
                        geom_prepended_items = geom_prim.GetPrim().GetPrimStack()[0].referenceList.prependedItems
                        if len(xform_prepended_items) > 0:
                            usd_mesh_path = xform_prepended_items[0].assetPath
                        elif len(geom_prepended_items) > 0:
                            usd_mesh_path = geom_prepended_items[0].assetPath
                        else:
                            mesh_path = os.path.join(
                                TMP_USD_MESH_PATH,
                                "visual" if is_visual else "collision",
                                geom_prim.GetName() + ".usda",
                            )
                            mesh_stage = Usd.Stage.CreateNew(mesh_path)

                            mesh_xform_path = Sdf.Path("/").AppendPath(geom_prim.GetName())
                            mesh_geom_path = mesh_xform_path.AppendPath("SM_" + geom_prim.GetName())

                            mesh_xform = UsdGeom.Xform.Define(mesh_stage, mesh_xform_path)
                            mesh_geom = UsdGeom.Mesh.Define(mesh_stage, mesh_geom_path)

                            for xform_attr in xform_prim.GetAttributes():
                                if xform_attr.GetName() == "xformOp:transform" or xform_attr.GetName() == "xformOpOrder":
                                    continue
                                xform_attr_value = xform_attr.Get()
                                if xform_attr_value is not None:
                                    mesh_xform_attr = mesh_xform.GetPrim().CreateAttribute(
                                        name=xform_attr.GetName(), typeName=xform_attr.GetTypeName()
                                    )
                                    mesh_xform_attr.Set(xform_attr_value)

                            copy_prim(geom_prim, mesh_geom.GetPrim())

                            mesh_stage.Save()
                            mesh_type = "visual" if is_visual else "collision"
                            usd_mesh_path = f"./tmp/usd/{mesh_type}/{geom_prim.GetName()}.usda"

                        if usd_mesh_path is not None:
                            if usd_mesh_path.startswith("./"):
                                usd_mesh_path = usd_mesh_path[2:]
                            if not os.path.isabs(usd_mesh_path):
                                usd_mesh_path = os.path.join(os.path.dirname(self.usd_file_path), usd_mesh_path)

                            out_usd = os.path.join(
                                TMP_USD_MESH_PATH,
                                "visual" if is_visual else "collision",
                                geom_prim.GetName() + ".usda",
                            )

                            if usd_mesh_path not in self.usd_mesh_path_dict:
                                if not os.path.exists(out_usd):
                                    clear_meshes()
                                    import_usd(in_usd=usd_mesh_path)
                                    export_usd(out_usd=out_usd)
                                self.usd_mesh_path_dict[usd_mesh_path] = [out_usd]

                            elif out_usd not in self.usd_mesh_path_dict[usd_mesh_path]:
                                os.makedirs(os.path.dirname(out_usd))
                                shutil.copy(self.usd_mesh_path_dict[usd_mesh_path], out_usd)
                                self.usd_mesh_path_dict[usd_mesh_path].append(out_usd)

                            mesh_builder = geom_builder.add_mesh(mesh_name=geom_prim.GetName())
                            mesh_builder.save()

                    if self.with_physics and not is_visual:
                        geom_builder.enable_collision()
                        if not body_has_mass:
                            if geom_builder.xform.GetPrim().HasAPI(UsdPhysics.MassAPI):
                                physics_mass_api = UsdPhysics.MassAPI(geom_builder.xform)
                                mass = physics_mass_api.GetMassAttr().Get()
                                com = physics_mass_api.GetCenterOfMassAttr().Get()
                                diagonal_inertia = physics_mass_api.GetDiagonalInertiaAttr().Get()
                                principal_axes = physics_mass_api.GetPrincipalAxesAttr().Get()

                                geom_builder.set_inertial(
                                    mass=mass,
                                    com=com,
                                    diagonal_inertia=diagonal_inertia,
                                    principal_axes=principal_axes,
                                )
                            else:
                                geom_builder.compute_inertial()

                    if not is_visual:
                        from multiverse_parser.factory import (
                            COLLISION_MESH_COLOR,
                            COLLISION_MESH_OPACITY,
                        )

                        geom_builder.set_attribute(prefix="primvars", displayColor=COLLISION_MESH_COLOR)
                        geom_builder.set_attribute(prefix="primvars", displayOpacity=COLLISION_MESH_OPACITY)

    def build_joint(self, parent_prim):
        for xform_prim in [xform_prim for xform_prim in parent_prim.GetChildren() if xform_prim.IsA(UsdGeom.Xform)]:
            joint_prims = [joint_prim for joint_prim in xform_prim.GetChildren() if joint_prim.IsA(UsdPhysics.Joint)]
            for joint_prim in joint_prims:
                joint = UsdPhysics.Joint(joint_prim)
                joint_name = joint.GetPrim().GetName()
                parent_name = Sdf.Path(joint.GetBody0Rel().GetTargets()[0]).name
                child_name = Sdf.Path(joint.GetBody1Rel().GetTargets()[0]).name
                body_builder = body_dict[child_name]
                body_builder.enable_rigid_body()

                joint_axis = "Z"
                if joint_prim.IsA(UsdPhysics.FixedJoint):
                    joint_type = JointType.FIXED
                elif joint_prim.IsA(UsdPhysics.RevoluteJoint):
                    joint_type = JointType.REVOLUTE
                    joint = UsdPhysics.RevoluteJoint(joint)
                    joint_axis = joint.GetAxisAttr().Get()
                elif joint_prim.IsA(UsdPhysics.PrismaticJoint):
                    joint_type = JointType.PRISMATIC
                    joint = UsdPhysics.PrismaticJoint(joint)
                    joint_axis = joint.GetAxisAttr().Get()
                elif joint_prim.IsA(UsdPhysics.SphericalJoint):
                    joint_type = JointType.SPHERICAL
                else:
                    raise NotImplementedError(f"Joint type {joint_prim} not supported.")

                body1_transform = xform_cache.GetLocalToWorldTransform(
                    self.stage.GetPrimAtPath(joint.GetBody0Rel().GetTargets()[0]).GetPrim())
                body1_rot = body1_transform.ExtractRotationQuat()

                body2_transform = xform_cache.GetLocalToWorldTransform(
                    self.stage.GetPrimAtPath(joint.GetBody1Rel().GetTargets()[0]).GetPrim())
                body1_to_body2_transform = body2_transform * body1_transform.GetInverse()
                body1_to_body2_pos = body1_to_body2_transform.ExtractTranslation()

                joint_quat = joint.GetLocalRot1Attr().Get()
                joint_pos = body1_rot.GetInverse().Transform(
                    Gf.Vec3d(joint.GetLocalPos0Attr().Get()) - body1_to_body2_pos)

                joint_builder = body_builder._import_joint(
                    joint_name=joint_name,
                    parent_name=parent_name,
                    joint_type=joint_type,
                    joint_pos=joint_pos,
                    joint_quat=joint_quat,
                    joint_axis=joint_axis,
                )

                if joint_prim.IsA(UsdPhysics.RevoluteJoint) or joint_prim.IsA(UsdPhysics.PrismaticJoint):
                    joint_builder.joint.CreateLowerLimitAttr(joint.GetLowerLimitAttr().Get())
                    joint_builder.joint.CreateUpperLimitAttr(joint.GetUpperLimitAttr().Get())

            self.build_joint(xform_prim)
