import streamlit as st
import pandas as pd
import json
import hashlib
import secrets
import hmac
import re
from pathlib import Path
from datetime import date

# -------------------------
# ตั้งค่าหน้าเว็บ
# -------------------------
st.set_page_config(
    page_title="Daily Money",
    page_icon="💰",
    layout="wide"
)

USERS_FILE = Path("users.json")
DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)

COLUMNS = [
    "วันที่", "ประเภท", "หมวดหมู่",
    "จำนวนเงิน", "รายละเอียด"
]

# -------------------------
# ระบบบัญชีผู้ใช้
# -------------------------
def load_users():
    if USERS_FILE.exists():
        try:
            return json.loads(
                USERS_FILE.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            st.error("อ่านไฟล์บัญชีผู้ใช้ไม่ได้ กรุณาตรวจสอบ users.json")
            st.stop()
    return {}


def save_users(users):
    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    result = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        300000
    )

    return salt, result.hex()


def verify_password(password, user):
    salt, expected = user["salt"], user["password_hash"]
    _, actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected)


def valid_username(username):
    return bool(re.fullmatch(r"[A-Za-z0-9_]{4,20}", username))


def user_data_file(username):
    # ใช้ชื่อไฟล์จากแฮช ไม่ใช้ username เป็น path โดยตรง
    key = hashlib.sha256(username.lower().encode()).hexdigest()
    return DATA_DIR / f"{key}.csv"


# -------------------------
# CAPTCHA สำหรับฝึกใช้งาน
# -------------------------
def new_captcha():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(5))


if "captcha" not in st.session_state:
    st.session_state.captcha = new_captcha()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


# -------------------------
# อ่านและบันทึกธุรกรรม
# -------------------------
def load_transactions(username):
    path = user_data_file(username)

    if path.exists():
        try:
            data = pd.read_csv(path)
            for column in COLUMNS:
                if column not in data.columns:
                    data[column] = ""
            data["จำนวนเงิน"] = pd.to_numeric(
                data["จำนวนเงิน"], errors="coerce"
            ).fillna(0)
            return data[COLUMNS]
        except (ValueError, OSError, pd.errors.ParserError):
            st.error("อ่านไฟล์รายการเงินไม่ได้")
            st.stop()

    return pd.DataFrame(columns=COLUMNS)


def save_transactions(data, username):
    data.to_csv(
        user_data_file(username),
        index=False,
        encoding="utf-8-sig"
    )


def calculate_total(data, kind):
    amounts = pd.to_numeric(
        data.loc[data["ประเภท"] == kind, "จำนวนเงิน"],
        errors="coerce"
    ).fillna(0)
    return amounts.sum()


# -------------------------
# หน้า Login / Sign up
# -------------------------
def auth_page():
    st.title("💰 Daily Money")
    st.write("เว็บบันทึกรายรับ–รายจ่ายส่วนตัว")
    st.subheader("ยินดีต้อนรับ")

    st.info(
        "Username ต้องมี 4–20 ตัวอักษร ใช้ภาษาอังกฤษ "
        "ตัวเลข หรือ _ เท่านั้น"
    )

    login_tab, signup_tab = st.tabs(
        ["🔑 Log in", "📝 Sign up"]
    )

    with login_tab:
        st.markdown("### เข้าสู่ระบบ")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input(
                "Password", type="password"
            )

            st.markdown("**CAPTCHA: พิมพ์รหัสด้านล่าง**")
            st.code(st.session_state.captcha)

            captcha_input = st.text_input(
                "รหัสยืนยัน", key="login_captcha_input"
            )

            login_button = st.form_submit_button(
                "Log in", use_container_width=True
            )

        if login_button:
            users = load_users()
            account = users.get(username.lower())

            captcha_ok = (
                captcha_input.strip().upper()
                == st.session_state.captcha
            )

            if not captcha_ok:
                st.error("CAPTCHA ไม่ถูกต้อง")
                st.session_state.captcha = new_captcha()
                st.rerun()

            if account and verify_password(password, account):
                st.session_state.logged_in = True
                st.session_state.username = username.lower()
                st.rerun()
            else:
                st.error("Username หรือ Password ไม่ถูกต้อง")
                st.session_state.captcha = new_captcha()
                st.rerun()

    with signup_tab:
        st.markdown("### สมัครสมาชิก")

        with st.form("signup_form"):
            new_username = st.text_input(
                "ตั้ง Username", key="signup_username"
            )
            new_password = st.text_input(
                "ตั้ง Password",
                type="password",
                key="signup_password"
            )
            confirm_password = st.text_input(
                "ยืนยัน Password",
                type="password",
                key="signup_confirm"
            )

            st.markdown("**CAPTCHA: พิมพ์รหัสด้านล่าง**")
            st.code(st.session_state.captcha)

            signup_captcha = st.text_input(
                "รหัสยืนยัน",
                key="signup_captcha_input"
            )

            signup_button = st.form_submit_button(
                "Sign up", use_container_width=True
            )

        if signup_button:
            users = load_users()
            normalized = new_username.strip().lower()

            if not valid_username(new_username.strip()):
                st.error(
                    "Username ต้องมี 4–20 ตัว "
                    "ใช้ A-Z, a-z, 0-9 หรือ _"
                )
            elif normalized in users:
                st.error("Username นี้มีผู้ใช้แล้ว")
            elif len(new_password) < 8:
                st.error("Password ต้องมีอย่างน้อย 8 ตัวอักษร")
            elif new_password != confirm_password:
                st.error("Password ทั้งสองช่องไม่ตรงกัน")
            elif signup_captcha.strip().upper() != st.session_state.captcha:
                st.error("CAPTCHA ไม่ถูกต้อง")
                st.session_state.captcha = new_captcha()
                st.rerun()
            else:
                salt, password_hash = hash_password(new_password)

                users[normalized] = {
                    "salt": salt,
                    "password_hash": password_hash
                }
                save_users(users)

                st.success(
                    "สมัครสมาชิกสำเร็จ! ไปที่ Log in เพื่อเข้าสู่ระบบ"
                )
                st.session_state.captcha = new_captcha()

    if st.button("🔄 เปลี่ยน CAPTCHA"):
        st.session_state.captcha = new_captcha()
        st.rerun()


