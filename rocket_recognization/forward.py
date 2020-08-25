# -*- coding: utf-8 -*-
import sys
sys.path.append('/home/robin/XRocket/rocket_recognization')
import torch
from torch.utils.data import DataLoader
from rocketDataset import RocketDataSet
from torchvision import transforms
import numpy as np
import pandas as pd
resnet34=torch.load('/home/robin/XRocket/rocket_recognization/resnet34_rocket100.pkl')
transform = transforms.Compose([transforms.Resize((640,480)),transforms.ToTensor()]) 
labels = pd.read_csv('/home/robin/XRocket/rocket_recognization/labels.csv')

def net_foward(img):
    loss_func = torch.nn.CrossEntropyLoss().cuda()
    img_tensor = transform(img)
    img_tensor=img_tensor.unsqueeze(0)
    output = resnet34(img_tensor.cuda())
    pred_y = int(torch.Tensor.max(output,1)[1].data.cpu().numpy())
    title = labels.loc[:,'class'][pred_y]+'运载火箭'
    print(title)
    return title