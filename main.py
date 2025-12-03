from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from pydantic import BaseModel
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import os
import hashlib
import hmac
import database as db

# Authentication configuration
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD environment variable is required")

SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Skip authentication for login page and static files
        if request.url.path in ["/login", "/static/"] or request.url.path.startswith("/static/"):
            return await call_next(request)

        # Check for auth cookie
        auth_token = request.cookies.get("invoice_auth")
        if auth_token and self.verify_token(auth_token):
            return await call_next(request)

        # Redirect to login for protected routes
        if request.url.path == "/":
            return RedirectResponse(url="/login", status_code=302)

        # For API routes, return 401
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=401, detail="Authentication required")

        return RedirectResponse(url="/login", status_code=302)

    def verify_token(self, token: str) -> bool:
        try:
            expected_token = hmac.new(SECRET_KEY.encode(), ADMIN_PASSWORD.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(token, expected_token)
        except:
            return False

app = FastAPI(middleware=[Middleware(AuthMiddleware)])

def create_auth_token() -> str:
    return hmac.new(SECRET_KEY.encode(), ADMIN_PASSWORD.encode(), hashlib.sha256).hexdigest()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Load items from database (fallback to CSV for initial import)
def load_items():
    # Try to load from database first
    items = db.get_all_items()
    
    # If database is empty, try to import from CSV file
    if len(items) == 0:
        csv_path = Path("database/export_items.csv")
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_content = file.read()
                success, count, message = db.import_items_from_csv(csv_content)
                if success:
                    items = db.get_all_items()
    
    return items

# Load customers from CSV
def load_customers():
    customers = []
    csv_path = Path("customer.csv")
    
    if not csv_path.exists():
        return customers
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            try:
                name = row.get('Name', '').strip()
                address = row.get('Address', '').strip()
                tax_id = row.get('Tax ID', '').strip()
                
                if name:
                    customers.append({
                        'name': name,
                        'address': address,
                        'tax_id': tax_id
                    })
            except Exception as e:
                continue
    
    return customers

# Pydantic models for request validation
class SellerInfoUpdate(BaseModel):
    shop_name: str
    shop_address: str
    tax_id: str
    phone: str

class InvoiceCreate(BaseModel):
    items: List[Dict]
    customer: Dict

# Global caches
ITEMS_CACHE = load_items()
CUSTOMERS_CACHE = load_customers()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/", status_code=302)
        auth_token = create_auth_token()
        response.set_cookie(
            key="invoice_auth",
            value=auth_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        return response
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid password"
        })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="invoice_auth")
    return response

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/items")
async def get_items():
    # Load fresh data from database
    items = db.get_all_items()
    return JSONResponse(content=items)

@app.get("/api/customers")
async def get_customers():
    return JSONResponse(content=CUSTOMERS_CACHE)

# ==================== Seller Info Endpoints ====================

@app.get("/api/seller")
async def get_seller():
    """ดึงข้อมูลผู้ขาย"""
    seller = db.get_or_create_default_seller()
    return JSONResponse(content=seller)

@app.put("/api/seller/{seller_id}")
async def update_seller(seller_id: int, seller_data: SellerInfoUpdate):
    """อัปเดตข้อมูลผู้ขาย"""
    success = db.update_seller_info(
        seller_id,
        seller_data.shop_name,
        seller_data.shop_address,
        seller_data.tax_id,
        seller_data.phone
    )
    
    if success:
        seller = db.get_seller_info(seller_id)
        return JSONResponse(content=seller)
    else:
        raise HTTPException(status_code=400, detail="Failed to update seller info")

# ==================== Items Endpoints ====================

@app.get("/api/items/count")
async def get_items_count():
    """ดึงจำนวนสินค้าทั้งหมด"""
    count = db.get_items_count()
    return JSONResponse(content={"count": count})

