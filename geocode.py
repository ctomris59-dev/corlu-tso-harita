#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Çorlu TSO Sanayi Haritası - Konum (geocoding) betiği
=====================================================

Bu betik companies.json içindeki firma adreslerini enlem/boylam (lat/lng)
koordinatlarına çevirir ve dosyayı yerinde günceller.

NEDEN YEREL BİLGİSAYARDA ÇALIŞTIRILIYOR?
Nominatim (OpenStreetMap arama servisi) tarayıcı içinden veya paylaşımlı/
bulut ortamlarından gelen yoğun otomatik istekleri engelleyebiliyor. Kendi
bilgisayarınızdan, doğru bir User-Agent başlığıyla ve saniyede en fazla 1
istek göndererek çalıştırmak Nominatim'in kullanım politikasına (ODbL / usage
policy) uygun ve güvenilir bir yöntemdir.

KULLANIM:
    python geocode.py

(Ekstra paket kurulumu gerekmez — betik yalnızca Python'un standart
kütüphanesini kullanır.)

- Zaten koordinatı bulunmuş firmaları atlar (tekrar tekrar çalıştırmak güvenlidir).
- 1.091 adres için ilk çalıştırma yaklaşık 35-40 dakika sürer (adres başına ~2 sn).
- Ctrl+C ile durdurup daha sonra kaldığı yerden devam ettirebilirsiniz.
- Üye listesi (SANAYİ.xlsx) güncellenip companies.json yeniden üretildiğinde,
  sadece yeni eklenen / koordinatsız kayıtlar için tekrar istek atar.

