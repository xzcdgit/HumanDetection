import cv2
import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen
class CommonAlgorithms:

    def __init__(self) -> None:
        pass
    
    #RGB图像分离
    @classmethod
    def ChannelsSplit(cls,img) -> tuple[cv2.Mat, cv2.Mat,cv2.Mat]:
        b, g ,r =cv2.split(img)                 #顺序是b,g,r，不是r,g,b
        return b, g, r
    
    #图像调整大小
    @classmethod
    def ImgResize(cls, img:cv2.Mat, ratio:float):
        height,width = img.shape[:2]  #获取原图像的水平方向尺寸和垂直方向尺寸。
        img = cv2.resize(img, (int(width*ratio), int(height*ratio)), interpolation=cv2.INTER_CUBIC) 
        cv2.waitKey(0)
        return img


 #弧光检测 特殊设置
def ArclightCheck(img:cv2.Mat):
    ori_img = img

    #截取roi区域
    #img = img[270:1200,400:]

    #弧光为蓝紫光，只取b通道结果作为灰度图像
    b, g ,r =cv2.split(img)                 #顺序是b,g,r，不是r,g,b
    #b,g,r = CommonAlgorithms.ChannelsSplit(img)
    #图像二值化
    ret, binary = cv2.threshold(b, 220, 255, cv2.THRESH_BINARY)
    #开运算去噪点
    kernel = np.ones((3,3), np.uint8)
    open = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    # 1、根据二值图找到轮廓
    contours, hierarchy = cv2.findContours(open, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 轮廓      层级                               轮廓检索模式(推荐此)  轮廓逼近方法
    val_indexs = []

    for index,contour in enumerate(contours):
        area = cv2.contourArea(contour, False)
        if area > 120 and area < 5000:
            M = cv2.moments(contour)
            cx = M['m10']/M['m00']
            cy = M['m01']/M['m00']
            if cy>300 and cy<1300 and cx>400:
                val_indexs.append(index)
    return val_indexs, contours 


if __name__ == '__main__':
    img_dir = r'C:\Users\01477483\HM Web\CaptureFiles\2024-05-24\10.70.37.10_01_20240524082251902.jpg'#帧存放路径
    img = cv2.imread(img_dir)            #opencv读取图像文件
    #缩放图像
    img = CommonAlgorithms.ImgResize(img, 0.5)
    #弧光检测
    res,tmp = ArclightCheck(img)
    print(len(res))
    for i in res:
        dst = cv2.drawContours(img, tmp[i], -1, (0, 0, 255), 3)
    cv2.imshow("img",img)
    cv2.waitKey(0)

    