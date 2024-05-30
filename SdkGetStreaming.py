# coding=utf-8

import os
import platform
import tkinter
import HCNetSDK
import PlayCtrl
import numpy as np
import cv2
import queue
import threading


DLL_PATH_WIN = r"D:\Code\Python\HumanDetection\lib\win"
DLL_PATH_LINUX = r"D:\Code\Python\HumanDetection\lib\linux"
data_chane1 = queue.Queue(3)

class YU12ToMat:

    def __init__(self) -> None:
        self.frame_buffer = []
        self.USE_COLOR = 1

    def add_frame(self, height, width, data):
        if data_chane1.full():
            cc = data_chane1.get()
        res, img = self.read(height, width, data)
        data_chane1.put(img)

    def read(self, nHeight, nWidth, imgsrc, img_type=True):
        if img_type:  # 彩色图像
            pImgYUV = np.zeros(
                (nHeight, nWidth, 3), dtype=np.uint8
            )  # OpenCV 空图像对象
            # print('shape of pImgYCrCb=', pImgYUV.shape)
            self.yv12toYUV(pImgYUV, imgsrc)  # 得到全部YUV图像数据
            pImgdst = cv2.cvtColor(pImgYUV, cv2.COLOR_YUV2RGB)  # 转为RGB图像对象
            # pImgdst = cv2.cvtColor(imgsrc, cv2.COLOR_YUV2RGB_YV12)
        else:  # 灰度图像
            pImgYUV = np.zeros((nHeight, nWidth), dtype=np.uint8)  # OpenCV 空图像对象
            self.yv12toYUV(pImgYUV, imgsrc)  # 得到图像的Y分量（灰度图像）
            pImgdst = pImgYUV
        # end if
        # self.frame_buffer.clear()
        return True, pImgdst

    def yv12toYUV(self, outYuv: np.ndarray, inYv12: np.ndarray):
        """
        :param outYuv: 3 dimension ndarray
        :param inYv12: 1 dimension ndarray
        :return:
        """
        height = outYuv.shape[0]
        width = outYuv.shape[1]
        ndim = outYuv.ndim
        #print("yv12toYUV: width=", width, "height=", height)

        if ndim == 2:
            # Y
            outYuv[:, :] = inYv12[0 : width * height].reshape(height, -1)
        elif ndim == 3:
            # Y
            outYuv[:, :, 0] = inYv12[0 : width * height].reshape(height, -1)
            # U
            tmp = inYv12[width * height : width * height + width * height // 4].reshape(
                height // 2, -1
            )
            outYuv[:, :, 1][::2][:, ::2] = tmp
            outYuv[:, :, 1][::2][:, 1::2] = tmp
            outYuv[:, :, 1][1::2][:, ::2] = tmp
            outYuv[:, :, 1][1::2][:, 1::2] = tmp
            # V
            tmp = inYv12[width * height + width * height // 4 :].reshape(
                height // 2, -1
            )
            outYuv[:, :, 2][::2][:, ::2] = tmp
            outYuv[:, :, 2][::2][:, 1::2] = tmp
            outYuv[:, :, 2][1::2][:, ::2] = tmp
            outYuv[:, :, 2][1::2][:, 1::2] = tmp


