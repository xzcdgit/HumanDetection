import time
import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu, modbus_tcp
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRectF, QPointF


class ModbusRtuClientClass:
    def __init__(
        self,
        method="rtu",
        port="COM3",
        baudrate: int = 115200,
    ) -> None:

        self.method = method
        self.port = port
        self.is_connected = False
        self.master = modbus_rtu.RtuMaster(
            serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                xonxoff=0,
            )
        )
        self.master.open()
        self.master.set_timeout(0.5)
        self.master.set_verbose(True)

    def write_single_coil(self, slave=1, output_index: int = -1, output_val: int = 0):
        # res = self.master.execute(1, cst.WRITE_SINGLE_COIL, 3, output_value=1)
        res = 0
        try:
            if self.master.isinstance():
                res = self.master.execute(
                    slave, cst.WRITE_SINGLE_COIL, output_index, output_value=output_val
                )
        except Exception as e:
            print(e)
        return res


class ModbusTcpClientClass:
    def __init__(
        self, host: str = "192.168.31.65", port: int = 502, timeout: float = 0.2
    ) -> None:
        self.count_reconnect_try = 0
        self.count_reconnect_limit = 3
        self.host = host
        self.port = port
        self.master = modbus_tcp.TcpMaster(self.host, self.port, timeout)
        self.master.set_timeout(0.5)
        print("connected")

    def write_single_coil(self, output_index: int = -1, output_val: int = 0):
        try:
            self.count_reconnect_try = 0
            self.master.execute(
                0, cst.WRITE_SINGLE_COIL, output_index, output_value=output_val
            )
            return True
        except TimeoutError as e:
            self.reconnect()
            return False

    def reconnect(self):
        self.master = modbus_tcp.TcpMaster(self.host, self.port, timeout_in_sec=0.2)
        self.count_reconnect_try += 1
        if self.count_reconnect_try > self.count_reconnect_limit:
            return False
        return True

    def close(self):
        self.master.close()

    def __del__(self):
        try:
            self.master.close()
            print("成功关闭端口")
        except Exception as e:
            print("关闭端口失败")


class FrameGetThread(QThread):

    finishSignal = pyqtSignal(str)

    def __init__(self, parent=None) -> None:

        super().__init__(parent)
        self.modbus_controller = ModbusTcpClientClass("192.168.31.65", 502, 0.2)
        self.is_quit = False
        self.coil_params = [-1, -1]

    def run(self):
        while self.is_quit == False:
            if self.coil_params[1] >= 0:
                self.modbus_controller.write_single_coil(
                    self.coil_params[0], self.coil_params[1]
                )

    def quit_thread(self):
        self.is_quit = True

    def set_coil(self, index, val):
        self.coil_params = [index, val]


if __name__ == "__main__":
    myDemo = ModbusTcpClientClass()
    myDemo.write_single_coil(2, 1)
    time.sleep(0.1)
    myDemo.write_single_coil(2, 0)
    time.sleep(0.1)
    myDemo.write_single_coil(1, 1)
    time.sleep(0.1)
    myDemo.write_single_coil(1, 0)
