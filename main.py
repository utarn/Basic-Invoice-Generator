from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Load items from CSV
def load_items():
    items = []
    csv_path = Path("export_items.csv")
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            try:
                # Get SKU, Name, and Price
                sku = row.get('SKU', '').strip()
                name = row.get('Name', '').strip()
                price_str = row.get('Price [okbooks]', '0').strip()
                
                # Parse price
                try:
                    price = float(price_str) if price_str else 0.0
                except ValueError:
                    price = 0.0
                
                # Only include items with valid data
                if sku and name and price > 0:
                    items.append({
                        'sku': sku,
                        'name': name,
                        'price': price
                    })
            except Exception as e:
                continue
    
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

# Global caches
ITEMS_CACHE = load_items()
CUSTOMERS_CACHE = load_customers()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/items")
async def get_items():
    return JSONResponse(content=ITEMS_CACHE)

@app.get("/api/customers")
async def get_customers():
    return JSONResponse(content=CUSTOMERS_CACHE)

@app.post("/api/generate-invoice")
async def generate_invoice(request: Request):
    data = await request.json()
    invoice_items = data.get('items', [])
    customer_info = data.get('customer', {})
    
    # Calculate totals
    total = sum(item['price'] * item['quantity'] for item in invoice_items)
    
    # Generate invoice HTML
    invoice_html = templates.TemplateResponse(
        "invoice.html",
        {
            "request": request,
            "items": invoice_items,
            "total": total,
            "customer": customer_info,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
    )
    
    return invoice_html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)