Bittiğinde companies.json dosyasını index.html ile aynı klasörde tutup
GitHub'a öylece push edebilirsiniz.
"""

import json
import time
import sys
import datetime
import urllib.parse
import urllib.request
import urllib.error

INPUT_FILE = "companies.json"
# Nominatim kullanım politikası: uygulamanızı ve bir iletişim yolunu tanımlayan
# gerçek bir User-Agent gönderin. Aşağıdaki değeri kendi bilgilerinizle
# güncellemeniz önerilir (zorunlu değil ama nazik bir davranıştır).
USER_AGENT = "CorluTSOSanayiHaritasi/1.0 (iletisim: proje@corlutso.org.tr)"
REGION_HINT = ", Tekirdağ, Türkiye"
VIEWBOX = "26.9,41.35,28.3,40.75"  # Çorlu/Ergene/Marmaraereğlisi çevresi
SLEEP_SECONDS = 1.1  # Nominatim kuralı: saniyede en fazla 1 istek

# OSB / sanayi sitesi adı bulunamazsa, hiçbir sonuç çıkmayan adresler için
# mutlak son çare: ilçe merkezine düş (kaba/yaklaşık konum olarak işaretlenir,
# haritada farklı bir işaretle gösterilir).
DISTRICT_CENTERS = {
    "Çorlu": (41.1615, 27.8004),
    "Ergene": (41.1750, 27.9330),
    "Marmaraereğlisi": (40.9739, 27.9647),
    "Belirsiz": (41.0800, 27.9000),
}

_area_cache = {}


def simplify_address(adres: str) -> str:
    """Aşırı spesifik kapı/no bilgilerini temizleyip eşleşme ihtimalini artırır."""
    import re
    s = re.sub(r"NO\s*:\s*\S+", " ", adres, flags=re.IGNORECASE)
    s = re.sub(r"KAT\s*:\s*\S+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"/\s*\d+\s*/?", " ", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def extract_area(adres: str):
    """Adresten sadece mahalle/OSB/köy adını çıkarır (sokak, no vb. olmadan).
    Örn: 'ULAŞ OSB MAHALLESİ 216 SK. NO:5 /1/_ ERGENE/TEKİRDAĞ' -> 'ULAŞ OSB MAHALLESİ'
    Bu, sokak/parsel seviyesinde eşleşme bulunamadığında en azından doğru
    sanayi bölgesi/mahalle seviyesinde bir konum yakalamak için kullanılır."""
    import re
    m = re.search(r"^(.*?(?:MAHALLESİ|MAH\.|KÖYÜ|BELDESİ|ORGANİZE SANAYİ BÖLGESİ|\bOSB\b))", adres, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def nominatim_search(query: str):
    url = (
        "https://nominatim.openstreetmap.org/search?"
        + urllib.parse.urlencode(
            {
                "format": "json",
                "limit": 1,
                "countrycodes": "tr",
                "viewbox": VIEWBOX,
                "bounded": 0,
                "q": query,
            }
        )
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def photon_search(query: str):
    """Komoot'un ücretsiz, açık kaynaklı geocoder'ı. Aynı OSM verisini farklı
    bir arama motoruyla (Elasticsearch tabanlı, serbest metin) tarar - bu
    yüzden Nominatim'in bulamadığı bazı adresleri bulabilir."""
    url = (
        "https://photon.komoot.io/api/?"
        + urllib.parse.urlencode(
            {"q": query, "limit": 1, "lat": 41.02, "lon": 27.85, "zoom": 12}
        )
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        feats = data.get("features") or []
        if feats:
            lng, lat = feats[0]["geometry"]["coordinates"]
            return float(lat), float(lng)
    return None


def search_both(query: str):
    """Aynı sorguyu önce Photon, sonra Nominatim'de dener (ikisi de ücretsiz,
    ikisi de OSM tabanlı ama farklı arama mantığı kullanıyor)."""
    for fn, name in ((photon_search, "photon"), (nominatim_search, "nominatim")):
        try:
            result = fn(query)
            time.sleep(SLEEP_SECONDS)
            if result:
                return result
        except urllib.error.HTTPError as e:
            print(f"  HTTP hata ({name}, {e.code}): {query[:55]}...")
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            print(f"  Hata ({name}): {e}")
            time.sleep(SLEEP_SECONDS)
    return None


def geocode_company(company):
    attempts = [
        company["adres"] + REGION_HINT,
        simplify_address(company["adres"]) + ", " + company["ilce"] + REGION_HINT,
    ]
    area = extract_area(company["adres"])
    if area:
        area_query = area + ", " + company["ilce"] + REGION_HINT
        if area_query not in attempts:
            attempts.append(area_query)

    for i, q in enumerate(attempts):
        # Mahalle/OSB seviyesi sorguları (son deneme) tekrar tekrar aynı
        # sonucu vereceği için önbelleğe alınır - gereksiz istek atılmaz.
        is_area_tier = (area and i == len(attempts) - 1)
        if is_area_tier and q in _area_cache:
            result = _area_cache[q]
        else:
            result = search_both(q)
            if is_area_tier:
                _area_cache[q] = result
        if result:
            return result[0], result[1], is_area_tier

    # Mutlak son çare: ilçe merkezi (kaba/yaklaşık konum).
    district = DISTRICT_CENTERS.get(company["ilce"])
    if district:
        return district[0], district[1], True

    return None


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    companies = data["companies"]
    todo = [c for c in companies if c.get("lat") is None]
    total_todo = len(todo)
    already_done = len(companies) - total_todo

    print(f"Toplam firma: {len(companies)}")
    print(f"Zaten konumlu: {already_done}")
    print(f"Konumlanacak: {total_todo}")
    if total_todo == 0:
        print("Yapılacak bir şey yok. Tüm firmalar zaten konumlanmış.")
        return

    # İki servis (Photon + Nominatim) art arda denendiği için önceki tahmine göre
    # biraz daha uzun sürebilir; kaba bir üst sınır veriyoruz.
    est_minutes = round(total_todo * SLEEP_SECONDS * 2.2 / 60)
    print(f"Tahmini süre: ~{est_minutes} dakika (çoğu adres daha erken bulunacağı için genelde daha kısa sürer)\n")

    found = 0
    failed = 0
    try:
        for i, company in enumerate(todo, 1):
            result = geocode_company(company)
            if result:
                company["lat"], company["lng"], approx = result
                company["approx"] = approx
                found += 1
                status = "OK (yaklaşık)" if approx else "OK"
            else:
                failed += 1
                status = "BULUNAMADI"
            print(f"[{i}/{total_todo}] {status:12s} {company['unvan'][:55]}")

            # Her 20 kayıtta bir ara kaydet (kesinti olursa veri kaybolmasın)
            if i % 20 == 0:
                data["geocodedAt"] = datetime.date.today().isoformat()
                with open(INPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
    except KeyboardInterrupt:
        print("\n\nDurduruldu. Şimdiye kadarki sonuçlar kaydediliyor...")

    data["geocodedAt"] = datetime.date.today().isoformat()
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"\nTamamlandı. Bulunan: {found}, Bulunamayan: {failed}")
    print(f"'{INPUT_FILE}' güncellendi.")
    if failed:
        print(
            f"\n{failed} adres eşleştirilemedi. Bu betiği tekrar çalıştırırsanız "
            "sadece bu kayıtlar için yeniden denenir (adresleri sicil kaydına göre "
            "elle sadeleştirmeniz gerekebilir)."
        )


if __name__ == "__main__":
    main()
