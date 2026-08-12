# Çorlu TSO Sanayi Haritası

Çorlu, Ergene ve Marmaraereğlisi ilçelerindeki sanayici üyeleri sektör/alt sektör
bazında haritada gösteren, aranabilir bir web uygulaması.

## Klasördeki dosyalar

- **`index.html`** — sitenin kendisi (harita, filtreler, liste).
- **`companies.json`** — üye verisi (unvan, adres, ilçe, sektör/alt sektör,
  faaliyet, ve varsa enlem/boylam).
- **`geocode.py`** — adresleri harita koordinatına çeviren, kendi
  bilgisayarınızda bir kez çalıştırdığınız Python betiği.
- **`fetch_osb_boundaries.py`** — (opsiyonel) OSB sınırlarını OpenStreetMap'ten
  çekip `osb-boundaries.json` üretir; haritada OSB alanlarını hafif renkli
  bölgeler olarak gösterir.

## Yeni özellikler

- **Yol Tarifi Al** — her firma popup'ında ve liste kartında, Google Maps'e
  yönlendirme modunda açan buton.
- **Kuş uçuşu erişim mesafesi** — her firma popup'ında İstanbul, TEM Otoyolu,
  Tekirdağ Limanı, Çorlu ve İstanbul Havalimanı'na yaklaşık mesafe.
- **Paylaşılabilir bağlantı** — filtre uyguladığınızda URL otomatik güncellenir
  (`?sektor=...&ilce=...`); üstteki "🔗 Bağlantıyı Kopyala" butonuyla o anki
  filtrelenmiş görünümün linkini kopyalayabilirsiniz.
- **Sektörel Dağılım** — üstteki "📊 İstatistikler" butonu, tüm sektörlerin
  üye sayısını bar grafik olarak gösterir.
- **OSB sınırları** — `osb-boundaries.json` dosyası varsa, haritada ilgili
  OSB'ler hafif yeşil/çizgili bir alan olarak görünür (bkz. aşağıdaki adım).
- **Son güncelleme etiketi** — sayfa altında üye listesinin ve konum verisinin
  ne zaman alındığı otomatik gösterilir.
- **"Bu bilgi hatalı, bildir"** — her popup'ta, TSO'ya doğrudan e-posta
  taslağı açan bir bildirim linki (adresi `proje@corlutso.org.tr` olarak
  ayarlanmış — kendi resmi e-posta adresinizle değiştirmek isterseniz
  `index.html` içinde `reportUrl` fonksiyonundaki adresi güncelleyin).

## 1) Konumları oluşturun (ilk kurulumda bir kez)

`companies.json` içindeki firmaların `lat`/`lng` alanları şu an **boş**.
Bunları doldurmak için:

```bash
python geocode.py
```

