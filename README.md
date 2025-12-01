# Thai Invoice Generator

ระบบสร้างใบเสร็จรับเงินภาษาไทย (ไม่รวม VAT)

## Features
- อ่านข้อมูลสินค้าจากไฟล์ CSV (export_items.csv)
- ค้นหาและเลือกสินค้าด้วย VirtualSelect (รองรับการค้นหาแบบ real-time)
- เพิ่มสินค้าลงในรายการพร้อมระบุจำนวน
- สร้างใบเสร็จรับเงินแบบเต็มหน้ากระดาษ A4
- รองรับการพิมพ์ใบเสร็จ

## Installation

1. ติดตั้ง uv (ถ้ายังไม่มี):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. ติดตั้ง dependencies และ sync environment:
```bash
uv sync
```

3. ตรวจสอบไฟล์ export_items.csv อยู่ในโฟลเดอร์เดียวกับ main.py

## Usage

1. เริ่มต้นเซิร์ฟเวอร์:
```bash
uv run python main.py
```

หรือ
```bash
uv run uvicorn main:app --reload
```

2. เปิดเว็บเบราว์เซอร์ที่: http://localhost:8000

3. ขั้นตอนการใช้งาน:
   - เลือกสินค้าจาก dropdown (สามารถค้นหาได้)
   - กรอกจำนวนสินค้า
   - คลิก "เพิ่มสินค้า"
   - เมื่อเลือกสินค้าครบแล้ว คลิก "สร้างใบเสร็จรับเงิน"
   - ใบเสร็จจะเปิดในหน้าต่างใหม่ พร้อมปุ่มพิมพ์

## CSV Format

ไฟล์ export_items.csv ต้องมีคอลัมน์:
- SKU: รหัสสินค้า
- Name: ชื่อสินค้า (ภาษาไทย)
- Price [okbooks]: ราคาสินค้า

## Technology Stack
- **Backend**: Python FastAPI
- **Frontend**: HTML, CSS, jQuery
- **Select Component**: VirtualSelect.js
- **Template Engine**: Jinja2

## Project Structure
```
invoice-generator/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── export_items.csv        # Product database
├── templates/
│   ├── index.html         # Main interface
│   └── invoice.html       # Invoice template
├── static/                # Static files (if needed)
└── README.md
```

## License
MIT