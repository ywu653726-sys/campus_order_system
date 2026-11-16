from datetime import datetime
import sqlite3
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(
    title="校園小吃線上點餐系統 API",
    description="Asia University Campus Snack Ordering System",
    version="1.0.0",
)


# --- 資料庫初始化函式 ---
def init_db():
  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            is_available INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # 2. 加上這段：建立 orders 訂單表格（為了取消訂單功能）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            status TEXT DEFAULT '訂單成立'
        )
    """)

  conn.commit()
  conn.close()


@app.on_event("startup")
def startup_event():
  init_db()


# --- Pydantic 請求資料驗證模型 ---
class MenuItemCreate(BaseModel):
  name: str
  price: int
  is_available: int = 1


# --- 1. GET 路由：取得所有開放中的餐點 ---
@app.get("/menus", summary="列出所有開放中的餐點與價格")
def get_menus():
  conn = sqlite3.connect("shop.db")
  conn.row_factory = sqlite3.Row
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM menu WHERE is_available = 1")
  rows = cursor.fetchall()
  conn.close()
  return {"status": "success", "data": [dict(row) for row in rows]}


# --- 2. POST 路由：新增餐點 ---
@app.post(
    "/menus",
    status_code=status.HTTP_201_CREATED,
    summary="新增一筆餐點項目",
)
def create_menu_item(item: MenuItemCreate):
  if item.price <= 0:
    raise HTTPException(status_code=400, detail="餐點價格必須大於 0")

  created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  conn = sqlite3.connect("shop.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO menu (name, price, is_available, created_at)
        VALUES (?, ?, ?, ?)
    """,
      (item.name, item.price, item.is_available, created_at),
  )
  conn.commit()
  new_id = cursor.lastrowid
  conn.close()

  return {
      "status": "success",
      "message": "餐點新增成功",
      "data": {
          "id": new_id,
          "name": item.name,
          "price": item.price,
          "is_available": item.is_available,
          "created_at": created_at,
      },
  }

# --- 3. DELETE 路由：取消訂單 ---
@app.delete("/orders/{order_id}")
def cancel_order(order_id: int):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    
    # 檢查該筆訂單是否存在
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="找不到指定的訂單")
    
    # 執行刪除
    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    
    return {"ok": True, "message": f"成功取消訂單編號 {order_id}"}
