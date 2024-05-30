import time
import threading
from PIL import Image
import cv2
import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen
import torchvision
import SdkGetStreaming
from BodyCheck import ObjectDetection
from ImageGet import RTSCapture
import SpcecialChecks
import asyncio
import detect_api
from multiprocessing import Lock, Pool
import torch


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

        #sdk取图线程
        SdkGetStreaming.start_thread()
    
    def quit_thread(self):
        self.is_quit = True

    def run_rtsp(self) -> None:

        pen = QPen(QColor(255,0,0,), 3)
        rtscap = RTSCapture.create(url = "rtsp://admin:13860368866xzc@10.70.37.10/Streaming/Channels/1")
        rtscap.start_read()
        while self.is_quit == False:
            if rtscap.isStarted():
                ok, frame = rtscap.read_latest_frame()
                if ok:
                    img = frame
                else:
                    continue
            #图像AI分析
            input_image = Image.fromarray(np.uint8(img))
            output_dict = self.my_classicer.img_calculate(input_image)
            out_boxes = output_dict["boxes"].cpu()
            out_scores = output_dict["scores"].cpu()
            out_labels = output_dict["labels"].cpu()
            num_boxes = out_boxes.shape[0]

            #图像格式转换
            cvimg = img
            height, width, depth = cvimg.shape
            cvimg = cv2.cvtColor(cvimg, cv2.COLOR_BGR2RGB)
            cvimg = QImage(cvimg.data, width, height, width * depth, QImage.Format.Format_RGB888)
            
            self.painter.begin(cvimg)

            #绘画参数设置
            self.painter.setPen(pen)
            self.painter.setFont(QFont('SimSun', 30))
            
            # 最大方框绘制数max_vis 判定阈值thres
            max_vis = 20
            thres = 0.8
            count_person = 0

            #idxs = torchvision.ops.nms(out_boxes,out_scores,0.85)
            #for idx in idxs:
            for idx in range(0, min(num_boxes, max_vis)):
                score = out_scores[idx].numpy()
                bbox = out_boxes[idx].numpy()
                class_name = self.my_classicer.COCO_INSTANCE_CATEGORY_NAMES[out_labels[idx]]
                #中心点计算
                box_center = (0.5*(bbox[0]+bbox[2]), 0.5*(bbox[1]+bbox[3]))
                # 如果目标不为人或者分数小于这个阈值，则不绘制
                if class_name == "person" and score > thres and box_center[1] > 300:
                        
                    #绘制边界框
                    rect = QRectF(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
                    self.painter.drawRect(rect)
                    #绘制名称
                    point = QPointF(bbox[0],bbox[1])
                    self.painter.drawText(point,"人 {:.2f}".format(score))
                    count_person += 1
            self.painter.end()
            #存在人员标识符
            exist_person = False
            if count_person>0:
                exist_person = True
            cvimg = cvimg.scaled(1200,800)
            #回调
            self.imgSignal.emit(QPixmap(cvimg))
            self.infoSignal.emit({"person_num":count_person, "exist_person":exist_person})
        
        rtscap.stop_read()
        rtscap.release()
        self.is_quit = False

    def run_sdk(self) -> None:
        #加载yolov5的神经网络模型
        self.net = detect_api.DetectAPI(weights=r'D:\Code\Python\HumanDetection\best.pt',device='0',thres=0.6)
        #循环运算
        while self.is_quit == False:
            if not SdkGetStreaming.data_chane1.empty():
                self.img = SdkGetStreaming.data_chane1.get()
            else:
                print("None")
                continue
            qimg1, infos = self.ai_deal_Yolov5()
                
            self.imgSignal.emit((qimg1, None))
            self.infoSignal.emit(infos)
            time.sleep(0.01)
        self.is_quit = False

    def run(self) -> None:
        #thread_ai = threading.Thread(target=self.ai_deal_thread)
        #thread_ai.setDaemon(True) #主线程退出时强制退出子线程
        #thread_ai.start()

        #thread_arclight = threading.Thread(target=self.arclight_deal_thread)
        #thread_arclight.setDaemon(True) #主线程退出时强制退出子线程
        #thread_arclight.start()
        self.run_sdk()





        
    def ai_deal_BodyCheck(self) -> None:
        img = self.img[:, 1100:]
        if img is None:
            return None, {"person_num":-1, "exist_person":-1}
        ratio = 0.3
        pen = QPen(QColor(255,0,0,), 3)
        #图像AI分析
        input_image = Image.fromarray(np.uint8(img))
        output_dict = self.my_classicer.img_calculate(input_image)
        out_boxes = output_dict["boxes"].cpu()
        out_scores = output_dict["scores"].cpu()
        out_labels = output_dict["labels"].cpu()
        num_boxes = out_boxes.shape[0]

        #图像格式转换
        cvimg = img
        height, width, depth = cvimg.shape
        cvimg = cv2.cvtColor(cvimg, cv2.COLOR_BGR2RGB)
        cvimg = QImage(cvimg.data, width, height, width * depth, QImage.Format.Format_RGB888)
        
        self.painter.begin(cvimg)

        #绘画参数设置
        self.painter.setPen(pen)
        self.painter.setFont(QFont('SimSun', 30))
        
        # 最大方框绘制数max_vis 判定阈值thres
        max_vis = 20
        thres = 0.85
        count_person = 0

        #idxs = torchvision.ops.nms(out_boxes,out_scores,0.85)
        #for idx in idxs:
        for idx in range(0, min(num_boxes, max_vis)):
            score = out_scores[idx].numpy()
            bbox = out_boxes[idx].numpy()
            class_name = self.my_classicer.COCO_INSTANCE_CATEGORY_NAMES[out_labels[idx]]
            #中心点计算
            box_center = (0.5*(bbox[0]+bbox[2]), 0.5*(bbox[1]+bbox[3]))
            # 如果目标不为人或者分数小于这个阈值，则不绘制
            if class_name == "person" and score > thres and box_center[1] > 300:
                    
                #绘制边界框
                rect = QRectF(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
                self.painter.drawRect(rect)
                #绘制名称
                point = QPointF(bbox[0],bbox[1])
                self.painter.drawText(point,"人 {:.2f}".format(score))
                count_person += 1
        self.painter.end()
        #存在人员标识符
        exist_person = False
        if count_person>0:
            exist_person = True
        qimg = cvimg.scaled(int(cvimg.width()*ratio), int(cvimg.height()*ratio))
        infos = {"person_num":count_person, "exist_person":exist_person}
        #回调
        return qimg, infos

    def ai_deal_Yolov5(self) -> None:
        img = self.img[:, 1100:]
        if img is None:
            return None, {"person_num":-1, "exist_person":-1}
        
        count_person = 0
        count_arclights = 0

        #图像AI分析
        with torch.no_grad():
            result, names = self.net.detect([img])
            img = result[0][0]  # 每一帧图片的处理结果图片
            # 每一帧图像的识别结果（可包含多个物体）
            #print(len(result[0]))
            for cls, (x1, y1, x2, y2), conf in result[0][1]:
                #print(names[cls], x1, y1, x2, y2, conf)  # 识别物体种类、左上角x坐标、左上角y轴坐标、右下角x轴坐标、右下角y轴坐标，置信度
                if names[cls] == "person":
                    count_person += 1
                elif names[cls] == "arclight":
                    count_arclights += 1
                '''
                cv2.rectangle(img,(x1,y1),(x2,y2),(0,255,0))
                cv2.putText(img,names[cls],(x1,y1-20),cv2.FONT_HERSHEY_DUPLEX,1.5,(255,0,0))'''
            #print()  # 将每一帧的结果输出分开
            #height,width = img.shape[:2]
            #res = cv2.resize(img,(width//2,height//2),interpolation=cv2.INTER_CUBIC)   #dsize=（2*width,2*height）

        #图像格式转换
        cvimg = img
        height, width, depth = cvimg.shape
        cvimg = cv2.cvtColor(cvimg, cv2.COLOR_BGR2RGB)
        cvimg = QImage(cvimg.data, width, height, width * depth, QImage.Format.Format_RGB888)

        #存在人员标识符
        exist_person = False
        if count_person>0:
            exist_person = True

        #弧光存在标识符
        if count_arclights>0:
            exist_arclights = True
        else:
            exist_arclights = False
        
        #回传图像数据和判定结果
        ratio = 0.5 #图片尺寸变换比例
        qimg = cvimg.scaled(int(cvimg.width()*ratio), int(cvimg.height()*ratio))
        infos = {"person_num":count_person, "exist_person":exist_person, "arclight_num":count_arclights, "exist_arclights":exist_arclights}
        #回调
        return qimg, infos

    def arclight_deal(self) ->None:
        #裁剪区
        img = self.img[:, 1600:2500]
        #屏蔽区
        img[500:, :200] = 0
        img[800:, :450] = 0

        if img is None:
            return None, {"arclight_num":-1, "exist_arclights":-1}
        ratio = 0.3
        val_list, contours = SpcecialChecks.ArclightCheck(img)
        count_arclights = len(val_list)
        dst = img
        for i in val_list:
            dst = cv2.drawContours(img, contours[i], -1, (0, 0, 255), 3)

        if count_arclights>0:
            exist_arclights = True
        else:
            exist_arclights = False

        #图像格式转换
        cvimg = dst
        height, width, depth = cvimg.shape
        cvimg = cv2.cvtColor(cvimg, cv2.COLOR_BGR2RGB)
        cvimg = QImage(cvimg.data, width, height, width * depth, QImage.Format.Format_RGB888)
        qimg = cvimg.scaled(int(cvimg.width()*ratio), int(cvimg.height()*ratio))
        infos = {"arclight_num":count_arclights, "exist_arclights":exist_arclights}
        #回调
        return qimg, infos

    def ai_deal_thread(self):
        while True:
            self.ai_deal()
            time.sleep(0.05)

    def arclight_deal_thread(self):
        while True:
            self.arclight_deal()
            time.sleep(0.05)
