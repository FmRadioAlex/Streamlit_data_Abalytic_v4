import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client


supabase_config = st.secrets["supabase"]

SUPABASE_URL = supabase_config["url"]
SUPABASE_KEY = supabase_config["key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_data():
    res = supabase.table("data").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        df = pd.DataFrame(columns=["nick", "amount", "updated_at"])

    return df


def update_balance(nick, amount):
    existing = supabase.table("data").select("*").eq("nick", nick).execute()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if existing.data:
        current = existing.data[0]["amount"]
        new_amount = current + amount

        supabase.table("data").update({
            "amount": new_amount,
            "updated_at": now
        }).eq("nick", nick).execute()

    else:
        supabase.table("data").insert({
            "nick": nick,
            "amount": amount,
            "updated_at": now
        }).execute()


def log_action(user, action, nick="", amount=None):
    supabase.table("logs").insert({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "action": action,
        "nick": nick,
        "amount": amount
    }).execute()


st.set_page_config(page_title="Balance System", page_icon="💰")


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None


if not st.session_state.authenticated:
    nick = st.text_input("Name:")
    pwd = st.text_input("Password:", type="password")
  
    if st.button("Login"):
        users = st.secrets["database"]["users"]

        if nick in users and pwd == users[nick]:
            st.session_state.authenticated = True
            st.session_state.user = nick
            log_action(nick, "Login")
            st.rerun()
        else:
            st.error("❌ Wrong login")
    

    if st.button("Guest"):
        st.session_state.authenticated = True
        st.session_state.user = "Guest"
        st.rerun()
        

    st.stop()



if st.session_state.user != "Guest":
    
    df = load_data()

    all_nicks = df["nick"].dropna().tolist() if not df.empty else []

    tabs = st.tabs(["💰 Баланс", "📊 Статистика", "🧾 Логи"])


    with tabs[0]:
        st.write("User:", st.session_state.user)

        st.sidebar.subheader("➕ Update balance")

        with st.sidebar.form("add_form"):
            amount = st.number_input("Amount (+ / -)", value=0)

            nick = st.selectbox(
                "Nick (choose or type new)",
                options=all_nicks,
                accept_new_options=True
            )

            if st.form_submit_button("Apply"):
                update_balance(nick, amount)
                log_action(st.session_state.user, "Update", nick, amount)
                st.rerun()

        st.subheader("📋 Current balances")
        st.dataframe(df, hide_index=True)

        st.subheader("🗑️ Delete user")

        if not df.empty:
            selected = st.selectbox("Select nick", df["nick"])

            if st.button("Delete user"):
                supabase.table("data").delete().eq("nick", selected).execute()
                log_action(st.session_state.user, "Delete", selected)
                st.rerun()


    with tabs[1]:
        if not df.empty:
            col1, col2 = st.columns(2)

            col1.metric("Total balance", int(df["amount"].sum()))

            col2.image("https://media1.tenor.com/m/Y5CKgQyhMb8AAAAC/crying-dog-watery-eyes.gif")

            st.subheader("Balance per user")

            chart_df = df.sort_values("amount", ascending=False)
            st.bar_chart(chart_df.set_index("nick")["amount"])

            st.subheader("Leaderboard")

            st.dataframe(
                chart_df,
                hide_index=True
            )


    with tabs[2]:
        logs = supabase.table("logs").select("*").execute()
        logs_df = pd.DataFrame(logs.data)

        if not logs_df.empty:
            st.dataframe(logs_df.sort_values("time", ascending=False))

if st.session_state.user == "Guest":
    df = load_data()
    st.dataframe(df, hide_index=True)
