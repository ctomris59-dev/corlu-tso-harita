#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSB İçine Taşıma Betiği
========================
Adresinde bir OSB adı geçen ama (Nominatim sokak seviyesinde bulamadığı için)
yanlışlıkla ilçe merkezine düşmüş firmaları, o OSB'nin gerçek sınır poligonu
içine taşır.

Örnek: Adresinde "Türkgücü Organize Sanayi Bölgesi" geçen ama haritada
Çorlu şehir merkezinde görünen firmalar, artık osb-boundaries.json'daki
Türkgücü poligonunun İÇİNE rastgele bir noktaya yerleştirilir.

ÖN KOŞUL: Önce fetch_osb_boundaries.py çalıştırılmış ve osb-boundaries.json
üretilmiş olmalı.

KULLANIM:
    python fix_osb_locations.py

Bu betik SADECE şu iki durumdaki firmaları taşır:
  1. approx=true olan (yani zaten "yaklaşık konum" işaretli) VE
  2. adresinde ilgili OSB adı geçen
firmaları. Sokak seviyesinde net bulunmuş (approx=false) kayıtlara dokunmaz.
"""

import json
import random
import re

COMPANIES_FILE = "companies.json"
BOUNDARIES_FILE = "osb-boundaries.json"

# OSB etiketi -> adreste aranacak, o OSB'ye ait olası ifadeler (büyük harf).
ALIASES = {
    "Ergene-1 Organize Sanayi Bölgesi": [
        "ERGENE-1 ORGANİZE SANAYİ BÖLGESİ", "ERGENE 1 ORGANİZE SANAYİ BÖLGESİ",
        "ERGENE-1 OSB", "VAKIFLAR ORGANİZE SANAYİ",
    ],
    "Ergene-2 Organize Sanayi Bölgesi": [
        "ERGENE-2 ORGANİZE SANAYİ BÖLGESİ", "ERGENE 2 ORGANİZE SANAYİ BÖLGESİ",
        "ERGENE 2 OSB", "ERGENE-2 OSB", "ULAŞ ORGANİZE SANAYİ",
    ],
    "Türkgücü Organize Sanayi Bölgesi": [
        "TÜRKGÜCÜ ORGANİZE SANAYİ BÖLGESİ", "TÜRKGÜCÜ OSB",
    ],
    "Velimeşe Organize Sanayi Bölgesi": [
        "VELİMEŞE ORGANİZE SANAYİ BÖLGESİ", "VELİMEŞE OSB",
    ],
    "Marmaraereğlisi Organize Sanayi Bölgesi": [
        "MARMARAEREĞLİSİ ORGANİZE SANAYİ BÖLGESİ",
        "MARMARA EREĞLİSİ ORGANİZE SANAYİ BÖLGESİ", "MARMARA EREĞLİSİ OSB",
    ],
    "Deri Karma Organize Sanayi Bölgesi": [
        "DERİ KARMA ORGANİZE SANAYİ BÖLGESİ", "ÇORLU DERİ ORGANİZE SANAYİ BÖLGESİ",
        "ÇORLU DERİ KARMA ORGANİZE SANAYİ BÖLGESİ", "ÇORLU DERİ OSB",
    ],
    "Avrupa Serbest Bölgesi": [
        "AVRUPA SERBEST BÖLGESİ",
    ],
}


def tr_upper(s):
    return (s or "").replace("i", "İ").replace("ı", "I").upper()


def point_in_ring(lng, lat, ring):
    """Ray-casting algoritması: nokta, tek bir poligon halkasının içinde mi?"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def point_in_geometry(lng, lat, geometry):
    if geometry["type"] == "Polygon":
        rings = geometry["coordinates"]
        return point_in_ring(lng, lat, rings[0])
    if geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            if point_in_ring(lng, lat, poly[0]):
                return True
    return False


def bbox_of(geometry):
    coords = []
    if geometry["type"] == "Polygon":
        coords = geometry["coordinates"][0]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            coords.extend(poly[0])
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lngs), max(lngs), min(lats), max(lats)


def random_point_in_geometry(geometry, tries=500):
    min_lng, max_lng, min_lat, max_lat = bbox_of(geometry)
    for _ in range(tries):
        lng = random.uniform(min_lng, max_lng)
        lat = random.uniform(min_lat, max_lat)
        if point_in_geometry(lng, lat, geometry):
            return lat, lng
    # Poligon çok ince/karmaşıksa son çare: bbox merkezi
    return (min_lat + max_lat) / 2, (min_lng + max_lng) / 2


def main():
    with open(COMPANIES_FILE, encoding="utf-8") as f:
        data = json.load(f)

    try:
        with open(BOUNDARIES_FILE, encoding="utf-8") as f:
            boundaries = json.load(f)
    except FileNotFoundError:
        print(f"'{BOUNDARIES_FILE}' bulunamadı. Önce fetch_osb_boundaries.py çalıştırın.")
        return

    geoms_by_label = {}
    for feat in boundaries.get("features", []):
        name = feat.get("properties", {}).get("name")
        if name:
            geoms_by_label[name] = feat["geometry"]

    if not geoms_by_label:
        print("osb-boundaries.json içinde hiç poligon yok. Yapılacak bir şey yok.")
        return

    print(f"{len(geoms_by_label)} OSB poligonu bulundu: {', '.join(geoms_by_label)}\n")

    moved = 0
    for company in data["companies"]:
        if not company.get("approx"):
            continue  # Zaten net (sokak seviyesi) bulunmuş, dokunma
        adres_upper = tr_upper(company["adres"])
        for label, aliases in ALIASES.items():
            if label not in geoms_by_label:
                continue
            if any(alias in adres_upper for alias in aliases):
                geometry = geoms_by_label[label]
                # Zaten bu poligonun içindeyse tekrar taşımaya gerek yok
                if company.get("lat") is not None and point_in_geometry(
                    company["lng"], company["lat"], geometry
                ):
                    break
                lat, lng = random_point_in_geometry(geometry)
                company["lat"], company["lng"] = lat, lng
                moved += 1
                print(f"  Taşındı -> {label}: {company['unvan'][:55]}")
                break

    with open(COMPANIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"\nToplam {moved} firma, adreslerindeki OSB'nin gerçek sınırları içine taşındı.")
    print(f"'{COMPANIES_FILE}' güncellendi.")


if __name__ == "__main__":
    main()
