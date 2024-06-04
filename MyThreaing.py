import time
import cv2
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen
import torch
import SdkGetStreaming
from BodyCheck import ObjectDetection
import detect_api


class FrameGetThread(QThread):

    finishSignal = pyqtSignal(str)
    imgSignal = pyqtSignal(tuple)
    infoSignal = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.my_classicer = ObjectDetection()
        self.painter = QPainter()
        self.img = None
        self.is_quit = False
        # sdk取图线程
        SdkGetStreaming.start_thread()

    def quit_thread(self):
        self.is_quit = True

    def run(self) -> None:
        self.run_sdk()

    def run_sdk(self) -> None:
        # 加载yolov5的神经网络模型
        self.net = detect_api.DetectAPI(
            weights=r"D:\Code\Python\HumanDetection\best.pt", device="0", thres=0.4
        )
        # 循环运算
        while self.is_quit == False:
            if not SdkGetStreaming.data_chane1.empty():
                self.img = SdkGetStreaming.data_chane1.get()
            else:
                print("None")
                continue
            qimg1, infos = self.ai_deal_Yolov5()
            self.imgSignal.emit((qimg1, None))
            self.infoSignal.emit(infos)
            time.sleep(0.02)
        self.is_quit = False

    def ai_deal_Yolov5(self) -> None:
        img = self.img[:, 1100:]
        if img is None:
            return None, {"person_num": -1, "exist_person": -1}

        count_person = 0
        count_arclights = 0
        trans_distance = 999
        # 图像AI分析
        with torch.no_grad():
            result, names = self.net.detect([img])
            img = result[0][0]  # 每一帧图片的处理结果图片
            # 每一帧图像的识别结果（可包含多个物体）
            # print(len(result[0]))
            for cls, (x1, y1, x2, y2), conf in result[0][1]:
                # print(names[cls], x1, y1, x2, y2, conf)  # 识别物体种类、左上角x坐标、左上角y轴坐标、右下角x轴坐标、右下角y轴坐标，置信度
                if names[cls] == "person":
                    count_person += 1
                    # 高度中心计算
                    center_y = 0.5 * abs(y2 + y1)
                    # 判定距离通道中心最近的识别框
                    if center_y < 600:
                        trans_distance = min(trans_distance, (600 - center_y) * 1.8)
                    else:
                        trans_distance = min(trans_distance, center_y - 600)

                elif names[cls] == "arclight":
                    count_arclights += 1
        # 图像格式转换
        cvimg = img
        height, width, depth = cvimg.shape
        cvimg = cv2.cvtColor(cvimg, cv2.COLOR_BGR2RGB)
        cvimg = QImage(
            cvimg.data, width, height, width * depth, QImage.Format.Format_RGB888
        )
        # 存在人员标识符
        if count_person > 0:
            exist_person = True
        else:
            exist_person = False
        # 弧光存在标识符
        if count_arclights > 0:
            exist_arclights = True
        else:
            exist_arclights = False
        # 回传图像数据和判定结果
        ratio = 0.5  # 图片尺寸变换比例
        qimg = cvimg.scaled(int(cvimg.width() * ratio), int(cvimg.height() * ratio))
        infos = {
            "person_num": count_person,
            "exist_person": exist_person,
            "arclight_num": count_arclights,
            "exist_arclights": exist_arclights,
            "min_distance": trans_distance,
        }
        return qimg, infos