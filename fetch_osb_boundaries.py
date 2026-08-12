#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSB Sınırları Betiği
=====================
Çorlu/Ergene/Marmaraereğlisi bölgesindeki organize sanayi bölgelerinin
sınır poligonlarını OpenStreetMap (Nominatim) üzerinden çeker ve
osb-boundaries.json dosyasına yazar. index.html bu dosya varsa
haritada ilgili OSB'leri hafif renkli bir alan olarak çizer.

ÖNEMLİ: Bazı OSB'ler OpenStreetMap'te poligon olarak haritalanmamış
olabilir - bu durumda o OSB için sonuç boş kalır, hata vermez, index.html
sadece o OSB'yi çizmez. Bu normaldir, OSM gönüllü katkısına dayalı bir
haritadır ve her bölge eksiksiz haritalanmamış olabilir.

KULLANIM:
    python fetch_osb_boundaries.py

Yalnızca bir kez (veya OSB listesi değiştiğinde) çalıştırmanız yeterli -
şirket listesi güncellendiğinde tekrar çalıştırmanıza gerek yok.
"""

import json
import time
import urllib.parse
import urllib.request

USER_AGENT = "CorluTSOSanayiHaritasi/1.0 (iletisim: proje@corlutso.org.tr)"
OUTPUT_FILE = "osb-boundaries.json"
SLEEP_SECONDS = 1.1

# (Haritada gösterilecek etiket, Nominatim'de aranacak sorgu)
OSB_LIST = [
    ("Ergene-1 Organize Sanayi Bölgesi", "Ergene-1 Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye"),
    ("Ergene-2 Organize Sanayi Bölgesi ", "Ergene-2 Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye"),
    ("Velimeşe OSB", "Velimeşe Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye"),
    ("Çorlu Deri OSB", "Çorlu Deri Karma Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye"),
    ("Türkgücü OSB", "Türkgücü Organize Sanayi Bölgesi, Çorlu, Tekirdağ, Türkiye"),
    ("Ergene 2. OSB", "Ergene-2 Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye"),
    ("Avrupa Serbest Bölgesi", "Avrupa Serbest Bölgesi, Ergene, Tekirdağ, Türkiye"),
]


def search_polygon(query: str):
    url = (
        "https://nominatim.openstreetmap.org/search?"
        + urllib.parse.urlencode(
            {
                "format": "json",
                "limit": 1,
                "countrycodes": "tr",
                "polygon_geojson": 1,
                "q": query,
            }
        )
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data and data[0].get("geojson"):
            geom = data[0]["geojson"]
            if geom.get("type") in ("Polygon", "MultiPolygon"):
                return geom
    return None


def main():
    features = []
    for label, query in OSB_LIST:
        print(f"Aranıyor: {label} ...", end=" ")
        try:
            geom = search_polygon(query)
        except Exception as e:
            geom = None
            print(f"hata: {e}")
        if geom:
            features.append({
                "type": "Feature",
                "properties": {"name": label},
                "geometry": geom,
            })
            print("BULUNDU (poligon)")
        else:
            print("bulunamadı (OSM'de poligon olarak haritalanmamış olabilir)")
        time.sleep(SLEEP_SECONDS)

    fc = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=1)

    print(f"\n{len(features)}/{len(OSB_LIST)} OSB sınırı bulundu.")
    print(f"'{OUTPUT_FILE}' oluşturuldu. index.html ile aynı klasörde tutup GitHub'a yükleyin.")


if __name__ == "__main__":
    main()
