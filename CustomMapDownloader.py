# -*- coding: utf-8 -*-
"""
 CustomMapDownloader - Custom Map Downloader QGIS Plugin
        begin                : 2025-11-18
        copyright            : (C) 2025 by Abhinav Jayswal
        email                : abhinavjayaswal10@gmail.com
 GPL v2 or later
"""
import os
import math
import sqlite3
import tempfile

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QSize, Qt, QEventLoop
from qgis.PyQt.QtGui import QIcon, QImage, QPainter, QColor
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QProgressDialog
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsPointXY,
    QgsRectangle,
    QgsMapSettings,
    QgsMapRendererParallelJob,
    QgsRasterLayer
)

from .resources import *
from .CustomMapDownloader_dialog import CustomMapDownloaderDialog
from osgeo import gdal, osr
import numpy as np


# ---------------------------------------------------------------------------
# Slippy-tile math helpers (EPSG:3857 / Web Mercator)
# ---------------------------------------------------------------------------

def _lon_to_tile_x(lon_deg, zoom):
    return int((lon_deg + 180.0) / 360.0 * (1 << zoom))


def _lat_to_tile_y(lat_deg, zoom):
    lat_r = math.radians(lat_deg)
    return int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * (1 << zoom))


def _tile_bounds_deg(tx, ty, zoom):
    """Return (min_lon, min_lat, max_lon, max_lat) in degrees for a tile."""
    n = 1 << zoom
    min_lon = tx / n * 360.0 - 180.0
    max_lon = (tx + 1) / n * 360.0 - 180.0
    max_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / n))))
    min_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + 1) / n))))
    return min_lon, min_lat, max_lon, max_lat


def _tile_bounds_3857(tx, ty, zoom):
    """Return (xmin, ymin, xmax, ymax) in EPSG:3857 metres for a tile."""
    min_lon, min_lat, max_lon, max_lat = _tile_bounds_deg(tx, ty, zoom)
    crs_src = QgsCoordinateReferenceSystem("EPSG:4326")
    crs_dst = QgsCoordinateReferenceSystem("EPSG:3857")
    tr = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())
    bl = tr.transform(QgsPointXY(min_lon, min_lat))
    tr2 = tr.transform(QgsPointXY(max_lon, max_lat))
    return bl.x(), bl.y(), tr2.x(), tr2.y()


def _min_visible_zoom(min_lon, min_lat, max_lon, max_lat):
    """Return the lowest zoom level where the bbox spans at least 2 tiles
    in either x or y direction (i.e. the area is 'visible' as distinct tiles).
    Returns 0 if it never spans more than 1 tile below zoom 22."""
    for z in range(0, 23):
        tx_min = _lon_to_tile_x(min_lon, z)
        tx_max = _lon_to_tile_x(max_lon, z)
        ty_min = _lat_to_tile_y(max_lat, z)
        ty_max = _lat_to_tile_y(min_lat, z)
        if (tx_max - tx_min + 1) >= 2 or (ty_max - ty_min + 1) >= 2:
            return z
    return 0


def _tile_count(min_lon, min_lat, max_lon, max_lat, zoom_min, zoom_max):
    """Return total number of tiles across a zoom range for a bbox."""
    return _tile_count_padded(min_lon, min_lat, max_lon, max_lat, zoom_min, zoom_max, 0)


