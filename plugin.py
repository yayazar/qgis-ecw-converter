import os

from qgis.core import (Qgis, QgsApplication, QgsMapLayer, QgsProject,
                       QgsTask)
from qgis.PyQt.QtWidgets import (QAction, QCheckBox, QComboBox, QDialog,
                                 QDialogButtonBox, QFileDialog, QFormLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                 QSpinBox)

from . import converter


class ConvertTask(QgsTask):
    def __init__(self, src, dst, mode, target, drop_alpha):
        super().__init__("ECW dönüştürme: " + os.path.basename(src),
                         QgsTask.CanCancel)
        self.src, self.dst, self.mode = src, dst, mode
        self.target, self.drop_alpha = target, drop_alpha
        self.error = None
        self.sizes = None

    def run(self):
        try:
            self.sizes = converter.convert(
                self.src, self.dst, self.mode, self.target, self.drop_alpha,
                progress=lambda f: (self.setProgress(f * 100),
                                    not self.isCanceled())[1])
            return True
        except Exception as e:  # noqa: BLE001
            self.error = str(e)
            return False


class ConvertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ortofoto → ECW")
        self.setMinimumWidth(480)
        form = QFormLayout(self)

        self.layer = QComboBox()
        for lyr in QgsProject.instance().mapLayers().values():
            if (lyr.type() == QgsMapLayer.RasterLayer
                    and os.path.isfile(lyr.source())):
                self.layer.addItem(lyr.name(), lyr.source())
        form.addRow("Raster katman:", self.layer)

        self.mode = QComboBox()
        if converter.ecw_available():
            self.mode.addItem("ECW (dalgacık sıkıştırma)", converter.MODE_ECW)
        self.mode.addItem("Kayıpsız döşemeli GeoTIFF + piramit",
                          converter.MODE_LOSSLESS_TIFF)
        form.addRow("Çıktı biçimi:", self.mode)

        self.target = QSpinBox()
        self.target.setRange(0, 99)
        self.target.setValue(0)
        self.target.setSuffix(" %")
        self.target.setToolTip("ECW hedef küçülme oranı. 0 = en yüksek kalite.")
        form.addRow("ECW hedef küçülme:", self.target)

        self.alpha = QCheckBox("4. bandı (alfa) at, RGB yaz")
        form.addRow("", self.alpha)

        self.out = QLineEdit()
        browse = QPushButton("…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.out)
        row.addWidget(browse)
        form.addRow("Çıktı dosyası:", row)

        self.note = QLabel()
        self.note.setWordWrap(True)
        form.addRow(self.note)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

        self.layer.currentIndexChanged.connect(self._refresh)
        self.mode.currentIndexChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        is_ecw = self.mode.currentData() == converter.MODE_ECW
        self.target.setEnabled(is_ecw)
        src = self.layer.currentData()
        if src:
            self.out.setText(converter.default_output(src, self.mode.currentData()))
        self.note.setText(
            "Uyarı: ECW kayıplı bir dalgacık biçimidir; piksel değerleri "
            "birebir korunmaz (hedef %0'da bile). Bire bir kayıpsız sonuç "
            "için GeoTIFF seçeneğini kullanın."
            if is_ecw else
            "Kayıpsız (DEFLATE), 512×512 döşemeli, piramitli GeoTIFF üretilir.")

    def _browse(self):
        flt = ("ECW (*.ecw)" if self.mode.currentData() == converter.MODE_ECW
               else "GeoTIFF (*.tif)")
        path, _ = QFileDialog.getSaveFileName(self, "Çıktı", self.out.text(), flt)
        if path:
            self.out.setText(path)


class EcwConverterPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self._tasks = []

    def initGui(self):
        self.action = QAction("Ortofoto → ECW", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToRasterMenu("&ECW Converter", self.action)
        self.iface.addRasterToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginRasterMenu("&ECW Converter", self.action)
        self.iface.removeRasterToolBarIcon(self.action)

    def run(self):
        dlg = ConvertDialog(self.iface.mainWindow())
        if dlg.layer.count() == 0:
            self.iface.messageBar().pushWarning(
                "ECW Converter", "Projede dosya tabanlı raster katman yok.")
            return
        if not dlg.exec_():
            return
        task = ConvertTask(dlg.layer.currentData(), dlg.out.text(),
                           dlg.mode.currentData(), dlg.target.value(),
                           dlg.alpha.isChecked())
        task.taskCompleted.connect(lambda t=task: self._done(t))
        task.taskTerminated.connect(lambda t=task: self._failed(t))
        self._tasks.append(task)
        QgsApplication.taskManager().addTask(task)

    def _done(self, t):
        out, src = t.sizes
        self.iface.messageBar().pushMessage(
            "ECW Converter",
            "Bitti: %s (%.1f MB → %.1f MB)" % (
                os.path.basename(t.dst), src / 1e6, out / 1e6),
            level=Qgis.Success, duration=0)
        self._tasks.remove(t)
        self.iface.addRasterLayer(t.dst, os.path.basename(t.dst))

    def _failed(self, t):
        msg = t.error or "İptal edildi."
        self.iface.messageBar().pushMessage(
            "ECW Converter", msg, level=Qgis.Critical, duration=0)
        self._tasks.remove(t)