# -------------------------
# หน้า Dashboard
# -------------------------
def dashboard():
    username = st.session_state.username

    top_left, top_right = st.columns([4, 1])
    top_left.title("💰 Daily Money")
    top_left.caption(f"เข้าสู่ระบบในชื่อ {username}")

    if top_right.button("Log out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    data = load_transactions(username)

    income = calculate_total(data, "รายรับ")
    expense = calculate_total(data, "รายจ่าย")
    balance = income - expense

    col1, col2, col3 = st.columns(3)
    col1.metric("💚 รายรับรวม", f"{income:,.2f} บาท")
    col2.metric("❤️ รายจ่ายรวม", f"{expense:,.2f} บาท")
    col3.metric("💵 เงินคงเหลือ", f"{balance:,.2f} บาท")

    st.divider()
    st.subheader("📝 เพิ่มรายการ")

    with st.form("add_transaction", clear_on_submit=True):
        day = st.date_input("วันที่", value=date.today())
        kind = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย"])
        category = st.selectbox(
            "หมวดหมู่",
            ["เงินค่าขนม", "เงินเดือน", "อาหาร",
             "เดินทาง", "การเรียน", "ช้อปปิ้ง", "อื่น ๆ"]
        )
        amount = st.number_input(
            "จำนวนเงิน (บาท)", min_value=0.01, value=1.0
        )
        detail = st.text_input("รายละเอียด")

        add = st.form_submit_button("บันทึกรายการ")

        if add:
            new_row = pd.DataFrame([{
                "วันที่": day.isoformat(),
                "ประเภท": kind,
                "หมวดหมู่": category,
                "จำนวนเงิน": amount,
                "รายละเอียด": detail
            }])

            data = pd.concat([data, new_row], ignore_index=True)
            save_transactions(data, username)
            st.success("บันทึกรายการแล้ว")
            st.rerun()

    st.divider()
    st.subheader("📋 ประวัติรายรับ–รายจ่าย")

    if data.empty:
        st.info("ยังไม่มีรายการ ลองเพิ่มรายการแรกได้เลย")
        return

    
    # ===== แผนภูมิวงกลมสรุปรายจ่ายประจำเดือน =====
    st.divider()
    st.subheader("📊 แผนภูมิวงกลมรายจ่ายประจำเดือน")

    chart_data = data.copy()
    chart_data["วันที่"] = pd.to_datetime(
        chart_data["วันที่"], errors="coerce"
    )
    chart_data["จำนวนเงิน"] = pd.to_numeric(
        chart_data["จำนวนเงิน"], errors="coerce"
    ).fillna(0)

    valid_dates = chart_data["วันที่"].dropna()

    if not valid_dates.empty:
        months = sorted(
            valid_dates.dt.to_period("M").unique(),
            reverse=True
        )

        selected_month = st.selectbox(
            "เลือกเดือน",
            months,
            format_func=lambda month: month.strftime("%m/%Y"),
            key="expense_chart_month"
        )

        monthly_data = chart_data[
            (chart_data["วันที่"].dt.to_period("M") == selected_month)
            & (chart_data["ประเภท"] == "รายจ่าย")
        ]

        if not monthly_data.empty:
            summary = monthly_data.groupby(
                "หมวดหมู่"
            )["จำนวนเงิน"].sum().sort_values(ascending=False)

            st.metric(
                "รายจ่ายรวมประจำเดือน",
                f"{summary.sum():,.2f} บาท"
            )

            st.plotly_chart(
                {
                    "data": [{
                        "type": "pie",
                        "labels": summary.index.tolist(),
                        "values": summary.values.tolist(),
                        "hole": 0,
                        "textinfo": "label+percent",
                        "hovertemplate":
                            "%{label}<br>%{value:,.2f} บาท"
                            "<br>%{percent}<extra></extra>"
                    }],
                    "layout": {
                        "title": "สัดส่วนรายจ่ายตามหมวดหมู่",
                        "height": 450
                    }
                },
                use_container_width=True
            )

            st.dataframe(
                summary.rename("จำนวนเงิน (บาท)"),
                use_container_width=True
            )
        else:
            st.info("เดือนนี้ยังไม่มีรายการรายจ่าย")
    else:
        st.info("ยังไม่มีวันที่สำหรับสร้างแผนภูมิ")

    data = data.reset_index(drop=True)
    st.write("จำนวนรายการทั้งหมด:", len(data))
    st.write("ข้อมูลที่โหลดมา:", data)
    options = list(range(len(data)))

    def item_label(i):
        row = data.iloc[i]
        return (
            f"{i + 1}. {row['วันที่']} | {row['ประเภท']} | "
            f"{row['รายละเอียด']} | {row['จำนวนเงิน']:,.2f} บาท"
        )

    selected = st.selectbox(
        "เลือกรายการเพื่อแก้ไขหรือลบ",
        options,
        format_func=item_label
    )

    row = data.iloc[selected]

    with st.form("edit_transaction"):
        st.markdown("### ✏️ แก้ไขรายการ")

        try:
            old_day = pd.to_datetime(row["วันที่"]).date()
        except (ValueError, TypeError):
            old_day = date.today()

        edit_day = st.date_input("วันที่", value=old_day)
        edit_kind = st.selectbox(
            "ประเภท",
            ["รายรับ", "รายจ่าย"],
            index=0 if row["ประเภท"] == "รายรับ" else 1
        )

        categories = [
            "เงินค่าขนม", "เงินเดือน", "อาหาร",
            "เดินทาง", "การเรียน", "ช้อปปิ้ง", "อื่น ๆ"
        ]
        old_category = str(row["หมวดหมู่"])
        category_index = (
            categories.index(old_category)
            if old_category in categories else len(categories) - 1
        )

        edit_category = st.selectbox(
            "หมวดหมู่", categories, index=category_index
        )
        edit_amount = st.number_input(
            "จำนวนเงิน (บาท)",
            min_value=0.01,
            value=max(float(row["จำนวนเงิน"]), 0.01)
        )
        edit_detail = st.text_input(
            "รายละเอียด",
            value="" if pd.isna(row["รายละเอียด"])
            else str(row["รายละเอียด"])
        )

        update = st.form_submit_button("บันทึกการแก้ไข")

        if update:
            data.loc[selected, "วันที่"] = edit_day.isoformat()
            data.loc[selected, "ประเภท"] = edit_kind
            data.loc[selected, "หมวดหมู่"] = edit_category
            data.loc[selected, "จำนวนเงิน"] = edit_amount
            data["รายละเอียด"] = data["รายละเอียด"].fillna("").astype(object)
            data.loc[selected, "รายละเอียด"] = edit_detail

            save_transactions(data, username)
            st.success("แก้ไขรายการแล้ว")
            st.rerun()

    if st.button("🗑️ ลบรายการที่เลือก"):
        data = data.drop(index=selected).reset_index(drop=True)
        save_transactions(data, username)
        st.success("ลบรายการแล้ว")
        st.rerun()

    st.divider()
    st.dataframe(
        data.sort_values("วันที่", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 ดาวน์โหลดรายงาน CSV",
        data=data.to_csv(index=False).encode("utf-8-sig"),
        file_name="รายรับรายจ่าย.csv",
        mime="text/csv"
    )


# -------------------------
# เรียกหน้าเว็บตามสถานะ
# -------------------------
if st.session_state.logged_in:
    dashboard()
else:
    auth_page()