def _tile_count_padded(min_lon, min_lat, max_lon, max_lat, zoom_min, zoom_max, padding):
    """Return total tiles across a zoom range, expanding each zoom by `padding` tiles
    in every direction (clamped to valid tile indices for that zoom)."""
    total = 0
    for z in range(zoom_min, zoom_max + 1):
        n_tiles = 1 << z
        tx_min = max(0, _lon_to_tile_x(min_lon, z) - padding)
        tx_max = min(n_tiles - 1, _lon_to_tile_x(max_lon, z) + padding)
        ty_min = max(0, _lat_to_tile_y(max_lat, z) - padding)
        ty_max = min(n_tiles - 1, _lat_to_tile_y(min_lat, z) + padding)
        total += (tx_max - tx_min + 1) * (ty_max - ty_min + 1)
    return total


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class CustomMapDownloader:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, "i18n",
                                   f"CustomMapDownloader_{locale}.qm")
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        self.actions = []
        self.menu = self.tr(u"&MapDownloader")
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate("CustomMapDownloader", message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip:
            action.setStatusTip(status_tip)
        if whats_this:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = ":/plugins/CustomMapDownloader/icon.png"
        self.add_action(icon_path,
                        text=self.tr(u"Download Map (GeoTIFF / MBTiles)"),
                        callback=self.run,
                        parent=self.iface.mainWindow())
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u"&MapDownloader"), action)
            self.iface.removeToolBarIcon(action)

    # ------------------------------------------------------------------ #
    #  Main run                                                            #
    # ------------------------------------------------------------------ #

    def run(self):
        if self.first_start:
            self.first_start = False
            self.dlg = CustomMapDownloaderDialog()

        self.dlg.populate_layers()
        self.dlg.show()
        result = self.dlg.exec_()
        if not result:
            return

        params = self.dlg.get_parameters()

        if params is None:
            QMessageBox.critical(self.iface.mainWindow(), "Error",
                                 "Invalid input parameters. Please check all fields.")
            return
        if not params.get("layer"):
            QMessageBox.critical(self.iface.mainWindow(), "Error",
                                 "Please select a layer.")
            return
        if not params.get("output_path"):
            QMessageBox.critical(self.iface.mainWindow(), "Error",
                                 "Please specify an output file path.")
            return

        fmt = params.get("format", "geotiff")
        label = "Preparing export..." if fmt == "mbtiles" else "Rendering GeoTIFF..."
        progress = QProgressDialog(label, "Cancel", 0, 100, self.iface.mainWindow())
        progress.setWindowTitle("Custom Map Downloader")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        QCoreApplication.processEvents()
        progress.show()
        QCoreApplication.processEvents()

        try:
            if fmt == "mbtiles":
                self.export_mbtiles(params, progress)
                progress.close()
                QMessageBox.information(self.iface.mainWindow(), "Success",
                                        f"MBTiles saved to:\n{params['output_path']}")
            else:
                self.export_geotiff(params, progress)
                progress.close()
                if params.get("load_as_layer"):
                    layer_name = os.path.basename(params["output_path"])
                    rl = QgsRasterLayer(params["output_path"], layer_name)
                    if rl.isValid():
                        QgsProject.instance().addMapLayer(rl)
                        QMessageBox.information(self.iface.mainWindow(), "Success",
                                                f"GeoTIFF saved and loaded:\n{params['output_path']}")
                    else:
                        QMessageBox.warning(self.iface.mainWindow(), "Partial Success",
                                            f"GeoTIFF saved but failed to load as layer:\n{params['output_path']}")
                else:
                    QMessageBox.information(self.iface.mainWindow(), "Success",
                                            f"GeoTIFF saved to:\n{params['output_path']}")
        except Exception as e:
            progress.close()
            QMessageBox.critical(self.iface.mainWindow(), "Error",
                                 f"Export failed:\n{str(e)}")

    # ------------------------------------------------------------------ #
    #  GeoTIFF export (unchanged logic)                                   #
    # ------------------------------------------------------------------ #

    def export_geotiff(self, params, progress=None):
        lat = params["lat"]
        lon = params["lon"]
        gsd = params["gsd"]
        width = params["width"]
        height = params["height"]
        layer = params["layer"]
        output_path = params["output_path"]
        add_georeferencing = params["add_georeferencing"]
        output_crs_epsg = params.get("output_crs", "EPSG:3857")

        def _prog(val, text):
            if progress:
                progress.setValue(val)
                progress.setLabelText(text)
                QCoreApplication.processEvents()

        _prog(5, "Computing extent...")

        crs_src = QgsCoordinateReferenceSystem("EPSG:4326")
        crs_dest = QgsCoordinateReferenceSystem(output_crs_epsg)
        transformer = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())
        center = transformer.transform(QgsPointXY(lon, lat))

        if crs_dest.isGeographic():
            meters_per_deg_lat = 111320.0
            meters_per_deg_lon = 111320.0 * math.cos(math.radians(lat))
            half_w = (width * gsd) / 2.0 / meters_per_deg_lon
            half_h = (height * gsd) / 2.0 / meters_per_deg_lat
        else:
            half_w = (width * gsd) / 2.0
            half_h = (height * gsd) / 2.0

        extent = QgsRectangle(center.x() - half_w, center.y() - half_h,
                              center.x() + half_w, center.y() + half_h)

        _prog(15, f"Rendering {width}x{height} px...")

        ms = QgsMapSettings()
        ms.setLayers([layer])
        ms.setExtent(extent)
        ms.setOutputSize(QSize(width, height))
        ms.setDestinationCrs(crs_dest)

        render = QgsMapRendererParallelJob(ms)
        loop = QEventLoop()
        render.renderingComplete.connect(loop.quit)
        render.start()
        loop.exec_()
        render.waitForFinished()
        _prog(70, "Writing output file...")
        rendered = render.renderedImage()

        if not add_georeferencing:
            rendered.save(output_path, "tif")
            return

        rendered = rendered.convertToFormat(QImage.Format_RGBA8888)
        ptr = rendered.bits()
        ptr.setsize(rendered.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)

        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(output_path, width, height, 4, gdal.GDT_Byte,
                           options=["COMPRESS=LZW", "TILED=YES"])
        if ds is None:
            raise Exception("Failed to create GeoTIFF file")

        px = (extent.xMaximum() - extent.xMinimum()) / width
        py = (extent.yMaximum() - extent.yMinimum()) / height
        ds.SetGeoTransform([extent.xMinimum(), px, 0, extent.yMaximum(), 0, -py])

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(output_crs_epsg.split(":")[1]))
        ds.SetProjection(srs.ExportToWkt())

        for i in range(4):
            _prog(70 + (i + 1) * 7, f"Writing band {i + 1}/4...")
            band = ds.GetRasterBand(i + 1)
            band.WriteArray(arr[:, :, i])
            band.FlushCache()
        _prog(100, "Done.")
        ds = None

    # ------------------------------------------------------------------ #
    #  MBTiles export                                                      #
    # ------------------------------------------------------------------ #

    def export_mbtiles(self, params, progress=None):
        layer = params["layer"]
        output_path = params["output_path"]
        extent = params["extent"]          # dict: min_lat/min_lon/max_lat/max_lon
        zoom_min = params["zoom_min"]
        zoom_max = params["zoom_max"]
        tile_size = params["tile_size"]
        padding = params.get("tile_padding", 1)

        min_lat = extent["min_lat"]
        min_lon = extent["min_lon"]
        max_lat = extent["max_lat"]
        max_lon = extent["max_lon"]

        # CRS objects (tiles always in EPSG:3857)
        crs_4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        crs_3857 = QgsCoordinateReferenceSystem("EPSG:3857")

        # Create / open MBTiles SQLite database
        if os.path.exists(output_path):
            os.remove(output_path)
        conn = sqlite3.connect(output_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE metadata (name TEXT, value TEXT);
            CREATE TABLE tiles (
                zoom_level  INTEGER,
                tile_column INTEGER,
                tile_row    INTEGER,
                tile_data   BLOB,
                PRIMARY KEY (zoom_level, tile_column, tile_row)
            );
            CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);
        """)
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("name", "Custom Map Downloader"))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("type", "overlay"))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("version", "1"))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("description", "Exported by Custom Map Downloader QGIS plugin"))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("format", "png"))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("bounds",
            f"{min_lon},{min_lat},{max_lon},{max_lat}"))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("minzoom", str(zoom_min)))
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("maxzoom", str(zoom_max)))
        conn.commit()

        total_tiles = _tile_count_padded(
            min_lon, min_lat, max_lon, max_lat, zoom_min, zoom_max, padding)

        if progress:
            progress.setRange(0, total_tiles)
            progress.setValue(0)
            progress.setLabelText(f"Exporting {total_tiles} tiles...")
            QCoreApplication.processEvents()

        done = 0
        for z in range(zoom_min, zoom_max + 1):
            n_tiles = 1 << z
            tx_min = max(0, _lon_to_tile_x(min_lon, z) - padding)
            tx_max = min(n_tiles - 1, _lon_to_tile_x(max_lon, z) + padding)
            ty_min = max(0, _lat_to_tile_y(max_lat, z) - padding)
            ty_max = min(n_tiles - 1, _lat_to_tile_y(min_lat, z) + padding)
            tiles_this_zoom = (tx_max - tx_min + 1) * (ty_max - ty_min + 1)

            for tx in range(tx_min, tx_max + 1):
                for ty in range(ty_min, ty_max + 1):
                    if progress and progress.wasCanceled():
                        conn.commit()
                        conn.close()
                        raise Exception("Export cancelled by user.")

                    png_data = self._render_tile(layer, tx, ty, z, tile_size,
                                                 crs_3857, crs_4326)

                    # MBTiles uses TMS y (flipped)
                    tms_y = (1 << z) - 1 - ty
                    cur.execute(
                        "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)",
                        (z, tx, tms_y, sqlite3.Binary(png_data))
                    )
                    done += 1
                    if progress:
                        pct = int(done * 100 / total_tiles) if total_tiles else 100
                        progress.setValue(done)
                        progress.setLabelText(
                            f"Zoom {z}  |  Tile {done}/{total_tiles}  ({pct}%)")
                        QCoreApplication.processEvents()

            conn.commit()

        conn.close()

    def _render_tile(self, layer, tx, ty, zoom, tile_size, crs_3857, crs_4326):
        """Render one slippy tile and return PNG bytes."""
        xmin, ymin, xmax, ymax = _tile_bounds_3857(tx, ty, zoom)
        extent = QgsRectangle(xmin, ymin, xmax, ymax)

        ms = QgsMapSettings()
        ms.setLayers([layer])
        ms.setExtent(extent)
        ms.setOutputSize(QSize(tile_size, tile_size))
        ms.setDestinationCrs(crs_3857)
        ms.setBackgroundColor(QColor(0, 0, 0, 0))

        render = QgsMapRendererParallelJob(ms)
        render.start()
        render.waitForFinished()
        img = render.renderedImage()

        # Save to PNG bytes via temp file
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        img.save(tmp.name, "PNG")
        with open(tmp.name, "rb") as f:
            data = f.read()
        os.unlink(tmp.name)
        return data
