from __future__ import division
import time
import torch
from torch.autograd import Variable
import numpy as np
import cv2
from util import *
from darknet import Darknet
import random
import pickle as pkl
from imutils.video import WebcamVideoStream
import imutils
import argparse

WIDTH = 480
ZOOM_WIDTH = 1280

def get_test_input(input_dim, CUDA):
    img = cv2.imread("imgs/messi.jpg")
    img = cv2.resize(img, (input_dim, input_dim))
    img_ = img[:, :, ::-1].transpose((2, 0, 1))
    img_ = img_[np.newaxis, :, :, :] / 255.0
    img_ = torch.from_numpy(img_).float()
    img_ = Variable(img_)

    if CUDA:
        img_ = img_.cuda()

    return img_


def prep_image(img, inp_dim):
    """
    Prepare image for inputting to the neural network. 
    
    Returns a Variable 
    """
    orig_im = img
    dim = orig_im.shape[1], orig_im.shape[0]
    img = cv2.resize(orig_im, (inp_dim, inp_dim))
    img_ = img[:, :, ::-1].transpose((2, 0, 1)).copy()
    img_ = torch.from_numpy(img_).float().div(255.0).unsqueeze(0)
    return img_, orig_im, dim


def write(x, img):
    c1 = tuple(x[1:3].int())
    c2 = tuple(x[3:5].int())
    cls = int(x[-1])
    label = "{0}".format(classes[cls])
    color = random.choice(colors)
    cv2.rectangle(img, c1, c2, color, 1)
    t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, 1, 1)[0]
    c2 = c1[0] + t_size[0] + 3, c1[1] + t_size[1] + 4
    cv2.rectangle(img, c1, c2, color, -1)
    cv2.putText(img, label, (c1[0], c1[1] + t_size[1] + 4), cv2.FONT_HERSHEY_PLAIN, 1, [225, 255, 255], 1);
    return img


def arg_parse():
    """
    Parse arguements to the detect module
    
    """
    parser = argparse.ArgumentParser(description='YOLO v3 Cam Demo')
    parser.add_argument("--confidence", dest="confidence", help="Object Confidence to filter predictions", default=0.4)
    parser.add_argument("--nms_thresh", dest="nms_thresh", help="NMS Threshhold", default=0.5)
    parser.add_argument("--reso", dest='reso', help="Input resolution of the network. Increase "
                                                    "to increase accuracy. Decrease to increase speed",
                        default="192", type=str)
    return parser.parse_args()


if __name__ == '__main__':
    cfgfile = "cfg/yolov3-tiny.cfg"
    weightsfile = "yolov3-tiny.weights"
    num_classes = 80

    args = arg_parse()
    confidence = float(args.confidence)
    nms_thesh = float(args.nms_thresh)
    start = 0
    CUDA = torch.cuda.is_available()
    bbox_attrs = 5 + num_classes

    model = Darknet(cfgfile)
    model.load_weights(weightsfile)

    model.net_info["height"] = args.reso
    inp_dim = int(model.net_info["height"])

    assert inp_dim % 32 == 0
    assert inp_dim > 32

    if CUDA:
        model.cuda()

    model.eval()

    videofile = 'video.avi'
    vs = WebcamVideoStream(src=0).start()

    frames = 0
    start = time.time()
    last_time = 0
    while vs.stream.isOpened():

        # ret, frame = cap.read()
        frame = vs.read()
        ret = vs.grabbed
        frame = imutils.resize(frame, width=WIDTH)

        if ret:
            img, orig_im, dim = prep_image(frame, inp_dim)
            #im_dim = torch.FloatTensor(dim).repeat(1,2)
            if CUDA:
                im_dim = im_dim.cuda()
                img = img.cuda()

            output = model(Variable(img), CUDA)
            output = write_results(output, confidence, num_classes, nms=True, nms_conf=nms_thesh)
            if type(output) == int:
                frames += 1
                if (time.time() - last_time) > 10:
                    last_time = time.time()
                    print("FPS of the video is {:5.2f}".format(frames / (time.time() - start)))
                #orig_im = imutils.resize(orig_im, width=ZOOM_WIDTH)
                cv2.imshow("frame", orig_im)
                key = cv2.waitKey(1)
                if key & 0xFF == ord('q'):
                    break
                continue

            output[:, 1:5] = torch.clamp(output[:, 1:5], 0.0, float(inp_dim)) / inp_dim

            #            im_dim = im_dim.repeat(output.size(0), 1)
            output[:, [1, 3]] *= frame.shape[1]
            output[:, [2, 4]] *= frame.shape[0]

            classes = load_classes('data/coco.names')
            colors = pkl.load(open("pallete", "rb"))
            try:
                list(map(lambda x: write(x, orig_im), output))
            except:
                continue

            #orig_im = imutils.resize(orig_im, width=ZOOM_WIDTH)
            cv2.imshow("frame", orig_im)
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                break
            frames += 1
            if (time.time() - last_time) > 10:
                last_time = time.time()
                print("FPS of the video is {:5.2f}".format(frames / (time.time() - start)))
        else:
            break
    vs.stop()
