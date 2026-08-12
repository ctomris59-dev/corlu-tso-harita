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
    ("Ergene-1 Organize Sanayi Bölgesi", [
        "Ergene-1 Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye",
        "Vakıflar Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye",
    ]),
    ("Ergene-2 Organize Sanayi Bölgesi", [
        "Ergene-2 Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye",
        "Ulaş Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye",
    ]),
    ("Türkgücü Organize Sanayi Bölgesi", [
        "Türkgücü Organize Sanayi Bölgesi, Çorlu, Tekirdağ, Türkiye",
        "Türkgücü OSB, Çorlu, Tekirdağ, Türkiye",
        "Türkgücü, Çorlu, Tekirdağ, Türkiye",
    ]),
    ("Velimeşe Organize Sanayi Bölgesi", [
        "Velimeşe Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye",
        "Velimeşe OSB, Ergene, Tekirdağ, Türkiye",
        "Velimeşe Mahallesi, Ergene, Tekirdağ, Türkiye",
        "Velimeşe, Tekirdağ, Türkiye",
    ]),
    ("Marmaraereğlisi Organize Sanayi Bölgesi", [
        "Marmaraereğlisi Organize Sanayi Bölgesi, Marmaraereğlisi, Tekirdağ, Türkiye",
        "Marmara Ereğlisi Organize Sanayi Bölgesi, Tekirdağ, Türkiye",
        "Marmara Ereğlisi OSB, Tekirdağ, Türkiye",
    ]),
    ("Deri Karma Organize Sanayi Bölgesi", [
        "Çorlu Deri Organize Sanayi Bölgesi, Çorlu, Tekirdağ, Türkiye",
        "Çorlu Deri OSB, Çorlu, Tekirdağ, Türkiye",
        "Çorlu Deri Organize Sanayi Bölgesi, Tekirdağ, Türkiye",
        "Çorlu Deri OSB",
        "Deri Karma Organize Sanayi Bölgesi, Çorlu, Tekirdağ, Türkiye",
        "Deri Karma OSB, Çorlu, Tekirdağ, Türkiye",
        "Marmaracık Deri Organize Sanayi Bölgesi, Ergene, Tekirdağ, Türkiye",
    ]),
    ("Avrupa Serbest Bölgesi", [
        "Avrupa Serbest Bölgesi, Ergene, Tekirdağ, Türkiye",
    ]),
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
    existing = {}
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            prev = json.load(f)
        for feat in prev.get("features", []):
            name = feat.get("properties", {}).get("name")
            if name:
                existing[name] = feat
        if existing:
            print(f"Önceki çalıştırmadan {len(existing)} OSB zaten bulunmuş, atlanacak.\n")
    except FileNotFoundError:
        pass

    features = []
    for label, queries in OSB_LIST:
        if label in existing:
            features.append(existing[label])
            print(f"Aranıyor: {label} ... (önceden bulunmuş, atlandı)")
            continue
        print(f"Aranıyor: {label} ...", end=" ")
        geom = None
        for query in queries:
            try:
                geom = search_polygon(query)
            except Exception as e:
                print(f"hata ({query[:35]}...): {e}", end=" ")
                geom = None
            time.sleep(SLEEP_SECONDS)
            if geom:
                break
        if geom:
            features.append({
                "type": "Feature",
                "properties": {"name": label},
                "geometry": geom,
            })
            print("BULUNDU (poligon)")
        else:
            print("bulunamadı (OSM'de poligon olarak haritalanmamış olabilir)")

    fc = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=1)

    print(f"\n{len(features)}/{len(OSB_LIST)} OSB sınırı bulundu.")
    print(f"'{OUTPUT_FILE}' oluşturuldu. index.html ile aynı klasörde tutup GitHub'a yükleyin.")


if __name__ == "__main__":
    main()
