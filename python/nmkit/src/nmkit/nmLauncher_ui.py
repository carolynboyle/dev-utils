# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'nmLauncher.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QLabel,
    QListView, QPushButton, QSizePolicy, QWidget)

class Ui_NMConnect(object):
    def setupUi(self, NMConnect):
        if not NMConnect.objectName():
            NMConnect.setObjectName(u"NMConnect")
        NMConnect.resize(477, 401)
        self.connections_list = QListView(NMConnect)
        self.connections_list.setObjectName(u"connections_list")
        self.connections_list.setGeometry(QRect(40, 130, 211, 251))
        self.frame = QFrame(NMConnect)
        self.frame.setObjectName(u"frame")
        self.frame.setGeometry(QRect(300, 150, 121, 191))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.add_connection = QPushButton(self.frame)
        self.add_connection.setObjectName(u"add_connection")
        self.add_connection.setGeometry(QRect(30, 10, 61, 28))
        self.edit_connection = QPushButton(self.frame)
        self.edit_connection.setObjectName(u"edit_connection")
        self.edit_connection.setGeometry(QRect(30, 50, 61, 28))
        self.delete_connection = QPushButton(self.frame)
        self.delete_connection.setObjectName(u"delete_connection")
        self.delete_connection.setGeometry(QRect(30, 90, 61, 28))
        self.connect = QPushButton(self.frame)
        self.connect.setObjectName(u"connect")
        self.connect.setGeometry(QRect(30, 150, 61, 28))
        self.line = QFrame(self.frame)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(30, 130, 61, 16))
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.label = QLabel(NMConnect)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(30, 50, 371, 31))
        self.CurrentConnection = QFrame(NMConnect)
        self.CurrentConnection.setObjectName(u"CurrentConnection")
        self.CurrentConnection.setGeometry(QRect(30, 30, 401, 81))
        self.CurrentConnection.setFrameShape(QFrame.StyledPanel)
        self.CurrentConnection.setFrameShadow(QFrame.Raised)
        self.conn_name = QLabel(self.CurrentConnection)
        self.conn_name.setObjectName(u"conn_name")
        self.conn_name.setGeometry(QRect(10, 10, 91, 51))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.conn_name.sizePolicy().hasHeightForWidth())
        self.conn_name.setSizePolicy(sizePolicy)
        self.conn_description = QLabel(self.CurrentConnection)
        self.conn_description.setObjectName(u"conn_description")
        self.conn_description.setGeometry(QRect(110, 10, 281, 51))
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.conn_description.sizePolicy().hasHeightForWidth())
        self.conn_description.setSizePolicy(sizePolicy1)
        self.frame_label = QLabel(NMConnect)
        self.frame_label.setObjectName(u"frame_label")
        self.frame_label.setGeometry(QRect(40, 0, 401, 20))
        self.line_2 = QFrame(NMConnect)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setGeometry(QRect(30, 110, 391, 16))
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)
        self.frame.raise_()
        self.connections_list.raise_()
        self.label.raise_()
        self.CurrentConnection.raise_()
        self.frame_label.raise_()
        self.line_2.raise_()

        self.retranslateUi(NMConnect)

        QMetaObject.connectSlotsByName(NMConnect)
    # setupUi

    def retranslateUi(self, NMConnect):
        NMConnect.setWindowTitle(QCoreApplication.translate("NMConnect", u"Dialog", None))
#if QT_CONFIG(tooltip)
        NMConnect.setToolTip(QCoreApplication.translate("NMConnect", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.connections_list.setToolTip(QCoreApplication.translate("NMConnect", u"<html><head/><body><p>select an item from the list, to  add or modify connections use the buttons to the right </p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.add_connection.setText(QCoreApplication.translate("NMConnect", u"Add", None))
        self.edit_connection.setText(QCoreApplication.translate("NMConnect", u"Edit", None))
        self.delete_connection.setText(QCoreApplication.translate("NMConnect", u"Delete", None))
        self.connect.setText(QCoreApplication.translate("NMConnect", u"Connect", None))
        self.label.setText("")
#if QT_CONFIG(tooltip)
        self.CurrentConnection.setToolTip(QCoreApplication.translate("NMConnect", u"<html><head/><body><p>current connection will appear here when selected from the list below ...</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.conn_name.setText("")
        self.conn_description.setText(QCoreApplication.translate("NMConnect", u"<html><head/><body><p><br/></p></body></html>", None))
        self.frame_label.setText(QCoreApplication.translate("NMConnect", u"<html><head/><body><p align=\"center\"><span style=\" font-size:14pt; font-weight:600; text-decoration: underline;\">Current Connection</span></p></body></html>", None))
    # retranslateUi

