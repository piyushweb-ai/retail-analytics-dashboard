from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).parent / "dashboard_data"

st.set_page_config(page_title="Retail Analytics", page_icon="🛍️", layout="wide")


@st.cache_data
def load(name, **kwargs):
    return pd.read_csv(DATA / name, **kwargs)

kpis = load("kpis.csv").iloc[0]
monthly = load("monthly_revenue.csv", parse_dates=["Month"])
countries = load("country_revenue.csv")
products = load("top_products.csv")
rfm = load("rfm_clusters.csv")
forecast = load("forecast_next_6_months.csv", parse_dates=["ds"])

st.title("Retail Analytics: Customer Segments & Sales Forecast")
st.caption(f"UCI Online Retail II · {kpis['start']} to {kpis['end']} · cancellations and bad rows removed")

tab1, tab2, tab3 = st.tabs(["Overview", "Customer segments", "Sales forecast"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total revenue", f"£{kpis['total_revenue']:,.0f}")
    c2.metric("Orders", f"{int(kpis['orders']):,}")
    c3.metric("Identified customers", f"{int(kpis['customers']):,}")

    st.plotly_chart(px.line(monthly, x="Month", y="Revenue", markers=True, title="Monthly revenue"))

    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(countries.head(10), x="Revenue", y="Country", orientation="h",
               title="Top 10 countries by revenue").update_yaxes(autorange="reversed"))
    right.plotly_chart(
        px.bar(products.head(10), x="Revenue", y="Description", orientation="h",
               title="Top 10 products by revenue").update_yaxes(autorange="reversed"))

with tab2:
    view = st.radio("Group customers by", ["K-Means clusters", "RFM segments"], horizontal=True)
    col = "ClusterName" if view == "K-Means clusters" else "Segment"

    profile = rfm.groupby(col).agg(
        Customers=("CustomerID", "count"),
        Avg_Recency_days=("Recency", "mean"),
        Avg_Orders=("Frequency", "mean"),
        Avg_Spend=("Monetary", "mean"),
        Total_Revenue=("Monetary", "sum"),
    ).round(1).sort_values("Total_Revenue", ascending=False)
    profile["Customers_%"] = (profile["Customers"] / profile["Customers"].sum() * 100).round(1)
    profile["Revenue_%"] = (profile["Total_Revenue"] / profile["Total_Revenue"].sum() * 100).round(1)
    st.dataframe(profile)

    share = (profile[["Customers_%", "Revenue_%"]].reset_index()
             .melt(id_vars=col, var_name="Measure", value_name="Percent"))
    st.plotly_chart(px.bar(share, x=col, y="Percent", color="Measure", barmode="group",
                           title="Customer share vs revenue share"))

    st.plotly_chart(px.scatter(rfm, x="Recency", y="Monetary", color=col, log_y=True,
                               opacity=0.6, title="Customers by recency and total spend"))

    pick = st.selectbox("Download the customers in a group", sorted(rfm[col].unique()))
    sub = rfm[rfm[col] == pick]
    st.download_button(f"Download {len(sub):,} customers (CSV)", sub.to_csv(index=False),
                       file_name=pick.replace("/", "-").replace(" ", "_") + ".csv")

with tab3:
    st.subheader("Next 6 months: Dec 2011 to May 2012")
    hist = monthly.rename(columns={"Month": "Date"}).assign(Series="Actual")
    fut = (forecast.melt(id_vars="ds", var_name="Series", value_name="Revenue")
           .rename(columns={"ds": "Date"}))
    st.plotly_chart(px.line(pd.concat([hist, fut]), x="Date", y="Revenue",
                            color="Series", markers=True))

    table = forecast.assign(ds=forecast["ds"].dt.strftime("%b %Y")).set_index("ds").round(0)
    st.dataframe(table)
    st.info(
        "Backtest on Jun to Nov 2011: seasonal naive MAPE 6.5%, Prophet MAPE 6.9%, so the two "
        "models are roughly tied. With only two years of data, treat these forecasts as a guide: "
        "the typical error is about 7%, and individual months can miss by more."
    )