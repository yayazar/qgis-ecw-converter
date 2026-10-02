# ECW Converter – QGIS eklentisi

Projedeki GeoTIFF ortofotoyu ECW'ye (veya kayıpsız döşemeli GeoTIFF'e) dönüştürür.

**Kurulum:** `qgis_ecw_converter` klasörünü QGIS profil dizinindeki `python/plugins/` altına kopyalayın, Eklentiler menüsünden etkinleştirin. Menü: Raster → ECW Converter.

**Önemli:**
- ECW kayıplı dalgacık biçimidir; piksel değerleri birebir korunmaz. Birebir kayıpsızlık için GeoTIFF seçeneği kullanılır (DEFLATE + 512 döşeme + piramit).
- ECW yazmak için QGIS/GDAL'ın ECW sürücüsüyle (ERDAS SDK) derlenmiş olması gerekir; OSGeo4W standart kurulumunda yoktur. Yoksa ECW seçeneği listede görünmez. Büyük dosyaların (>500 MB) ECW yazımı ayrıca lisans gerektirebilir.
- Çıktının yanına koordinat sistemi için `.prj` yazılır.
