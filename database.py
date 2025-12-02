import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

DATABASE_PATH = "invoices.db"


def get_db_connection():
    """สร้างการเชื่อมต่อกับฐานข้อมูล"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """สร้างตารางในฐานข้อมูล"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ตารางข้อมูลผู้ขาย (ร้านค้า)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seller_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            shop_address TEXT NOT NULL,
            tax_id TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ตารางใบเสร็จ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            running_number INTEGER NOT NULL,
            buddhist_year INTEGER NOT NULL,
            invoice_date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            customer_tax_id TEXT,
            seller_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES seller_info (id)
        )
    """)
    
    # ตารางรายการสินค้าในใบเสร็จ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
        )
    """)
    
    # ตารางสินค้า (Items)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # สร้าง index สำหรับการค้นหาสินค้า
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_items_sku 
        ON items(sku)
    """)
    
    # สร้าง index สำหรับการค้นหา
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_invoice_number 
        ON invoices(invoice_number)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_invoice_date 
        ON invoices(invoice_date)
    """)
    
    conn.commit()
    conn.close()


def get_thai_buddhist_year() -> int:
    """คำนวณปีพุทธศักราช"""
    current_year = datetime.now().year
    return current_year + 543


def get_next_running_number(buddhist_year: int) -> int:
    """หาเลขรันถัดไปสำหรับปีนั้นๆ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MAX(running_number) as max_number 
        FROM invoices 
        WHERE buddhist_year = ?
    """, (buddhist_year,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result['max_number'] is None:
        return 1
    return result['max_number'] + 1


def generate_invoice_number() -> Tuple[str, int, int]:
    """สร้างเลขที่ใบเสร็จในรูปแบบ เลขรัน/ปีพ.ศ."""
    buddhist_year = get_thai_buddhist_year()
    running_number = get_next_running_number(buddhist_year)
    invoice_number = f"{running_number:03d}/{buddhist_year}"
    
    return invoice_number, running_number, buddhist_year


# ==================== Seller Info Functions ====================

def get_seller_info(seller_id: int = 1) -> Optional[Dict]:
    """ดึงข้อมูลผู้ขาย"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM seller_info WHERE id = ?
    """, (seller_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None


def get_or_create_default_seller() -> Dict:
    """ดึงหรือสร้างข้อมูลผู้ขายเริ่มต้น"""
    seller = get_seller_info(1)
    
    if seller is None:
        # สร้างข้อมูลเริ่มต้น
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO seller_info (shop_name, shop_address, tax_id, phone)
            VALUES (?, ?, ?, ?)
        """, (
            "ชื่อร้าน",
            "ที่อยู่ร้าน",
            "0000000000000",
            "000-000-0000"
        ))
        
        conn.commit()
        seller_id = cursor.lastrowid
        conn.close()
        
        seller = get_seller_info(seller_id)
    
    return seller


def update_seller_info(seller_id: int, shop_name: str, shop_address: str, 
                       tax_id: str, phone: str) -> bool:
    """อัปเดตข้อมูลผู้ขาย"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE seller_info 
            SET shop_name = ?, shop_address = ?, tax_id = ?, phone = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (shop_name, shop_address, tax_id, phone, seller_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        conn.close()
        print(f"Error updating seller info: {e}")
        return False


# ==================== Invoice Functions ====================

def save_invoice(customer_info: Dict, items: List[Dict], 
                seller_id: int = 1) -> Optional[Dict]:
    """บันทึกใบเสร็จลงฐานข้อมูล"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # สร้างเลขที่ใบเสร็จ
        invoice_number, running_number, buddhist_year = generate_invoice_number()
        
        # คำนวณยอดรวม
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        # บันทึกใบเสร็จ
        invoice_date = datetime.now().strftime("%d/%m/%Y")
        
        cursor.execute("""
            INSERT INTO invoices 
            (invoice_number, running_number, buddhist_year, invoice_date,
             customer_name, customer_address, customer_tax_id, seller_id, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_number,
            running_number,
            buddhist_year,
            invoice_date,
            customer_info['name'],
            customer_info['address'],
            customer_info.get('tax_id', ''),
            seller_id,
            total_amount
        ))
        
        invoice_id = cursor.lastrowid
        
        # บันทึกรายการสินค้า
        for item in items:
            subtotal = item['price'] * item['quantity']
            cursor.execute("""
                INSERT INTO invoice_items 
                (invoice_id, sku, name, price, quantity, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item['sku'],
                item['name'],
                item['price'],
                item['quantity'],
                subtotal
            ))
        
        conn.commit()
        
        # ดึงข้อมูลใบเสร็จที่สร้างขึ้น
        invoice = get_invoice_by_id(invoice_id)
        conn.close()
        
        return invoice
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error saving invoice: {e}")
        return None


def get_invoice_by_id(invoice_id: int) -> Optional[Dict]:
    """ดึงข้อมูลใบเสร็จตาม ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ดึงข้อมูลใบเสร็จ
    cursor.execute("""
        SELECT i.*, s.shop_name, s.shop_address, s.tax_id as seller_tax_id, s.phone
        FROM invoices i
        JOIN seller_info s ON i.seller_id = s.id
        WHERE i.id = ?
    """, (invoice_id,))
    
    invoice_row = cursor.fetchone()
    
    if not invoice_row:
        conn.close()
        return None
    
    invoice = dict(invoice_row)
    
    # ดึงรายการสินค้า
    cursor.execute("""
        SELECT * FROM invoice_items WHERE invoice_id = ?
    """, (invoice_id,))
    
    items = [dict(row) for row in cursor.fetchall()]
    invoice['items'] = items
    
    conn.close()
    return invoice


def get_invoice_by_number(invoice_number: str) -> Optional[Dict]:
    """ค้นหาใบเสร็จด้วยเลขที่ใบเสร็จ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM invoices WHERE invoice_number = ?
    """, (invoice_number,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return get_invoice_by_id(result['id'])
    return None


def search_invoices(query: str = "", limit: int = 50) -> List[Dict]:
    """ค้นหาใบเสร็จ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if query:
        cursor.execute("""
            SELECT i.*, s.shop_name
            FROM invoices i
            JOIN seller_info s ON i.seller_id = s.id
            WHERE i.invoice_number LIKE ? 
               OR i.customer_name LIKE ?
               OR i.invoice_date LIKE ?
            ORDER BY i.created_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
    else:
        cursor.execute("""
            SELECT i.*, s.shop_name
            FROM invoices i
            JOIN seller_info s ON i.seller_id = s.id
            ORDER BY i.created_at DESC
            LIMIT ?
        """, (limit,))
    
    invoices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return invoices


# ==================== Items Functions ====================

def get_all_items() -> List[Dict]:
    """ดึงรายการสินค้าทั้งหมด"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT sku, name, price FROM items ORDER BY sku
    """)
    
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return items


def get_items_count() -> int:
    """นับจำนวนสินค้าทั้งหมด"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM items")
    result = cursor.fetchone()
    conn.close()
    
    return result['count'] if result else 0


def clear_all_items() -> bool:
    """ลบสินค้าทั้งหมด"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM items")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        print(f"Error clearing items: {e}")
        return False


def import_items_from_csv(csv_content: str) -> Tuple[bool, int, str]:
    """นำเข้าสินค้าจาก CSV content
    
    Returns:
        Tuple of (success, count, message)
    """
    import csv
    import io
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ลบข้อมูลเก่าทั้งหมด
        cursor.execute("DELETE FROM items")
        
        # อ่าน CSV
        csv_file = io.StringIO(csv_content)
        csv_reader = csv.DictReader(csv_file)
        
        count = 0
        for row in csv_reader:
            try:
                sku = row.get('SKU', '').strip()
                name = row.get('Name', '').strip()
                price_str = row.get('Price [okbooks]', '0').strip()
                category = row.get('Category', '').strip()
                
                # Parse price
                try:
                    price = float(price_str) if price_str else 0.0
                except ValueError:
                    price = 0.0
                
                # Only include items with valid data
                if sku and name and price > 0:
                    cursor.execute("""
                        INSERT INTO items (sku, name, price, category)
                        VALUES (?, ?, ?, ?)
                    """, (sku, name, price, category))
                    count += 1
            except Exception as e:
                continue
        
        conn.commit()
        conn.close()
        
        return True, count, f"นำเข้าสินค้าสำเร็จ {count} รายการ"
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, 0, f"เกิดข้อผิดพลาด: {str(e)}"


# เริ่มต้นฐานข้อมูลเมื่อ import module
init_database()