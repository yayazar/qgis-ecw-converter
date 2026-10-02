"""GDAL tabanlı dönüştürme mantığı (QGIS arayüzünden bağımsız)."""
import os

from osgeo import gdal, osr

gdal.UseExceptions()

MODE_ECW = "ecw"
MODE_LOSSLESS_TIFF = "tiff"


def ecw_available():
    return gdal.GetDriverByName("ECW") is not None


def default_output(src_path, mode):
    base, _ = os.path.splitext(src_path)
    return base + ("_ecw.ecw" if mode == MODE_ECW else "_opt.tif")


def convert(src_path, dst_path, mode, target=None, drop_alpha=False,
            progress=None):
    """Kaynak rasteri dönüştürür; dönen değer: (çıktı_boyutu, kaynak_boyutu).

    target: ECW için hedef küçülme yüzdesi (düşük = yüksek kalite). 0 = en
    yüksek kalite. ECW dalgacık (wavelet) tabanlıdır; gerçek kayıpsız yazım
    desteklenmez, bu yüzden gerçek kayıpsızlık için MODE_LOSSLESS_TIFF kullanın.
    """
    src = gdal.Open(src_path)
    if src is None:
        raise RuntimeError("Kaynak dosya açılamadı: %s" % src_path)

    bands = None
    if drop_alpha and src.RasterCount == 4:
        bands = [1, 2, 3]

    cb = None
    if progress is not None:
        def cb(frac, _msg, _data):
            return 0 if progress(frac) is False else 1

    if mode == MODE_ECW:
        if not ecw_available():
            raise RuntimeError("Bu GDAL sürümünde ECW sürücüsü yok.")
        opts = gdal.TranslateOptions(
            format="ECW", bandList=bands, callback=cb,
            creationOptions=["TARGET=%d" % int(target or 0)])
    else:
        opts = gdal.TranslateOptions(
            format="GTiff", bandList=bands, callback=cb,
            creationOptions=["TILED=YES", "BLOCKXSIZE=512", "BLOCKYSIZE=512",
                             "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9",
                             "BIGTIFF=IF_SAFER", "NUM_THREADS=ALL_CPUS"])

    out = gdal.Translate(dst_path, src, options=opts)
    if out is None:
        raise RuntimeError("Dönüştürme başarısız.")
    out.FlushCache()

    if mode == MODE_LOSSLESS_TIFF:
        # Piramitler: uzaklaştırınca akıcı gösterim için.
        out.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64])
    out = None

    # Netcad/Civil 3D gibi yazılımlar için koordinat sistemi yan dosyası.
    wkt = src.GetProjection()
    if wkt:
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt)
        prj = os.path.splitext(dst_path)[0] + ".prj"
        with open(prj, "w") as f:
            f.write(srs.ExportToWkt(["FORMAT=WKT1_ESRI"]))
    src_size = os.path.getsize(src_path)
    src = None
    return os.path.getsize(dst_path), src_size
