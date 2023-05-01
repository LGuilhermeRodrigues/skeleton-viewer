import os
import time
import sys

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtChart import QChart,QLineSeries,QChartView
from PyQt5.QtCore import QPointF, QThreadPool, pyqtSlot, QRunnable
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import QObject, QThread, pyqtSignal

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd


class ThreadManager(QObject):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.threadpool = QThreadPool()

    def start(self):
        self.worker = Worker()
        self.threadpool.start(self.worker)

    def stop(self):
        if self.worker:
            self.worker.terminate = True
        self.worker = None

    def is_paused(self):
        return not self.worker


class MWindow(QMainWindow):
    def __init__(self):
        super(MWindow, self).__init__()
        
        self.setGeometry(200,200,1280,720)
        self.setWindowTitle('Skeleton Viewer')

        self.file_list = QtWidgets.QListWidget()
        self.file_list.addItems(get_files())
        for i in self.file_list.findItems('', QtCore.Qt.MatchContains):
            i.setToolTip(i.text())
        self.file_list.setFixedWidth(200)
        self.file_list.itemDoubleClicked.connect(file_change)

        self.slider1 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider1.setRange(0, 100)
        self.slider1.sliderPressed.connect(slider_pressed)
        self.slider1.sliderReleased.connect(slider_released)

        self.pause_button = QtWidgets.QPushButton('⏯️️')
        self.pause_button.setFixedWidth(45)
        self.pause_button.clicked.connect(pause_button_clicked)

        self.slider_box_layout = QtWidgets.QHBoxLayout()
        self.slider_box_layout.addWidget(self.pause_button)
        self.slider_box_layout.addWidget(self.slider1)
        self.slider_box = QtWidgets.QWidget()
        self.slider_box.setFixedHeight(20)
        self.slider_box.setLayout(self.slider_box_layout)
        self.slider_box_layout.setContentsMargins(0,0,25,0)

        self.series = QLineSeries()
        self.series.setUseOpenGL(True)
        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart_view = QChartView(self.chart)
        self.chart.createDefaultAxes()
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.legend().hide()
        self.chart_view.setFixedHeight(300)

        self.scatter_figure = plt.figure(figsize=(4,4))
        self.scatter_canvas = FigureCanvasQTAgg(self.scatter_figure)
        self.ax = self.scatter_figure.add_subplot(111, projection='3d')
        self.ax.set_xlim3d(-1,1)
        self.ax.set_ylim3d(-1,1)
        self.ax.set_zlim3d(-1,1)

        self.v_layout = QtWidgets.QVBoxLayout()
        self.widget_v_layout = QtWidgets.QWidget()
        self.widget_v_layout.setLayout(self.v_layout)
        self.v_layout.addWidget(self.chart_view)
        self.v_layout.addWidget(self.slider_box)
        self.v_layout.addWidget(self.scatter_canvas)

        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(self.file_list)
        self.h_layout.addWidget(self.widget_v_layout)

        self.widget_h_layout = QtWidgets.QWidget()
        self.widget_h_layout.setLayout(self.h_layout)
        self.setCentralWidget(self.widget_h_layout)
        self.thread_manager = ThreadManager()
        self.frame_index=0
        self.update_sider_timer = QtCore.QTimer()
        self.update_sider_timer.timeout.connect(update_slider)
        self.update_sider_timer.start(500)
        self.slider_is_pressed = False

    def closeEvent(self, event):
        self.thread_manager.stop()
        super().closeEvent(event)


def pause_button_clicked():
    if mw.thread_manager.is_paused():
        mw.thread_manager.start()
    else:
        mw.thread_manager.stop()


def update_slider():
    if not mw.slider_is_pressed:
        mw.slider1.setValue(mw.frame_index)


def slider_pressed():
    mw.slider_is_pressed = True
    mw.thread_manager.stop()


def slider_released():
    mw.slider_is_pressed = False
    mw.thread_manager.start()


def get_files():
    f = []
    path = os.path.expanduser("~/Documents/BRAINN_XR_Data/CSV")
    for (dirpath, dirnames, filenames) in os.walk(path):
        f.extend(filenames)
    f.reverse()
    return f


def file_change(item):
    path = os.path.expanduser("~/Documents/BRAINN_XR_Data/CSV")
    print('file change: '+item.text())
    load_csv(os.path.join(path, item.text()))


