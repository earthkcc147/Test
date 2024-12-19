import os
import json
import requests
from dotenv import load_dotenv, set_key

# โหลดค่าจากไฟล์ .env
load_dotenv()

# อ่านค่าจาก .env
API_URL = os.getenv("API_URL")
USERS_JSON = os.getenv("USERS")
API_KEY = os.getenv("API_KEY")  # คีย์ API สำหรับเชื่อมต่อกับ API ใหม่
API_CHECK_SERVICE_URL = API_URL

# แปลงข้อมูล USERS_JSON เป็น dictionary
try:
    users_data = json.loads(USERS_JSON)
except json.JSONDecodeError:
    print("ไม่สามารถแปลงข้อมูล USERS จาก .env ได้ ❌")
    exit()

# รับ username และ password จากผู้ใช้
username = input("กรุณากรอก Username: ")
password = input("กรุณากรอก Password: ")

# ตรวจสอบ username และ password
if username not in users_data or users_data[username]['password'] != password:
    print("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง ❌")
    exit()

# ดึงข้อมูลผู้ใช้ปัจจุบัน
current_user = users_data[username]
api_key = current_user['api_key']
products = current_user['products']
BL = float(current_user['BL'])  # ใช้ยอดเงินจากไฟล์ .env โดยตรง (เปลี่ยนจาก balance เป็น BL)

print(f"ยินดีต้อนรับ {username}! ✅")

# ฟังก์ชันดึงยอดเงินจาก API
def get_balance(api_k):
    # เนื่องจากเราไม่ต้องการดึงยอดเงินจาก API อีกต่อไป
    return BL  # คืนยอดเงินที่เก็บไว้ในไฟล์ .env

# ฟังก์ชันดึงข้อมูลอัตราค่าบริการจาก API
def get_service_rate():
    try:
        response = requests.post(API_CHECK_SERVICE_URL, data={'key': API_KEY, 'action': 'services'})
        if response.status_code == 200:
            services_data = response.json()
            return {service['service']: float(service['rate']) for service in services_data}
        else:
            print("ไม่สามารถเชื่อมต่อกับ API เพื่อตรวจสอบอัตราค่าบริการ ❌")
            return {}
    except requests.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e} ❌")
        return {}

# ฟังก์ชันการสั่งซื้อสินค้า
def place_order(category, product_key, quantity, link):
    global BL  # อ้างอิงถึงตัวแปร BL ที่อยู่ภายนอกฟังก์ชัน
    product = products[category][product_key]
    min_quantity = product['min_quantity']
    max_quantity = product['max_quantity']

    # ตรวจสอบว่าจำนวนสินค้าที่เลือกอยู่ในช่วงที่อนุญาต
    if quantity < min_quantity or quantity > max_quantity:
        print(f"จำนวนสินค้าต้องอยู่ระหว่าง {min_quantity} ถึง {max_quantity} ชิ้น ❌")
        return

    total_price = round(product['price_per_unit'] * quantity, 2)

    # ดึงข้อมูลอัตราค่าบริการจาก API
    service_rates = get_service_rate()
    if not service_rates:
        print("ไม่สามารถดึงข้อมูลอัตราค่าบริการจาก API ได้ ❌")
        return

    # ตรวจสอบว่าอัตราค่าบริการที่ได้จาก API สามารถนำไปคำนวณราคาจริงได้หรือไม่
    if product['service'] not in service_rates:
        print(f"บริการที่เลือกไม่มีอัตราค่าบริการ ❌")
        return

    service_rate = service_rates[product['service']]
    adjusted_price = round(total_price * service_rate, 2)

    # ตรวจสอบว่าราคาที่ปรับแล้วเพียงพอกับยอดเงินใน BL หรือไม่
    if adjusted_price > BL:
        print(f"ยอดเงินไม่เพียงพอในการซื้อสินค้า {product['description']} ❌")
        return

    # แสดงรายละเอียดการสั่งซื้อให้ผู้ใช้ยืนยัน
    print(f"\n--- รายละเอียดการสั่งซื้อ ---")
    print(f"สินค้า: {product['description']}")
    print(f"จำนวนที่เลือก: {quantity} ชิ้น")
    print(f"ราคาต่อหน่วย: {product['price_per_unit']:.2f} บาท")
    print(f"ราคาทั้งหมด: {total_price:.2f} บาท")
    print(f"ราคาหลังจากอัตราค่าบริการ: {adjusted_price:.2f} บาท")
    print(f"ลิงก์ที่กรอก: {link}")
    print(f"ยอดเงินที่คุณมี: {BL:.2f} บาท 💳")

    # การยืนยันการสั่งซื้อ
    confirm = input("คุณต้องการยืนยันการสั่งซื้อหรือไม่? (y/n): ").lower()
    if confirm != 'y':
        print("ยกเลิกการสั่งซื้อ ❌")
        return

    # ข้อมูลการสั่งซื้อที่ต้องการส่งไปยัง API
    data_order = {
        "key": api_key,
        "action": "add",
        "service": product['service'],
        "link": link,
        "quantity": quantity
    }

    try:
        response_order = requests.post(API_URL, data=data_order)
        if response_order.status_code == 200:
            order_data = response_order.json()
            if 'order' in order_data:
                remaining_BL = round(BL - adjusted_price, 2)
                print(f"การสั่งซื้อสำเร็จ! คำสั่งซื้อ ID: {order_data['order']} ✅")
                print(f"รวมราคาทั้งหมด: {adjusted_price:.2f} บาท 💵")
                print(f"ยอดเงินที่เหลือหลังจากการสั่งซื้อ: {remaining_BL:.2f} บาท 💳")

                # อัพเดต BL ในไฟล์ .env
                BL = remaining_BL
                set_key(".env", "USERS", json.dumps(users_data, ensure_ascii=False))  # อัพเดตข้อมูล USERS

                # อัพเดต BL ของผู้ใช้ในไฟล์ .env
                users_data[username]['BL'] = str(BL)
                set_key(".env", "USERS", json.dumps(users_data, ensure_ascii=False))

            else:
                print("การสั่งซื้อไม่สำเร็จ ❌")
        else:
            print("เกิดข้อผิดพลาดในการสั่งซื้อ ❌")
    except requests.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e} ❌")

