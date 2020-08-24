#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5 import QtMultimedia
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QApplication, QTextEdit, QFileDialog
from PyQt5.QtCore import QFile, QIODevice
import os.path
from pyaudio import PyAudio, paInt16
import numpy as np
from datetime import datetime
import wave
from QAonMilitaryKG.military_qa import MilitaryGraph
from rocket_recognization import forward
from PIL import Image
from text2speech import TTS_Ws_Param, tts
from speech2text import STT_Ws_Param, stt
import websocket

class recorder:
    def __init__(self):
        self.num_samples = 2000  # pyaudio内置缓冲大小
        self.sampling_rate = 8000  # 取样频率
        self.level = 1000  # 声音保存的阈值
        self.count_num = 20  # NUM_SAMPLES个取样之内出现COUNT_NUM个大于LEVEL的取样则记录声音
        self.save_length = 8  # 声音记录的最小长度：SAVE_LENGTH * NUM_SAMPLES 个取样
        
        self.voice_string = []

    def savewav(self, filename):
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(self.sampling_rate)
        wf.writeframes(np.array(self.voice_string).tostring())
        wf.close()

    def record(self):
        pa = PyAudio()
        stream = pa.open(format=paInt16, channels=1, rate=self.sampling_rate, input=True,
                         frames_per_buffer=self.num_samples)
        save_count = 0
        save_buffer = []

        while True:
            # 读入NUM_SAMPLES个取样
            string_audio_data = stream.read(self.num_samples)
            # 将读入的数据转换为数组
            audio_data = np.fromstring(string_audio_data, dtype=np.short)
            # 计算大于LEVEL的取样的个数
            large_sample_count = np.sum(audio_data > self.level)
            print(np.max(audio_data))
            # 如果个数大于COUNT_NUM，则至少保存SAVE_LENGTH个块
            if large_sample_count > self.count_num:
                save_count = self.save_length
            else:
                save_count -= 1

            if save_count < 0:
                save_count = 0

            if save_count > 0:
                # 将要保存的数据存放到save_buffer中
                save_buffer.append(string_audio_data)
            else:
                if len(save_buffer) > 0:
                    self.voice_string = save_buffer
                    save_buffer = []
                    print("Record a piece of voice successfully!")
                    return True


def get_file_content(file_path):
    with open(file_path, 'rb') as fp:
        return fp.read()


def audio_2_str(voiceFileName):
    r = recorder()
    voiceStatus = r.record()
    if voiceStatus:
        r.savewav(voiceFileName +".wav")
        pass
    return voiceStatus

