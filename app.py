
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
import secrets
import hmac
import random
import re
from pathlib import Path
from datetime import date

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Daily Money",
    page_icon="💰",
    layout="wide"
)

# =========================
# PATHS
# =========================
BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users.json"
DATA_DIR = BASE_DIR / "user_data"
DATA_DIR.mkdir(exist_ok=True)

# =========================
# STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f5f7ff, #eefbf5);
}
h1, h2, h3 {
    color: #243b53;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5eaf0;
    padding: 18px;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
}
div.stButton > button {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# USER STORAGE
# =========================
def load_users():
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        300000
    ).hex()

def make_password_record(password):
    salt = secrets.token_hex(16)
    return {
        "salt": salt,
        "password_hash": hash_password(password, salt)
    }

def verify_password(password, record):
    try:
        expected = record["password_hash"]
        actual = hash_password(password, record["salt"])
        return hmac.compare_digest(actual, expected)
    except (KeyError, TypeError):
        return False

def user_data_file(username):
    safe_name = hashlib.sha256(
        username.lower().encode("utf-8")
    ).hexdigest()
    return DATA_DIR / f"{safe_name}.csv"

# =========================
# TRANSACTIONS
# =========================
COLUMNS = [
    "วันที่", "ประเภท", "หมวดหมู่", "รายละเอียด", "จำนวนเงิน"
]

def load_transactions(username):
    path = user_data_file(username)

    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)

    try:
        df = pd.read_csv(path)
        for column in COLUMNS:
            if column not in df.columns:
                df[column] = ""
        df["รายละเอียด"] = df["รายละเอียด"].fillna("").astype(str)
        df["จำนวนเงิน"] = pd.to_numeric(
            df["จำนวนเงิน"], errors="coerce"
        ).fillna(0)
        return df[COLUMNS]
    except (OSError, pd.errors.ParserError, ValueError):
        return pd.DataFrame(columns=COLUMNS)

def save_transactions(username, df):
    df.to_csv(
        user_data_file(username),
        index=False,
        encoding="utf-8-sig"
    )

# =========================
# MATH CAPTCHA
# =========================
def new_captcha():
    operation = random.choice(["+", "-", "×"])

    if operation == "+":
        a = random.randint(5, 50)
        b = random.randint(5, 50)
        answer = a + b
    elif operation == "-":
        a = random.randint(10, 50)
        b = random.randint(1, a)
        answer = a - b
    else:
        a = random.randint(2, 12)
        b = random.randint(2, 9)
        answer = a * b

    st.session_state.math_captcha = {
        "question": f"{a} {operation} {b} = ?",
        "answer": str(answer)
    }

def ensure_captcha():
    if "math_captcha" not in st.session_state:
        new_captcha()

def check_captcha(user_answer):
    ensure_captcha()
    return (
        user_answer.strip().isdigit()
        and user_answer.strip()
        == st.session_state.math_captcha["answer"]
    )

# =========================
# SESSION STATE
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

# =========================
# HEADER
# =========================
st.title("💰 Daily Money")
st.caption("จัดการรายรับรายจ่ายในแต่ละวันได้ง่าย ๆ")