def load_csv(filepath):
    mw.thread_manager.stop()
    csv = pd.read_csv(filepath)
    df = pd.DataFrame(csv, columns=['time','shoulderRangle', 'shoulderLangle', 'kneeRangle', 'kneeLangle'])
    df2 = df.pivot_table(columns=['time'], aggfunc='size')
    mw.chart.removeAllSeries()
    mw.series = QLineSeries()
    series2 = QLineSeries()
    series3 = QLineSeries()
    series4 = QLineSeries()
    mw.series.setUseOpenGL(True)
    # add pandas time and r_angle to pyqt series
    initial_hour = str(df['time'][0])[:-4]
    initial_minute = str(df['time'][0])[-4:-2]
    initial_second = str(df['time'][0])[-2:]
    end_hour = str(df['time'][len(df)-1])[:-4]
    end_minute = str(df['time'][len(df)-1])[-4:-2]
    end_second = str(df['time'][len(df)-1])[-2:]
    seconds = int(end_hour)*3600+int(end_minute)*60+int(end_second)-int(initial_hour)*3600-int(initial_minute)*60-int(initial_second)
    lines = len(df)-1
    average_fps = 1.0*lines/seconds
    j=0
    last_time=-1
    current_time = df['time'][0]
    milliseconds = 0
    global elapsed_seconds_list
    elapsed_seconds_list = []
    for i in range(len(df)):
        csv_time = df['time'][i]
        try:
            times = df2[csv_time]
            if csv_time==last_time:
                milliseconds+=1
            else:
                milliseconds=0
                j+=1
            elapsed_seconds = j+milliseconds*1.0/times
            elapsed_seconds_list.append(elapsed_seconds)
            elapsed_minutes = elapsed_seconds/60
            mw.series.append(elapsed_minutes,df['shoulderRangle'][i])
            series2.append(elapsed_minutes,df['shoulderLangle'][i])
            series3.append(elapsed_minutes,df['kneeRangle'][i])
            series4.append(elapsed_minutes,df['kneeLangle'][i])
            last_time = csv_time
        except KeyError:
            j+=1
    mw.chart.addSeries(mw.series)
    mw.chart.addSeries(series2)
    series2.setColor(QColor(255,0,0))
    mw.chart.addSeries(series3)
    series3.setColor(QColor(0,255,0))
    mw.chart.addSeries(series4)
    series4.setColor(QColor(255,255,0))
    mw.chart.createDefaultAxes()

    mw.slider1.setValue(0)
    mw.slider1.setRange(0, len(elapsed_seconds_list)-1)
    create_skeleton(filepath)


def create_skeleton(filepath):
    csv = pd.read_csv(filepath)
    global skeleton_df
    skeleton_df = pd.DataFrame(csv, columns=['l_shoulderX','l_shoulderY','l_shoulderZ','r_shoulderX','r_shoulderY','r_shoulderZ','l_elbowX','l_elbowY','l_elbowZ','r_elbowX','r_elbowY','r_elbowZ','l_wristX','l_wristY','l_wristZ','r_wristX','r_wristY','r_wristZ','l_hipX','l_hipY','l_hipZ','r_hipX','r_hipY','r_hipZ','l_kneeX','l_kneeY','l_kneeZ','r_kneeX','r_kneeY','r_kneeZ','l_ankleX','l_ankleY','l_ankleZ','r_ankleX','r_ankleY','r_ankleZ'])
    mw.thread_manager.start()


points_list = []
lines_list = []


