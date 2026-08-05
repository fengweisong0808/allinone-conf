import datetime
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="asTech/AIO Operation Dashboard", layout="wide")


# 2. Load and Preprocess Data
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 文件名已更新为 AIO data.xlsx
    file_path = os.path.join(current_dir, "AIO data.xlsx")

    df = pd.read_excel(file_path)

    short_names = {
        "ASTECH定制ALL IN ONE诊断配置(北美)": "ASTECH定制ALL IN ONE诊断配置(北美)",
        "asTech ALL-IN-ONE(4G)北美主机扩展配置": (
            "asTech ALL-IN-ONE(4G)北美主机扩展配置"
        ),
        "ASTECH定制海外SMARTLINK(维修端)诊断配置": (
            "ASTECH定制海外SMARTLINK(维修端)诊断配置"
        ),
        "asTech 定制ALL-IN-ONE(4G)北美诊断配置（SMARTLINK 1.0）": (
            "asTech 定制ALL-IN-ONE(4G)北美诊断配置（SMARTLINK 1.0）"
        ),
        "asTech 定制ALL-IN-ONE(4G)北美诊断配置（SMARTLINK2.0）": (
            "asTech 定制ALL-IN-ONE(4G)北美诊断配置（SMARTLINK2.0）"
        ),
        "ASTECH定制海外SMARTLINK B(服务端)诊断配置": (
            "ASTECH定制海外SMARTLINK B(服务端)诊断配置"
        ),
        "asTech 定制ALL-IN-ONE(WIFI版)北美主机扩展配置": (
            "asTech 定制ALL-IN-ONE(WIFI版)北美主机扩展配置"
        ),
    }
    df["Product"] = df["CONF_NAME"].map(short_names).fillna(df["CONF_NAME"])

    df["CREATE_TIME"] = pd.to_datetime(df["CREATE_TIME"], errors="coerce")
    df["SALE_TIME"] = pd.to_datetime(df["SALE_TIME"], errors="coerce")
    df["REG_TIME"] = pd.to_datetime(df["REG_TIME"], errors="coerce")
    df["UPDATE_TIME"] = pd.to_datetime(df["UPDATE_TIME"], errors="coerce")
    df["FREE_END_TIME"] = pd.to_datetime(df["FREE_END_TIME"], errors="coerce")

    return df


df = load_data()
all_products = list(df["Product"].dropna().unique())

# 3. Sidebar Navigation
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio(
    "Select Page",
    [
        "Home Page",
        "Registration Trend",
        "Expiration & Renewal",
        "Software Update & Activity",
        "Geographic Hotmap",
        "Lifecycle Lead Time",
    ],
    index=0,
)

st.sidebar.write("---")
st.sidebar.caption("Logged in as: admin")
st.sidebar.caption(f"Data Rows: {len(df):,} units")

# ==============================================================================
# Module 1: Home Page
# ==============================================================================
if page == "Home Page":
    st.title("AIO Sold Units Dashboard")
    st.caption("Monthly Update Data Dashboard")
    st.write("---")

    st.subheader("Welcome")
    st.write("This is the main page of the dashboard.")
    st.write(
        "Please select a page from the sidebar menu to view different"
        " analytics reports."
    )
    st.write("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Data Source")
        st.subheader("AIO data.xlsx")
    with col2:
        st.caption("Total Records")
        st.subheader(f"{len(df):,} Rows")
    with col3:
        st.caption("Status")
        st.subheader("Ready")

    st.write("")
    st.write("")

    st.info("""
    **System Navigation Guidance:**
    
    All operational modules and analytical charts are neatly organized in the sidebar menu on the left:
    
    * **Registration Trend**: Multi-product registration growth over time.
    * **Expiration & Renewal**: Track upcoming software expiration dates and export targeted marketing lists.
    * **Software Update & Activity**: Monitor user engagement and inactive device risks.
    * **Geographic Hotmap**: View global & regional device distribution.
    * **Lifecycle Lead Time**: Measure production, sale, and activation delays.
    
    *Please click any menu item on the left to start exploring.*
    """)

