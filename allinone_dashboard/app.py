import datetime
import os
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="asTech/AIO Operation Dashboard", layout="wide")


# 2. Load and Preprocess Data (加入云端自动 IP 归属州解析与缓存机制)
@st.cache_data(ttl=86400)  # 缓存 24 小时
def load_data():
  current_dir = os.path.dirname(os.path.abspath(__file__))

  possible_filenames = [
      "AIO data.xlsx",
      "aio data.xlsx",
      "AIO_data.xlsx",
      "aio历史数据.xlsx",
  ]

  file_path = None
  for fname in possible_filenames:
    temp_path = os.path.join(current_dir, fname)
    if os.path.exists(temp_path):
      file_path = temp_path
      break

  if file_path is None:
    existing_files = os.listdir(current_dir)
    raise FileNotFoundError(
        f"Excel file not found in {current_dir}. Existing files:"
        f" {existing_files}"
    )

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

  # 自动在云端通过批量接口解析美国 IP 对应的州简称 (CA, TX, NY 等)
  us_mask = df["COUNTRY_CN"].isin(["美国", "USA", "United States"])
  if us_mask.any():
    us_ips = df.loc[us_mask, "PDT_REG_IP"].dropna().unique()
    ip_to_state = {}

    # 使用免费批量 IP 解析接口（100个/包，几秒内即可解析完全部 IP）
    batch_size = 100
    for i in range(0, len(us_ips), batch_size):
      chunk = us_ips[i : i + batch_size].tolist()
      try:
        url = "http://ip-api.com/batch?fields=query,status,region"
        res = requests.post(url, json=chunk, timeout=5).json()
        for item in res:
          if item.get("status") == "success" and item.get("region"):
            ip_to_state[item["query"]] = item["region"]
      except Exception:
        pass

    # 映射回 DataFrame
    df["US_State_Code"] = df["PDT_REG_IP"].map(
        lambda ip: ip_to_state.get(ip, "CA")
    )
  else:
    df["US_State_Code"] = "CA"

  return df


df = load_data()
all_products = list(df["Product"].dropna().unique())

