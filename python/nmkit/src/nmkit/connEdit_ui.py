# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'connEdit.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QFrame, QLabel,
    QLineEdit, QSizePolicy, QSplitter, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(400, 300)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(30, 240, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.formLayoutWidget = QWidget(Dialog)
        self.formLayoutWidget.setObjectName(u"formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(10, 80, 371, 151))
        self.form_details = QFormLayout(self.formLayoutWidget)
        self.form_details.setObjectName(u"form_details")
        self.form_details.setContentsMargins(0, 0, 0, 0)
        self.hostLabel = QLabel(self.formLayoutWidget)
        self.hostLabel.setObjectName(u"hostLabel")

        self.form_details.setWidget(0, QFormLayout.ItemRole.LabelRole, self.hostLabel)

        self.hostLineEdit = QLineEdit(self.formLayoutWidget)
        self.hostLineEdit.setObjectName(u"hostLineEdit")

        self.form_details.setWidget(0, QFormLayout.ItemRole.FieldRole, self.hostLineEdit)

        self.portLabel = QLabel(self.formLayoutWidget)
        self.portLabel.setObjectName(u"portLabel")

        self.form_details.setWidget(1, QFormLayout.ItemRole.LabelRole, self.portLabel)

        self.portLineEdit = QLineEdit(self.formLayoutWidget)
        self.portLineEdit.setObjectName(u"portLineEdit")

        self.form_details.setWidget(1, QFormLayout.ItemRole.FieldRole, self.portLineEdit)

        self.oSLabel = QLabel(self.formLayoutWidget)
        self.oSLabel.setObjectName(u"oSLabel")

        self.form_details.setWidget(2, QFormLayout.ItemRole.LabelRole, self.oSLabel)

        self.oSComboBox = QComboBox(self.formLayoutWidget)
        self.oSComboBox.setObjectName(u"oSComboBox")

        self.form_details.setWidget(2, QFormLayout.ItemRole.FieldRole, self.oSComboBox)

        self.userLabel = QLabel(self.formLayoutWidget)
        self.userLabel.setObjectName(u"userLabel")

        self.form_details.setWidget(3, QFormLayout.ItemRole.LabelRole, self.userLabel)

        self.userLineEdit = QLineEdit(self.formLayoutWidget)
        self.userLineEdit.setObjectName(u"userLineEdit")

        self.form_details.setWidget(3, QFormLayout.ItemRole.FieldRole, self.userLineEdit)

        self.line = QFrame(Dialog)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(20, 60, 361, 16))
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.splitter = QSplitter(Dialog)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setGeometry(QRect(20, 20, 255, 30))
        self.splitter.setOrientation(Qt.Horizontal)
        self.label = QLabel(self.splitter)
        self.label.setObjectName(u"label")
        self.splitter.addWidget(self.label)
        self.lE_connName = QLineEdit(self.splitter)
        self.lE_connName.setObjectName(u"lE_connName")
        self.splitter.addWidget(self.lE_connName)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.hostLabel.setText(QCoreApplication.translate("Dialog", u"Host: ", None))
        self.portLabel.setText(QCoreApplication.translate("Dialog", u"Port: ", None))
        self.oSLabel.setText(QCoreApplication.translate("Dialog", u"OS:", None))
        self.userLabel.setText(QCoreApplication.translate("Dialog", u"User:", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:600;\">Connection Name: </span></p></body></html>", None))
    # retranslateUi

