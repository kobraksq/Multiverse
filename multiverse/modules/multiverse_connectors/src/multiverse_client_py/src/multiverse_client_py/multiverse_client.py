#!/usr/bin/env python3

import dataclasses
from typing import List, Dict, Callable, TypeVar

from multiverse_client_pybind import MultiverseClientPybind  # noqa

T = TypeVar("T")


@dataclasses.dataclass
class MultiverseMetaData:
    world_name: str = "world"
    simulation_name: str = ""
    length_unit: str = "m"
    angle_unit: str = "rad"
    mass_unit: str = "kg"
    time_unit: str = "s"
    handedness: str = "rhs"


class SocketAddress:
    host: str = "tcp://127.0.0.1"
    port: str = ""

    def __init__(self, port: str) -> None:
        self.port = port


class MultiverseClient:
    _server_addr: SocketAddress = SocketAddress(port="7000")
    _client_addr: SocketAddress
    _meta_data: MultiverseMetaData
    _multiverse_socket: MultiverseClientPybind
    _start_time: float
    _api_callbacks: Dict[str, Callable[[List[str]], List[str]]]

    def __init__(
            self,
            client_addr: SocketAddress,
            multiverse_meta_data: MultiverseMetaData,
    ) -> None:
        if not isinstance(client_addr.port, str) or client_addr.port == "":
            raise ValueError(f"Must specify client port for {self.__class__.__name__}.")
        if multiverse_meta_data.simulation_name == "":
            raise ValueError(f"Must specify simulation name.")
        self._send_data = None
        self._client_addr = client_addr
        self._meta_data = multiverse_meta_data
        self._multiverse_socket = MultiverseClientPybind(
            f"{self._server_addr.host}:{self._server_addr.port}"
        )
        self.request_meta_data = {
            "meta_data": self._meta_data.__dict__,
            "send": {},
            "receive": {},
        }
        self._start_time = 0.0

    def loginfo(self, message: str) -> None:
        raise NotImplementedError(f"Must implement loginfo() for {self.__class__.__name__}.")

    def logwarn(self, message: str) -> None:
        raise NotImplementedError(f"Must implement logwarn() for {self.__class__.__name__}.")

    def run(self) -> None:
        message = f"[Client {self._client_addr.port}] Start {self.__class__.__name__}{self._client_addr.port}."
        self.loginfo(message)
        self._run()

    def _run(self) -> None:
        raise NotImplementedError(f"Must implement _run() for {self.__class__.__name__}.")

    def stop(self) -> None:
        self._disconnect()

    @property
    def request_meta_data(self) -> Dict:
        return self._request_meta_data

    @request_meta_data.setter
    def request_meta_data(self, request_meta_data: Dict) -> None:
        self._request_meta_data = request_meta_data
        self._multiverse_socket.set_request_meta_data(self._request_meta_data)

    @property
    def response_meta_data(self) -> Dict:
        response_meta_data = self._multiverse_socket.get_response_meta_data()
        assert isinstance(response_meta_data, dict)
        if response_meta_data == {}:
            message = f"[Client {self._client_addr.port}] Receive empty response meta data."
            self.logwarn(message)
        return response_meta_data

    @property
    def send_data(self) -> List[float]:
        return self._send_data

    @send_data.setter
    def send_data(self, send_data: List[float]) -> None:
        assert isinstance(send_data, list)
        self._send_data = send_data
        self._multiverse_socket.set_send_data(self._send_data)

    @property
    def receive_data(self) -> List[float]:
        receive_data = self._multiverse_socket.get_receive_data()
        assert isinstance(receive_data, list)
        return receive_data

    @property
    def api_callbacks(self) -> Dict[str, Callable[[List[str]], List[str]]]:
        return self._api_callbacks

    @api_callbacks.setter
    def api_callbacks(self, api_callbacks: Dict[str, Callable[[List[str]], List[str]]]) -> None:
        self._multiverse_socket.set_api_callbacks(api_callbacks)
        self._api_callbacks = api_callbacks

    def _bind_request_meta_data(self, request_meta_data: T) -> T:
        pass

    def _bind_response_meta_data(self, response_meta_data: T) -> T:
        pass

    def _bind_send_data(self, send_data: T) -> T:
        pass

    def _bind_receive_data(self, receive_data: T) -> T:
        pass

    def _connect_and_start(self) -> None:
        self._multiverse_socket.connect(self._client_addr.host, self._client_addr.port)
        self._multiverse_socket.start()
        self._start_time = self._multiverse_socket.get_time_now()

    def _disconnect(self) -> None:
        self._multiverse_socket.disconnect()

    def _communicate(self, resend_request_meta_data: bool = False) -> bool:
        return self._multiverse_socket.communicate(resend_request_meta_data)

    def _restart(self) -> None:
        self._disconnect()
        self._connect_and_start()

    @property
    def world_time(self) -> float:
        return self.response_meta_data["time"]

    @property
    def sim_time(self) -> float:
        return self._multiverse_socket.get_time_now() - self._start_time
