# -*- coding: UTF-8 -*-

"""

@Project Name: AOI_Defect_Monitor_Program
@File Name:    aoi_defect_monitor_program

@User:         smile
@Author:       Smile
@Email:        Xiaofei.Smile365@Gmail.com

@Date Time:    2021/5/4 10:59-w
@IDE:          PyCharm
@Source  : python3 -m pip install *** -i https://pypi.tuna.tsinghua.edu.cn/simple

@程式功能简介：
此程式用于对AOI Log档进行Defect分析，并进行报警；
1. 建立UI界面
2. 编写相应的功能模块

"""
import datetime
import sys  # 载入必需的模块
import os
import time

if hasattr(sys, 'frozen'):
    os.environ['PATH'] = sys._MEIPASS + ";" + os.environ['PATH']  # PyQt自身存在bug，打包时环境变量出错，无法运行，此语句对环境变量进行重新配置，消除bug

from PyQt5.QtGui import QIcon, QPalette, QBrush, QPixmap, QFont
from PyQt5.QtCore import Qt, QThread
from PyQt5 import QtCore
from PyQt5.QtWidgets import *

from watchdog.observers import Observer
from watchdog.events import *
from pyecharts import options as opts
from pyecharts.charts import *
from pyecharts.render import make_snapshot
from snapshot_phantomjs import snapshot

global alarm
global mark


class MyHandler(FileSystemEventHandler):
    """看门狗watchdog类，用于监控log生成"""

    def on_modified(self, event):
        global alarm
        global mark

        """监控文件是否被修改，如果被修改则触发相应自定义函数"""
        # 获取被修改的文件名称（含后缀名）&后缀名
        modified_file_name = os.path.basename(event.src_path)
        modified_file_type = os.path.splitext(modified_file_name)[-1][1:].lower()  # 获取被修改文件文件的后缀名

        mark = mark - 1
        if mark <= 0:
            # 判断是否为csv文件
            if modified_file_type == "log":
                # 关键节点写入日志
                # print(f"{datetime.datetime.now()}: 文件被修改:【{event.src_path}】\n")

                modified_log_file = open(event.src_path, encoding='utf-8')
                modified_log_file_content = modified_log_file.readlines()
                if len(modified_log_file_content) >= 50:
                    modified_log_file_content = str(modified_log_file_content[-50:])
                else:
                    modified_log_file_content = str(modified_log_file_content[-len(modified_log_file_content):])

                # noinspection PyAttributeOutsideInit
                self.list_defect_cont = [['OTHER_GLASS_DEFECT', 0], ['OTHER_ALIGN_DEFECT', 0], ['V_OPEN', 0],
                                         ['V_LINE', 0],
                                         ['H_OPEN', 0], ['H_LINE', 0]]

                OTHER_GLASS_DEFECT_cont = len(re.findall("OTHER_GLASS_DEFECT", modified_log_file_content))
                OTHER_ALIGN_DEFECT_cont = len(re.findall("OTHER_ALIGN_DEFECT", modified_log_file_content))
                V_OPEN_cont = len(re.findall('V_OPEN', modified_log_file_content))
                V_LINE_cont = len(re.findall('V_LINE', modified_log_file_content))
                H_OPEN_cont = len(re.findall('H_OPEN', modified_log_file_content))
                H_LINE_cont = len(re.findall('H_LINE', modified_log_file_content))

                self.list_defect_cont[0] = ['OTHER_GLASS_DEFECT', OTHER_GLASS_DEFECT_cont]
                self.list_defect_cont[1] = ['OTHER_ALIGN_DEFECT', OTHER_ALIGN_DEFECT_cont]
                self.list_defect_cont[2] = ['V_OPEN', V_OPEN_cont]
                self.list_defect_cont[3] = ['V_LINE', V_LINE_cont]
                self.list_defect_cont[4] = ['H_OPEN', H_OPEN_cont]
                self.list_defect_cont[5] = ['H_LINE', H_LINE_cont]

                if self.list_defect_cont[0][1] >= 25 or self.list_defect_cont[1][1] >= 25 or self.list_defect_cont[2][
                    1] >= 25 \
                        or self.list_defect_cont[3][1] >= 25 or self.list_defect_cont[4][1] >= 25 or \
                        self.list_defect_cont[5][1] >= 25:
                    self.close_aoi()
                    alarm = 1
                    self.chart()

                if mark % 10 == 9:
                    self.chart()

    # noinspection PyMethodMayBeStatic
    def chart(self):
        # noinspection PyAttributeOutsideInit
        self.list_defect_cont = sorted(self.list_defect_cont, key=(lambda x: [x[1]]), reverse=True)

        x_axis = []
        for i in range(0, 6):
            x_axis.append(self.list_defect_cont[i][0])

        y_axis = []
        for i in range(0, 6):
            y_axis.append(self.list_defect_cont[i][1])

        bar = (
            Bar(init_opts=opts.InitOpts(bg_color='rgba(255,250,250,0.2)',
                                        width='1000px',
                                        height='450px',
                                        page_title='Defect Monitor')).add_xaxis(x_axis).add_yaxis("Defect", y_axis, category_gap="20%", gap="0%")
                .set_global_opts(title_opts=opts.TitleOpts(title="In the last 50 pcs, Defect Monitor"),
                                 xaxis_opts=opts.AxisOpts(name="Defect Code",
                                                          axislabel_opts=opts.LabelOpts(rotate=-15)),
                                 yaxis_opts=opts.AxisOpts(name="单位：Pcs", max_=50))
                .set_series_opts(label_opts=opts.LabelOpts(is_show=True),
                                 markline_opts=opts.MarkLineOpts(data=[opts.MarkLineItem(y=25, name="阈值=25")])))
        make_snapshot(snapshot, bar.render('./source_file/defect_chart.html'), "./source_file/defect_chart.png")

    # noinspection PyMethodMayBeStatic
    def close_aoi(self):
        print(r'%s/source_file/kill_aoi.bat' % str(os.getcwd()).replace('\\','/'))
        os.system(r'%s/source_file/kill_aoi.bat' % str(os.getcwd()).replace('\\', '/'))