@app.post("/api/items/upload")
async def upload_items(file: UploadFile = File(...)):
    """อัปโหลดไฟล์ CSV สินค้า"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="กรุณาอัปโหลดไฟล์ CSV เท่านั้น")
    
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        success, count, message = db.import_items_from_csv(csv_content)
        
        if success:
            return JSONResponse(content={
                "success": True,
                "count": count,
                "message": message
            })
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="ไฟล์ CSV ไม่ถูกต้อง กรุณาตรวจสอบ encoding (ต้องเป็น UTF-8)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")

# ==================== Invoice Endpoints ====================

@app.post("/api/generate-invoice")
async def generate_invoice(request: Request):
    """สร้างและบันทึกใบเสร็จ"""
    data = await request.json()
    invoice_items = data.get('items', [])
    customer_info = data.get('customer', {})
    
    # บันทึกใบเสร็จลงฐานข้อมูล
    saved_invoice = db.save_invoice(customer_info, invoice_items)
    
    if not saved_invoice:
        raise HTTPException(status_code=500, detail="Failed to save invoice")
    
    # ดึงข้อมูลผู้ขาย
    seller = db.get_seller_info(saved_invoice['seller_id'])
    
    # Calculate totals
    total = saved_invoice['total_amount']
    
    # Generate invoice HTML
    invoice_html = templates.TemplateResponse(
        "invoice.html",
        {
            "request": request,
            "invoice_number": saved_invoice['invoice_number'],
            "items": invoice_items,
            "total": total,
            "customer": customer_info,
            "seller": seller,
            "date": saved_invoice['invoice_date']
        }
    )
    
    return invoice_html

@app.get("/api/invoices/search")
async def search_invoices_endpoint(query: str = "", limit: int = 50):
    """ค้นหาใบเสร็จ"""
    invoices = db.search_invoices(query, limit)
    return JSONResponse(content=invoices)

@app.get("/api/invoices/view", response_class=HTMLResponse)
async def view_invoice(request: Request, number: str, year: str):
    """แสดงใบเสร็จในรูปแบบ HTML"""
    import sys
    invoice_number = f"{number}/{year}"
    print(f"[DEBUG] Received number={number}, year={year}", file=sys.stderr)
    print(f"[DEBUG] Constructed invoice_number={invoice_number}", file=sys.stderr)
    sys.stderr.flush()
    
    invoice = db.get_invoice_by_number(invoice_number)
    print(f"[DEBUG] Invoice result: {invoice is not None}", file=sys.stderr)
    sys.stderr.flush()
    
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_number}")

    # เตรียมข้อมูลสำหรับเทมเพลต
    seller = {
        'shop_name': invoice['shop_name'],
        'shop_address': invoice['shop_address'],
        'tax_id': invoice['seller_tax_id'],
        'phone': invoice['phone']
    }

    customer = {
        'name': invoice['customer_name'],
        'address': invoice['customer_address'],
        'tax_id': invoice.get('customer_tax_id', '')
    }

    return templates.TemplateResponse(
        "invoice.html",
        {
            "request": request,
            "invoice_number": invoice['invoice_number'],
            "items": invoice['items'],
            "total": invoice['total_amount'],
            "customer": customer,
            "seller": seller,
            "date": invoice['invoice_date']
        }
    )

@app.get("/api/invoices/{invoice_number}")
async def get_invoice(invoice_number: str):
    """ดึงข้อมูลใบเสร็จด้วยเลขที่ใบเสร็จ"""
    invoice = db.get_invoice_by_number(invoice_number)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return JSONResponse(content=invoice)

@app.get("/api/test-db")
async def test_db():
    """Test database connection"""
    invoice = db.get_invoice_by_number("001/2568")
    return JSONResponse(content={"found": invoice is not None, "invoice": invoice})

@app.get("/api/test-debug")
async def test_debug():
    """Test if debug code is loaded"""
    import sys
    print("[DEBUG] Test debug endpoint called!", file=sys.stderr)
    sys.stderr.flush()
    return JSONResponse(content={"debug": "working", "timestamp": str(datetime.now())})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)