# 3. Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Page",
    [
        "Home Page",
        "Registration Trend",
        "Registration Hotmap",
        "Expiration & Renewal",
        "Software Update & Activity",
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
      "Please select a page from the sidebar menu to view different analytics"
      " reports."
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
    * **Registration Hotmap**: View global & regional device distribution.
    * **Expiration & Renewal**: Track upcoming software expiration dates and export targeted marketing lists.
    * **Software Update & Activity**: Monitor user engagement and inactive device risks.
    * **Lifecycle Lead Time**: Measure production, sale, and activation delays.
    
    *Please click any menu item on the left to start exploring.*
    """)

# ==============================================================================
# Module 2: Registration Trend
# ==============================================================================
elif page == "Registration Trend":
  st.title("Product Registration Trend")
  st.caption(
      "Only rows with valid registration are counted. The current incomplete"
      " week or month is automatically excluded."
  )

  with st.expander(" > Data loading notes (3)"):
    st.write("1. Only rows with valid registration timestamps are included.")
    st.write("2. Current incomplete periods are dynamically filtered out.")
    st.write(
        "3. Supports both linear trend and Year-over-Year (YoY) overlay"
        " comparison."
    )

  st.write("")

  ctrl_col1, ctrl_col2 = st.columns([1, 2.5])

  with ctrl_col1:
    st.write("**Trend View**")
    trend_view = st.radio(
        "Trend View",
        ["Product Registration Trend", "Year-over-Year Comparison"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.write("**Timebase**")
    timebase = st.radio(
        "Timebase",
        ["By Month", "By Week"],
        horizontal=True,
        label_visibility="collapsed",
    )

  with ctrl_col2:
    st.write("**Product Display Switches**")
    st.caption(
        "Turn individual product lines on or off. All enabled products are"
        " displayed in the same chart."
    )

    high_contrast_palette = [
        "#e74c3c",  # 鲜红
        "#2ecc71",  # 翠绿
        "#d35400",  # 咖啡橙
        "#3498db",  # 强天蓝
        "#f1c40f",  # 亮金黄
        "#8e44ad",  # 深紫
        "#2c3e50",  # 暗蓝灰
    ]

    prod_color_map = {
        prod: high_contrast_palette[i % len(high_contrast_palette)]
        for i, prod in enumerate(all_products)
    }

    enabled_products = []
    switch_cols = st.columns(4)
    for idx, prod_name in enumerate(all_products):
      col_target = switch_cols[idx % 4]
      with col_target:
        is_on = st.toggle(prod_name, value=True, key=f"sw_{idx}")
        if is_on:
          enabled_products.append(prod_name)

        color_hex = prod_color_map[prod_name]
        st.markdown(
            f"<div style='margin-top:-10px; margin-bottom:10px;"
            f" font-size:12px; color:{color_hex};'>● Chart color</div>",
            unsafe_allow_html=True,
        )

  t_df = df[df["Product"].isin(enabled_products)].copy()
  t_df["REG_TIME"] = pd.to_datetime(t_df["REG_TIME"], errors="coerce")
  t_df = t_df.dropna(subset=["REG_TIME"])

  t_df["Year"] = t_df["REG_TIME"].dt.year.astype(str)
  t_df["Month_Num"] = t_df["REG_TIME"].dt.month
  t_df["Month_Str"] = t_df["REG_TIME"].dt.strftime("%m (%b)")

  if trend_view == "Year-over-Year Comparison":
    all_years = sorted(t_df["Year"].unique()) if not t_df.empty else []

    st.write("---")
    st.write("**Year Display Switches**")
    st.caption("Turn individual years on or off for YoY comparison.")

    yoy_color_palette = [
        "#3498db",  # 蓝
        "#e74c3c",  # 红
        "#2ecc71",  # 绿
        "#f39c12",  # 橙
        "#8e44ad",  # 紫
        "#1abc9c",  # 青
        "#2c3e50",  # 灰
    ]

    year_color_map = {
        yr: yoy_color_palette[i % len(yoy_color_palette)]
        for i, yr in enumerate(all_years)
    }

    selected_years = []
    if all_years:
      year_cols = st.columns(min(len(all_years), 6))
      for idx, yr_name in enumerate(all_years):
        col_target = year_cols[idx % len(year_cols)]
        with col_target:
          yr_is_on = st.toggle(yr_name, value=True, key=f"yr_sw_{idx}")
          if yr_is_on:
            selected_years.append(yr_name)

          yr_color_hex = year_color_map[yr_name]
          st.markdown(
              f"<div style='margin-top:-10px; margin-bottom:10px;"
              f" font-size:12px; color:{yr_color_hex};'>● Chart color</div>",
              unsafe_allow_html=True,
          )

    t_yoy_df = t_df[t_df["Year"].isin(selected_years)].copy()

    if timebase == "By Month":
      yoy_grouped = (
          (
              t_yoy_df.groupby(["Year", "Month_Num", "Month_Str"])
              .size()
              .reset_index(name="Registered Units")
          )
          if not t_yoy_df.empty
          else pd.DataFrame()
      )

      if not yoy_grouped.empty:
        yoy_grouped = yoy_grouped.sort_values(["Month_Num", "Year"])

      st.write("---")
      m1, m2, m3, m4 = st.columns(4)
      m1.metric(
          "Registered Units",
          f"{yoy_grouped['Registered Units'].sum() if not yoy_grouped.empty else 0:,}",
      )
      m2.metric(
          "Products Enabled",
          f"{len(enabled_products)} / {len(all_products)}",
      )
      m3.metric(
          "Years Compared",
          f"{len(selected_years)} / {len(all_years)}",
      )
      m4.metric(
          "Latest Month Units",
          (
              f"{yoy_grouped.iloc[-1]['Registered Units']:,}"
              if not yoy_grouped.empty
              else "0"
          ),
      )

      st.write("")
      st.subheader("Year-over-Year Comparison (Overlay by Month)")

      if not yoy_grouped.empty:
        month_order = sorted(yoy_grouped["Month_Str"].unique())
        fig_line = px.line(
            yoy_grouped,
            x="Month_Str",
            y="Registered Units",
            color="Year",
            markers=True,
            color_discrete_map=year_color_map,
            category_orders={"Month_Str": month_order},
        )
        fig_line.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                title="Year",
            ),
            xaxis_title="Month",
            yaxis_title="Registered Units",
            hovermode="x unified",
            height=520,
        )
        st.plotly_chart(fig_line, width="stretch")
      else:
        st.warning("Please turn on at least one year and product switch above.")

    else:  # By Week
      if not t_yoy_df.empty:
        t_yoy_df["Week_Num"] = t_yoy_df["REG_TIME"].dt.isocalendar().week
        yoy_grouped = (
            t_yoy_df.groupby(["Year", "Week_Num"])
            .size()
            .reset_index(name="Registered Units")
        )
        yoy_grouped = yoy_grouped.sort_values(["Week_Num", "Year"])
      else:
        yoy_grouped = pd.DataFrame()

      st.write("---")
      m1, m2, m3, m4 = st.columns(4)
      m1.metric(
          "Registered Units",
          f"{yoy_grouped['Registered Units'].sum() if not yoy_grouped.empty else 0:,}",
      )
      m2.metric(
          "Products Enabled",
          f"{len(enabled_products)} / {len(all_products)}",
      )
      m3.metric(
          "Years Compared",
          f"{len(selected_years)} / {len(all_years)}",
      )
      m4.metric(
          "Active Weeks",
          yoy_grouped["Week_Num"].nunique() if not yoy_grouped.empty else 0,
      )

      st.write("")
      st.subheader("Year-over-Year Comparison (Overlay by Week)")

      if not yoy_grouped.empty:
        fig_line = px.line(
            yoy_grouped,
            x="Week_Num",
            y="Registered Units",
            color="Year",
            markers=True,
            color_discrete_map=year_color_map,
        )
        fig_line.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                title="Year",
            ),
            xaxis_title="Week Number",
            yaxis_title="Registered Units",
            hovermode="x unified",
            height=520,
        )
        st.plotly_chart(fig_line, width="stretch")
      else:
        st.warning("Please turn on at least one year and product switch above.")

  else:
    # 模式 B：常规多产品趋势图
    if timebase == "By Month":
      t_df["Period_Sort"] = t_df["REG_TIME"].dt.to_period("M")
    else:
      t_df["Period_Sort"] = t_df["REG_TIME"].dt.to_period("W")

    t_df["Period"] = t_df["Period_Sort"].astype(str)

    if not t_df.empty:
      full_grouped = (
          t_df.groupby(["Period_Sort", "Period", "Product"])
          .size()
          .reset_index(name="Registered Units")
      )
      full_grouped = full_grouped.sort_values("Period_Sort").reset_index(
          drop=True
      )
    else:
      full_grouped = pd.DataFrame()

    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    total_units = (
        full_grouped["Registered Units"].sum() if not full_grouped.empty else 0
    )
    prod_enabled_str = f"{len(enabled_products)} / {len(all_products)}"
    complete_periods = (
        full_grouped["Period"].nunique() if not full_grouped.empty else 0
    )
    latest_units = (
        full_grouped[full_grouped["Period"] == full_grouped["Period"].max()][
            "Registered Units"
        ].sum()
        if not full_grouped.empty
        else 0
    )

    m1.metric("Registered Units", f"{total_units:,}")
    m2.metric("Products Enabled", prod_enabled_str)
    m3.metric("Complete Periods", complete_periods)
    m4.metric("Latest Complete Period", f"{latest_units:,}")

    st.caption("Current incomplete period is not included.")
    st.write("")

    st.subheader("Registered Product Trend")
    if not full_grouped.empty:
      all_periods = sorted(full_grouped["Period"].unique())

      if len(all_periods) == 1:
        start_p, end_p = all_periods[0], all_periods[0]
      else:
        slider_val = st.select_slider(
            "Select Time Range",
            options=all_periods,
            value=(all_periods[0], all_periods[-1]),
            label_visibility="collapsed",
        )
        if isinstance(slider_val, (tuple, list)) and len(slider_val) == 2:
          start_p, end_p = slider_val
        else:
          start_p, end_p = slider_val, slider_val

      filtered_grouped = full_grouped[
          (full_grouped["Period"] >= start_p)
          & (full_grouped["Period"] <= end_p)
      ]

      sorted_unique_periods = sorted(filtered_grouped["Period"].unique())

      if not filtered_grouped.empty:
        fig_line = px.line(
            filtered_grouped,
            x="Period",
            y="Registered Units",
            color="Product",
            markers=True,
            color_discrete_map=prod_color_map,
            category_orders={"Period": sorted_unique_periods},
        )

        fig_line.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            xaxis_title="",
            yaxis_title="Registered Units",
            hovermode="x unified",
            height=500,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(
                type="category",
                categoryorder="array",
                categoryarray=sorted_unique_periods,
            ),
        )
        st.plotly_chart(fig_line, width="stretch")

        st.write("")
        with st.expander("Show Trend Data", expanded=False):
          pivot_df = (
              filtered_grouped.pivot(
                  index="Period",
                  columns="Product",
                  values="Registered Units",
              )
              .fillna(0)
              .astype(int)
          )

          for p in enabled_products:
            if p not in pivot_df.columns:
              pivot_df[p] = 0

          pivot_df = pivot_df[enabled_products]
          pivot_df["Total"] = pivot_df.sum(axis=1)
          pivot_df = pivot_df.reset_index()

          st.dataframe(pivot_df, width="stretch", hide_index=True)

        st.caption(
            f"Loaded products: {len(all_products)} | Registered rows:"
            f" {len(df):,} | Default timebase: {timebase} | View:"
            f" {trend_view}"
        )
      else:
        st.warning("No data found for the selected time range.")

    else:
      st.warning(
          "Please turn on at least one product switch above to view the trend."
      )

# ==============================================================================
# Module 3: Registration Hotmap (支持全量/按月/截至当前月累加 3种动态模式)
# ==============================================================================
elif page == "Registration Hotmap":
    st.title("Sold Units Hotmap")
    st.caption("Interactive regional heatmaps and product distribution")

    # 1. 顶部控制器：产品选择 + 视图选择 (United States / Global)
    col_h1, col_h2 = st.columns([2, 1])

    with col_h1:
        st.write("**Product Selection**")
        selected_prod = st.radio(
            "Product Selection",
            ["All Products"] + all_products,
            horizontal=True,
            label_visibility="collapsed",
        )

    with col_h2:
        st.write("**Geographic View**")
        geo_scope = st.radio(
            "Geographic View",
            ["United States (By State)", "Global (By Country)"],
            horizontal=True,
            label_visibility="collapsed",
        )

    # 2. 时间过滤模式切换控制器
    st.write("---")
    col_mode1, col_mode2 = st.columns([1, 2])

    with col_mode1:
        st.write("**Data Calculation Mode / 数据计算模式**")
        calc_mode = st.radio(
            "Calculation Mode",
            [
                "All Time Cumulative (历史全量总计)",
                "Cumulative Up To (截至当前月累加)",
                "Single Month Only (仅当月新增)",
            ],
            index=1,  # 默认选中截至当前月累加
            label_visibility="collapsed",
        )

    h_df = df.copy()
    if selected_prod != "All Products":
        h_df = h_df[h_df["Product"] == selected_prod]

    h_df["REG_TIME"] = pd.to_datetime(h_df["REG_TIME"], errors="coerce")
    h_df = h_df.dropna(subset=["REG_TIME"])
    h_df["Period"] = h_df["REG_TIME"].dt.to_period("M").astype(str)

    all_map_periods = sorted(h_df["Period"].unique())

    # 根据选中的模式计算 period_filtered_df
    if calc_mode == "All Time Cumulative (历史全量总计)":
        sel_period = f"All Time ({all_map_periods[0]} ~ {all_map_periods[-1]})"
        period_filtered_df = h_df

    elif calc_mode == "Cumulative Up To (截至当前月累加)":
        with col_mode2:
            st.caption(
                "Timeline Slider (Calculates cumulative data from start to"
                " selected month)"
            )
            if len(all_map_periods) > 1:
                target_month = st.select_slider(
                    "Timeline Slider",
                    options=all_map_periods,
                    value=all_map_periods[-1],  # 默认最晚月份
                    label_visibility="collapsed",
                )
            else:
                target_month = all_map_periods[0]

            sel_period = f"Cumulative Up To {target_month}"
            # 筛选 <= 当前选定月份的数据
            period_filtered_df = h_df[h_df["Period"] <= target_month]

    else:  # Single Month Only (仅当月新增)
        with col_mode2:
            st.caption("Timeline Slider (Filters data for selected month only)")
            if len(all_map_periods) > 1:
                target_month = st.select_slider(
                    "Timeline Slider",
                    options=all_map_periods,
                    value=all_map_periods[-1],
                    label_visibility="collapsed",
                )
            else:
                target_month = all_map_periods[0]

            sel_period = f"Single Month: {target_month}"
            # 仅筛选 == 当前选定月份的数据
            period_filtered_df = h_df[h_df["Period"] == target_month]

    st.write("")

    # 3. 视图 A：美国各州精细热力图 (United States By State)
    if geo_scope == "United States (By State)":
        us_df = period_filtered_df[
            period_filtered_df["COUNTRY_CN"].isin(
                ["美国", "USA", "United States"]
            )
        ].copy()

        state_counts = (
            us_df.groupby("US_State_Code")
            .size()
            .reset_index(name="Sold Units")
        )

        total_us_units = (
            state_counts["Sold Units"].sum() if not state_counts.empty else 0
        )
        active_states_cnt = (
            state_counts[state_counts["Sold Units"] > 0][
                "US_State_Code"
            ].nunique()
            if not state_counts.empty
            else 0
        )

        top_state_row = (
            state_counts.sort_values("Sold Units", ascending=False).iloc[0]
            if not state_counts.empty
            else None
        )
        top_state_name = (
            f"{top_state_row['US_State_Code']} ({top_state_row['Sold Units']:,})"
            if top_state_row is not None
            else "N/A"
        )

        # 4 个 KPI 卡片
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Product", selected_prod)
        k2.metric("Total Sold Units", f"{total_us_units:,}")
        k3.metric("Active States", f"{active_states_cnt}")
        k4.metric("Top State", top_state_name)

        st.write("---")
        st.subheader(f"{selected_prod} Sold Units Hotmap ({sel_period})")

        if not state_counts.empty:
            fig_map = px.choropleth(
                state_counts,
                locations="US_State_Code",
                locationmode="USA-states",
                color="Sold Units",
                scope="usa",
                color_continuous_scale="YlOrRd",
                labels={"Sold Units": "Sold Units"},
            )

            fig_map.update_traces(
                hovertemplate=(
                    "<b>State: %{location}</b><br>Sold Units:"
                    " %{z:,}<extra></extra>"
                )
            )

            fig_map.update_layout(
                geo=dict(
                    bgcolor="rgba(0,0,0,0)",
                    lakecolor="#ffffff",
                    showlakes=True,
                ),
                height=600,
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(fig_map, width="stretch")
        else:
            st.info("No US state data available for the selected parameters.")

    # 视图 B：全球国家热力图 (Global By Country)
    else:
        country_counts = (
            period_filtered_df.groupby("COUNTRY_CN")
            .size()
            .reset_index(name="Sold Units")
        )

        total_global_units = (
            country_counts["Sold Units"].sum() if not country_counts.empty else 0
        )
        active_countries_cnt = (
            country_counts[country_counts["Sold Units"] > 0][
                "COUNTRY_CN"
            ].nunique()
            if not country_counts.empty
            else 0
        )

        top_country_row = (
            country_counts.sort_values("Sold Units", ascending=False).iloc[0]
            if not country_counts.empty
            else None
        )
        top_country_name = (
            f"{top_country_row['COUNTRY_CN']} ({top_country_row['Sold Units']:,})"
            if top_country_row is not None
            else "N/A"
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Product", selected_prod)
        k2.metric("Total Sold Units", f"{total_global_units:,}")
        k3.metric("Active Countries", f"{active_countries_cnt}")
        k4.metric("Top Country", top_country_name)

        st.write("---")
        st.subheader(f"Global Sold Units Distribution ({sel_period})")

        if not country_counts.empty:
            fig_map = px.choropleth(
                country_counts,
                locations="COUNTRY_CN",
                locationmode="country names",
                color="Sold Units",
                color_continuous_scale="YlOrRd",
                labels={"Sold Units": "Sold Units"},
            )
            fig_map.update_layout(
                height=600,
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(fig_map, width="stretch")
        else:
            st.info(
                "No global country data available for the selected parameters."
            )

# ==============================================================================
# Module 4: Expiration & Renewal
# ==============================================================================
elif page == "Expiration & Renewal":
  st.title("Monthly Renewal / Expiration Histogram")
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
      exp_df[(exp_df["Days_To_Expire"] >= 0) & (exp_df["Days_To_Expire"] <= 30)]
  )
  d60 = len(
      exp_df[(exp_df["Days_To_Expire"] > 30) & (exp_df["Days_To_Expire"] <= 60)]
  )
  d90 = len(
      exp_df[(exp_df["Days_To_Expire"] > 60) & (exp_df["Days_To_Expire"] <= 90)]
  )
  expired = len(exp_df[exp_df["Days_To_Expire"] < 0])

  k1, k2, k3, k4 = st.columns(4)
  k1.metric("Expiring in 30 Days", f"{d30:,}", delta_color="inverse")
  k2.metric("Expiring in 31-60 Days", f"{d60:,}")
  k3.metric("Expiring in 61-90 Days", f"{d90:,}")
  k4.metric("Expired Devices", f"{expired:,}")

  st.write("---")
  st.subheader("Monthly Expiration Distribution")

  exp_df["Expire_Month"] = exp_df["FREE_END_TIME"].dt.to_period("M").astype(str)
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
  st.plotly_chart(fig_exp, width="stretch")

  st.write("---")
  st.subheader("Export Expiring Serial Numbers")

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
      export_list[[
          "SERIAL_NO",
          "Product",
          "FREE_END_TIME",
          "EMAIL",
          "COUNTRY_CN",
          "USER_NAME",
      ]]
  )

  csv_data = (
      export_list[[
          "SERIAL_NO",
          "Product",
          "FREE_END_TIME",
          "EMAIL",
          "COUNTRY_CN",
          "USER_NAME",
      ]]
      .to_csv(index=False)
      .encode("utf-8-sig")
  )
  st.download_button(
      "Export List (CSV)",
      data=csv_data,
      file_name=f"expiring_list_{target_month}.csv",
      mime="text/csv",
  )

# ==============================================================================
# Module 5: Software Update & Activity
# ==============================================================================
elif page == "Software Update & Activity":
  st.title("Software Update & User Engagement")
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
    st.plotly_chart(fig_pie, width="stretch")

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
    st.plotly_chart(fig_act_bar, width="stretch")

  st.write("---")
  st.subheader("🚨 Inactive / High Risk Devices List")
  risk_df = df_act[
      df_act["Activity_Status"].isin(
          ["Inactive Risk (91-180 Days)", "High Churn Risk (> 180 Days)"]
      )
  ]
  st.write(f"Total **{len(risk_df):,}** inactive devices detected:")
  st.dataframe(
      risk_df[[
          "SERIAL_NO",
          "Product",
          "UPDATE_TIME",
          "Days_Since_Update",
          "EMAIL",
          "COUNTRY_CN",
      ]]
  )

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

  lc_df = lc_df[(lc_df["Production_To_Sale"] >= 0) & (lc_df["Sale_To_Reg"] >= 0)]

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
  st.plotly_chart(fig_lc, width="stretch")
