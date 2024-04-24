import signal
import subprocess
import unittest
from time import sleep, time

from multiverse_client_py import MultiverseClient, MultiverseMetaData, SocketAddress


def start_multiverse_server(server_port: str) -> subprocess.Popen:
    return subprocess.Popen(["multiverse_server", f"tcp://127.0.0.1:{server_port}"])


def kill_multiverse_server(process: subprocess.Popen):
    process.send_signal(signal.SIGINT)
    process.wait()


class MultiverseClientTest(MultiverseClient):
    def __init__(self, 
                 client_addr: SocketAddress, 
                 multiverse_meta_data: MultiverseMetaData) -> None:
        super().__init__(client_addr, multiverse_meta_data)

    def loginfo(self, message: str) -> None:
        print(message)

    def logwarn(self, message: str) -> None:
        print(message)

    def _run(self) -> None:
        self._connect_and_start()

    def send_and_receive_meta_data(self):
        self._communicate(True)

    def send_and_receive_data(self):
        self._communicate(False)


class MultiverseClientTestCase(unittest.TestCase):
    meta_data = MultiverseMetaData(
        world_name="world",
        length_unit="m",
        angle_unit="rad",
        mass_unit="kg",
        time_unit="s",
        handedness="rhs",
    )
    time_start = 0.0
    _server_port = "6500"
    _process = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.time_start = time()

        MultiverseClientTest._server_addr.port = cls._server_port
        cls._process = start_multiverse_server(cls._server_port)

    @classmethod
    def tearDownClass(cls) -> None:
        kill_multiverse_server(cls._process)

    def create_multiverse_client_send(self, port, object_name, attribute_names):
        meta_data = self.meta_data
        meta_data.simulation_name = "sim_test_send"
        multiverse_client = MultiverseClientTest(client_addr=SocketAddress(port=port),
                                                 multiverse_meta_data=meta_data)
        multiverse_client.request_meta_data["send"][object_name] = attribute_names
        multiverse_client.run()
        return multiverse_client

    def multiverse_client_send_data(self, multiverse_client, send_data):
        multiverse_client.send_data = send_data
        multiverse_client.send_and_receive_data()

    def create_multiverse_client_receive(self, port, object_name, attribute_names):
        meta_data = self.meta_data
        meta_data.simulation_name = "sim_test_receive"
        multiverse_client = MultiverseClientTest(client_addr=SocketAddress(port=port),
                                                 multiverse_meta_data=meta_data)
        multiverse_client.request_meta_data["receive"][object_name] = attribute_names
        multiverse_client.run()
        return multiverse_client

    def create_multiverse_client_reset(self, port):
        meta_data = self.meta_data
        meta_data.simulation_name = "sim_test_reset"
        multiverse_client = MultiverseClientTest(client_addr=SocketAddress(port=port),
                                                 multiverse_meta_data=meta_data)
        multiverse_client.run()
        return multiverse_client

    def create_multiverse_client_spawn(self, port):
        meta_data = self.meta_data
        meta_data.simulation_name = "sim_test_spawn"
        multiverse_client = MultiverseClientTest(client_addr=SocketAddress(port=port),
                                                 multiverse_meta_data=meta_data)
        multiverse_client.run()
        return multiverse_client

    def test_multiverse_client_send_creation(self):
        multiverse_client_test_send = self.create_multiverse_client_send("1234", "object_1", ["position", "quaternion"])
        self.assertIn("time", multiverse_client_test_send.response_meta_data)
        time_send = multiverse_client_test_send.response_meta_data["time"]
        self.assertIn("send", multiverse_client_test_send.response_meta_data)
        send_objects = multiverse_client_test_send.response_meta_data["send"]
        self.assertDictEqual(multiverse_client_test_send.response_meta_data, {
            'meta_data': {'angle_unit': 'rad', 'handedness': 'rhs', 'length_unit': 'm', 'mass_unit': 'kg',
                          'simulation_name': 'sim_test_send', 'time_unit': 's', 'world_name': 'world'},
            'send': send_objects,
            'time': time_send})
        multiverse_client_test_send.stop()

    def test_multiverse_client_send_data(self):
        multiverse_client_test_send = self.create_multiverse_client_send("1234", "object_1", ["position", "quaternion"])

        time_now = time() - self.time_start
        self.multiverse_client_send_data(multiverse_client_test_send, [time_now, 3.0, 2.0, 1.0, 1.0, 0.0, 0.0, 0.0])

        self.assertEqual(multiverse_client_test_send.receive_data, [time_now])
        multiverse_client_test_send.stop()

        return multiverse_client_test_send, time_now

    def test_multiverse_client_receive_creation(self):
        _, time_send = self.test_multiverse_client_send_data()

        multiverse_client_test_receive = self.create_multiverse_client_receive("1235", "object_1",
                                                                               ["position", "quaternion"])

        self.assertDictEqual(multiverse_client_test_receive.response_meta_data, {
            'meta_data': {'angle_unit': 'rad', 'handedness': 'rhs', 'length_unit': 'm', 'mass_unit': 'kg',
                          'simulation_name': 'sim_test_receive', 'time_unit': 's', 'world_name': 'world'},
            'receive': {'object_1': {'position': [3, 2, 1], 'quaternion': [1, 0, 0, 0]}}, 'time': time_send})

        multiverse_client_test_receive.stop()

    def test_multiverse_client_reset_creation(self):
        multiverse_client_test_reset = self.create_multiverse_client_reset("1236")
        self.assertIn("time", multiverse_client_test_reset.response_meta_data)
        time_reset = multiverse_client_test_reset.response_meta_data["time"]
        self.assertDictEqual(multiverse_client_test_reset.response_meta_data, {
            'meta_data': {'angle_unit': 'rad', 'handedness': 'rhs', 'length_unit': 'm', 'mass_unit': 'kg',
                          'simulation_name': 'sim_test_reset', 'time_unit': 's', 'world_name': 'world'},
            'time': time_reset})
        multiverse_client_test_reset.stop()

    def test_multiverse_client_reset(self):
        self.test_multiverse_client_send_data()
        multiverse_client_test_reset = self.create_multiverse_client_reset("1236")

        multiverse_client_test_reset.send_data = [0.0]
        multiverse_client_test_reset.send_and_receive_data()

        self.assertEqual(multiverse_client_test_reset.receive_data, [0.0])
        multiverse_client_test_reset.stop()

    def test_multiverse_client_spawn_creation(self):
        multiverse_client_test_spawn = self.create_multiverse_client_spawn("1237")

        self.assertIn("time", multiverse_client_test_spawn.response_meta_data)
        time_spawn = multiverse_client_test_spawn.response_meta_data["time"]
        self.assertDictEqual(multiverse_client_test_spawn.response_meta_data, {
            'meta_data': {'angle_unit': 'rad', 'handedness': 'rhs', 'length_unit': 'm', 'mass_unit': 'kg',
                          'simulation_name': 'sim_test_spawn', 'time_unit': 's', 'world_name': 'world'},
            'time': time_spawn})

        multiverse_client_test_spawn.stop()