# ฟังก์ชันเลือกสินค้า
def choose_product(category):
    if category not in products:
        print("ไม่มีสินค้าในหมวดหมู่นี้ ❌")
        return

    category_products = products[category]
    print("\n--- รายการสินค้า ---")
    for index, (product_name, details) in enumerate(category_products.items(), start=1):
        print(f"{index}. {details['description']} - ราคาต่อหน่วย: {details['price_per_unit']:.2f} บาท")
        print(f"   จำนวนขั้นต่ำ: {details['min_quantity']} - จำนวนสูงสุด: {details['max_quantity']}")

    print("0. ย้อนกลับ 🔙")

    choice = int(input("กรุณาเลือกสินค้าที่ต้องการ: "))
    if choice == 0:
        return

    if 1 <= choice <= len(category_products):
        product_key = list(category_products.keys())[choice - 1]
        product = category_products[product_key]
        print(f"คุณเลือก {product['description']}")

        min_quantity = product['min_quantity']
        max_quantity = product['max_quantity']
        price_per_unit = product['price_per_unit']
        print(f"จำนวนขั้นต่ำ: {min_quantity}, จำนวนสูงสุด: {max_quantity}")
        print(f"ราคาต่อหน่วย: {price_per_unit:.2f} บาท")

        link = input("กรุณากรอกลิงก์ที่ต้องการ: ")
        quantity = int(input(f"กรุณากรอกจำนวนที่ต้องการซื้อ (ระหว่าง {min_quantity} และ {max_quantity}): "))
        place_order(category, product_key, quantity, link)

# เมนูหลัก
def show_category_menu():
    print(f"\n--- เมนูหลัก --- ยอดเงิน: {BL:.2f} บาท 💳")
    print("1. Facebook")
    print("2. TikTok")
    print("3. Instagram")
    print("4. Discord")
    print("0. ออกจากโปรแกรม 🚪")

# ลูปหลัก
while True:
    show_category_menu()
    category_choice = int(input("กรุณาเลือกหมวดหมู่สินค้า: "))

    if category_choice == 0:
        print("ออกจากโปรแกรม 👋")
        break
    elif category_choice == 1:
        choose_product("facebook")
    elif category_choice == 2:
        choose_product("tiktok")
    elif category_choice == 3:
        choose_product("instagram")
    elif category_choice == 4:
        choose_product("discord")
    else:
        print("ตัวเลือกไม่ถูกต้อง ❌")