# ==============================================================================
# Module 2: Registration Trend
# ==============================================================================
elif page == "Registration Trend":
    st.title("📈 Product Registration Trend")
    st.caption(
        "Analyze registration growth by REG_TIME across multiple"
        " configurations"
    )

    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        timebase = st.radio("Timebase:", ["By Month", "By Week"], horizontal=True)
    with col_t2:
        selected_prods_trend = st.multiselect(
            "Product Display Switches:", all_products, default=all_products
        )

    t_df = df[df["Product"].isin(selected_prods_trend)].copy()

    if timebase == "By Month":
        t_df["Period"] = t_df["REG_TIME"].dt.to_period("M").astype(str)
    else:
        t_df["Period"] = t_df["REG_TIME"].dt.to_period("W").astype(str)

    grouped = (
        t_df.groupby(["Period", "Product"])
        .size()
        .reset_index(name="Registered Units")
    )

    st.write("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered Units", f"{grouped['Registered Units'].sum():,}")
    m2.metric(
        "Products Enabled", f"{len(selected_prods_trend)} / {len(all_products)}"
    )
    m3.metric("Complete Periods", grouped["Period"].nunique())

    st.subheader("Registered Product Trend Chart")
    fig_line = px.line(
        grouped,
        x="Period",
        y="Registered Units",
        color="Product",
        markers=True,
    )
    fig_line.update_layout(
        height=500,
        xaxis_title="",
        yaxis_title="Registered Units",
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ==============================================================================
# Module 3: Expiration & Renewal
# ==============================================================================
elif page == "Expiration & Renewal":
    st.title("⏳ Monthly Renewal / Expiration Histogram")
    st.caption(
        "Track software expiration timelines and export targeted renewal lists"
    )

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        selected_prods_exp = st.multiselect(
            "Select Product Configurations:", all_products, default=all_products
        )

    exp_df = df[
        df["Product"].isin(selected_prods_exp) & df["FREE_END_TIME"].notnull()
    ].copy()

    now = pd.Timestamp.now()
    exp_df["Days_To_Expire"] = (exp_df["FREE_END_TIME"] - now).dt.days

    d30 = len(
        exp_df[
            (exp_df["Days_To_Expire"] >= 0) & (exp_df["Days_To_Expire"] <= 30)
        ]
    )
    d60 = len(
        exp_df[
            (exp_df["Days_To_Expire"] > 30) & (exp_df["Days_To_Expire"] <= 60)
        ]
    )
    d90 = len(
        exp_df[
            (exp_df["Days_To_Expire"] > 60) & (exp_df["Days_To_Expire"] <= 90)
        ]
    )
    expired = len(exp_df[exp_df["Days_To_Expire"] < 0])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Expiring in 30 Days", f"{d30:,}", delta_color="inverse")
    k2.metric("Expiring in 31-60 Days", f"{d60:,}")
    k3.metric("Expiring in 61-90 Days", f"{d90:,}")
    k4.metric("Expired Devices", f"{expired:,}")

    st.write("---")
    st.subheader("📅 Monthly Expiration Distribution")

    exp_df["Expire_Month"] = (
        exp_df["FREE_END_TIME"].dt.to_period("M").astype(str)
    )
    exp_monthly = (
        exp_df.groupby(["Expire_Month", "Product"])
        .size()
        .reset_index(name="Expiring Units")
    )

    fig_exp = px.bar(
        exp_monthly,
        x="Expire_Month",
        y="Expiring Units",
        color="Product",
        title="Monthly Software Expiration Units",
        barmode="stack",
    )
    fig_exp.update_layout(
        height=450, xaxis_title="Expiration Month", yaxis_title="Units"
    )
    st.plotly_chart(fig_exp, use_container_width=True)

    st.write("---")
    st.subheader("📥 Export Expiring Serial Numbers")

    ex_col1, ex_col2 = st.columns(2)
    with ex_col1:
        target_month = st.selectbox(
            "Select Expiration Month:", sorted(exp_df["Expire_Month"].unique())
        )
    with ex_col2:
        target_prod = st.selectbox(
            "Select Product Configuration:", ["All Products"] + all_products
        )

    export_list = exp_df[exp_df["Expire_Month"] == target_month].copy()
    if target_prod != "All Products":
        export_list = export_list[export_list["Product"] == target_prod]

    st.write(f"Matched **{len(export_list):,}** devices:")
    st.dataframe(
        export_list[
            [
                "SERIAL_NO",
                "Product",
                "FREE_END_TIME",
                "EMAIL",
                "COUNTRY_CN",
                "USER_NAME",
            ]
        ]
    )

    csv_data = (
        export_list[
            [
                "SERIAL_NO",
                "Product",
                "FREE_END_TIME",
                "EMAIL",
                "COUNTRY_CN",
                "USER_NAME",
            ]
        ]
        .to_csv(index=False)
        .encode("utf-8-sig")
    )
    st.download_button(
        "📥 Export List (CSV)",
        data=csv_data,
        file_name=f"expiring_list_{target_month}.csv",
        mime="text/csv",
    )

# ==============================================================================
# Module 4: Software Update & Activity
# ==============================================================================
elif page == "Software Update & Activity":
    st.title("🔄 Software Update & User Engagement")
    st.caption(
        "Analyze user retention and software update recency based on"
        " UPDATE_TIME"
    )

    now = pd.Timestamp.now()
    df_act = df.copy()
    df_act["Days_Since_Update"] = (now - df_act["UPDATE_TIME"]).dt.days

    def activity_label(days):
        if pd.isnull(days):
            return "Unknown"
        elif days <= 30:
            return "Active (<= 30 Days)"
        elif days <= 90:
            return "Moderate (31-90 Days)"
        elif days <= 180:
            return "Inactive Risk (91-180 Days)"
        else:
            return "High Churn Risk (> 180 Days)"

    df_act["Activity_Status"] = df_act["Days_Since_Update"].apply(activity_label)

    status_counts = df_act["Activity_Status"].value_counts().reset_index()
    status_counts.columns = ["Activity_Status", "Count"]

    a1, a2 = st.columns([1, 2])
    with a1:
        st.subheader("User Engagement Structure")
        fig_pie = px.pie(
            status_counts,
            names="Activity_Status",
            values="Count",
            color="Activity_Status",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with a2:
        st.subheader("Engagement by Product Configuration")
        prod_act = (
            df_act.groupby(["Product", "Activity_Status"])
            .size()
            .reset_index(name="Units")
        )
        fig_act_bar = px.bar(
            prod_act,
            x="Product",
            y="Units",
            color="Activity_Status",
            barmode="group",
        )
        st.plotly_chart(fig_act_bar, use_container_width=True)

    st.write("---")
    st.subheader("🚨 Inactive / High Risk Devices List")
    risk_df = df_act[
        df_act["Activity_Status"].isin(
            ["Inactive Risk (91-180 Days)", "High Churn Risk (> 180 Days)"]
        )
    ]
    st.write(f"Total **{len(risk_df):,}** inactive devices detected:")
    st.dataframe(
        risk_df[
            [
                "SERIAL_NO",
                "Product",
                "UPDATE_TIME",
                "Days_Since_Update",
                "EMAIL",
                "COUNTRY_CN",
            ]
        ]
    )

# ==============================================================================
# Module 5: Geographic Hotmap
# ==============================================================================
elif page == "Geographic Hotmap":
    st.title("🗺️ Geographic Distribution & Hotmap")
    st.caption(
        "Analyze device activations geographically based on PDT_REG_IP &"
        " COUNTRY_CN"
    )

    country_counts = df["COUNTRY_CN"].value_counts().reset_index()
    country_counts.columns = ["Country", "Units"]

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Top Active Countries")
        st.dataframe(country_counts.head(10))
    with c2:
        st.subheader("Registration Distribution by Country")
        fig_geo = px.bar(
            country_counts.head(10),
            x="Country",
            y="Units",
            color="Units",
            color_continuous_scale="YlOrRd",
            text_auto=True,
        )
        st.plotly_chart(fig_geo, use_container_width=True)

# ==============================================================================
# Module 6: Lifecycle Lead Time
# ==============================================================================
elif page == "Lifecycle Lead Time":
    st.title("🔄 Product Lifecycle Lead Time Analysis")
    st.caption(
        "Measure lead times across Production (CREATE) -> Sale (SALE) ->"
        " Registration (REG)"
    )

    lc_df = df.copy()
    lc_df["Production_To_Sale"] = (
        lc_df["SALE_TIME"] - lc_df["CREATE_TIME"]
    ).dt.days
    lc_df["Sale_To_Reg"] = (lc_df["REG_TIME"] - lc_df["SALE_TIME"]).dt.days
    lc_df["Production_To_Reg"] = (
        lc_df["REG_TIME"] - lc_df["CREATE_TIME"]
    ).dt.days

    lc_df = lc_df[
        (lc_df["Production_To_Sale"] >= 0) & (lc_df["Sale_To_Reg"] >= 0)
    ]

    p_sale_med = lc_df["Production_To_Sale"].median()
    s_reg_med = lc_df["Sale_To_Reg"].median()
    p_reg_med = lc_df["Production_To_Reg"].median()

    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Analyzed Rows", f"{len(lc_df):,}")
    l2.metric("Typical Production → Sale", f"{p_sale_med:.1f} days")
    l3.metric("Typical Sale → Registration", f"{s_reg_med:.1f} days")
    l4.metric("Typical Production → Registration", f"{p_reg_med:.1f} days")

    st.write("---")
    st.subheader("Typical Lead Time by Product (Median Days)")

    lc_summary = (
        lc_df.groupby("Product")[["Production_To_Sale", "Sale_To_Reg"]]
        .median()
        .reset_index()
    )
    fig_lc = px.bar(
        lc_summary,
        x="Product",
        y=["Production_To_Sale", "Sale_To_Reg"],
        barmode="group",
        labels={"value": "Median Days"},
    )
    fig_lc.update_layout(height=450)
    st.plotly_chart(fig_lc, use_container_width=True)
