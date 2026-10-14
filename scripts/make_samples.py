"""Generate SYNTHETIC supplier documents for the demo (all companies, people and numbers are fictional).
Each document: HTML -> PDF + PNG "scan" (slight rotation, noise) + ground-truth JSON for extraction tests.

    python scripts/make_samples.py
"""
import json
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "data" / "samples"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 0 }
body { font-family: 'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', sans-serif; margin: 0; padding: 48px 56px; color: #1a1a1a; font-size: 14px; width: 1100px; }
.hdr { display: flex; justify-content: space-between; border-bottom: 3px solid #234; padding-bottom: 14px; }
.co { font-size: 22px; font-weight: 700; color: #234 } .sub { color: #555; font-size: 12px; line-height: 1.5 }
h1 { font-size: 20px; margin: 26px 0 6px; letter-spacing: .02em } h2 { font-size: 15px; margin: 22px 0 8px; color: #234 }
table { border-collapse: collapse; width: 100%; margin-top: 6px } td, th { border: 1px solid #999; padding: 7px 9px; text-align: left; vertical-align: top }
th { background: #eef1f4; width: 42% } .stamp { margin-top: 30px; display: flex; justify-content: space-between; align-items: flex-end }
.seal { width: 150px; height: 150px; border: 4px solid #b3262e; border-radius: 50%; color: #b3262e; display: flex; align-items: center;
        justify-content: center; text-align: center; font-weight: 700; font-size: 12px; transform: rotate(-12deg); opacity: .8 }
.sig { font-family: 'Snell Roundhand', cursive; font-size: 26px; color: #123 } .small { font-size: 11px; color: #666; margin-top: 22px }
"""


def doc_html(company, address, title, sections, seal, signer, footer, lang="en"):
    rows = ""
    for h, items in sections:
        rows += f"<h2>{h}</h2><table>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in items) + "</table>"
    return f"""<!doctype html><html lang="{lang}"><meta charset="utf-8"><style>{CSS}</style><body>
<div class="hdr"><div><div class="co">{company}</div><div class="sub">{address}</div></div><div class="sub" style="text-align:right">SYNTHETIC DEMO DOCUMENT<br>fictional data</div></div>
<h1>{title}</h1>{rows}
<div class="stamp"><div><div class="sig">{signer[0]}</div><div class="sub">{signer[1]}</div></div><div class="seal">{seal}</div></div>
<div class="small">{footer}</div></body></html>"""


DOCS = [
    dict(id="01_indonesia_slab_verified", lang="id",
         company="PT Baja Samudra Nusantara", address="Kawasan Industri Cilegon Blok C-7, Banten 42435, Indonesia · NIB 9120007714421",
         title="Komunikasi Data Emisi CBAM / CBAM Emissions Data Communication",
         sections=[("Instalasi / Installation", [("Nama instalasi / Installation name", "PT Baja Samudra Nusantara — Slab Plant 2"),
                                                 ("Negara / Country", "Indonesia (ID)"), ("UN/LOCODE", "ID CXP"),
                                                 ("Rute produksi / Production route", "BF-BOF (blast furnace – basic oxygen furnace) — CBAM route (C)")]),
                   ("Barang / Goods", [("Kode CN / CN code", "7207 11 14"), ("Deskripsi", "Slab baja karbon rendah, cor kontinu / continuously cast low-carbon slabs")]),
                   ("Emisi / Emissions", [("Periode pelaporan / Reporting period", "01.01.2025 – 31.12.2025"),
                                          ("Emisi langsung spesifik / Specific direct embedded emissions", "2,10 tCO2e / t"),
                                          ("Total emisi langsung / Total direct emissions", "3 360 000 tCO2e"),
                                          ("Volume produksi / Production volume", "1 600 000 t"),
                                          ("Harga karbon dibayar / Carbon price paid", "Tidak ada / none")]),
                   ("Verifikasi / Verification", [("Status", "Diverifikasi / Verified (reasonable assurance)"),
                                                  ("Verifikator / Verifier", "Equator Carbon Assurance B.V. — accredited ISO 14065, accreditation no. RvA-V-114"),
                                                  ("Tanggal / Date", "14.03.2026")])],
         seal="PT BAJA<br>SAMUDRA<br>NUSANTARA<br>★", signer=("R. Hartono", "Environmental Manager · 18.03.2026"),
         footer="Data disusun sesuai Peraturan Pelaksana (UE) 2025/2547. Untuk importir: Acciai Liguri S.r.l., EORI IT01234567890.",
         truth=dict(installation_name="PT Baja Samudra Nusantara — Slab Plant 2", installation_country="ID", cn_code="7207 11 14",
                    production_route="C", specific_direct_emissions=2.10, total_direct_emissions_t=3360000, production_volume_t=1600000,
                    reporting_period_start="2025-01-01", reporting_period_end="2025-12-31", verified=True,
                    verifier_name="Equator Carbon Assurance B.V.", carbon_price_paid=None), expect="ACCEPT"),
    dict(id="02_china_hrc_verified", lang="zh",
         company="华东恒钢板材有限公司", address="中国江苏省南通市港闸区钢城路88号 · 统一社会信用代码 91320600MA1X7K2Q8T",
         title="CBAM 碳排放数据通报（设施层面）",
         sections=[("设施信息", [("设施名称", "华东恒钢板材有限公司 热轧一厂"), ("国家", "中国 (CN)"), ("生产路线", "高炉-转炉 (BF-BOF)，CBAM 路线 (C)")]),
                   ("货物", [("CN 编码", "7208 39 00"), ("货物描述", "热轧卷板，宽度 ≥ 600 mm，厚度 < 3 mm")]),
                   ("排放数据", [("报告期", "2025-01-01 至 2025-12-31"), ("单位产品直接内含排放", "1.95 tCO2e/吨"),
                                 ("直接排放总量", "4 680 000 tCO2e"), ("产量", "2 400 000 吨"), ("已支付碳价", "全国碳市场：62 元/tCO2e（约 7.9 欧元）")]),
                   ("核查", [("核查状态", "已核查（合理保证）"), ("核查机构", "Shanghai GreenLedger Verification Co. — ISO 14065 认可"),
                             ("核查日期", "2026-02-27")])],
         seal="华东恒钢<br>板材有限公司<br>★<br>专用章", signer=("王建国", "能源环保部经理 · 2026-03-02"),
         footer="本通报依据欧盟实施条例 (EU) 2025/2547 编制。进口商：Laminati Riviera S.p.A.",
         truth=dict(installation_name="华东恒钢板材有限公司 热轧一厂", installation_country="CN", cn_code="7208 39 00", production_route="C",
                    specific_direct_emissions=1.95, total_direct_emissions_t=4680000, production_volume_t=2400000,
                    reporting_period_start="2025-01-01", reporting_period_end="2025-12-31", verified=True,
                    verifier_name="Shanghai GreenLedger Verification Co.", carbon_price_paid=7.9), expect="ACCEPT"),
    dict(id="03_india_slab_selfdeclared", lang="en",
         company="Deccan Coastal Steel Pvt. Ltd.", address="Plot 14, MIDC Taloja, Navi Mumbai 410208, Maharashtra, India · CIN U27100MH2011PTC2219",
         title="Supplier Declaration of Embedded Emissions (CBAM)",
         sections=[("Installation", [("Installation name", "Deccan Coastal Steel — Melt Shop & Caster"), ("Country", "India"),
                                     ("Production route", "Integrated BF-BOF")]),
                   ("Goods", [("CN code", "7207 12 10"), ("Description", "Steel slabs, width ≥ 2× thickness, continuously cast")]),
                   ("Emissions", [("Reporting period", "April 2025 – March 2026 (FY 2025-26)"),
                                  ("Specific direct embedded emissions", "2.35 tCO2e per tonne of slab"),
                                  ("Carbon price paid", "Not applicable")]),
                   ("Verification", [("Status", "Self-declared by the operator. Third-party verification planned for Q1 2027."),
                                     ("Verifier", "—")])],
         seal="DECCAN<br>COASTAL<br>STEEL<br>PVT LTD", signer=("A. Kulkarni", "Head – Sustainability · 10.04.2026"),
         footer="This declaration is provided for information to EU importers. Buyer: Acciai Liguri S.r.l.",
         truth=dict(installation_name="Deccan Coastal Steel — Melt Shop & Caster", installation_country="IN", cn_code="7207 12 10",
                    production_route="C", specific_direct_emissions=2.35, reporting_period_start="2025-04-01",
                    reporting_period_end="2026-03-31", verified=False, verifier_name=None, carbon_price_paid=None), expect="NEEDS_SUPPLIER"),
    dict(id="04_turkey_billet_eaf_verified", lang="tr",
         company="Ege Hurda Çelik Sanayi A.Ş.", address="Aliağa Organize Sanayi Bölgesi, 35800 İzmir, Türkiye · Vergi No 3240017781",
         title="CBAM Gömülü Emisyon Bildirimi / Embedded Emissions Communication",
         sections=[("Tesis", [("Tesis adı", "Ege Hurda Çelik — Ark Ocağı Tesisi"), ("Ülke", "Türkiye (TR)"),
                              ("Üretim rotası", "Hurda bazlı elektrik ark ocağı (EAF) — CBAM rota (E)")]),
                   ("Ürün", [("GTİP / CN kodu", "7207 11 14"), ("Tanım", "Kütük, sürekli döküm, düşük karbonlu")]),
                   ("Emisyonlar", [("Raporlama dönemi", "01.01.2025 – 31.12.2025"), ("Spesifik doğrudan gömülü emisyon", "0,42 tCO2e/t"),
                                   ("Toplam doğrudan emisyon", "462 000 tCO2e"), ("Üretim miktarı", "1 100 000 t"),
                                   ("Ödenen karbon fiyatı", "Yok")]),
                   ("Doğrulama", [("Durum", "Doğrulandı (makul güvence)"), ("Doğrulayıcı", "Anadolu Karbon Doğrulama Ltd. — TÜRKAK akrediteli, ISO 14065"),
                                  ("Tarih", "05.02.2026")])],
         seal="EGE HURDA<br>ÇELİK<br>A.Ş.", signer=("M. Yıldız", "Çevre Müdürü · 09.02.2026"),
         footer="Uygulama Yönetmeliği (AB) 2025/2547 uyarınca hazırlanmıştır. İthalatçı: Trafilerie del Ponente S.r.l.",
         truth=dict(installation_name="Ege Hurda Çelik — Ark Ocağı Tesisi", installation_country="TR", cn_code="7207 11 14",
                    production_route="E", specific_direct_emissions=0.42, total_direct_emissions_t=462000, production_volume_t=1100000,
                    reporting_period_start="2025-01-01", reporting_period_end="2025-12-31", verified=True,
                    verifier_name="Anadolu Karbon Doğrulama Ltd.", carbon_price_paid=None), expect="ACCEPT"),
    dict(id="05_vietnam_missing_fields", lang="vi",
         company="Công ty TNHH Thép Cửa Biển", address="KCN Phú Mỹ II, Thị xã Phú Mỹ, Bà Rịa – Vũng Tàu, Việt Nam",
         title="Thông báo phát thải CBAM / CBAM emissions notice",
         sections=[("Cơ sở / Installation", [("Tên cơ sở", "Nhà máy cán nóng Cửa Biển"), ("Quốc gia", "Việt Nam (VN)"),
                                              ("Lộ trình sản xuất / route", "—")]),
                   ("Hàng hóa / Goods", [("Mô tả", "Thép cuộn cán nóng / hot-rolled coil")]),
                   ("Phát thải / Emissions", [("Phát thải trực tiếp riêng / Specific direct emissions", "1,80 tCO2e/tấn"),
                                              ("Kỳ báo cáo / Reporting period", "—")]),
                   ("Thẩm định / Verification", [("Trạng thái", "Đã thẩm định / verified"), ("Đơn vị thẩm định", "—")])],
         seal="CÔNG TY<br>THÉP<br>CỬA BIỂN", signer=("Nguyễn V. Long", "Trưởng phòng Môi trường · 21.03.2026"),
         footer="Người mua / Buyer: Laminati Riviera S.p.A.",
         truth=dict(installation_name="Nhà máy cán nóng Cửa Biển", installation_country="VN", cn_code=None, production_route=None,
                    specific_direct_emissions=1.80, reporting_period_start=None, reporting_period_end=None, verified=True,
                    verifier_name=None, carbon_price_paid=None), expect="NEEDS_SUPPLIER"),
    dict(id="06_ukraine_implausible", lang="uk",
         company="ТОВ «Приазовська Сталь Груп»", address="вул. Металургів, 7, м. Запоріжжя, 69000, Україна · ЄДРПОУ 41022387",
         title="Повідомлення про вбудовані викиди CBAM / CBAM embedded emissions",
         sections=[("Установка / Installation", [("Назва установки", "Приазовська Сталь — Конверторний цех"), ("Країна", "Україна (UA)"),
                                                  ("Технологічний маршрут", "Доменна піч – киснево-конвертерний (BF-BOF), маршрут (C)")]),
                   ("Товар / Goods", [("Код УКТ ЗЕД / CN", "7207 11 14"), ("Опис", "Сляби, безперервне лиття")]),
                   ("Викиди / Emissions", [("Звітний період", "01.01.2025 – 31.12.2025"), ("Питомі прямі вбудовані викиди", "0,35 tCO2e/т"),
                                           ("Ціна вуглецю сплачена", "немає")]),
                   ("Верифікація / Verification", [("Статус", "Верифіковано"), ("Верифікатор", "ТОВ «Карбон Аудит Україна», ISO 14065"),
                                                   ("Дата", "02.03.2026")])],
         seal="ПРИАЗОВСЬКА<br>СТАЛЬ<br>ГРУП", signer=("О. Коваленко", "Головний еколог · 04.03.2026"),
         footer="Покупець: Acciai Liguri S.r.l.",
         truth=dict(installation_name="Приазовська Сталь — Конверторний цех", installation_country="UA", cn_code="7207 11 14",
                    production_route="C", specific_direct_emissions=0.35, reporting_period_start="2025-01-01",
                    reporting_period_end="2025-12-31", verified=True, verifier_name="ТОВ «Карбон Аудит Україна»", carbon_price_paid=None),
         expect="NEEDS_HUMAN"),
]

INVOICE = dict(id="07_fattura_acciai_liguri", lang="it",
               company="Acciai Liguri S.r.l.", address="Via del Porto 21, 18100 Imperia (IM) · P.IVA IT01234567890 · EORI IT01234567890",
               title="Registro importazioni Q3 2026 — merci CBAM (dati di esempio)",
               sections=[("Spedizioni", [("PT Baja Samudra Nusantara (ID) · CN 7207 11 14", "12 400 t · Bolla doganale 26IT0042A7"),
                                          ("Deccan Coastal Steel (IN) · CN 7207 12 10", "8 150 t · Bolla doganale 26IT0042B2"),
                                          ("Priazovska Stal Grup (UA) · CN 7207 11 14", "5 300 t · Bolla doganale 26IT0043C9")])],
               seal="ACCIAI<br>LIGURI<br>S.R.L.", signer=("G. Ferraro", "Responsabile acquisti · 02.10.2026"),
               footer="Dichiarante CBAM autorizzato. Dati fittizi per dimostrazione.",
               truth=dict(shipments=[{"supplier": "PT Baja Samudra Nusantara", "country": "ID", "cn": "7207 11 14", "tonnes": 12400},
                                     {"supplier": "Deccan Coastal Steel", "country": "IN", "cn": "7207 12 10", "tonnes": 8150},
                                     {"supplier": "Priazovska Stal Grup", "country": "UA", "cn": "7207 11 14", "tonnes": 5300}]),
               expect=None)


def render(html: str, stem: Path):
    tmp = Path(tempfile.mkdtemp(prefix="fea-chrome-"))
    try:
        h = stem.with_suffix(".html")
        h.write_text(html, encoding="utf-8")
        base = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}", "--hide-scrollbars"]
        subprocess.run(base + ["--no-pdf-header-footer", f"--print-to-pdf={stem.with_suffix('.pdf')}", h.as_uri()],
                       check=True, capture_output=True, timeout=60)
        png = stem.with_suffix(".clean.png")
        subprocess.run(base + ["--window-size=1212,1600", f"--screenshot={png}", h.as_uri()], check=True, capture_output=True, timeout=60)
        scan(png, stem.with_suffix(".png"))
        png.unlink()
        h.unlink()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scan(src: Path, dst: Path, seed: int = 7):
    """Make it look photographed/scanned: paper tint, tiny rotation, blur and grain."""
    rnd = random.Random(hash(dst.name) & 0xFFFF)
    im = Image.open(src).convert("RGB")
    im = im.rotate(rnd.uniform(-1.4, 1.4), resample=Image.BICUBIC, expand=True, fillcolor=(236, 232, 222))
    tint = Image.new("RGB", im.size, (246, 241, 228))
    im = Image.blend(im, tint, 0.12).filter(ImageFilter.GaussianBlur(0.6))
    px = im.load()
    for _ in range(im.size[0] * im.size[1] // 90):
        x, y = rnd.randrange(im.size[0]), rnd.randrange(im.size[1])
        g = rnd.randrange(150, 230)
        px[x, y] = (g, g, g)
    im.save(dst, optimize=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for d in DOCS + [INVOICE]:
        stem = OUT / d["id"]
        render(doc_html(d["company"], d["address"], d["title"], d["sections"], d["seal"], d["signer"], d["footer"], d["lang"]), stem)
        stem.with_suffix(".truth.json").write_text(json.dumps({"truth": d["truth"], "expect": d["expect"], "lang": d["lang"]},
                                                               ensure_ascii=False, indent=1))
        manifest.append({"id": d["id"], "lang": d["lang"], "expect": d["expect"]})
        print("made", d["id"])
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
