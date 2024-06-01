
import sys
import time
import datetime
import logging
import ctypes
import asyncio
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtGui import QPixmap
from Ui_Main import Ui_MainWindow
from MyThreaing import FrameGetThread
import Modbus
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")

class MyApp(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)    # 设置界面
        self.connect_ui_signal() # 连接ui信号
        self.init_frame_class() # 图像获取类初始化
        self.last_update_time = 0
        self.fps = 0
        self.last_update_time2 = 0
        self.fps2 = 0
        self.frame_count = 0
        self.person_last_time = time.time() #最近一次出现人体的时间
        self.arcligth_last_time = time.time() #最近一次出现弧光的时间
        self.is_lock = False #异常锁定标识符
        self.unlock_time_stamp = time.time() #锁定结束时间戳
        self.lock_time = 10 #锁定时长
        self.last_output_signal = False
        self.last_exist_person_info = {"min_distance":500}
        #self.modbus_controller = Modbus.ModbusTcpClientClass('192.168.31.65', 502 ,0.1)
        self.init_log()

    #图像线程设置
    def init_frame_class(self):
        self.recall_img = FrameGetThread()
        self.recall_img.imgSignal.connect(self.recall_show_img)
        self.recall_img.infoSignal.connect(self.recall_show_info)
    
    #日志模块初始化
    def init_log(self):
        
        logger = logging.getLogger(__name__)
        logger.setLevel(level = logging.INFO)
        handler = logging.FileHandler("log.txt")
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger

    def connect_ui_signal(self):
        self.pushButton.clicked.connect(self.start_img_thread) # 设置图像显示线程
        self.pushButton_2.clicked.connect(self.quit_img_thread) # 退出图像显示线程
        
    #启动取图线程
    def start_img_thread(self):
        self.recall_img.start()
        self.last_update_time = time.time()

    def quit_img_thread(self):
        self.recall_img.quit_thread()

    #检测回调
    #图像回调
    def recall_show_img(self, pixs:tuple):
        if pixs[0] is not None:
            self.label.setPixmap(QPixmap(pixs[0]))
            self.label.setScaledContents(True)
        if pixs[1] is not None:
            self.label_4.setPixmap(QPixmap(pixs[1]))
            self.label_4.setScaledContents(True)
    #判定信息回调
    def recall_show_info(self, infos:dict):
        is_person = False
        is_arclight = False

        #当前时间记录
        current_time = time.time()
        
        #帧率显示
        fps = 0
        last_time = time.time()
        el_time = last_time-self.last_update_time
        if el_time:
            fps = 1/el_time
        self.label_2.setText("{:.1f}".format(fps))
        self.last_update_time = last_time

        #Ai人体检测判定
        #人员存在
        if infos["exist_person"]:
            is_person = True
            self.person_last_time = time.time()
            self.label_3.setText("是")
            self.label_3.setStyleSheet("color: white; background-color: Red ")
            self.last_exist_person_info = infos #记录最近一次有人的帧信息
            #self.modbus_controller.write_single_coil(2,1)
        else:#本帧图像无人
            #判定人员是否从图像边界消失
            if self.last_exist_person_info["min_distance"] < 500 and self.is_lock == False: #非边界消失并且未锁定，锁定按键x秒
                print("目标失踪！")
                self.unlock_time_stamp = time.time()+self.lock_time #设置锁定结束时间
                self.is_lock = True #修改锁定标识符

            elif self.is_lock == False and current_time-self.person_last_time > 0.5:
                is_person = False
                self.label_3.setText("否")
                self.label_3.setStyleSheet("color: white; background-color: Green ")
                #self.modbus_controller.write_single_coil(2,0)

            #如果已经锁定且当前时间大于锁定截至时间则解锁
            elif current_time > self.unlock_time_stamp:
                self.is_lock = False #解锁

        #弧光存在判定
        if infos["exist_arclights"]:
            is_arclight = True
            self.arcligth_last_time = time.time()
            self.label_6.setText("是")
            self.label_6.setStyleSheet("color: white; background-color: Red ")
            #self.modbus_controller.write_single_coil(3,1)

        #弧光信号保留x秒
        elif current_time-self.arcligth_last_time > 1:
            is_arclight = False
            self.label_6.setText("否")
            self.label_6.setStyleSheet("color: white; background-color: Green ")
            #self.modbus_controller.write_single_coil(3,0)

        is_out = is_arclight or is_person
        #调试信息输出
        self.statusbar.showMessage("测试信息 人员检定框数：{} 弧光检定框数：{} 最小距离：{:.1f}  判定结果：{}".format(infos["person_num"], infos["arclight_num"], infos["min_distance"], is_out))
        
        '''
        #存在信号判定输出
        if is_out:
            self.modbus_controller.write_single_coil(1,1)
        else:
            self.modbus_controller.write_single_coil(1,0)

        print(is_out, is_out != self.last_output_signal)
        '''
        #日志记录
        if is_out != self.last_output_signal:
            self.last_output_signal = is_out
            self.logger.info("existent personnel "+str(is_out))
        
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myapp = MyApp()
    myapp.show()
    sys.exit(app.exec_())