class MultiverseClientSpawnTestCase(unittest.TestCase):
    meta_data = MultiverseMetaData(
        length_unit="m",
        angle_unit="rad",
        mass_unit="kg",
        time_unit="s",
        handedness="rhs",
    )
    time_start = 0.0
    _server_port = "7000"
    _process = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.time_start = time()
        # _process = subprocess.Popen(["multiverse_launch", "multiverse/resources/muv/empty.muv"])

    # @classmethod
    # def tearDownClass(cls) -> None:
    #     kill_multiverse_server(cls._process)

    def create_multiverse_client_spawn(self, port, world_name):
        meta_data = self.meta_data
        meta_data.world_name = world_name
        meta_data.simulation_name = "sim_test_spawn"
        multiverse_client = MultiverseClientTest(client_addr=SocketAddress(port=port),
                                                 multiverse_meta_data=meta_data)
        multiverse_client.run()
        return multiverse_client

    def create_multiverse_client_destroy(self, port, world_name):
        meta_data = self.meta_data
        meta_data.world_name = world_name
        meta_data.simulation_name = "sim_test_destroy"
        multiverse_client = MultiverseClientTest(client_addr=SocketAddress(port=port),
                                                 multiverse_meta_data=meta_data)
        multiverse_client.run()
        return multiverse_client

    def test_multiverse_client_spawn_creation(self):
        multiverse_client_test_spawn = self.create_multiverse_client_spawn("1337", "world")
        self.assertIn("time", multiverse_client_test_spawn.response_meta_data)
        time_spawn = multiverse_client_test_spawn.response_meta_data["time"]
        self.assertDictEqual(multiverse_client_test_spawn.response_meta_data, {
            'meta_data': {'angle_unit': 'rad', 'handedness': 'rhs', 'length_unit': 'm', 'mass_unit': 'kg',
                          'simulation_name': 'sim_test_spawn', 'time_unit': 's', 'world_name': 'world'},
            'time': time_spawn})

        multiverse_client_test_spawn.stop()

    def test_multiverse_client_spawn(self):
        multiverse_client_test_spawn = self.create_multiverse_client_spawn("1337", "world")

        multiverse_client_test_spawn.request_meta_data["meta_data"]["simulation_name"] = "empty_simulation"
        multiverse_client_test_spawn.request_meta_data["send"]["milk_box"] = ["position",
                                                                              "quaternion",
                                                                              "relative_velocity"]
        multiverse_client_test_spawn.request_meta_data["send"]["panda"] = ["position",
                                                                           "quaternion"]
        multiverse_client_test_spawn.send_and_receive_meta_data()

        time_now = time() - self.time_start
        multiverse_client_test_spawn.send_data = [time_now,
                                                  0, 0, 5,
                                                  0.0, 0.0, 0.0, 1.0,
                                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                  0, 0, 3,
                                                  0.0, 0.0, 0.0, 1.0]
        multiverse_client_test_spawn.send_and_receive_data()

        multiverse_client_test_spawn.stop()

    def test_multiverse_client_move(self):
        multiverse_client_test_move = self.create_multiverse_client_spawn("1337", "world")

        x_pos = [0.0, 1.0, 1.0, 1.0, 0.0, -1.0, -1.0, -1.0, 0.0]
        y_pos = [1.0, 1.0, 0.0, -1.0, -1.0, -1.0, 0.0, 1.0, 1.0]
        for i in range(9):
            multiverse_client_test_move.request_meta_data["meta_data"]["simulation_name"] = "empty_simulation"
            multiverse_client_test_move.request_meta_data["send"]["milk_box"] = ["position",
                                                                                 "quaternion",
                                                                                 "relative_velocity"]
            multiverse_client_test_move.send_and_receive_meta_data()

            time_now = time() - self.time_start
            multiverse_client_test_move.send_data = [time_now,
                                                     x_pos[i], y_pos[i], 5,
                                                     0.0, 0.0, 0.0, 1.0,
                                                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            multiverse_client_test_move.send_and_receive_data()

            sleep(1)

        multiverse_client_test_move.stop()

    def test_multiverse_client_destroy(self):
        multiverse_client_test_destroy = self.create_multiverse_client_destroy("1338", "world")

        multiverse_client_test_destroy.request_meta_data["meta_data"]["simulation_name"] = "empty_simulation"
        multiverse_client_test_destroy.request_meta_data["send"]["milk_box"] = []
        multiverse_client_test_destroy.request_meta_data["receive"]["milk_box"] = []
        multiverse_client_test_destroy.send_and_receive_meta_data()

        time_now = time() - self.time_start
        multiverse_client_test_destroy.send_data = [time_now]
        multiverse_client_test_destroy.send_and_receive_data()

        multiverse_client_test_destroy.stop()

    def test_multiverse_client_spawn_and_destroy(self):
        multiverse_client_test_spawn = self.create_multiverse_client_spawn("1337", "world")
        multiverse_client_test_spawn.request_meta_data["meta_data"]["simulation_name"] = "empty_simulation"
        multiverse_client_test_spawn.request_meta_data["send"]["bread_1"] = ["position", "quaternion"]
        multiverse_client_test_spawn.send_and_receive_meta_data()

        time_now = time() - self.time_start
        multiverse_client_test_spawn.send_data = [time_now,
                                                  0.0, 0.0, 3,
                                                  0.0, 0.0, 0.0, 1.0]
        multiverse_client_test_spawn.send_and_receive_data()
        multiverse_client_test_spawn.stop()

        sleep(2)

        multiverse_client_test_destroy = self.create_multiverse_client_destroy("1338", "world")

        multiverse_client_test_destroy.request_meta_data["meta_data"]["simulation_name"] = "empty_simulation"
        multiverse_client_test_destroy.request_meta_data["send"]["bread_1"] = []
        multiverse_client_test_destroy.request_meta_data["receive"]["bread_1"] = []
        multiverse_client_test_destroy.send_and_receive_meta_data()

        time_now = time() - self.time_start
        multiverse_client_test_destroy.send_data = [time_now]
        multiverse_client_test_destroy.send_and_receive_data()

        multiverse_client_test_destroy.stop()


if __name__ == "__main__":
    unittest.main()