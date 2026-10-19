
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

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="Daily Money",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users.json"
DATA_DIR = BASE_DIR / "user_data"
DATA_DIR.mkdir(exist_ok=True)

# =====================================
# CSS DESIGN
# =====================================

st.markdown("""
<style>
.stApp {
    background: #f0f5fb;
    color: #303747;
}
.block-container {
    max-width: 560px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.hero {
    display: none;
}
.auth-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 24px 18px;
    box-shadow: 0 5px 24px rgba(40, 55, 90, 0.04);
    border: none;
}
div[data-testid="stTabs"] button {
    font-weight: 600;
}
div[data-testid="stTextInput"] input {
    background: #f3f6fa;
    border: 1px solid transparent;
    border-radius: 10px;
    min-height: 48px;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #6576ed;
    box-shadow: 0 0 0 1px #6576ed;
}
div.stButton > button,
div.stFormSubmitButton > button {
    border-radius: 10px;
    min-height: 48px;
    font-weight: 600;
}
div.stFormSubmitButton > button {
    background: #6576ed;
    color: white;
    border: none;
}
div.stFormSubmitButton > button:hover {
    background: #5365dc;
    color: white;
}
div[data-testid="stAlert"] {
    border-radius: 10px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px;
}
footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# =====================================
# USER ACCOUNTS
# =====================================
def load_users():
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        st.error("อ่านไฟล์ users.json ไม่สำเร็จ กรุณาตรวจสอบไฟล์")
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
        actual = hash_password(password, record["salt"])
        return hmac.compare_digest(actual, record["password_hash"])
    except (KeyError, TypeError):
        return False

def transaction_path(username):
    filename = hashlib.sha256(
        username.lower().encode("utf-8")
    ).hexdigest()
    return DATA_DIR / f"{filename}.csv"

# =====================================
# TRANSACTION DATA
# =====================================
COLUMNS = ["วันที่", "ประเภท", "หมวดหมู่", "รายละเอียด", "จำนวนเงิน"]

def load_transactions(username):
    path = transaction_path(username)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)

    try:
        df = pd.read_csv(path)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""

        df["รายละเอียด"] = df["รายละเอียด"].fillna("").astype(str)
        df["จำนวนเงิน"] = pd.to_numeric(
            df["จำนวนเงิน"], errors="coerce"
        ).fillna(0)
        return df[COLUMNS]
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame(columns=COLUMNS)

def save_transactions(username, df):
    df.to_csv(
        transaction_path(username),
        index=False,
        encoding="utf-8-sig"
    )

# =====================================
# MATH CAPTCHA
# =====================================
def new_captcha():
    operation = random.choice(["+", "-", "×"])

    if operation == "+":
        a, b = random.randint(5, 50), random.randint(5, 50)
        answer = a + b
    elif operation == "-":
        a = random.randint(10, 50)
        b = random.randint(1, a)
        answer = a - b
    else:
        a, b = random.randint(2, 12), random.randint(2, 9)
        answer = a * b

    st.session_state.math_captcha = {
        "question": f"{a} {operation} {b} = ?",
        "answer": str(answer)
    }

def ensure_captcha():
    if "math_captcha" not in st.session_state:
        new_captcha()

def check_captcha(answer):
    ensure_captcha()
    return (
        answer.strip().isdigit()
        and answer.strip() == st.session_state.math_captcha["answer"]
    )

# =====================================
# SESSION
# =====================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

# =====================================
# HEADER
# =====================================
st.markdown("""
<div class="hero">
    <div class="hero-title">💰 Daily Money</div>
    <div class="hero-subtitle">
        จัดการรายรับรายจ่ายในแต่ละวันได้ง่าย ๆ
    </div>
</div>
""", unsafe_allow_html=True)

# =====================================
# AUTH PAGES
# =====================================

if not st.session_state.logged_in:
    left, center, right = st.columns([0.2, 3, 0.2])

    with center:
        st.markdown(
            """
            <div style="text-align:center; padding: 4px 0 18px;">
                <div style="font-size:28px; font-weight:750; color:#303747;">
                    💰 Daily Money
                </div>
                <div style="color:#818a9b; font-size:14px; margin-top:4px;">
                    จัดการเงินของคุณให้ง่ายขึ้น
                </div>
            </div>
            <hr style="border:0; border-top:1px solid #e5eaf3;">
            """,
            unsafe_allow_html=True
        )

        login_tab, signup_tab = st.tabs(
            ["🔐 เข้าสู่ระบบ", "📝 สมัครสมาชิก"]
        )

        with login_tab:
            st.subheader("ยินดีต้อนรับกลับ!")

            ensure_captcha()

            with st.form("login_form"):
                login_username = st.text_input(
                    "ชื่อผู้ใช้",
                    placeholder="กรอกชื่อผู้ใช้ของคุณ"
                )
                login_password = st.text_input(
                    "รหัสผ่าน",
                    type="password",
                    placeholder="กรอกรหัสผ่านของคุณ"
                )

                st.info(
                    "🧮 แก้โจทย์: "
                    + st.session_state.math_captcha["question"]
                )

                login_answer = st.text_input(
                    "คำตอบ CAPTCHA",
                    placeholder="พิมพ์คำตอบ"
                )

                login_submit = st.form_submit_button(
                    "เข้าสู่ระบบ",
                    use_container_width=True
                )

            if st.button(
                "🔄 เปลี่ยนโจทย์",
                key="login_refresh",
                use_container_width=True
            ):
                new_captcha()
                st.rerun()

            if login_submit:
                if not check_captcha(login_answer):
                    new_captcha()
                    st.session_state.login_message = (
                        "คำตอบ CAPTCHA ไม่ถูกต้อง กรุณาลองใหม่"
                    )
                    st.rerun()
                else:
                    users = load_users()
                    key = login_username.strip().lower()
                    record = users.get(key)

                    if record and verify_password(login_password, record):
                        st.session_state.logged_in = True
                        st.session_state.username = key
                        st.session_state.pop("math_captcha", None)
                        st.session_state.pop("login_message", None)
                        st.rerun()
                    else:
                        new_captcha()
                        st.session_state.login_message = (
                            "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
                        )
                        st.rerun()

            if st.session_state.get("login_message"):
                st.error(st.session_state.login_message)

        with signup_tab:
            st.subheader("สร้างบัญชีใหม่")

            ensure_captcha()

            with st.form("signup_form"):
                signup_username = st.text_input(
                    "ตั้งชื่อผู้ใช้",
                    placeholder="ชื่อผู้ใช้ 4–20 ตัว"
                )
                signup_password = st.text_input(
                    "ตั้งรหัสผ่าน",
                    type="password",
                    placeholder="อย่างน้อย 8 ตัวอักษร"
                )
                signup_confirm = st.text_input(
                    "ยืนยันรหัสผ่าน",
                    type="password",
                    placeholder="กรอกรหัสผ่านอีกครั้ง"
                )

                st.info(
                    "🧮 แก้โจทย์: "
                    + st.session_state.math_captcha["question"]
                )

                signup_answer = st.text_input(
                    "คำตอบ CAPTCHA",
                    placeholder="พิมพ์คำตอบ"
                )

                signup_submit = st.form_submit_button(
                    "สมัครสมาชิก",
                    use_container_width=True
                )

            if st.button(
                "🔄 เปลี่ยนโจทย์",
                key="signup_refresh",
                use_container_width=True
            ):
                new_captcha()
                st.rerun()

            if signup_submit:
                if not check_captcha(signup_answer):
                    new_captcha()
                    st.session_state.signup_message = (
                        "คำตอบ CAPTCHA ไม่ถูกต้อง กรุณาลองใหม่"
                    )
                    st.rerun()
                else:
                    clean_username = signup_username.strip()
                    key = clean_username.lower()
                    users = load_users()
                    error = None

                    if not re.fullmatch(
                        r"[A-Za-z0-9_]{4,20}", clean_username
                    ):
                        error = "ชื่อผู้ใช้ต้องมี 4–20 ตัว ใช้ภาษาอังกฤษ ตัวเลข หรือ _"
                    elif key in users:
                        error = "ชื่อผู้ใช้นี้ถูกใช้แล้ว"
                    elif len(signup_password) < 8:
                        error = "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"
                    elif signup_password != signup_confirm:
                        error = "รหัสผ่านทั้งสองช่องไม่ตรงกัน"

                    if error:
                        st.session_state.signup_message = error
                        st.rerun()
                    else:
                        users[key] = make_password_record(signup_password)
                        save_users(users)
                        st.session_state.signup_message = (
                            "สมัครสมาชิกสำเร็จ! ไปที่แท็บเข้าสู่ระบบได้เลย"
                        )
                        st.session_state.pop("math_captcha", None)
                        st.rerun()

            if st.session_state.get("signup_message"):
                st.success(st.session_state.signup_message)

    st.stop()


# =====================================
# DASHBOARD
# =====================================
username = st.session_state.username

head_col, logout_col = st.columns([4, 1])
with head_col:
    st.subheader(f"สวัสดี, {username} 👋")
    st.caption("วันนี้มาจัดการเงินให้เป็นระเบียบกัน")
with logout_col:
    if st.button("ออกจากระบบ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

df = load_transactions(username)

# =====================================
# ADD TRANSACTION CARD
# =====================================
with st.container(border=True):
    st.subheader("➕ เพิ่มรายการ")

    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            tx_date = st.date_input("วันที่", value=date.today())
            tx_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย"])
            tx_category = st.selectbox(
                "หมวดหมู่",
                [
                    "อาหาร", "เดินทาง", "การเรียน", "ของใช้",
                    "เงินเดือน/ค่าขนม", "ความบันเทิง", "อื่น ๆ"
                ]
            )

        with col2:
            tx_amount = st.number_input(
                "จำนวนเงิน (บาท)", min_value=0.01, step=1.0
            )
            tx_detail = st.text_input("รายละเอียด (ไม่บังคับ)")

        add_submit = st.form_submit_button(
            "💾 บันทึกรายการ", use_container_width=True
        )

    if add_submit:
        new_row = pd.DataFrame([{
            "วันที่": tx_date.isoformat(),
            "ประเภท": tx_type,
            "หมวดหมู่": tx_category,
            "รายละเอียด": tx_detail.strip(),
            "จำนวนเงิน": float(tx_amount)
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        save_transactions(username, df)
        st.success("บันทึกรายการเรียบร้อย!")
        st.rerun()

# =====================================
# SUMMARY CARDS
# =====================================
income = df.loc[df["ประเภท"] == "รายรับ", "จำนวนเงิน"].sum()
expense = df.loc[df["ประเภท"] == "รายจ่าย", "จำนวนเงิน"].sum()
balance = income - expense

st.subheader("📊 ภาพรวมการเงิน")
c1, c2, c3 = st.columns(3)
c1.metric("💵 รายรับรวม", f"฿{income:,.2f}")
c2.metric("🛍️ รายจ่ายรวม", f"฿{expense:,.2f}")
c3.metric("💰 คงเหลือ", f"฿{balance:,.2f}")

# =====================================
# EXPENSE CHART
# =====================================
with st.container(border=True):
    st.subheader("📈 สัดส่วนรายจ่าย")

    expense_df = df[df["ประเภท"] == "รายจ่าย"].copy()

    if not expense_df.empty:
        totals = expense_df.groupby(
            "หมวดหมู่", as_index=False
        )["จำนวนเงิน"].sum()

        fig = px.pie(
            totals,
            names="หมวดหมู่",
            values="จำนวนเงิน",
            hole=0.48
        )
        fig.update_layout(
            margin=dict(t=15, b=15, l=10, r=10),
            legend_title_text="หมวดหมู่"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายจ่ายสำหรับแสดงกราฟ")

# =====================================
# HISTORY
# =====================================
with st.container(border=True):
    st.subheader("📋 ประวัติรายการ")

    if df.empty:
        st.info("ยังไม่มีรายการ ลองเพิ่มรายการแรกของคุณได้เลย")
    else:
        shown_df = df.copy()
        shown_df["จำนวนเงิน"] = shown_df["จำนวนเงิน"].map(
            lambda value: f"฿{value:,.2f}"
        )
        st.dataframe(
            shown_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ ดาวน์โหลดประวัติ CSV",
            data=df.to_csv(
                index=False, encoding="utf-8-sig"
            ).encode("utf-8-sig"),
            file_name="daily_money.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("✏️ แก้ไขหรือลบรายการ")

        selected_index = st.selectbox(
            "เลือกรายการที่ต้องการจัดการ",
            options=list(df.index),
            format_func=lambda i: (
                f"{df.loc[i, 'วันที่']} | "
                f"{df.loc[i, 'ประเภท']} | "
                f"{df.loc[i, 'หมวดหมู่']} | "
                f"฿{float(df.loc[i, 'จำนวนเงิน']):,.2f}"
            )
        )

        selected = df.loc[selected_index]

        with st.form("edit_form"):
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
                "อาหาร", "เดินทาง", "การเรียน", "ของใช้",
                "เงินเดือน/ค่าขนม", "ความบันเทิง", "อื่น ๆ"
            ]
            current_category = str(selected["หมวดหมู่"])
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
            edit_submit = st.form_submit_button(
                "บันทึกการแก้ไข", use_container_width=True
            )

        if edit_submit:
            df["รายละเอียด"] = df["รายละเอียด"].fillna("").astype(object)
            df.loc[selected_index, "วันที่"] = edit_date.isoformat()
            df.loc[selected_index, "ประเภท"] = edit_type
            df.loc[selected_index, "หมวดหมู่"] = edit_category
            df.loc[selected_index, "จำนวนเงิน"] = float(edit_amount)
            df.loc[selected_index, "รายละเอียด"] = edit_detail.strip()
            save_transactions(username, df)
            st.success("แก้ไขรายการเรียบร้อย!")
            st.rerun()

        if st.button("🗑️ ลบรายการที่เลือก"):
            df = df.drop(index=selected_index).reset_index(drop=True)
            save_transactions(username, df)
            st.success("ลบรายการเรียบร้อย!")
            st.rerun()

st.markdown(
    "<div style='text-align:center;color:#8791a3;padding:25px 0;'>"
    "💚 Daily Money · วางแผนเงินของคุณในทุกวัน"
    "</div>",
    unsafe_allow_html=True
)