# =========================
# LOGIN / SIGNUP
# =========================
if not st.session_state.logged_in:
    login_tab, signup_tab = st.tabs([
        "🔐 เข้าสู่ระบบ",
        "📝 สมัครสมาชิก"
    ])

    with login_tab:
        st.subheader("ยินดีต้อนรับสมาซิก")

        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้")
            password = st.text_input(
                "รหัสผ่าน", type="password"
            )

            ensure_captcha()
            st.info(
                "🧮 แก้โจทย์: "
                + st.session_state.math_captcha["question"]
            )

            login_answer = st.text_input("คำตอบ CAPTCHA")
            submitted = st.form_submit_button(
                "เข้าสู่ระบบ",
                use_container_width=True
            )

        if submitted:
            if not check_captcha(login_answer):
                new_captcha()
                st.error("คำตอบ CAPTCHA ไม่ถูกต้อง ลองโจทย์ใหม่ได้เลย")
            else:
                users = load_users()
                key = username.strip().lower()
                record = users.get(key)

                if record and verify_password(password, record):
                    st.session_state.logged_in = True
                    st.session_state.username = key
                    st.session_state.pop("math_captcha", None)
                    st.rerun()
                else:
                    new_captcha()
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        if st.button("🔄 เปลี่ยนโจทย์ CAPTCHA", key="login_refresh"):
            new_captcha()
            st.rerun()

    with signup_tab:
        st.subheader("สร้างบัญชีใหม่")

        with st.form("signup_form"):
            new_username = st.text_input("ตั้งชื่อผู้ใช้")
            new_password = st.text_input(
                "ตั้งรหัสผ่าน", type="password"
            )
            confirm_password = st.text_input(
                "ยืนยันรหัสผ่าน", type="password"
            )

            ensure_captcha()
            st.info(
                "🧮 แก้โจทย์: "
                + st.session_state.math_captcha["question"]
            )

            signup_answer = st.text_input("คำตอบ CAPTCHA")
            signup_submitted = st.form_submit_button(
                "สมัครสมาชิก",
                use_container_width=True
            )

        if signup_submitted:
            if not check_captcha(signup_answer):
                new_captcha()
                st.error("คำตอบ CAPTCHA ไม่ถูกต้อง ลองใหม่อีกครั้ง")
            else:
                clean_username = new_username.strip()
                key = clean_username.lower()
                users = load_users()

                if not re.fullmatch(
                    r"[A-Za-z0-9_]{4,20}", clean_username
                ):
                    st.error(
                        "ชื่อผู้ใช้ต้องมี 4–20 ตัว "
                        "ใช้เฉพาะภาษาอังกฤษ ตัวเลข และ _"
                    )
                elif key in users:
                    st.error("ชื่อผู้ใช้นี้ถูกใช้แล้ว")
                elif len(new_password) < 8:
                    st.error("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
                elif new_password != confirm_password:
                    st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                else:
                    users[key] = make_password_record(new_password)
                    save_users(users)
                    st.success("สมัครสมาชิกสำเร็จ! ไปที่แท็บเข้าสู่ระบบได้เลย")
                    st.session_state.pop("math_captcha", None)
                    st.rerun()

        if st.button("🔄 เปลี่ยนโจทย์ CAPTCHA", key="signup_refresh"):
            new_captcha()
            st.rerun()

    st.stop()

# =========================
# DASHBOARD
# =========================
username = st.session_state.username

top_left, top_right = st.columns([3, 1])
with top_left:
    st.subheader(f"สวัสดี, {username} 👋")
with top_right:
    if st.button("ออกจากระบบ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.pop("math_captcha", None)
        st.rerun()

df = load_transactions(username)

# =========================
# ADD TRANSACTION
# =========================
with st.container(border=True):
    st.subheader("➕ เพิ่มรายการ")

    with st.form("add_transaction_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            transaction_date = st.date_input(
                "วันที่", value=date.today()
            )
            transaction_type = st.selectbox(
                "ประเภท", ["รายรับ", "รายจ่าย"]
            )
            category = st.selectbox(
                "หมวดหมู่",
                [
                    "อาหาร", "เดินทาง", "การเรียน",
                    "ของใช้", "เงินเดือน/ค่าขนม",
                    "ความบันเทิง", "อื่น ๆ"
                ]
            )

        with col2:
            amount = st.number_input(
                "จำนวนเงิน (บาท)",
                min_value=0.01,
                step=1.0
            )
            detail = st.text_input("รายละเอียด (ไม่บังคับ)")

        add_submitted = st.form_submit_button(
            "บันทึกรายการ",
            use_container_width=True
        )

    if add_submitted:
        new_row = pd.DataFrame([{
            "วันที่": transaction_date.isoformat(),
            "ประเภท": transaction_type,
            "หมวดหมู่": category,
            "รายละเอียด": detail.strip(),
            "จำนวนเงิน": float(amount)
        }])

        df = pd.concat([df, new_row], ignore_index=True)
        save_transactions(username, df)
        st.success("บันทึกรายการเรียบร้อย!")
        st.rerun()

# =========================
# SUMMARY
# =========================
income = df.loc[df["ประเภท"] == "รายรับ", "จำนวนเงิน"].sum()
expense = df.loc[df["ประเภท"] == "รายจ่าย", "จำนวนเงิน"].sum()
balance = income - expense

st.subheader("📊 ภาพรวมการเงิน")

c1, c2, c3 = st.columns(3)
c1.metric("💵 รายรับรวม", f"฿{income:,.2f}")
c2.metric("🛍️ รายจ่ายรวม", f"฿{expense:,.2f}")
c3.metric("💰 คงเหลือ", f"฿{balance:,.2f}")

# =========================
# CHART
# =========================
with st.container(border=True):
    st.subheader("📈 สัดส่วนรายจ่าย")

    expense_df = df[df["ประเภท"] == "รายจ่าย"].copy()

    if not expense_df.empty:
        category_totals = (
            expense_df.groupby("หมวดหมู่", as_index=False)
            ["จำนวนเงิน"].sum()
        )

        fig = px.pie(
            category_totals,
            names="หมวดหมู่",
            values="จำนวนเงิน",
            hole=0.45
        )
        fig.update_layout(
            margin=dict(t=20, b=20, l=10, r=10),
            legend_title_text="หมวดหมู่"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายจ่ายสำหรับแสดงกราฟ")

# =========================
# TRANSACTION HISTORY
# =========================
with st.container(border=True):
    st.subheader("📋 ประวัติรายการ")

    if df.empty:
        st.info("ยังไม่มีรายการ ลองเพิ่มรายรับหรือรายจ่ายรายการแรกดูนะ")
    else:
        display_df = df.copy()
        display_df["จำนวนเงิน"] = display_df["จำนวนเงิน"].map(
            lambda x: f"฿{x:,.2f}"
        )
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        csv_data = df.to_csv(
            index=False, encoding="utf-8-sig"
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ ดาวน์โหลดประวัติเป็น CSV",
            data=csv_data,
            file_name="daily_money_transactions.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("✏️ แก้ไขหรือลบรายการ")

        selected_index = st.selectbox(
            "เลือกรายการ",
            options=list(df.index),
            format_func=lambda i: (
                f"{df.loc[i, 'วันที่']} | "
                f"{df.loc[i, 'ประเภท']} | "
                f"{df.loc[i, 'หมวดหมู่']} | "
                f"฿{float(df.loc[i, 'จำนวนเงิน']):,.2f}"
            )
        )

        selected = df.loc[selected_index]

        with st.form("edit_transaction_form"):
            edit_date = st.date_input(
                "วันที่",
                value=pd.to_datetime(selected["วันที่"]).date()
            )
            edit_type = st.selectbox(
                "ประเภท",
                ["รายรับ", "รายจ่าย"],
                index=0 if selected["ประเภท"] == "รายรับ" else 1
            )
            categories = [
                "อาหาร", "เดินทาง", "การเรียน",
                "ของใช้", "เงินเดือน/ค่าขนม",
                "ความบันเทิง", "อื่น ๆ"
            ]
            current_category = selected["หมวดหมู่"]
            if current_category not in categories:
                categories.append(current_category)

            edit_category = st.selectbox(
                "หมวดหมู่",
                categories,
                index=categories.index(current_category)
            )
            edit_amount = st.number_input(
                "จำนวนเงิน",
                min_value=0.01,
                value=max(0.01, float(selected["จำนวนเงิน"])),
                step=1.0
            )
            edit_detail = st.text_input(
                "รายละเอียด",
                value=str(selected["รายละเอียด"])
                if pd.notna(selected["รายละเอียด"]) else ""
            )

            update_submitted = st.form_submit_button(
                "บันทึกการแก้ไข",
                use_container_width=True
            )

        if update_submitted:
            df.loc[selected_index, "วันที่"] = edit_date.isoformat()
            df.loc[selected_index, "ประเภท"] = edit_type
            df.loc[selected_index, "หมวดหมู่"] = edit_category
            df.loc[selected_index, "จำนวนเงิน"] = float(edit_amount)
            df.loc[selected_index, "รายละเอียด"] = edit_detail.strip()
            save_transactions(username, df)
            st.success("แก้ไขรายการแล้ว")
            st.rerun()

        if st.button("🗑️ ลบรายการที่เลือก", type="secondary"):
            df = df.drop(index=selected_index).reset_index(drop=True)
            save_transactions(username, df)
            st.success("ลบรายการแล้ว")
            st.rerun()

st.caption("Daily Money • บันทึกรายรับรายจ่ายอย่างเป็นระบบ 💚")
