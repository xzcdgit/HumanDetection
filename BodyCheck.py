import os
import sys
import time
from PIL import Image
from matplotlib import pyplot as plt

import torch.nn as nn
import torch
import numpy as np
import torchvision.transforms as transforms
import torchvision

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
class ObjectDetection():
    def __init__(self) -> None:
        # classes_coco
        self.COCO_INSTANCE_CATEGORY_NAMES = [
            '__background__', 'person', 'bicycle', 'car', 'motorcycle',
            'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
            'fire hydrant', 'N/A', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear',
            'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
            'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard',
            'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'N/A',
            'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana',
            'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog',
            'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
            'N/A', 'dining table', 'N/A', 'N/A', 'toilet', 'N/A', 'tv',
            'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 'microwave',
            'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book', 'clock',
            'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        # config
        self.preprocess = transforms.Compose([
            transforms.ToTensor(),
        ])

        self.model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(pretrained=True)  #载入预训练模型
        #self.model = torch.load('model.pkl')
        self.model.eval()
        #if torch.cuda.is_available():
        #    self.model.to('cuda')
        
    def img_calculate(self, input_image:Image):

        # 1. load data & model
        input_image = input_image.convert("RGB")  #载入图像
        '''
        #model.eval()  设置为预测模式 主要是针对dropout和batch normalization层 
        #dropout是训练阶段让一定比例的神经元失去作用（屏蔽部分神经元），
        来减少结果对局部特征的过分依赖，而测试时应使用整个模型
        
        #batch normalization 数据归一化 由于模型只能计算当前batch的均值和方差，
        所以最后需要对所有批次的均值和方差作指数平均，而训练时这个行为没有太大的意义
        '''
        # 2. preprocess
        img_chw = self.preprocess(input_image)  #对输入的图片进行处理（转为Tensor）
        # 3. to device
        if torch.cuda.is_available():  #将数据和模型转移至gpu进行计算
            img_chw = img_chw.to('cuda')
            self.model.to('cuda')
        # 4. forward
        # 这里图片不再是 BCHW 的形状，而是一个list，每个元素是图片
        input_list = [img_chw]
        with torch.no_grad():
            #tic = time.time()
            #print("input img tensor shape:{}".format(input_list[0].shape))
            output_list = self.model(input_list)  #将输入列表传入模型运算输出list
            # 输出也是一个 list，每个元素是一个 dict
            output_dict = output_list[0]
            #print("pass: {:.3f}s".format(time.time() - tic))
            #for k, v in output_dict.items():
            #    print("key:{}, value:{}".format(k, v))
        return output_dict

def test_local_pic():
    #BASE_DIR = r"D:\Code\Python\HumanDetection"    
    my_classicer = ObjectDetection()
    #files = os.listdir(BASE_DIR)
    fig, ax = plt.subplots(figsize=(12, 12))
    #for file in files:
    #图像获取
    #path_img = BASE_DIR+"\\"+file
    #path_img = os.path.join(BASE_DIR, "demo_img2.png")
    path_img = r"D:\Code\Python\HumanDetection\test.jpeg"
    input_image = Image.open(path_img)

    #print("图像类型   ",type(input_image))
    output_dict = my_classicer.img_calculate(input_image)
    # 5. visualization
    out_boxes = output_dict["boxes"].cpu()
    out_scores = output_dict["scores"].cpu()
    out_labels = output_dict["labels"].cpu()
    
    #图像AI分析-非极大值抑制
    i = torchvision.ops.nms(out_boxes,out_scores,0.45)



    ax.imshow(input_image, aspect='equal')
    num_boxes = out_boxes.shape[0]

    print("NMS", i)
    print("num_boxes", num_boxes)

    # 这里最多绘制 40 个框
    max_vis = 40
    thres = 0.9
    #for idx in range(0, min(num_boxes, max_vis)):
    for idx in i:
        print(idx)
        score = out_scores[idx].numpy()
        bbox = out_boxes[idx].numpy()
        class_name = my_classicer.COCO_INSTANCE_CATEGORY_NAMES[out_labels[idx]]
        # 如果分数小于这个阈值，则不绘制
        if score < thres:
            continue
        #绘制边界框
        ax.add_patch(
            plt.Rectangle((bbox[0], bbox[1]),
                            bbox[2] - bbox[0],
                            bbox[3] - bbox[1],
                            fill=False,
                            edgecolor='red',
                            linewidth=3.5))
        #绘制边界框文字说明
        ax.text(bbox[0],
                bbox[1] - 2,
                '{:s} {:.3f}'.format(class_name, score),
                bbox=dict(facecolor='blue', alpha=0.5),
                fontsize=14,
                color='white')
    plt.pause(99999)
    plt.cla()

if __name__ == "__main__":
    test_local_pic()
