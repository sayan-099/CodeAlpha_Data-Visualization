"""Interactive Superstore sales and profit dashboard."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "dataset" / "Sample - Superstore.csv"
INK = "#17263c"
BLUE = "#4263eb"
TEAL = "#0f9d8a"
GOLD = "#e7a43b"

st.set_page_config(page_title="Superstore | Sales & Profit", page_icon="📊", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA, encoding="latin1")
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="mixed")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="mixed")
    df["Year"] = df["Order Date"].dt.year
    df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    return df


df = load_data()

st.markdown(
    """<style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1440px;}
    h1, h2, h3 {color: #17263c; letter-spacing: -0.03em;}
    [data-testid="stMetric"] {background: #f4f7fb; border: 1px solid #e6ebf2;
      padding: 16px 18px; border-radius: 14px;}
    [data-testid="stMetricLabel"] {color: #64748b;}
    </style>""",
    unsafe_allow_html=True,
)

st.caption("DATA STORY  /  RETAIL PERFORMANCE  /  2014–2017")
st.title("Growth is strong. Profit is uneven.")
st.markdown(
    "Explore where sales are growing, which product lines convert sales into profit, "
    "and where discounting may be eroding returns."
)

with st.sidebar:
    st.header("Explore the data")
    year_range = st.slider("Order year", int(df.Year.min()), int(df.Year.max()), (int(df.Year.min()), int(df.Year.max())))
    regions = st.multiselect("Region", sorted(df.Region.unique()), default=sorted(df.Region.unique()))
    categories = st.multiselect("Category", sorted(df.Category.unique()), default=sorted(df.Category.unique()))
    segments = st.multiselect("Customer segment", sorted(df.Segment.unique()), default=sorted(df.Segment.unique()))
    st.caption("All metrics and charts respond to these filters.")

f = df[
    df.Year.between(year_range[0], year_range[1])
    & df.Region.isin(regions)
    & df.Category.isin(categories)
    & df.Segment.isin(segments)
].copy()

if f.empty:
    st.warning("No records match these filters. Adjust the selections in the sidebar.")
    st.stop()

sales = f.Sales.sum()
profit = f.Profit.sum()
orders = f["Order ID"].nunique()
margin = profit / sales if sales else 0
previous_year = f[f.Year == year_range[1] - 1].Sales.sum()
current_year = f[f.Year == year_range[1]].Sales.sum()
change = (current_year / previous_year - 1) * 100 if previous_year else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("Sales", f"${sales:,.0f}", f"{change:+.1f}% vs prior year" if change is not None else None)
k2.metric("Profit", f"${profit:,.0f}")
k3.metric("Profit margin", f"{margin:.1%}")
k4.metric("Orders", f"{orders:,}")

st.markdown("### Sales momentum")
monthly = f.groupby("Month", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
monthly["3-month sales average"] = monthly.Sales.rolling(3, min_periods=1).mean()
trend = px.line(monthly, x="Month", y=["Sales", "3-month sales average"], markers=True,
                color_discrete_map={"Sales": BLUE, "3-month sales average": GOLD},
                labels={"value": "Amount ($)", "variable": "Series", "Month": "Order month"})
trend.update_layout(height=360, margin=dict(l=10, r=10, t=15, b=10), legend_title_text="",
                    hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white")
trend.update_xaxes(showgrid=False)
trend.update_yaxes(gridcolor="#edf1f6", tickprefix="$", tickformat="~s")
st.plotly_chart(trend, use_container_width=True)

left, right = st.columns([1.05, 1])
with left:
    st.markdown("### Sales can hide weak returns")
    by_sub = f.groupby(["Category", "Sub-Category"], as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    bar = px.bar(by_sub.sort_values("Profit"), x="Profit", y="Sub-Category", color="Category", orientation="h",
                 color_discrete_sequence=[BLUE, TEAL, GOLD], custom_data=["Sales"],
                 labels={"Profit": "Profit ($)", "Sub-Category": ""})
    bar.update_traces(hovertemplate="%{y}<br>Profit: $%{x:,.0f}<br>Sales: $%{customdata[0]:,.0f}<extra></extra>")
    bar.update_layout(height=520, margin=dict(l=5, r=10, t=10, b=10), showlegend=True,
                      legend_title_text="Category", plot_bgcolor="white", paper_bgcolor="white")
    bar.update_xaxes(gridcolor="#edf1f6", tickprefix="$", tickformat="~s", zerolinecolor="#9aa6b2")
    bar.update_yaxes(showgrid=False)
    st.plotly_chart(bar, use_container_width=True)

with right:
    st.markdown("### Revenue vs. return by region")
    region = f.groupby("Region", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    region["Margin"] = region.Profit / region.Sales
    bubble = px.scatter(region, x="Sales", y="Profit", size="Sales", color="Margin", text="Region",
                        color_continuous_scale="Teal", size_max=58,
                        labels={"Sales": "Sales ($)", "Profit": "Profit ($)", "Margin": "Margin"})
    bubble.update_traces(textposition="top center", marker_line_color="white", marker_line_width=2,
                         hovertemplate="%{text}<br>Sales: $%{x:,.0f}<br>Profit: $%{y:,.0f}<br>Margin: %{marker.color:.1%}<extra></extra>")
    bubble.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white", paper_bgcolor="white",
                         coloraxis_colorbar_tickformat=".0%")
    bubble.update_xaxes(gridcolor="#edf1f6", tickprefix="$", tickformat="~s")
    bubble.update_yaxes(gridcolor="#edf1f6", tickprefix="$", tickformat="~s")
    st.plotly_chart(bubble, use_container_width=True)

st.markdown("### Discount and profit")
discount = f.assign(**{"Discount band": pd.cut(f.Discount, bins=[-0.01, 0, .1, .2, .3, .5, 1],
                                                 labels=["0%", "1–10%", "11–20%", "21–30%", "31–50%", "50%+"])})
discount_summary = discount.groupby("Discount band", observed=True, as_index=False).agg(
    Sales=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique")
)
discount_summary["Margin"] = discount_summary.Profit / discount_summary.Sales
disc_chart = px.bar(discount_summary, x="Discount band", y="Margin", color="Margin",
                    color_continuous_scale="RdYlGn", range_color=[-.3, .3],
                    custom_data=["Sales", "Profit", "Orders"], labels={"Margin": "Profit margin", "Discount band": "Average line discount"})
disc_chart.add_hline(y=0, line_color="#17263c", line_width=1)
disc_chart.update_traces(hovertemplate="Discount %{x}<br>Margin: %{y:.1%}<br>Sales: $%{customdata[0]:,.0f}<br>Profit: $%{customdata[1]:,.0f}<extra></extra>")
disc_chart.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                         plot_bgcolor="white", paper_bgcolor="white", coloraxis_showscale=False)
disc_chart.update_yaxes(tickformat=".0%", gridcolor="#edf1f6", zeroline=False)
st.plotly_chart(disc_chart, use_container_width=True)

cat = f.groupby("Category").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
cat["Margin"] = cat.Profit / cat.Sales
best_region = region.sort_values("Margin", ascending=False).iloc[0]
worst_region = region.sort_values("Margin").iloc[0]
low_discount = discount_summary[discount_summary["Discount band"].isin(["0%", "1–10%"])]
high_discount = discount_summary[discount_summary["Discount band"].isin(["21–30%", "31–50%", "50%+"])]
low_margin = low_discount.Profit.sum() / low_discount.Sales.sum() if low_discount.Sales.sum() else 0
high_margin = high_discount.Profit.sum() / high_discount.Sales.sum() if high_discount.Sales.sum() else 0

st.markdown("### What the filtered view suggests")
insight1, insight2, insight3 = st.columns(3)
top_cat = cat.Sales.idxmax()
top_profit = cat.Profit.idxmax()
thin_cat = cat.Margin.idxmin()
insight1.markdown(f"**{top_cat} drives the most revenue** at **${cat.loc[top_cat, 'Sales']:,.0f}**; **{top_profit}** contributes the most profit at **${cat.loc[top_profit, 'Profit']:,.0f}**.")
insight2.markdown(f"**{thin_cat} has the thinnest category margin** ({cat.loc[thin_cat, 'Margin']:.1%}). Review its discount and product mix before pursuing volume alone.")
insight3.markdown(f"**{best_region.Region} leads regional margin** ({best_region.Margin:.1%}); **{worst_region.Region}** is lowest ({worst_region.Margin:.1%}). High discount bands average **{high_margin:.1%}** margin vs **{low_margin:.1%}** for discounts up to 10%.")

st.caption("Source: Sample Superstore transaction data. Profit margin = profit ÷ sales. Discount bands group line-level discount rates; patterns are descriptive and do not establish causation.")