def update_skeleton(frame_index=0):
    global skeleton_df
    global points_list
    global lines_list
    for i in range(len(points_list)):
        points_list[i].remove()
    points_list = []

    p = mw.ax.scatter(skeleton_df['l_shoulderX'][frame_index],skeleton_df['l_shoulderZ'][frame_index],skeleton_df['l_shoulderY'][frame_index],color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['r_shoulderX'][frame_index],skeleton_df['r_shoulderZ'][frame_index],skeleton_df['r_shoulderY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['l_elbowX'][frame_index],skeleton_df['l_elbowZ'][frame_index],skeleton_df['l_elbowY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['r_elbowX'][frame_index],skeleton_df['r_elbowZ'][frame_index],skeleton_df['r_elbowY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['l_wristX'][frame_index],skeleton_df['l_wristZ'][frame_index],skeleton_df['l_wristY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['r_wristX'][frame_index],skeleton_df['r_wristZ'][frame_index],skeleton_df['r_wristY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['l_hipX'][frame_index],skeleton_df['l_hipZ'][frame_index],skeleton_df['l_hipY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['r_hipX'][frame_index],skeleton_df['r_hipZ'][frame_index],skeleton_df['r_hipY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['l_kneeX'][frame_index],skeleton_df['l_kneeZ'][frame_index],skeleton_df['l_kneeY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['r_kneeX'][frame_index],skeleton_df['r_kneeZ'][frame_index],skeleton_df['r_kneeY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['l_ankleX'][frame_index],skeleton_df['l_ankleZ'][frame_index],skeleton_df['l_ankleY'][frame_index], color='blue')
    points_list.append(p)
    p = mw.ax.scatter(skeleton_df['r_ankleX'][frame_index],skeleton_df['r_ankleZ'][frame_index],skeleton_df['r_ankleY'][frame_index], color='blue')
    points_list.append(p)

    for i in range(len(lines_list)):
        l = lines_list[i].pop(0)
        l.remove()
    lines_list = []

    x = [skeleton_df['l_wristX'][frame_index], skeleton_df['l_elbowX'][frame_index]]
    y = [skeleton_df['l_wristY'][frame_index], skeleton_df['l_elbowY'][frame_index]]
    z = [skeleton_df['l_wristZ'][frame_index], skeleton_df['l_elbowZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['r_wristX'][frame_index], skeleton_df['r_elbowX'][frame_index]]
    y = [skeleton_df['r_wristY'][frame_index], skeleton_df['r_elbowY'][frame_index]]
    z = [skeleton_df['r_wristZ'][frame_index], skeleton_df['r_elbowZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['l_elbowX'][frame_index], skeleton_df['l_shoulderX'][frame_index]]
    y = [skeleton_df['l_elbowY'][frame_index], skeleton_df['l_shoulderY'][frame_index]]
    z = [skeleton_df['l_elbowZ'][frame_index], skeleton_df['l_shoulderZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['r_elbowX'][frame_index], skeleton_df['r_shoulderX'][frame_index]]
    y = [skeleton_df['r_elbowY'][frame_index], skeleton_df['r_shoulderY'][frame_index]]
    z = [skeleton_df['r_elbowZ'][frame_index], skeleton_df['r_shoulderZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['l_shoulderX'][frame_index], skeleton_df['r_shoulderX'][frame_index]]
    y = [skeleton_df['l_shoulderY'][frame_index], skeleton_df['r_shoulderY'][frame_index]]
    z = [skeleton_df['l_shoulderZ'][frame_index], skeleton_df['r_shoulderZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['l_shoulderX'][frame_index], skeleton_df['l_hipX'][frame_index]]
    y = [skeleton_df['l_shoulderY'][frame_index], skeleton_df['l_hipY'][frame_index]]
    z = [skeleton_df['l_shoulderZ'][frame_index], skeleton_df['l_hipZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['r_shoulderX'][frame_index], skeleton_df['r_hipX'][frame_index]]
    y = [skeleton_df['r_shoulderY'][frame_index], skeleton_df['r_hipY'][frame_index]]
    z = [skeleton_df['r_shoulderZ'][frame_index], skeleton_df['r_hipZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['l_hipX'][frame_index], skeleton_df['r_hipX'][frame_index]]
    y = [skeleton_df['l_hipY'][frame_index], skeleton_df['r_hipY'][frame_index]]
    z = [skeleton_df['l_hipZ'][frame_index], skeleton_df['r_hipZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['l_hipX'][frame_index], skeleton_df['l_kneeX'][frame_index]]
    y = [skeleton_df['l_hipY'][frame_index], skeleton_df['l_kneeY'][frame_index]]
    z = [skeleton_df['l_hipZ'][frame_index], skeleton_df['l_kneeZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['r_hipX'][frame_index], skeleton_df['r_kneeX'][frame_index]]
    y = [skeleton_df['r_hipY'][frame_index], skeleton_df['r_kneeY'][frame_index]]
    z = [skeleton_df['r_hipZ'][frame_index], skeleton_df['r_kneeZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['l_kneeX'][frame_index], skeleton_df['l_ankleX'][frame_index]]
    y = [skeleton_df['l_kneeY'][frame_index], skeleton_df['l_ankleY'][frame_index]]
    z = [skeleton_df['l_kneeZ'][frame_index], skeleton_df['l_ankleZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    x = [skeleton_df['r_kneeX'][frame_index], skeleton_df['r_ankleX'][frame_index]]
    y = [skeleton_df['r_kneeY'][frame_index], skeleton_df['r_ankleY'][frame_index]]
    z = [skeleton_df['r_kneeZ'][frame_index], skeleton_df['r_ankleZ'][frame_index]]
    l = mw.ax.plot(x, z, y, color='blue')
    lines_list.append(l)
    mw.scatter_figure.canvas.draw()


class Worker(QRunnable):
    def __init__(self):
        super(Worker, self).__init__()
        self.terminate = False

    @pyqtSlot()
    def run(self):
        global elapsed_seconds_list
        for frame_index in range(mw.slider1.value(), len(elapsed_seconds_list)-1):
            if self.terminate:
                break
            else:
                frame_time = elapsed_seconds_list[frame_index+1] - elapsed_seconds_list[frame_index]
                update_skeleton(frame_index)
                mw.frame_index = frame_index
                time.sleep(frame_time)


app = QApplication(sys.argv)
mw = MWindow()
mw.show()
sys.exit(app.exec_())
