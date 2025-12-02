# Thai Invoice Generator

ระบบสร้างใบเสร็จรับเงินภาษาไทย (ไม่รวม VAT) พร้อมระบบจัดเก็บและค้นหา

## Features
- อ่านข้อมูลสินค้าจากไฟล์ CSV (export_items.csv)
- ค้นหาและเลือกสินค้าด้วย VirtualSelect (รองรับการค้นหาแบบ real-time)
- เพิ่มสินค้าลงในรายการพร้อมระบุจำนวน
- **จัดการข้อมูลผู้ขาย** (ชื่อร้าน, ที่อยู่, เลขประจำตัวผู้เสียภาษี, เบอร์โทรศัพท์)
- **ระบบเลขที่ใบเสร็จอัตโนมัติ** ในรูปแบบ "เลขรัน/ปีพ.ศ." (เช่น 001/2567, 002/2567)
- **บันทึกใบเสร็จลง SQLite database** อัตโนมัติ
- **ค้นหาและดูใบเสร็จย้อนหลัง** ด้วยเลขที่ใบเสร็จ, ชื่อลูกค้า หรือวันที่
- สร้างใบเสร็จรับเงินแบบเต็มหน้ากระดาษ A4 พร้อมข้อมูลผู้ขายและผู้ซื้อครบถ้วน
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

   **แท็บ "สร้างใบเสร็จ":**
   - กรอกข้อมูลผู้ซื้อ (ชื่อ, ที่อยู่, เลขประจำตัวผู้เสียภาษี)
   - เลือกสินค้าจาก dropdown (สามารถค้นหาได้)
   - กรอกจำนวนสินค้า
   - คลิก "เพิ่มสินค้า"
   - เมื่อเลือกสินค้าครบแล้ว คลิก "สร้างใบเสร็จรับเงิน"
   - ใบเสร็จจะถูกบันทึกลงฐานข้อมูลพร้อมเลขที่ใบเสร็จอัตโนมัติ
   - ใบเสร็จจะเปิดในหน้าต่างใหม่ พร้อมปุ่มพิมพ์
   
   **แท็บ "ข้อมูลผู้ขาย":**
   - กรอกข้อมูลร้านค้า/ผู้ขาย
   - คลิก "บันทึกข้อมูลผู้ขาย"
   - ข้อมูลจะถูกใช้ในใบเสร็จทุกฉบับ
   
   **แท็บ "ค้นหาใบเสร็จ":**
   - กรอกคำค้นหา (เลขที่ใบเสร็จ, ชื่อลูกค้า หรือวันที่)
   - คลิกปุ่ม "ดูใบเสร็จ" เพื่อเปิดใบเสร็จในหน้าต่างใหม่

## Database

ระบบใช้ SQLite database (`invoices.db`) เพื่อจัดเก็บ:
- **seller_info**: ข้อมูลผู้ขาย/ร้านค้า
- **invoices**: ข้อมูลใบเสร็จทั้งหมด
- **invoice_items**: รายการสินค้าในแต่ละใบเสร็จ

ฐานข้อมูลจะถูกสร้างอัตโนมัติเมื่อรันโปรแกรมครั้งแรก

## CSV Format

ไฟล์ export_items.csv ต้องมีคอลัมน์:
- SKU: รหัสสินค้า
- Name: ชื่อสินค้า (ภาษาไทย)
- Price [okbooks]: ราคาสินค้า

ไฟล์ customer.csv (ถ้ามี) ต้องมีคอลัมน์:
- Name: ชื่อลูกค้า
- Address: ที่อยู่ลูกค้า
- Tax ID: เลขประจำตัวผู้เสียภาษี

## Technology Stack
- **Backend**: Python FastAPI
- **Database**: SQLite3
- **Frontend**: HTML, CSS, jQuery
- **Select Component**: VirtualSelect.js
- **Template Engine**: Jinja2

## Project Structure
```
invoice-generator/
├── main.py                 # FastAPI application
├── database.py             # Database models and functions
├── invoices.db             # SQLite database (auto-generated)
├── export_items.csv        # Product database
├── customer.csv            # Customer database (optional)
├── pyproject.toml          # Project dependencies (uv)
├── uv.lock                 # Lock file
├── templates/
│   ├── index.html         # Main interface with tabs
│   └── invoice.html       # Invoice template
├── static/                # Static files
└── README.md
```

## Invoice Number Format

เลขที่ใบเสร็จจะถูกสร้างอัตโนมัติในรูปแบบ: **เลขรัน/ปีพ.ศ.**

ตัวอย่าง:
- 001/2567
- 002/2567
- 003/2567
- ...
- 001/2568 (เริ่มเลขรันใหม่เมื่อเปลี่ยนปี)

## Deployment to Railway

This project is ready to deploy on Railway's free tier:

### Quick Deploy

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Railway**:
   - Visit [railway.app](https://railway.app) and sign up/login
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will automatically detect the configuration and deploy
   - Your app will be available at `https://your-app-name.up.railway.app`

### Configuration Files

The following files have been added for Railway compatibility:

- **requirements.txt**: Python dependencies for Railway
- **railway.toml**: Railway-specific configuration
- **Procfile**: Process configuration for web service
- **.dockerignore**: Files to exclude from deployment

### Database Persistence

The SQLite database (`invoices.db`) will be stored in Railway's persistent volume. Your invoice data will be preserved across deployments.

### Environment Variables

No additional environment variables are required. The app automatically uses Railway's `PORT` variable.

### Monitoring

After deployment, you can:
- View logs in the Railway dashboard
- Monitor resource usage
- Set up custom domains (if needed)

### Important Notes

- Railway's free tier includes $5/month credit
- The database is persisted automatically
- CSV files (`export_items.csv`, `customer.csv`) must be committed to the repository

## License
MIT