(Ekstra paket kurulumu gerekmez — betik Python'un standart kütüphanesiyle çalışır.)

- 1.091 adres için yaklaşık **40-60 dakika** sürer (her adres önce
  [Photon](https://photon.komoot.io/), bulunamazsa
  [Nominatim](https://nominatim.openstreetmap.org/) ile denenir — ikisi de
  ücretsiz, ikisi de OpenStreetMap verisini kullanır ama farklı arama
  mantığına sahip oldukları için birlikte kullanmak isabeti artırır).
- Tam adres hiçbir şekilde bulunamazsa, adresteki OSB/mahalle adı (ör.
  "Ulaş OSB Mahallesi") ayrı bir sorgu olarak denenir; o da olmazsa firma
  ilçe merkezine yaklaşık olarak yerleştirilir. Bu şekilde konumlanan
  firmalar haritada **çizgili işaretle** ayırt edilir ve popup'ta
  "yaklaşık konum" notu görünür.
- Yarıda `Ctrl+C` ile durdurabilirsiniz; her 20 kayıtta bir otomatik kaydeder,
  tekrar çalıştırdığınızda kaldığı yerden devam eder.
- Bu betiği **kendi bilgisayarınızdan** çalıştırmanız önemli — bulut/tarayıcı
  ortamlarından atılan toplu istekler Nominatim tarafından engellenebiliyor;
  betik gerçek bir tarayıcı/IP'den, kurallara uygun hızda çalıştığı için
  güvenilir sonuç verir.
- Üye listesi ileride güncellenirse (yeni Excel'den `companies.json`'u
  yeniden ürettiğinizde), betiği tekrar çalıştırmanız yeterli — sadece
  konumu olmayan yeni kayıtlar için istek atar, eskileri tekrar sorgulamaz.

## 2) OSB sınırlarını ekleyin (opsiyonel ama önerilir)

```bash
python fetch_osb_boundaries.py
```

- Ulaş OSB, Vakıflar OSB, Velimeşe OSB, Çorlu Deri OSB, Türkgücü OSB, Ergene 2.
  OSB ve Avrupa Serbest Bölgesi için OpenStreetMap'te sınır poligonu arar.
- Bazıları OSM'de haritalı olmayabilir — bulunamayanlar sessizce atlanır,
  hata vermez.
- `osb-boundaries.json` dosyasını üretir; bunu da diğer dosyalarla birlikte
  GitHub'a yüklemeniz yeterli, `index.html` otomatik algılar.

## 3) GitHub Pages'te yayınlama

1. GitHub'da yeni bir repo oluşturun (herkese açık bir site istiyorsanız
   **public**; erişimi kısıtlamak istiyorsanız GitHub Enterprise/Pro plan
   gerekir, aksi halde Pages özelliği repo'nun herkese açık olmasını gerektirir).
2. Bu dosyaları (`index.html`, `companies.json`, konumlar oluşturulmuş
   haliyle, ve varsa `osb-boundaries.json`) repo'nun **ana dizinine** yükleyin.
3. Repo → **Settings → Pages** → *Source*: `Deploy from a branch` →
   Branch: `main` / `root` seçip kaydedin.
4. Birkaç dakika içinde site şu adreste yayında olur:
   `https://<kullanici-adiniz>.github.io/<repo-adi>/`

## 4) Veri güncellendiğinde

TSO'dan yeni bir üye listesi aldığınızda:

1. Yeni Excel'i işleyip yeni bir `companies.json` üretin (bu adım için bana
   tekrar sorabilirsiniz — Excel'i verirseniz güncel dosyayı hazırlarım).
2. `geocode.py`'yi tekrar çalıştırın (sadece yeni/eksik kayıtlar için
   sorgu atar).
3. Güncellenmiş `companies.json`'u GitHub repo'suna push edin — site
   otomatik güncellenir.

## ⚠️ Yayına almadan önce kontrol edilmesi gereken KVKK notu

Daha önce paylaştığım KVKK kontrol listesinde, **288 numaralı kayıt**
("AMOR'E DESIGN HOME TEXTILE KOLLEKTİF ŞİRKETİ HAKKI KALAYCIOĞLU") unvanında
hâlâ bir gerçek kişinin tam adı geçiyordu (Yüksek risk). Bu site **herkese
açık** olacağı için, yayına almadan önce bu kaydı TSO hukuk/KVKK sorumlusuyla
son bir kez teyit etmenizi öneririm. Diğer kayıtlar (sadece soyisim/marka
niteliğinde olanlar) düşük risk olarak değerlendirilmişti.

## Teknik notlar

- Harita: [Leaflet.js](https://leafletjs.com/) + CARTO açık zemin katmanı.
- Kümeleme: Leaflet.markercluster (1.000+ firma haritada sorunsuz görünür).
- Geocoding: [Photon](https://photon.komoot.io/) (birincil) + [Nominatim](https://nominatim.openstreetmap.org/) (yedek) — ikisi de ücretsiz, OpenStreetMap tabanlı.
- Sunucu gerektirmez — sadece statik dosyalar, GitHub Pages / Netlify /
  herhangi bir statik hosting ile çalışır.