def start_watchdog():
    """启动看门狗程式"""
    # 创建看门狗watchdog实例并运行。
    path = r'D:/AOI_Data/Log/Controller/Inspect/'  # 被监控文件夹的路径,即ALS生成log的位置

    # 创建watchdog实例
    event_handler = MyHandler()

    # 开启服务
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


class MyThread_Start_Watchdog(QThread):  # 线程类
    def __init__(self):
        super(MyThread_Start_Watchdog, self).__init__()

    def run(self):  # 线程执行函数
        start_watchdog()


# noinspection PyAttributeOutsideInit
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        global alarm
        global mark
        alarm = 0
        mark = 0
        super(QMainWindow, self).__init__(parent)

        self.screen = QDesktopWidget().screenGeometry()

        self.resize(1024, 768)
        self.setWindowIcon(QIcon('./source_file/platform.ico'))
        self.setWindowTitle("AOI Defect Monitor Program")

        self.palette = QPalette()
        self.palette.setBrush(QPalette.Background,
                              QBrush(QPixmap('./source_file/background.jpg').scaled(self.width(), self.height())))
        self.setPalette(self.palette)
        self.setAutoFillBackground(True)

        self.size = self.geometry()
        self.move((self.screen.width() - self.size.width()) / 2, (self.screen.height() - self.size.height()) / 2)

        self.status = self.statusBar()

        self.setFixedSize(1024, 768)

        self.label_set()
        self.layout_set()

        self.my_thread_start_watchdog = MyThread_Start_Watchdog()
        self.my_thread_start_watchdog.start()  # 启动线程

        self.qtm_real_time = QtCore.QTimer()
        self.qtm_real_time.timeout.connect(self.real_time)
        self.qtm_real_time.start(1000)

        self.main_frame = QWidget()
        self.main_frame.setLayout(self.layout_v_windows)
        self.setCentralWidget(self.main_frame)

        self.status.showMessage("The AOI Defect Monitor Program Starting", 2000)
        self.label_title.setFocus()

    def label_set(self):
        self.label_title = QLabel()
        self.label_title.setFocus()
        self.label_title.setText("<b>AOI Defect 监控程式<b>")
        self.label_title.setFont(QFont("SanSerif", 24))
        self.label_title.setStyleSheet("Color: RGB(64, 224, 208)")
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_title.setFixedSize(400, 80)
        self.layout_h_label_title = QHBoxLayout()
        self.layout_h_label_title.addWidget(self.label_title)

        self.layout_h_title = QHBoxLayout()
        self.layout_h_title.addLayout(self.layout_h_label_title)

        self.label_designer = QLabel()
        self.label_designer.setText("Developer:AUO")
        self.label_designer.setFont(QFont("SanSerif", 10))
        self.label_designer.setStyleSheet("Color: RGB(128, 128, 0)")
        self.label_designer.setAlignment(Qt.AlignRight)
        self.label_designer.setFixedSize(140, 20)
        self.layout_h_label_designer = QHBoxLayout()
        self.layout_h_label_designer.addWidget(self.label_designer)

        self.label_time = QLabel()
        self.label_time.setText("1997/01/01 00:00:00")
        self.label_time.setFont(QFont("SanSerif", 10))
        self.label_time.setStyleSheet("Color: RGB(128, 128, 0)")
        self.label_time.setAlignment(Qt.AlignLeft)
        self.label_time.setFixedSize(150, 20)
        self.layout_h_label_time = QHBoxLayout()
        self.layout_h_label_time.addWidget(self.label_time)

        self.layout_h_designer_and_time = QHBoxLayout()
        self.layout_h_designer_and_time.addLayout(self.layout_h_label_designer)
        self.layout_h_designer_and_time.addStretch(1)
        self.layout_h_designer_and_time.addLayout(self.layout_h_label_time)

        self.label_information = QLabel()
        self.label_information.setText(
            "In the last 50 pcs, Defect 预警阈值：>=25pcs；\n*被监控Defect：\n1.OTHER_GLASS_DEFECT 2.OTHER_ALIGN_DEFECT \n3.V_OPEN             4.V_LINE             \n5.H_OPEN             6.H_LINE")
        self.label_information.setFont(QFont("SanSerif", 16))
        self.label_information.setStyleSheet("Color: RGB(128, 128, 0)")
        self.label_information.setAlignment(Qt.AlignLeft)
        self.label_information.setFixedSize(500, 120)
        self.layout_h_label_information = QHBoxLayout()
        self.layout_h_label_information.addWidget(self.label_information)

        self.label_photo_alarm = QLabel()
        self.label_photo_alarm.setAlignment(Qt.AlignCenter)
        self.label_photo_alarm.setToolTip("红绿灯")
        self.label_photo_alarm.setPixmap(QPixmap("./source_file/green.png").scaled(100, 100))
        self.label_photo_alarm.setFixedSize(100, 100)
        self.layout_h_label_photo_alarm = QHBoxLayout()
        self.layout_h_label_photo_alarm.addWidget(self.label_photo_alarm)

        self.button_clear_alarm = QPushButton()
        self.button_clear_alarm.setText("清除报警")
        self.button_clear_alarm.setToolTip("清除报警。")
        self.button_clear_alarm.clicked.connect(self.clear_alarm)
        self.button_clear_alarm.setFont(QFont("微软雅黑", 10))
        self.button_clear_alarm.setFixedSize(175, 30)
        self.layout_button_clear_alarm = QHBoxLayout()
        self.layout_button_clear_alarm.addWidget(self.button_clear_alarm)

        self.layout_button_alarm = QVBoxLayout()
        self.layout_button_alarm.addLayout(self.layout_h_label_photo_alarm)
        self.layout_button_alarm.addLayout(self.layout_button_clear_alarm)

        self.layout_information_button_alarm = QHBoxLayout()
        self.layout_information_button_alarm.addLayout(self.layout_h_label_information)
        self.layout_information_button_alarm.addLayout(self.layout_button_alarm)

        self.label_photo_defect_chart = QLabel()
        self.label_photo_defect_chart.setAlignment(Qt.AlignCenter)
        self.label_photo_defect_chart.setToolTip("Defect Chart")
        self.label_photo_defect_chart.setPixmap(QPixmap("./source_file/defect_chart_sample.png").scaled(1000, 450))
        self.label_photo_defect_chart.setFixedSize(1000, 450)
        self.layout_h_label_photo_defect_chart = QHBoxLayout()
        self.layout_h_label_photo_defect_chart.addWidget(self.label_photo_defect_chart)

    def layout_set(self):
        self.layout_v_windows = QVBoxLayout()

        self.layout_v_windows.addLayout(self.layout_h_title)
        self.layout_v_windows.addLayout(self.layout_h_designer_and_time)
        self.layout_v_windows.addLayout(self.layout_information_button_alarm)
        self.layout_v_windows.addStretch(1)
        self.layout_v_windows.addLayout(self.layout_h_label_photo_defect_chart)
        # self.layout_v_windows.addStretch(1)

    def clear_alarm(self):
        global mark
        global alarm

        def enter_password(information='请输入密码'):
            global mark
            global alarm

            str_password, ok = QInputDialog.getText(self, 'Enter Password', information)
            if ok:
                if str_password == "3.1415926":
                    mark = 50
                    alarm = 0
                    self.label_photo_alarm.setPixmap(QPixmap("./source_file/green.png").scaled(100, 100))
                    self.label_photo_defect_chart.setPixmap(
                        QPixmap("./source_file/defect_chart_sample.png").scaled(1000, 450))
                else:
                    enter_password(information='密码错误，请重新输入密码')

        enter_password(information='请输入密码')

    def real_time(self):
        global alarm
        self.real_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.label_time.setText(self.real_time)

        if mark <= 0 and mark % 10 == 8 and os.path.exists('./source_file/defect_chart.png'):
            self.label_photo_defect_chart.setPixmap(QPixmap("./source_file/defect_chart.png").scaled(1000, 450))

        if mark <= 0 and alarm == 1:
            self.label_photo_alarm.setPixmap(QPixmap("./source_file/alarm.png").scaled(100, 100))
            if mark <= 0 and os.path.exists('./source_file/defect_chart.png'):
                self.label_photo_defect_chart.setPixmap(QPixmap("./source_file/defect_chart.png").scaled(1000, 450))


if __name__ == '__main__':
    app_system = QApplication(sys.argv)
    form_system = MainWindow()
    form_system.show()
    sys.exit(app_system.exec_())

    pass
