#!/usr/bin/env python3
from typing import Dict

from multiverse_interfaces.msg import ObjectData
from multiverse_interfaces.srv import Socket

from .ros_service import MultiverseRosService
from ..multiverse_ros_node import SimulationMetaData


class SocketService(MultiverseRosService):
    _srv_name = "/multiverse/socket"
    _srv_type = Socket
    _worlds = {}
    _simulation_name = ""

    def __init__(
            self,
            node_name: str,
            client_host: str = "tcp://127.0.0.1",
            client_port: str = "",
            simulation_metadata: SimulationMetaData = SimulationMetaData()
    ) -> None:
        super().__init__(node_name=node_name, client_host=client_host, client_port=client_port,
                         simulation_metadata=simulation_metadata)

    def update_world(self, world_name) -> None:
        self.request_meta_data["meta_data"]["world_name"] = world_name
        self.request_meta_data["receive"][""] = [""]
        self._communicate(True)
        receive_objects = self.response_meta_data["receive"]
        if self.response_meta_data.get("receive") is not None:
            self._worlds[world_name] = {}
            self._worlds[world_name][""] = {""}
            for object_name, object_attributes in receive_objects.items():
                self._worlds[world_name][object_name] = {""}
                for attribute_name in object_attributes:
                    self._worlds[world_name][""].add(attribute_name)
                    self._worlds[world_name][object_name].add(attribute_name)

    def _bind_request_meta_data(self, request: Socket.Request) -> Socket.Request:
        meta_data = request.meta_data
        world_name = meta_data.world_name
        if world_name == "":
            self.get_logger().warn(f"World is not set, set to default world")
            world_name = "world"

        self._simulation_name = meta_data.simulation_name
        if self._simulation_name == "":
            world_need_update = False

            if self._worlds.get(world_name) is None:
                world_need_update = True
            else:
                for object_attribute in request.receive:
                    if self._worlds[world_name].get(object_attribute.object_name) is None:
                        world_need_update = True
                        break
                    for attribute_name in object_attribute.attribute_names:
                        if attribute_name not in self._worlds[world_name][object_attribute.object_name]:
                            world_need_update = True
                            break

            if world_need_update:
                self.update_world(world_name)

        request_meta_data: Dict = {"meta_data": {}, "send": {}, "receive": {}}
        request_meta_data["meta_data"]["world_name"] = world_name
        request_meta_data["meta_data"][
            "simulation_name"] = "ros" if self._simulation_name == "" else self._simulation_name
        request_meta_data["meta_data"][
            "length_unit"] = "m" if meta_data.length_unit == "" else meta_data.length_unit
        request_meta_data["meta_data"][
            "angle_unit"] = "rad" if meta_data.angle_unit == "" else meta_data.angle_unit
        request_meta_data["meta_data"][
            "mass_unit"] = "kg" if meta_data.mass_unit == "" else meta_data.mass_unit
        request_meta_data["meta_data"][
            "time_unit"] = "s" if meta_data.time_unit == "" else meta_data.time_unit
        request_meta_data["meta_data"][
            "handedness"] = "rhs" if meta_data.handedness == "" else meta_data.handedness

        send_data = [0]

        is_simulation_name_empty = self._simulation_name == ""

        for object_data in request.send:
            is_object_name_empty = object_data.object_name == ""
            if is_object_name_empty:
                continue
            request_meta_data["send"][object_data.object_name] = [object_data.attribute_name]
            send_data += object_data.data

        for object_attribute in request.receive:
            is_object_name_empty = object_attribute.object_name == ""
            object_not_found = world_name not in self._worlds or object_attribute.object_name not in self._worlds[
                world_name]
            if is_simulation_name_empty and object_not_found:
                continue
            if not is_simulation_name_empty and is_object_name_empty:
                continue
            self.request_meta_data["receive"][object_attribute.object_name] = []
            for attribute_name in object_attribute.attribute_names:
                empty_attribute_name = attribute_name == ""
                attribute_not_found = world_name not in self._worlds or attribute_name not in self._worlds[world_name][
                    object_attribute.object_name]
                if is_simulation_name_empty and attribute_not_found:
                    continue
                if not is_simulation_name_empty and empty_attribute_name:
                    continue
                self.request_meta_data["receive"][object_attribute.object_name].append(attribute_name)

        self.request_meta_data = request_meta_data
        self.send_data = send_data
        return request

    def _bind_response_meta_data(self, response: Socket.Request) -> Socket.Response:
        response_meta_data = self.response_meta_data
        if self._simulation_name != "" and (
                response_meta_data.get("send") is not None or response_meta_data.get("receive") is not None):
            self._communicate()
            self._communicate()
            self.request_meta_data["name"] = "ros"
            self._communicate(True)

        response_meta_data = self.response_meta_data

        response.meta_data.world_name = response_meta_data["meta_data"]["world_name"]
        response.meta_data.simulation_name = response_meta_data["meta_data"]["simulation_name"]
        response.meta_data.length_unit = response_meta_data["meta_data"]["length_unit"]
        response.meta_data.angle_unit = response_meta_data["meta_data"]["angle_unit"]
        response.meta_data.mass_unit = response_meta_data["meta_data"]["mass_unit"]
        response.meta_data.time_unit = response_meta_data["meta_data"]["time_unit"]
        response.meta_data.handedness = response_meta_data["meta_data"]["handedness"]

        response.send = []
        if response_meta_data.get("send") is not None:
            for object_name, object_data in response_meta_data["send"].items():
                for attribute_name, attribute_data in object_data.items():
                    response.send.append(ObjectData(object_name=object_name, attribute_name=attribute_name,
                                                    attribute_data=attribute_data))

        response.receive = []
        if response_meta_data.get("receive") is not None:
            for object_name, object_data in response_meta_data["receive"].items():
                for attribute_name, attribute_data in object_data.items():
                    response.receive.append(ObjectData(object_name=object_name, attribute_name=attribute_name,
                                                       attribute_data=attribute_data))

        return response
