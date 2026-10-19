
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
import secrets
import hmac
import re
from pathlib import Path
from datetime import date

# =========================
# ตั้งค่าหน้าเว็บ
# =========================
st.set_page_config(
    page_title="Daily Money",
    page_icon="💰",
    layout="wide",
)

st.markdown("""
<style>
    .block-container {
        max-width: 1250px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.3px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px;
        border-color: #DCE3ED;
    }

    div[data-testid="stMetric"] {
        background: #F7F9FC;
        border: 1px solid #E5EAF2;
        border-radius: 12px;
        padding: 15px;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
    }

    .small-note {
        color: #64748b;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# ไฟล์และข้อมูล
# =========================
USERS_FILE = Path("users.json")
DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)

COLUMNS = ["วันที่", "ประเภท", "หมวดหมู่", "จำนวนเงิน", "รายละเอียด"]
CATEGORIES = [
    "เงินค่าขนม", "เงินเดือน", "อาหาร",
    "เดินทาง", "การเรียน", "ช้อปปิ้ง", "อื่น ๆ"
]

def load_users():
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            result = json.load(f)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def user_data_path(username):
    # ใช้ชื่อไฟล์ที่ไม่เปิดเผยชื่อผู้ใช้โดยตรง
    safe_name = hashlib.sha256(username.lower().encode()).hexdigest()
    return DATA_DIR / f"{safe_name}.csv"

def empty_data():
    return pd.DataFrame(columns=COLUMNS)

def load_transactions(username):
    path = user_data_path(username)

    if not path.exists():
        return empty_data()

    try:
        data = pd.read_csv(path, encoding="utf-8-sig")
        for col in COLUMNS:
            if col not in data.columns:
                data[col] = ""

        data = data[COLUMNS].copy()
        data["วันที่"] = pd.to_datetime(
            data["วันที่"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        data["จำนวนเงิน"] = pd.to_numeric(
            data["จำนวนเงิน"], errors="coerce"
        ).fillna(0.0)
        data["รายละเอียด"] = data["รายละเอียด"].fillna("").astype(str)
        data["ประเภท"] = data["ประเภท"].fillna("รายจ่าย").astype(str)
        data["หมวดหมู่"] = data["หมวดหมู่"].fillna("อื่น ๆ").astype(str)
        return data

    except (OSError, ValueError, pd.errors.ParserError):
        st.error("อ่านไฟล์รายการไม่ได้ กรุณาตรวจสอบไฟล์ CSV")
        return empty_data()

def save_transactions(data, username):
    output = data.copy()
    output = output.reindex(columns=COLUMNS)
    output["รายละเอียด"] = output["รายละเอียด"].fillna("").astype(str)
    output.to_csv(
        user_data_path(username),
        index=False,
        encoding="utf-8-sig"
    )

# =========================
# รหัสผ่าน
# =========================
def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        300000
    ).hex()

def valid_password(password, salt, expected_hash):
    actual_hash = hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)

# =========================
# สถานะผู้ใช้และ CAPTCHA
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "captcha" not in st.session_state:
    st.session_state.captcha = "".join(
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for _ in range(5)
    )

def new_captcha():
    st.session_state.captcha = "".join(
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for _ in range(5)
    )

# =========================
# สมัครสมาชิก / เข้าสู่ระบบ
# =========================
def auth_page():
    st.markdown(
        "<h1 style='text-align:center'>💰 Daily Money</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center;color:#64748b'>"
        "ผู้ช่วยจัดการรายรับ–รายจ่ายของคุณ</p>",
        unsafe_allow_html=True
    )

    left, center, right = st.columns([1, 1.5, 1])

    with center:
        with st.container(border=True):
            login_tab, signup_tab = st.tabs(
                ["🔐 เข้าสู่ระบบ", "📝 สมัครสมาชิก"]
            )

            with login_tab:
                st.subheader("ยินดีต้อนรับสมาซิก")

                with st.form("login_form"):
                    login_username = st.text_input("ชื่อผู้ใช้")
                    login_password = st.text_input(
                        "รหัสผ่าน", type="password"
                    )

                    st.caption(
                        f"CAPTCHA: **{st.session_state.captcha}**"
                    )
                    login_captcha = st.text_input(
                        "พิมพ์รหัส CAPTCHA"
                    )

                    login_submit = st.form_submit_button(
                        "เข้าสู่ระบบ", use_container_width=True
                    )

                if login_submit:
                    users = load_users()
                    key = login_username.strip().lower()
                    user = users.get(key)

                    captcha_ok = hmac.compare_digest(
                        login_captcha.strip().upper(),
                        st.session_state.captcha
                    )
                    new_captcha()

                    if not captcha_ok:
                        st.error("CAPTCHA ไม่ถูกต้อง กรุณาลองใหม่")
                    elif not user:
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    elif not valid_password(
                        login_password,
                        user["salt"],
                        user["password_hash"]
                    ):
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.username = key
                        st.rerun()

                if st.button("🔄 เปลี่ยน CAPTCHA", key="refresh_login"):
                    new_captcha()
                    st.rerun()

            with signup_tab:
                st.subheader("สร้างบัญชีใหม่")

                with st.form("signup_form"):
                    new_username = st.text_input(
                        "ชื่อผู้ใช้ (4–20 ตัวอักษร)"
                    )
                    new_password = st.text_input(
                        "รหัสผ่าน (อย่างน้อย 8 ตัวอักษร)",
                        type="password"
                    )
                    confirm_password = st.text_input(
                        "ยืนยันรหัสผ่าน", type="password"
                    )

                    st.caption(
                        f"CAPTCHA: **{st.session_state.captcha}**"
                    )
                    signup_captcha = st.text_input(
                        "พิมพ์รหัส CAPTCHA"
                    )

                    signup_submit = st.form_submit_button(
                        "สมัครสมาชิก", use_container_width=True
                    )

                if signup_submit:
                    users = load_users()
                    key = new_username.strip().lower()

                    captcha_ok = hmac.compare_digest(
                        signup_captcha.strip().upper(),
                        st.session_state.captcha
                    )
                    new_captcha()

                    if not captcha_ok:
                        st.error("CAPTCHA ไม่ถูกต้อง กรุณาลองใหม่")
                    elif not re.fullmatch(
                        r"[a-zA-Z0-9_]{4,20}", new_username.strip()
                    ):
                        st.error(
                            "ชื่อผู้ใช้ต้องมี 4–20 ตัว "
                            "ใช้ภาษาอังกฤษ ตัวเลข หรือ _ เท่านั้น"
                        )
                    elif len(new_password) < 8:
                        st.error("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
                    elif new_password != confirm_password:
                        st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                    elif key in users:
                        st.error("ชื่อผู้ใช้นี้ถูกใช้แล้ว")
                    else:
                        salt = secrets.token_hex(16)
                        users[key] = {
                            "salt": salt,
                            "password_hash": hash_password(
                                new_password, salt
                            )
                        }
                        save_users(users)
                        st.success(
                            "สมัครสมาชิกสำเร็จ ไปที่แท็บเข้าสู่ระบบได้เลย"
                        )
                        st.rerun()

                if st.button(
                    "🔄 เปลี่ยน CAPTCHA", key="refresh_signup"
                ):
                    new_captcha()
                    st.rerun()

# =========================
# หน้า Dashboard
# =========================
def dashboard():
    username = st.session_state.username

    header_col, logout_col = st.columns([5, 1])
    with header_col:
        st.title("💰 Daily Money")
        st.caption(f"สวัสดี, {username} — จัดการเงินของคุณได้ที่นี่")

    with logout_col:
        if st.button("ออกจากระบบ", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    data = load_transactions(username)
    data = data.reset_index(drop=True)

    data["จำนวนเงิน"] = pd.to_numeric(
        data["จำนวนเงิน"], errors="coerce"
    ).fillna(0.0)
    data["รายละเอียด"] = data["รายละเอียด"].fillna("").astype(str)

    total_income = data.loc[
        data["ประเภท"] == "รายรับ", "จำนวนเงิน"
    ].sum()

    total_expense = data.loc[
        data["ประเภท"] == "รายจ่าย", "จำนวนเงิน"
    ].sum()

    balance = total_income - total_expense

    # ----- การ์ดภาพรวม -----
    with st.container(border=True):
        st.subheader("📊 ภาพรวมการเงิน")
        c1, c2, c3 = st.columns(3)

        c1.metric("💚 รายรับรวม", f"{total_income:,.2f} บาท")
        c2.metric("💗 รายจ่ายรวม", f"{total_expense:,.2f} บาท")
        c3.metric("💵 เงินคงเหลือ", f"{balance:,.2f} บาท")

    # ----- การ์ดเพิ่มรายการ -----
    with st.container(border=True):
        st.subheader("📝 เพิ่มรายการ")

        with st.form("add_transaction", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                add_day = st.date_input("วันที่", value=date.today())
                add_kind = st.selectbox(
                    "ประเภท", ["รายรับ", "รายจ่าย"]
                )
                add_category = st.selectbox(
                    "หมวดหมู่", CATEGORIES
                )

            with col2:
                add_amount = st.number_input(
                    "จำนวนเงิน (บาท)", min_value=0.01,
                    value=100.0, step=10.0
                )
                add_detail = st.text_input("รายละเอียด")

            add_submit = st.form_submit_button(
                "➕ บันทึกรายการ", use_container_width=True
            )

        if add_submit:
            new_row = pd.DataFrame([{
                "วันที่": add_day.isoformat(),
                "ประเภท": add_kind,
                "หมวดหมู่": add_category,
                "จำนวนเงิน": float(add_amount),
                "รายละเอียด": add_detail.strip()
            }])

            data = pd.concat([data, new_row], ignore_index=True)
            save_transactions(data, username)
            st.success("บันทึกรายการเรียบร้อยแล้ว")
            st.rerun()

    # ----- การ์ดประวัติ -----
    with st.container(border=True):
        st.subheader("🧾 ประวัติรายรับ–รายจ่าย")

        if data.empty:
            st.info("ยังไม่มีรายการ ลองเพิ่มรายการแรกได้เลย")
        else:
            history = data.copy()
            history["จำนวนเงิน"] = history["จำนวนเงิน"].map(
                lambda x: f"{x:,.2f}"
            )

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "📥 ดาวน์โหลดรายงาน CSV",
                data=data.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="daily_money_report.csv",
                mime="text/csv",
                use_container_width=True
            )

    # ----- การ์ดกราฟ -----
    with st.container(border=True):
        st.subheader("📈 แผนภูมิวงกลมรายจ่ายประจำเดือน")

        chart_data = data.copy()
        chart_data["วันที่"] = pd.to_datetime(
            chart_data["วันที่"], errors="coerce"
        )

        valid_dates = chart_data["วันที่"].dropna()

        if valid_dates.empty:
            st.info("เพิ่มรายการที่มีวันที่ เพื่อเริ่มดูกราฟ")
        else:
            months = sorted(
                valid_dates.dt.to_period("M").unique(),
                reverse=True
            )

            selected_month = st.selectbox(
                "เลือกเดือน",
                months,
                format_func=lambda m: m.strftime("%m/%Y"),
                key="chart_month"
            )

            monthly_expenses = chart_data[
                (chart_data["วันที่"].dt.to_period("M") == selected_month)
                & (chart_data["ประเภท"] == "รายจ่าย")
            ].copy()

            if monthly_expenses.empty:
                st.info("เดือนนี้ยังไม่มีรายการรายจ่าย")
            else:
                summary = (
                    monthly_expenses.groupby("หมวดหมู่")["จำนวนเงิน"]
                    .sum()
                    .reset_index()
                    .sort_values("จำนวนเงิน", ascending=False)
                )

                st.metric(
                    "รายจ่ายรวมประจำเดือน",
                    f"{summary['จำนวนเงิน'].sum():,.2f} บาท"
                )

                fig = px.pie(
                    summary,
                    names="หมวดหมู่",
                    values="จำนวนเงิน",
                    hole=0.35,
                    title="สัดส่วนรายจ่ายตามหมวดหมู่"
                )
                fig.update_traces(
                    textposition="inside",
                    textinfo="label+percent",
                    hovertemplate=(
                        "%{label}<br>%{value:,.2f} บาท"
                        "<br>%{percent}<extra></extra>"
                    )
                )
                fig.update_layout(
                    height=380,
                    margin=dict(t=60, b=20, l=20, r=20),
                    legend_title_text="หมวดหมู่"
                )
                st.plotly_chart(
                    fig, use_container_width=True
                )

                st.dataframe(
                    summary,
                    use_container_width=True,
                    hide_index=True
                )

    # ----- การ์ดแก้ไขและลบ -----
    with st.container(border=True):
        st.subheader("✏️ แก้ไขหรือลบรายการ")

        if data.empty:
            st.info("ยังไม่มีรายการให้แก้ไขหรือลบ")
        else:
            options = list(range(len(data)))

            def item_label(i):
                row = data.iloc[i]
                return (
                    f"{i + 1}. {row['วันที่']} | {row['ประเภท']} | "
                    f"{row['รายละเอียด']} | "
                    f"{row['จำนวนเงิน']:,.2f} บาท"
                )

            selected = st.selectbox(
                "เลือกรายการ",
                options,
                format_func=item_label,
                key="edit_selected"
            )

            row = data.iloc[selected]

            with st.form("edit_transaction"):
                st.markdown("#### แก้ไขรายละเอียด")

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

                old_category = str(row["หมวดหมู่"])
                category_index = (
                    CATEGORIES.index(old_category)
                    if old_category in CATEGORIES
                    else len(CATEGORIES) - 1
                )

                edit_category = st.selectbox(
                    "หมวดหมู่",
                    CATEGORIES,
                    index=category_index
                )

                edit_amount = st.number_input(
                    "จำนวนเงิน (บาท)",
                    min_value=0.01,
                    value=max(float(row["จำนวนเงิน"]), 0.01),
                    step=10.0
                )

                edit_detail = st.text_input(
                    "รายละเอียด",
                    value=str(row["รายละเอียด"])
                )

                update = st.form_submit_button(
                    "💾 บันทึกการแก้ไข",
                    use_container_width=True
                )

            if update:
                data.loc[selected, "วันที่"] = edit_day.isoformat()
                data.loc[selected, "ประเภท"] = edit_kind
                data.loc[selected, "หมวดหมู่"] = edit_category
                data.loc[selected, "จำนวนเงิน"] = float(edit_amount)
                data.loc[selected, "รายละเอียด"] = edit_detail

                save_transactions(data, username)
                st.success("แก้ไขรายการเรียบร้อยแล้ว")
                st.rerun()

            st.divider()
            confirm_delete = st.checkbox(
                "ฉันยืนยันว่าต้องการลบรายการที่เลือก"
            )

            if st.button(
                "🗑️ ลบรายการที่เลือก",
                type="secondary",
                use_container_width=True
            ):
                if confirm_delete:
                    data = data.drop(index=selected).reset_index(drop=True)
                    save_transactions(data, username)
                    st.success("ลบรายการเรียบร้อยแล้ว")
                    st.rerun()
                else:
                    st.warning("กรุณาติ๊กยืนยันก่อนลบรายการ")

# =========================
# เริ่มต้นแอป
# =========================
if st.session_state.logged_in:
    dashboard()
else:
    auth_page()