class GUI(QWidget):

    def __init__(self):
        super().__init__()

        self.initUI()
        self.sendState = 0 #0文字 1图片 2语音
        self.imgPath = ''
        self.voiceFile = ''
        self.handler = MilitaryGraph()
        self.answerfile = 'answer.pcm'
        self.rfile = QFile()
        
        format = QtMultimedia.QAudioFormat()
        format.setChannelCount(2)
        format.setSampleRate(8000)
        format.setSampleSize(16)
        format.setCodec("audio/pcm")
        format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
        format.setSampleType(QtMultimedia.QAudioFormat.UnSignedInt)
        self.audio_output = QtMultimedia.QAudioOutput(format)

    def initUI(self):

        self.selectImgBtn = QPushButton("选择图片")
        self.voiceInputBtn = QPushButton("语音输入")
        self.sendBtn = QPushButton("发送")
        self.cancelBtn = QPushButton("清空")
        self.textEdit = QTextEdit()
        self.showEdit = QTextEdit()
        self.showEdit.setReadOnly(True)
        # 水平布局
        hbox0 = QHBoxLayout()
        hbox0.addWidget(self.showEdit)
        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.textEdit)
        # 水平布局
        hbox2 = QHBoxLayout()
        hbox2.addStretch(1)
        hbox2.addWidget(self.voiceInputBtn)
        hbox2.addWidget(self.selectImgBtn)
        hbox2.addWidget(self.sendBtn)
        hbox2.addWidget(self.cancelBtn)

        # 垂直布局
        vbox = QVBoxLayout()
        vbox.addLayout(hbox0)
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)

        vbox.setStretchFactor(hbox0, 6)
        vbox.setStretchFactor(hbox1, 2)
        vbox.setStretchFactor(hbox2, 1)
        
        #事件
        self.sendBtn.clicked.connect(self.sendTextAction)
        self.cancelBtn.clicked.connect(self.clearAction)
        self.selectImgBtn.clicked.connect(self.selectImgAction)
        self.voiceInputBtn.clicked.connect(self.voiceInputAction)

        self.setLayout(vbox)    

        self.setGeometry(600, 600, 1000, 1000)
        self.setWindowTitle('军事知识问答系统')    
        self.show()
        
    def voiceInputAction(self):
        voiceFileName = 'tmp'
        print("voice input begin", self.voiceInputBtn.isDown())
        res = audio_2_str(voiceFileName)
        s = '<img src="/home/robin/RockeX/gui/voice.png"/>'
        if res:
            self.textEdit.setHtml(s)
        else:
            self.textEdit.setPlainText("录音失败")

        self.textEdit.setReadOnly(True)
        self.sendState = 2 #0文字 1图片 2语音
      
    def text2speech(self,answer):
        tts_wsParam = TTS_Ws_Param(APPID='5e2faa83', APIKey='58c05763b09a8d85d9a2f5645f981824',
            APISecret='1d83a8338cc3e0188c880b9ab514770e',
            Text=answer)
        tts(tts_wsParam,self.answerfile)
        self.rfile.setFileName(self.answerfile)
        self.rfile.open(QIODevice.ReadOnly)
        self.audio_output.start(self.rfile)  
    
    # 收到websocket消息的处理
    def on_message(ws, message):
        if self.count == 1:
            return
        try:
            code = json.loads(message)["code"]
            sid = json.loads(message)["sid"]
            if code != 0:
                errMsg = json.loads(message)["message"]
                print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))

            else:
                data = json.loads(message)["data"]["result"]["ws"]
                # print(json.loads(message))
                self.stt_result = ""
                for i in data:
                    for w in i["cw"]:
                        self.stt_result += w["w"]
                self.count += 1

        except Exception as e:
            print("receive msg,but parse exception:", e)
            
    '''
    # 收到websocket错误的处理
    def on_error(ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(ws):
        print("### websocket closed ###")

    # 收到websocket连接建立的处理
    def on_open(ws):
        def run(*args):
            frameSize = 8000  # 每一帧的音频大小
            intervel = 0.04  # 发送音频间隔(单位:s)
            status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧

            with open(wsParam.AudioFile, "rb") as fp:
                while True:
                    buf = fp.read(frameSize)
                    # 文件结束
                    if not buf:
                        status = STATUS_LAST_FRAME
                    # 第一帧处理
                    # 发送第一帧音频，带business 参数
                    # appid 必须带上，只需第一帧发送
                    if status == STATUS_FIRST_FRAME:

                        d = {"common": wsParam.CommonArgs,
                            "business": wsParam.BusinessArgs,
                            "data": {"status": 0, "format": "audio/L16;rate=16000",
                                    "audio": str(base64.b64encode(buf), 'utf-8'),
                                    "encoding": "raw"}}
                        d = json.dumps(d)
                        ws.send(d)
                        status = STATUS_CONTINUE_FRAME
                    # 中间帧处理
                    elif status == STATUS_CONTINUE_FRAME:
                        d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                    "audio": str(base64.b64encode(buf), 'utf-8'),
                                    "encoding": "raw"}}
                        ws.send(json.dumps(d))
                    # 最后一帧处理
                    elif status == STATUS_LAST_FRAME:
                        d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                    "audio": str(base64.b64encode(buf), 'utf-8'),
                                    "encoding": "raw"}}
                        ws.send(json.dumps(d))
                        time.sleep(1)
                        break
                    # 模拟音频采样间隔
                    time.sleep(intervel)
            ws.close()

        thread.start_new_thread(run, ())
    ''' 
    
    def sendTextAction(self):
        print('self.textEdit.text()')
        print(self.showEdit.toHtml())

        if self.sendState == 0:
            s = ''
            question = self.textEdit.toPlainText()
            if  question == '':
                return
            s = '<div align="right" style=""><img src="/home/robin/RockeX/gui/q.png" width="30" height="30" />'
            s = s + question
            s = s + '</div>'
        elif self.sendState == 1:
            s = '<img src="/home/robin/RockeX/gui/q.png" width="30" height="30" /><img src="'+self.imgPath+'" width="200" height="200"/>'
            img = Image.open(self.imgPath).convert('RGB')
            question = forward.net_foward(img)
        elif self.sendState == 2:
            stt_wsParam = STT_Ws_Param(APPID='5e2faa83', APIKey='58c05763b09a8d85d9a2f5645f981824',
                        APISecret='1d83a8338cc3e0188c880b9ab514770e',
                        AudioFile=r'tmp.wav')
            stt_result = stt(stt_wsParam,'')
            s = '<img src="/home/robin/RockeX/gui/q.png" width="30" height="30" /><img src="/home/robin/RockeX/gui/voice.png" width="100" height="30"/>' + stt_result
            question = stt_result
        
        self.showEdit.append(s)
        self.textEdit.clear()
        self.textEdit.setReadOnly(False)
        self.sendState = 0
        
        answer = self.handler.qa_main(question).strip()
        self.text2speech(answer)
        self.resText(answer)

    def initText(self):
        print("initText")
        s = '<div style=""><img src="/home/robin/RockeX/gui/smile.jpg" width="30" height="30" />请问需要什么帮助？</div>'
        self.text2speech('请问需要什么帮助？')
        self.showEdit.append(s)
    
    def resText(self, text):
        s = '<div style=""><img src="/home/robin/RockeX/gui/smile.jpg" width="30" height="30" />'+text+'</div>'
        self.showEdit.append(s)
        
    def clearAction(self):
        self.showEdit.clear()
        self.textEdit.clear()
        self.textEdit.setReadOnly(False)
        self.initText()
        self.sendState = 0

    def selectImgAction(self):
        fname = QFileDialog.getOpenFileName(self, '选择图片', '/', 'Image files (*.jpg *.gif *.png *.jpeg)')

        print(fname[0], os.path.isfile(fname[0]), self.sendState)
        # 判断文件存在
        if os.path.isfile(fname[0]):
            self.sendState = 1
            s = '<img src="'+fname[0]+'"/>'
            self.imgPath = fname[0]
            self.textEdit.setHtml(s)
            self.textEdit.setReadOnly(True)

        print(self.sendState)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GUI()
    ex.initText()
    sys.exit(app.exec_())












