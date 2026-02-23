# -*- coding: utf-8 -*-
"""
 CustomMapDownloaderDialog - Custom Map Downloader QGIS Plugin
        begin                : 2025-11-18
        copyright            : (C) 2025 by Abhinav Jayswal
        email                : abhinavjayaswal10@gmail.com
 GPL v2 or later
"""

import os
import math
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QCheckBox, QRadioButton, QStackedWidget, QPushButton,
    QButtonGroup, QWidget
)
from qgis.core import QgsProject, QgsCoordinateReferenceSystem

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'CustomMapDownloader_dialog_base.ui'))

# Approximate GSD (m/px) per Web Mercator zoom level at equator (256 px tiles)
ZOOM_GSD = {
    0: 156543, 1: 78272, 2: 39136, 3: 19568, 4: 9784,
    5: 4892,   6: 2446,  7: 1223,  8: 611,   9: 306,
    10: 153,   11: 76,   12: 38,   13: 19,   14: 10,
    15: 5,     16: 2.4,  17: 1.2,  18: 0.6,  19: 0.3,
    20: 0.15,  21: 0.075, 22: 0.037
}

CRS_OPTIONS = [
    ("EPSG:3857", "WGS 84 / Pseudo-Mercator (Web Mercator)"),
    ("EPSG:4326", "WGS 84 (Geographic, lat/lon)"),
    ("EPSG:3395", "WGS 84 / World Mercator"),
    ("EPSG:32643", "WGS 84 / UTM zone 43N"),
    ("EPSG:32644", "WGS 84 / UTM zone 44N"),
    ("EPSG:32645", "WGS 84 / UTM zone 45N"),
    ("EPSG:32646", "WGS 84 / UTM zone 46N"),
    ("EPSG:32633", "WGS 84 / UTM zone 33N"),
    ("EPSG:32634", "WGS 84 / UTM zone 34N"),
    ("EPSG:32635", "WGS 84 / UTM zone 35N"),
    ("EPSG:32636", "WGS 84 / UTM zone 36N"),
    ("EPSG:32637", "WGS 84 / UTM zone 37N"),
    ("EPSG:32638", "WGS 84 / UTM zone 38N"),
    ("EPSG:32639", "WGS 84 / UTM zone 39N"),
    ("EPSG:32640", "WGS 84 / UTM zone 40N"),
    ("EPSG:32641", "WGS 84 / UTM zone 41N"),
    ("EPSG:32642", "WGS 84 / UTM zone 42N"),
    ("EPSG:32733", "WGS 84 / UTM zone 33S"),
    ("EPSG:32734", "WGS 84 / UTM zone 34S"),
    ("EPSG:32735", "WGS 84 / UTM zone 35S"),
    ("EPSG:32736", "WGS 84 / UTM zone 36S"),
    ("EPSG:2154",  "RGF93 / Lambert-93 (France)"),
    ("EPSG:27700", "OSGB 1936 / British National Grid"),
    ("EPSG:25832", "ETRS89 / UTM zone 32N"),
    ("EPSG:25833", "ETRS89 / UTM zone 33N"),
    ("EPSG:3035",  "ETRS89 / LAEA Europe"),
    ("EPSG:2056",  "CH1903+ / LV95 (Switzerland)"),
]


class CustomMapDownloaderDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CustomMapDownloaderDialog, self).__init__(parent)
        self.setupUi(self)
        self.setMinimumWidth(520)
        self._build_ui()
        self._connect_signals()
        self._on_format_changed()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        layout = self.verticalLayout_main

        # Format selector
        fmt_box = QGroupBox("Export Format")
        fmt_row = QHBoxLayout()
        self.radioButton_geotiff = QRadioButton("GeoTIFF")
        self.radioButton_mbtiles = QRadioButton("MBTiles")
        self.radioButton_geotiff.setChecked(True)
        self._fmt_group = QButtonGroup(self)
        self._fmt_group.addButton(self.radioButton_geotiff, 0)
        self._fmt_group.addButton(self.radioButton_mbtiles, 1)
        fmt_row.addWidget(self.radioButton_geotiff)
        fmt_row.addWidget(self.radioButton_mbtiles)
        fmt_row.addStretch()
        fmt_box.setLayout(fmt_row)

        # Shared: layer
        layer_box = QGroupBox("Layer Selection")
        layer_row = QHBoxLayout()
        self.comboBox_layer = QComboBox()
        layer_row.addWidget(self.comboBox_layer)
        layer_box.setLayout(layer_row)

        # Shared: output path
        out_box = QGroupBox("Output File")
        out_row = QHBoxLayout()
        self.lineEdit_output = QLineEdit()
        self.lineEdit_output.setPlaceholderText("Select output file path...")
        self.pushButton_browse = QPushButton("Browse...")
        out_row.addWidget(self.lineEdit_output)
        out_row.addWidget(self.pushButton_browse)
        out_box.setLayout(out_row)

        # Stacked widget (page 0 = GeoTIFF, page 1 = MBTiles)
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.addWidget(self._build_geotiff_page())
        self.stackedWidget.addWidget(self._build_mbtiles_page())

        layout.insertWidget(0, fmt_box)
        layout.insertWidget(1, layer_box)
        layout.insertWidget(2, out_box)
        layout.insertWidget(3, self.stackedWidget)

    def _build_geotiff_page(self):
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(0, 0, 0, 0)

        # Coordinates
        coord_box = QGroupBox("Center Coordinates")
        fl = QFormLayout()
        self.lineEdit_lat = QLineEdit()
        self.lineEdit_lat.setPlaceholderText("e.g., 28.6139")
        self.lineEdit_lon = QLineEdit()
        self.lineEdit_lon.setPlaceholderText("e.g., 77.2090")
        fl.addRow("Latitude (decimal deg):", self.lineEdit_lat)
        fl.addRow("Longitude (decimal deg):", self.lineEdit_lon)
        coord_box.setLayout(fl)

        # Resolution & dimensions
        res_box = QGroupBox("Resolution and Dimensions")
        fl2 = QFormLayout()
        self.spinBox_gsd = QDoubleSpinBox()
        self.spinBox_gsd.setRange(0.01, 1000.0)
        self.spinBox_gsd.setDecimals(2)
        self.spinBox_gsd.setValue(5.0)
        self.spinBox_width = QSpinBox()
        self.spinBox_width.setRange(1, 20000)
        self.spinBox_width.setValue(5000)
        self.spinBox_height = QSpinBox()
        self.spinBox_height.setRange(1, 20000)
        self.spinBox_height.setValue(5000)
        fl2.addRow("GSD (meters/pixel):", self.spinBox_gsd)
        fl2.addRow("Width (pixels):", self.spinBox_width)
        fl2.addRow("Height (pixels):", self.spinBox_height)
        res_box.setLayout(fl2)

        # CRS
        crs_box = QGroupBox("Coordinate Reference System")
        crs_vl = QVBoxLayout()
        self.comboBox_crs = QComboBox()
        self.comboBox_crs.setToolTip("Select the output CRS for the GeoTIFF")
        for epsg, desc in CRS_OPTIONS:
            crs = QgsCoordinateReferenceSystem(epsg)
            if crs.isValid():
                self.comboBox_crs.addItem(f"{epsg} - {desc}", epsg)
        idx = self.comboBox_crs.findData("EPSG:3857")
        if idx >= 0:
            self.comboBox_crs.setCurrentIndex(idx)
        crs_vl.addWidget(self.comboBox_crs)
        crs_box.setLayout(crs_vl)

        # Export options
        opt_box = QGroupBox("Export Options")
        opt_vl = QVBoxLayout()
        self.checkBox_georeferencing = QCheckBox("Add georeferencing metadata (GeoTIFF)")
        self.checkBox_georeferencing.setChecked(True)
        self.checkBox_loadLayer = QCheckBox("Load exported image as layer in QGIS")
        self.checkBox_loadLayer.setChecked(True)
        opt_vl.addWidget(self.checkBox_georeferencing)
        opt_vl.addWidget(self.checkBox_loadLayer)
        opt_box.setLayout(opt_vl)

        vl.addWidget(coord_box)
        vl.addWidget(res_box)
        vl.addWidget(crs_box)
        vl.addWidget(opt_box)
        vl.addStretch()
        return page

    def _build_mbtiles_page(self):
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(0, 0, 0, 0)

        # --- Extent group ---
        ext_box = QGroupBox("Extent")
        ext_vl = QVBoxLayout()

        mode_row = QHBoxLayout()
        self.radioButton_centerPoint = QRadioButton("Center Point + Radius")
        self.radioButton_bbox = QRadioButton("Bounding Box")
        self.radioButton_centerPoint.setChecked(True)
        self._ext_group = QButtonGroup(self)
        self._ext_group.addButton(self.radioButton_centerPoint, 0)
        self._ext_group.addButton(self.radioButton_bbox, 1)
        mode_row.addWidget(self.radioButton_centerPoint)
        mode_row.addWidget(self.radioButton_bbox)
        mode_row.addStretch()

        # Center point sub-panel
        self.widget_centerPoint = QWidget()
        cp_fl = QFormLayout(self.widget_centerPoint)
        cp_fl.setContentsMargins(0, 4, 0, 0)
        self.lineEdit_mb_lat = QLineEdit()
        self.lineEdit_mb_lat.setPlaceholderText("e.g., 28.6139")
        self.lineEdit_mb_lon = QLineEdit()
        self.lineEdit_mb_lon.setPlaceholderText("e.g., 77.2090")
        self.spinBox_mb_radius = QDoubleSpinBox()
        self.spinBox_mb_radius.setRange(100, 500000)
        self.spinBox_mb_radius.setSingleStep(500)
        self.spinBox_mb_radius.setValue(5000)
        self.spinBox_mb_radius.setSuffix(" m")
        cp_fl.addRow("Latitude (deg):", self.lineEdit_mb_lat)
        cp_fl.addRow("Longitude (deg):", self.lineEdit_mb_lon)
        cp_fl.addRow("Radius:", self.spinBox_mb_radius)

        # Bounding box sub-panel
        self.widget_bbox = QWidget()
        bb_fl = QFormLayout(self.widget_bbox)
        bb_fl.setContentsMargins(0, 4, 0, 0)
        self.lineEdit_mb_minLat = QLineEdit()
        self.lineEdit_mb_minLat.setPlaceholderText("e.g., 28.50")
        self.lineEdit_mb_minLon = QLineEdit()
        self.lineEdit_mb_minLon.setPlaceholderText("e.g., 77.00")
        self.lineEdit_mb_maxLat = QLineEdit()
        self.lineEdit_mb_maxLat.setPlaceholderText("e.g., 28.75")
        self.lineEdit_mb_maxLon = QLineEdit()
        self.lineEdit_mb_maxLon.setPlaceholderText("e.g., 77.30")
        bb_fl.addRow("Min Latitude (deg):", self.lineEdit_mb_minLat)
        bb_fl.addRow("Min Longitude (deg):", self.lineEdit_mb_minLon)
        bb_fl.addRow("Max Latitude (deg):", self.lineEdit_mb_maxLat)
        bb_fl.addRow("Max Longitude (deg):", self.lineEdit_mb_maxLon)
        self.widget_bbox.setVisible(False)

        ext_vl.addLayout(mode_row)
        ext_vl.addWidget(self.widget_centerPoint)
        ext_vl.addWidget(self.widget_bbox)
        ext_box.setLayout(ext_vl)

        # --- Zoom / resolution group ---
        zoom_box = QGroupBox("Zoom / Resolution")
        zoom_vl = QVBoxLayout()

        zoom_mode_row = QHBoxLayout()
        self.radioButton_zoomRange = QRadioButton("Zoom Range")
        self.radioButton_singleShot = QRadioButton("Single Shot")
        self.radioButton_zoomRange.setChecked(True)
        self._zoom_group = QButtonGroup(self)
        self._zoom_group.addButton(self.radioButton_zoomRange, 0)
        self._zoom_group.addButton(self.radioButton_singleShot, 1)
        zoom_mode_row.addWidget(self.radioButton_zoomRange)
        zoom_mode_row.addWidget(self.radioButton_singleShot)
        zoom_mode_row.addStretch()

        # Zoom range sub-panel
        self.widget_zoomRange = QWidget()
        zr_fl = QFormLayout(self.widget_zoomRange)
        zr_fl.setContentsMargins(0, 4, 0, 0)

        self.spinBox_zoomMin = QSpinBox()
        self.spinBox_zoomMin.setRange(0, 22)
        self.spinBox_zoomMin.setValue(10)
        self.spinBox_zoomMin.setToolTip("Z10~153m  Z14~10m  Z17~1.2m  Z18~0.6m")
        self.label_zoomMinGsd = QLabel("~ 153 m/px")
        self.pushButton_autoZoom = QPushButton("Auto-detect")
        self.pushButton_autoZoom.setToolTip(
            "Set Min Zoom to the lowest level where your bbox spans more than one tile")
        self.pushButton_autoZoom.setFixedWidth(100)

        self.spinBox_zoomMax = QSpinBox()
        self.spinBox_zoomMax.setRange(0, 22)
        self.spinBox_zoomMax.setValue(17)
        self.spinBox_zoomMax.setToolTip("Z10~153m  Z14~10m  Z17~1.2m  Z18~0.6m")
        self.label_zoomMaxGsd = QLabel("~ 1.2 m/px")

        self.checkBox_allZooms = QCheckBox("All levels (0 - 22)")
        self.label_tileCount = QLabel("")
        self.label_tileCount.setStyleSheet("color: gray; font-style: italic;")

        zmin_row = QHBoxLayout()
        zmin_row.addWidget(self.spinBox_zoomMin)
        zmin_row.addWidget(self.label_zoomMinGsd)
        zmin_row.addWidget(self.pushButton_autoZoom)
        zmax_row = QHBoxLayout()
        zmax_row.addWidget(self.spinBox_zoomMax)
        zmax_row.addWidget(self.label_zoomMaxGsd)

        zr_fl.addRow("Min Zoom (coarse):", zmin_row)
        zr_fl.addRow("Max Zoom (fine):", zmax_row)
        zr_fl.addRow("", self.checkBox_allZooms)
        zr_fl.addRow("", self.label_tileCount)

        # Single shot sub-panel
        self.widget_singleShot = QWidget()
        ss_fl = QFormLayout(self.widget_singleShot)
        ss_fl.setContentsMargins(0, 4, 0, 0)
        self.spinBox_ssZoom = QSpinBox()
        self.spinBox_ssZoom.setRange(0, 22)
        self.spinBox_ssZoom.setValue(15)
        self.spinBox_ssZoom.setToolTip("Z10~153m  Z14~10m  Z17~1.2m  Z18~0.6m")
        self.label_ssGsd = QLabel("~ 5 m/px")
        ss_zoom_row = QHBoxLayout()
        ss_zoom_row.addWidget(self.spinBox_ssZoom)
        ss_zoom_row.addWidget(self.label_ssGsd)
        ss_fl.addRow("Zoom Level:", ss_zoom_row)
        self.widget_singleShot.setVisible(False)

        zoom_vl.addLayout(zoom_mode_row)
        zoom_vl.addWidget(self.widget_zoomRange)
        zoom_vl.addWidget(self.widget_singleShot)
        zoom_box.setLayout(zoom_vl)

        # --- Tile size group ---
        tile_box = QGroupBox("Tile Options")
        tile_fl = QFormLayout()
        self.spinBox_tileSize = QSpinBox()
        self.spinBox_tileSize.setRange(64, 1024)
        self.spinBox_tileSize.setSingleStep(64)
        self.spinBox_tileSize.setValue(256)
        self.spinBox_tileSize.setSuffix(" px")
        tile_fl.addRow("Tile size:", self.spinBox_tileSize)

        self.spinBox_tilePadding = QSpinBox()
        self.spinBox_tilePadding.setRange(0, 5)
        self.spinBox_tilePadding.setValue(1)
        self.spinBox_tilePadding.setToolTip(
            "Expand the tile range by N tiles in every direction at each zoom level.\n"
            "0 = exact bbox only, 1 = +1 ring of neighbours (recommended), 2 = +2 rings, etc.")
        tile_fl.addRow("Neighbour padding:", self.spinBox_tilePadding)
        tile_box.setLayout(tile_fl)

        vl.addWidget(ext_box)
        vl.addWidget(zoom_box)
        vl.addWidget(tile_box)
        vl.addStretch()
        return page

    # ------------------------------------------------------------------ #
    #  Signal wiring                                                       #
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self.pushButton_browse.clicked.connect(self.select_output_file)
        self._fmt_group.buttonClicked.connect(self._on_format_changed)
        self._ext_group.buttonClicked.connect(self._on_extent_mode_changed)
        self._zoom_group.buttonClicked.connect(self._on_zoom_mode_changed)
        self.spinBox_zoomMin.valueChanged.connect(self._on_zoom_min_changed)
        self.spinBox_zoomMax.valueChanged.connect(self._on_zoom_max_changed)
        self.spinBox_ssZoom.valueChanged.connect(self._on_ss_zoom_changed)
        self.checkBox_allZooms.toggled.connect(self._on_all_zooms_toggled)
        self.pushButton_autoZoom.clicked.connect(self._on_auto_zoom_clicked)
        # Extent field changes should refresh tile count
        for w in (self.lineEdit_mb_lat, self.lineEdit_mb_lon,
                  self.lineEdit_mb_minLat, self.lineEdit_mb_minLon,
                  self.lineEdit_mb_maxLat, self.lineEdit_mb_maxLon):
            w.textChanged.connect(self._update_tile_count)
        self.spinBox_mb_radius.valueChanged.connect(self._update_tile_count)
        self.spinBox_tilePadding.valueChanged.connect(self._update_tile_count)

    def _on_format_changed(self):
        is_mb = self.radioButton_mbtiles.isChecked()
        self.stackedWidget.setCurrentIndex(1 if is_mb else 0)
        self.adjustSize()

    def _on_extent_mode_changed(self):
        is_bbox = self.radioButton_bbox.isChecked()
        self.widget_centerPoint.setVisible(not is_bbox)
        self.widget_bbox.setVisible(is_bbox)
        self.adjustSize()
        self._update_tile_count()

    def _on_zoom_mode_changed(self):
        is_single = self.radioButton_singleShot.isChecked()
        self.widget_zoomRange.setVisible(not is_single)
        self.widget_singleShot.setVisible(is_single)
        self.adjustSize()

    def _on_zoom_min_changed(self, val):
        gsd = ZOOM_GSD.get(val, "?")
        self.label_zoomMinGsd.setText(f"~ {gsd} m/px")
        if val > self.spinBox_zoomMax.value():
            self.spinBox_zoomMax.setValue(val)
        self._update_tile_count()

    def _on_zoom_max_changed(self, val):
        gsd = ZOOM_GSD.get(val, "?")
        self.label_zoomMaxGsd.setText(f"~ {gsd} m/px")
        if val < self.spinBox_zoomMin.value():
            self.spinBox_zoomMin.setValue(val)
        self._update_tile_count()

    def _on_ss_zoom_changed(self, val):
        self.label_ssGsd.setText(f"~ {ZOOM_GSD.get(val, '?')} m/px")
        self._update_tile_count()

    def _on_all_zooms_toggled(self, checked):
        self.spinBox_zoomMin.setEnabled(not checked)
        self.spinBox_zoomMax.setEnabled(not checked)
        self._update_tile_count()

    def _on_auto_zoom_clicked(self):
        extent = self._read_mb_extent()
        if extent is None:
            QtWidgets.QMessageBox.warning(
                self, "Auto-detect",
                "Please fill in valid extent coordinates first.")
            return
        from .CustomMapDownloader import _min_visible_zoom
        z = _min_visible_zoom(
            extent["min_lon"], extent["min_lat"],
            extent["max_lon"], extent["max_lat"])
        self.spinBox_zoomMin.setValue(z)
        if self.spinBox_zoomMax.value() < z:
            self.spinBox_zoomMax.setValue(z)
        self._update_tile_count()

    def _update_tile_count(self):
        if not self.radioButton_mbtiles.isChecked():
            return
        extent = self._read_mb_extent()
        if extent is None:
            self.label_tileCount.setText("")
            return
        from .CustomMapDownloader import _tile_count_padded
        single_shot = self.radioButton_singleShot.isChecked()
        if single_shot:
            z_min = z_max = self.spinBox_ssZoom.value()
        elif self.checkBox_allZooms.isChecked():
            z_min, z_max = 0, 22
        else:
            z_min = self.spinBox_zoomMin.value()
            z_max = self.spinBox_zoomMax.value()
        padding = self.spinBox_tilePadding.value()
        n = _tile_count_padded(
            extent["min_lon"], extent["min_lat"],
            extent["max_lon"], extent["max_lat"],
            z_min, z_max, padding)
        # ~50 KB per PNG tile is a reasonable average estimate
        size_mb = n * 50 / 1024
        if size_mb >= 1024:
            size_str = f"~{size_mb / 1024:.1f} GB"
        elif size_mb >= 1:
            size_str = f"~{size_mb:.0f} MB"
        else:
            size_str = f"~{size_mb * 1024:.0f} KB"
        self.label_tileCount.setText(f"Estimated: {n:,} tiles  ({size_str})")

    def _read_mb_extent(self):
        """Return extent dict or None if fields are not yet valid."""
        try:
            if self.radioButton_bbox.isChecked():
                return {
                    'min_lat': float(self.lineEdit_mb_minLat.text()),
                    'min_lon': float(self.lineEdit_mb_minLon.text()),
                    'max_lat': float(self.lineEdit_mb_maxLat.text()),
                    'max_lon': float(self.lineEdit_mb_maxLon.text()),
                }
            else:
                lat = float(self.lineEdit_mb_lat.text())
                lon = float(self.lineEdit_mb_lon.text())
                r = self.spinBox_mb_radius.value()
                dlat = r / 111320.0
                dlon = r / (111320.0 * math.cos(math.radians(lat)))
                return {
                    'min_lat': lat - dlat, 'min_lon': lon - dlon,
                    'max_lat': lat + dlat, 'max_lon': lon + dlon,
                }
        except (ValueError, ZeroDivisionError):
            return None

    # ------------------------------------------------------------------ #
    #  Public helpers                                                      #
    # ------------------------------------------------------------------ #

    def populate_layers(self):
        self.comboBox_layer.clear()
        for layer in QgsProject.instance().mapLayers().values():
            self.comboBox_layer.addItem(layer.name(), layer)

    def select_output_file(self):
        if self.radioButton_mbtiles.isChecked():
            filt = "MBTiles Files (*.mbtiles);;All Files (*)"
            title = "Save MBTiles file"
        else:
            filt = "GeoTIFF Files (*.tif *.tiff);;All Files (*)"
            title = "Save GeoTIFF file"
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, title, "", filt)
        if filename:
            self.lineEdit_output.setText(filename)

    # ------------------------------------------------------------------ #
    #  Parameter extraction                                                #
    # ------------------------------------------------------------------ #

    def get_parameters(self):
        output_path = self.lineEdit_output.text()
        layer = self.comboBox_layer.currentData()
        if self.radioButton_mbtiles.isChecked():
            return self._get_mbtiles_params(layer, output_path)
        return self._get_geotiff_params(layer, output_path)

    def _get_geotiff_params(self, layer, output_path):
        try:
            return {
                'format': 'geotiff',
                'lat': float(self.lineEdit_lat.text()),
                'lon': float(self.lineEdit_lon.text()),
                'gsd': self.spinBox_gsd.value(),
                'width': self.spinBox_width.value(),
                'height': self.spinBox_height.value(),
                'layer': layer,
                'output_path': output_path,
                'load_as_layer': self.checkBox_loadLayer.isChecked(),
                'add_georeferencing': self.checkBox_georeferencing.isChecked(),
                'output_crs': self.comboBox_crs.currentData(),
            }
        except ValueError:
            return None

    def _get_mbtiles_params(self, layer, output_path):
        try:
            if self.radioButton_bbox.isChecked():
                extent = {
                    'min_lat': float(self.lineEdit_mb_minLat.text()),
                    'min_lon': float(self.lineEdit_mb_minLon.text()),
                    'max_lat': float(self.lineEdit_mb_maxLat.text()),
                    'max_lon': float(self.lineEdit_mb_maxLon.text()),
                }
            else:
                lat = float(self.lineEdit_mb_lat.text())
                lon = float(self.lineEdit_mb_lon.text())
                r = self.spinBox_mb_radius.value()
                dlat = r / 111320.0
                dlon = r / (111320.0 * math.cos(math.radians(lat)))
                extent = {
                    'min_lat': lat - dlat, 'min_lon': lon - dlon,
                    'max_lat': lat + dlat, 'max_lon': lon + dlon,
                }

            single_shot = self.radioButton_singleShot.isChecked()
            if single_shot:
                zoom_min = zoom_max = self.spinBox_ssZoom.value()
            elif self.checkBox_allZooms.isChecked():
                zoom_min, zoom_max = 0, 22
            else:
                zoom_min = self.spinBox_zoomMin.value()
                zoom_max = self.spinBox_zoomMax.value()

            return {
                'format': 'mbtiles',
                'layer': layer,
                'output_path': output_path,
                'extent': extent,
                'zoom_min': zoom_min,
                'zoom_max': zoom_max,
                'tile_size': self.spinBox_tileSize.value(),
                'tile_padding': self.spinBox_tilePadding.value(),
                'single_shot': single_shot,
            }
        except ValueError:
            return None