class GetSdkStreaming:

    # 全局参数初始化
    def __init__(
        self,
        ip: str = "10.70.37.10",
        port: int = 8000,
        user_name: str = "admin",
        password: str = "13860368866xzc",
    ) -> None:

        # 登录的设备信息
        self.ip = PlayCtrl.create_string_buffer(bytes(ip, encoding="utf8"))
        self.port = port
        self.user_name = PlayCtrl.create_string_buffer(
            bytes(user_name, encoding="utf8")
        )
        self.password = PlayCtrl.create_string_buffer(bytes(password, encoding="utf8"))

        self.is_windows = True  # 操作系统类型标识符
        self.preview_win = None  # 预览窗口
        self.pic_box = None  # 图片预览标签
        self.funcRealDataCallBack_V30 = None  # 实时预览回调函数，需要定义为全局的
        self.PlayCtrl_Port = PlayCtrl.c_long(-1)  # 播放句柄
        self.Playctrldll = None  # 播放库
        self.FuncDecCB = None  # 播放库解码回调函数，需要定义为全局的

        self.lRealPlayHandle = None
        self.lUserId = None
        self.device_info = None

        self.myTest = YU12ToMat()
        self.init_sdk()

    def init_sdk(self):
        # 获取系统平台
        self.GetPlatform()

        # 加载库,先加载依赖库
        self.LoadLib()

        self.SetSDKInitCfg()  # 设置组件库和SSL库加载路径


    def run(self):
        # 创建窗口
        self.preview_win = tkinter.Tk()
        self.preview_win.withdraw()  # 实现主窗口隐藏

        # 获取系统平台
        self.GetPlatform()

        # 加载库,先加载依赖库
        self.LoadLib()

        self.SetSDKInitCfg()  # 设置组件库和SSL库加载路径

        # 初始化DLL
        self.Objdll.NET_DVR_Init()
        # 启用SDK写日志
        self.Objdll.NET_DVR_SetLogToFile(
            3, bytes("./SdkLog_Python/", encoding="utf-8"), False
        )

        # 获取一个播放句柄
        if not self.Playctrldll.PlayM4_GetPort(PlayCtrl.byref(self.PlayCtrl_Port)):
            print("获取播放库句柄失败")

        # 登录设备
        (lUserId, device_info) = self.LoginDev(self.Objdll)
        if lUserId < 0:
            err = self.Objdll.NET_DVR_GetLastError()
            print(
                "Login device fail, error code is: %d"
                % self.Objdll.NET_DVR_GetLastError()
            )
            # 释放资源
            self.Objdll.NET_DVR_Cleanup()
            return 2

        # 定义码流回调函数
        funcRealDataCallBack_V30 = HCNetSDK.REALDATACALLBACK(self.RealDataCallBack_V30)
        # 开启预览
        lRealPlayHandle = self.OpenPreview(
            self.Objdll, lUserId, funcRealDataCallBack_V30
        )
        if lRealPlayHandle < 0:
            print(
                "Open preview fail, error code is: %d"
                % self.Objdll.NET_DVR_GetLastError()
            )
            # 登出设备
            self.Objdll.NET_DVR_Logout(lUserId)
            # 释放资源
            self.Objdll.NET_DVR_Cleanup()
            return 3

        self.preview_win.mainloop()
        # 关闭预览
        self.Objdll.NET_DVR_StopRealPlay(lRealPlayHandle)

        # 停止解码，释放播放库资源
        if self.PlayCtrl_Port.value > -1:
            self.Playctrldll.PlayM4_Stop(self.PlayCtrl_Port)
            self.Playctrldll.PlayM4_CloseStream(self.PlayCtrl_Port)
            self.Playctrldll.PlayM4_FreePort(self.PlayCtrl_Port)
            self.PlayCtrl_Port = PlayCtrl.c_long(-1)

        # 登出设备
        self.Objdll.NET_DVR_Logout(lUserId)

        # 释放资源
        self.Objdll.NET_DVR_Cleanup()

    def stop_get_streaming(self):
        if self.lRealPlayHandle >= 0:
            # 关闭预览
            self.Objdll.NET_DVR_StopRealPlay(self.lRealPlayHandle)

            # 停止解码，释放播放库资源
            if self.PlayCtrl_Port.value > -1:
                self.Playctrldll.PlayM4_Stop(self.PlayCtrl_Port)
                self.Playctrldll.PlayM4_CloseStream(self.PlayCtrl_Port)
                self.Playctrldll.PlayM4_FreePort(self.PlayCtrl_Port)
                self.PlayCtrl_Port = PlayCtrl.c_long(-1)
            if self.lUserId >= 0:
                # 登出设备
                self.Objdll.NET_DVR_Logout(self.lUserId)
            # 释放资源
            self.Objdll.NET_DVR_Cleanup()

    def LoadLib(self):
        # 加载库,先加载依赖库
        if self.is_windows:
            os.chdir(
                DLL_PATH_WIN
            )
            self.Objdll = HCNetSDK.ctypes.CDLL(r"./HCNetSDK.dll")  # 加载网络库
            self.Playctrldll = HCNetSDK.ctypes.CDLL(r"./PlayCtrl.dll")  # 加载播放库
        else:
            os.chdir(
                DLL_PATH_LINUX
            )
            self.Objdll = PlayCtrl.cdll.LoadLibrary(r"./libhcnetsdk.so")
            self.Playctrldll = PlayCtrl.cdll.LoadLibrary(r"./libPlayCtrl.so")

    # 获取当前系统环境
    def GetPlatform(self):
        sysstr = platform.system()
        print("" + sysstr)
        if sysstr != "Windows":
            self.is_windows = False

    # 设置SDK初始化依赖库路径
    def SetSDKInitCfg(self):
        # 设置HCNetSDKCom组件库和SSL库加载路径
        # print(os.getcwd())
        if self.is_windows:
            strPath = os.getcwd().encode("gbk")
            sdk_ComPath = HCNetSDK.NET_DVR_LOCAL_SDK_PATH()
            sdk_ComPath.sPath = strPath
            self.Objdll.NET_DVR_SetSDKInitCfg(2, PlayCtrl.byref(sdk_ComPath))
            self.Objdll.NET_DVR_SetSDKInitCfg(
                3, PlayCtrl.create_string_buffer(strPath + b"\libcrypto-1_1-x64.dll")
            )
            self.Objdll.NET_DVR_SetSDKInitCfg(
                4, PlayCtrl.create_string_buffer(strPath + b"\libssl-1_1-x64.dll")
            )
        else:
            strPath = os.getcwd().encode("utf-8")
            sdk_ComPath = HCNetSDK.NET_DVR_LOCAL_SDK_PATH()
            sdk_ComPath.sPath = strPath
            self.Objdll.NET_DVR_SetSDKInitCfg(2, PlayCtrl.byref(sdk_ComPath))
            self.Objdll.NET_DVR_SetSDKInitCfg(
                3, PlayCtrl.create_string_buffer(strPath + b"/libcrypto.so.1.1")
            )
            self.Objdll.NET_DVR_SetSDKInitCfg(
                4, PlayCtrl.create_string_buffer(strPath + b"/libssl.so.1.1")
            )

    def LoginDev(self, Objdll):
        # 登录注册设备
        device_info = HCNetSDK.NET_DVR_DEVICEINFO_V30()
        lUserId = Objdll.NET_DVR_Login_V30(
            self.ip,
            self.port,
            self.user_name,
            self.password,
            PlayCtrl.byref(device_info),
        )
        return (lUserId, device_info)

    # 解码回调函数
    def DecCBFun(self, nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
        if pFrameInfo.contents.nType == 3:
            self.myTest.add_frame(
                pFrameInfo.contents.nHeight,
                pFrameInfo.contents.nWidth,
                np.frombuffer(pBuf[:nSize], np.uint8).copy(),
            )

    # 实时播放部分
    def RealDataCallBack_V30(self, lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
        # 码流回调函数
        if dwDataType == HCNetSDK.NET_DVR_SYSHEAD:
            # 设置流播放模式
            self.Playctrldll.PlayM4_SetStreamOpenMode(self.PlayCtrl_Port, 0)
            # 打开码流，送入40字节系统头数据
            if self.Playctrldll.PlayM4_OpenStream(
                self.PlayCtrl_Port, pBuffer, dwBufSize, 1024 * 1024
            ):
                # 设置解码回调，可以返回解码后YUV视频数据
                self.FuncDecCB = PlayCtrl.DECCBFUNWIN(self.DecCBFun)
                self.Playctrldll.PlayM4_SetDecCallBackExMend(
                    self.PlayCtrl_Port, self.FuncDecCB, None, 0, None
                )

                # 开始解码播放
                if self.pic_box:
                    wininfo_id = self.pic_box.winfo_id()
                else:
                    wininfo_id = None
                if self.Playctrldll.PlayM4_Play(self.PlayCtrl_Port, wininfo_id):
                    print("播放库播放成功")
                else:
                    print("播放库播放失败")
            else:
                print("播放库打开流失败")
        elif dwDataType == HCNetSDK.NET_DVR_STREAMDATA:
            self.Playctrldll.PlayM4_InputData(self.PlayCtrl_Port, pBuffer, dwBufSize)
        else:
            print("其他数据,长度:", dwBufSize)

    def OpenPreview(self, Objdll, lUserId, callbackFun):
        """
        打开预览
        """
        preview_info = HCNetSDK.NET_DVR_PREVIEWINFO()
        preview_info.hPlayWnd = 0
        preview_info.lChannel = 1  # 通道号
        preview_info.dwStreamType = 0  # 主码流
        preview_info.dwLinkMode = 0  # TCP
        preview_info.bBlocked = 1  # 阻塞取流

        # 开始预览并且设置回调函数回调获取实时流数据
        lRealPlayHandle = Objdll.NET_DVR_RealPlay_V40(
            lUserId, PlayCtrl.byref(preview_info), callbackFun, None
        )
        return lRealPlayHandle

    def InputData(self, fileMp4, Playctrldll):
        while True:
            pFileData = fileMp4.read(4096)
            if pFileData is None:
                break
            if not Playctrldll.PlayM4_InputData(
                self.PlayCtrl_Port, pFileData, len(pFileData)
            ):
                break


def func():
    myDemo = GetSdkStreaming()
    myDemo.run()

def start_thread():
    t1 = threading.Thread(target=func)
    t1.setDaemon(True) #主线程退出时强制退出子线程
    t1.start()


if __name__ == "__main__":
    transor = YU12ToMat()
    t1 = threading.Thread(target=func)
    t1.setDaemon(True) #主线程退出时强制退出子线程
    t1.start()
    while True:
        if not data_chane1.empty():
            height, width, data = data_chane1.get()
            res, img = transor.read(height, width, data)
            cv2.imshow("test", img)
        if cv2.waitKey(40) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            break
