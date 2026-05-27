

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk

np.random.seed(42)

st.set_page_config(
    page_title="Massachusetts Food Waste Simulator",
    layout="wide"
)

# -----------------------------
# Color theme
# -----------------------------
COLOR_WASTE = "#e63946"      # red
COLOR_RESCUE = "#2a9d8f"     # teal
COLOR_SCARCITY = "#457b9d"   # blue
COLOR_RETAIL = "#f4a261"     # orange
COLOR_BG = "#f8f9fa"
COLOR_TEXT = "#1d3557"

st.markdown(f"""
<style>
.stApp {{ background-color: {COLOR_BG}; }}
h1, h2, h3 {{ color: {COLOR_TEXT}; }}

[data-testid="stMetric"] {{
    background-color: white;
    padding: 14px;
    border-radius: 14px;
    border: 1px solid #ddd;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}}

/* Sidebar: darker, readable, not cramped */
[data-testid="stSidebar"] {{
    background-color: #2f3542;
    min-width: 320px;
    max-width: 340px;
}}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {{
    color: #f1f2f6 !important;
}}

/* Slightly smaller labels without hiding slider content */
[data-testid="stSidebar"] label {{
    font-size: 0.88rem !important;
}}

[data-testid="stSidebar"] .stSlider {{
    padding-top: 0.15rem;
    padding-bottom: 0.35rem;
}}

.stSlider [role="slider"] {{
    background-color: {COLOR_RESCUE} !important;
    border: 2px solid white !important;
}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* Sidebar metric card text FIX */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background-color: #f8f9fa !important;
    border: 1px solid #ddd;
}

/* Metric label (top text) */
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: #333 !important;
    font-weight: 600;
}

/* Metric value (big number) */
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #111 !important;
    font-size: 26px;
}

/* Metric delta (if used) */
[data-testid="stSidebar"] [data-testid="stMetricDelta"] {
    color: #555 !important;
}

</style>
""", unsafe_allow_html=True)


st.markdown("""
<div style="
    width: 100%;
    height: 220px;
    background-image: url('https://images.unsplash.com/photo-1542838132-92c53300491e');
    background-size: cover;
    background-position: center;
    border-radius: 18px;
    margin-bottom: 25px;
"></div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Orange slider thumb */
.stSlider [role="slider"] {
    background-color: #f77f00 !important;
    border: 2px solid white !important;
}

/* Orange active slider track */
.stSlider [data-baseweb="slider"] > div > div {
    background: linear-gradient(90deg, #f4a261, #f77f00) !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Constants
# -----------------------------

BASELINE = {
    "price": 1.00,
    "elasticity": -1.2,
    "overproduction_rate": 0.35,
    "markdown_efficiency": 0.20,
    "donation_rate": 0.20,
    "food_bank_capacity": 500,
    "transport_efficiency": 0.70,
    "spoilage_rate": 0.15,
    "unit_cost": 3.0,
    "base_price": 8.0,
    "markdown_discount": 0.40,
    "waste_cost": 1.0,
    "diversion_potential": 0.30
}

MA_FOOD_WASTE_TONS_YEAR = 930_000
MA_POPULATION = 7_000_000
MA_FOOD_INSECURITY_RATE = 0.11
MA_DEIVERSION_POTENTIAL = 0.40
MEALS_PER_PERSON_PER_DAY = 3
MA_DIVERTED_TONS_YEAR = 380_000
US_FOOD_INSECURITY_RATE = 0.11
MA_DIVERSION_POTENTIAL = 0.30

US_FOOD_WASTE_TONS_YEAR = 66_000_000

MEAL_WEIGHT_LBS = 1.2
TONS_TO_LBS = 2000

def meals_to_tons(meals):
    return (meals * MEAL_WEIGHT_LBS)/TONS_TO_LBS

def tons_to_meals(tons):
    return (tons * TONS_TO_LBS)/MEAL_WEIGHT_LBS

MEALS_PER_TON = TONS_TO_LBS / MEAL_WEIGHT_LBS

daily_people_in_need = MA_POPULATION * MA_FOOD_INSECURITY_RATE


OBJECT_WEIGHTS_TONS = {
    "Average car": 2.18,
    "African elephant": 6.0,
    "School bus": 12.0,
    "Blue whale": 150.0,
    "Statue of Liberty": 225.0
}

def format_object_equivalent(value, obj_name):
    if value < 1:
        return f"≈ less than 1 {obj_name.lower()}"
    
    rounded = round(value, 1)

    if rounded == 1:
        return f"≈ 1 {obj_name.lower()}"
    else:
        return f"≈ {rounded} {obj_name.lower()}s"

OBJECT_ICONS = {
    "Average car": "🚗",
    "African elephant": "🐘",
    "School bus": "🚌",
    "Blue whale": "🐋",
    "Statue of Liberty": "🗽"
}

def pick_closest_object(waste_tons):
    return min(
        OBJECT_WEIGHTS_TONS,
        key=lambda obj: abs(OBJECT_WEIGHTS_TONS[obj] - max(waste_tons, 0.01))
    )

st.write("""
Here is the simulator to help to understand how the food waste can increase depending on multiple factors including sales and profit.
The question is, can you make a difference in sales and work with the other components in order to reduce the food waste and help with the hunger? Is it possible?
""")

# -----------------------------
# Title
# -----------------------------
st.title("Massachusetts Food Waste Simulator")

st.write("""
So, this is a mini game where you test how pricing, overproduction, food rescue,
and food bank capacity can affect food waste and food scarcity in Massachusetts.
""")

st.info("You are now viewing the baseline policy. Adjust sliders to see the changes.")

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Game Controls")

if st.sidebar.button("Reset to Baseline"):
    st.rerun()

speed = st.sidebar.slider("Animation speed", 0.005, 0.1, 0.03)

days = st.sidebar.slider("Days", 30, 365, 60)
scale = st.sidebar.slider("Simulation scale: % of MA system", 0.01, 5.0, 0.10)
base_sales = st.sidebar.slider("Average daily meals sold", 100, 5000, 1200)
sales_volatility = st.sidebar.slider("Sales unpredictability", 0, 1000, 150)

st.sidebar.subheader("Retail Decisions")
price = st.sidebar.slider("Price level", 0.50, 1.50, BASELINE["price"])
elasticity = st.sidebar.slider("Consumer price sensitivity", -3.0, -0.1, BASELINE["elasticity"])
overproduction_rate = st.sidebar.slider("Overproduction rate", 0.00, 1.00, BASELINE["overproduction_rate"])
markdown_efficiency = st.sidebar.slider("Markdown effectiveness", 0.00, 1.00, BASELINE["markdown_efficiency"])

st.sidebar.subheader("Retail Economics")

unit_cost = st.sidebar.slider("Cost per item ($)", 1.0, 10.0, 3.0)
base_price = st.sidebar.slider("Base shelf price ($)", 2.0, 20.0, 8.0)
markdown_discount = st.sidebar.slider("Markdown discount (%)", 0.0, 0.9, 0.4)
waste_cost = st.sidebar.slider("Waste disposal/loss cost ($ per item)", 0.0, 5.0, 1.0)

st.sidebar.subheader("Food Bank Program")
donation_rate = st.sidebar.slider("Donation/rescue attempt rate", 0.00, 1.00, BASELINE["donation_rate"])
diversion_potential = st.sidebar.slider(
    "Food recovery potential",
    0.10, 0.60, BASELINE["diversion_potential"],
    help="Share of surplus food that can realistically be rescued"
)
food_bank_capacity = st.sidebar.slider("Food bank daily capacity", 0, 5000, BASELINE["food_bank_capacity"])
transport_efficiency = st.sidebar.slider("Transportation efficiency", 0.00, 1.00, BASELINE["transport_efficiency"])
spoilage_rate = st.sidebar.slider("Spoilage during rescue", 0.00, 0.50, BASELINE["spoilage_rate"])


st.sidebar.divider()
st.sidebar.header("Federal Awareness")

st.sidebar.markdown(f"""
<div style="
    background-color: #f8f9fa;
    color: #1d3557;
    padding: 18px;
    border-radius: 16px;
    border-left: 6px solid #f4a261;
    margin-bottom: 14px;
">
    <div style="font-size: 15px; font-weight: 700; color: #1d3557;">
        U.S. wasted food
    </div>
    <div style="font-size: 30px; font-weight: 800; color: #111827;">
        {US_FOOD_WASTE_TONS_YEAR:,.0f}
    </div>
    <div style="font-size: 14px; color: #4b5563;">
        tons per year
    </div>
</div>

<div style="
    background-color: #f8f9fa;
    color: #1d3557;
    padding: 18px;
    border-radius: 16px;
    border-left: 6px solid #457b9d;
">
    <div style="font-size: 15px; font-weight: 700; color: #1d3557;">
        U.S. food insecurity
    </div>
    <div style="font-size: 30px; font-weight: 800; color: #111827;">
        {US_FOOD_INSECURITY_RATE:.1%}
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Simulation function
# -----------------------------
def run_simulation(
    days,
    scale,
    base_sales,
    sales_volatility,
    price,
    elasticity,
    overproduction_rate,
    markdown_efficiency,
    donation_rate,
    food_bank_capacity,
    transport_efficiency,
    spoilage_rate,
    unit_cost,
    base_price,
    markdown_discount,
    waste_cost
):


    daily_ma_waste_tons = MA_FOOD_WASTE_TONS_YEAR / 365
    daily_ma_waste_meals = daily_ma_waste_tons * MEALS_PER_TON
    scaled_daily_waste_meals = daily_ma_waste_meals * (scale / 100)

    daily_people_in_need = MA_POPULATION * MA_FOOD_INSECURITY_RATE
    daily_meal_need = daily_people_in_need * MEALS_PER_PERSON_PER_DAY

    scaled_daily_meal_need = daily_meal_need * (scale / 100)

    base_hunger_need = int(scaled_daily_meal_need)

    data = []

    for day in range(1, days + 1):
        expected_sales = base_sales * (price ** elasticity)
        sales = int(np.random.normal(expected_sales, sales_volatility))
        sales = max(sales, 0)

        food_prepared = int(sales * (1 + overproduction_rate))
        unsold_food = max(food_prepared - sales, 0)

        extra_sales_from_markdown = int(
            unsold_food * markdown_efficiency * max(1 - price, 0)
        )

        sales += extra_sales_from_markdown
        unsold_food = max(unsold_food - extra_sales_from_markdown, 0)

        recoverable_food = int(unsold_food * diversion_potential)

        potential_donation = int(recoverable_food * donation_rate)

        accepted_by_food_bank = min(potential_donation, food_bank_capacity)

        usable_donated_food = int(
        accepted_by_food_bank * transport_efficiency * (1 - spoilage_rate)
        )

        food_waste = max(unsold_food - usable_donated_food, 0)


        daily_hunger_need = int(
            np.random.normal(base_hunger_need, max(base_hunger_need * 0.10, 1))
        )
        daily_hunger_need = max(daily_hunger_need, 0)

        food_scarcity = max(daily_hunger_need - usable_donated_food, 0)

                # Retail economics
        final_price = base_price * price
        markdown_price = final_price * (1 - markdown_discount)

        regular_sales = max(sales - extra_sales_from_markdown, 0)

        revenue = (regular_sales * final_price) + (extra_sales_from_markdown * markdown_price)
        production_cost = food_prepared * unit_cost
        waste_loss = food_waste * waste_cost

        profit = revenue - production_cost - waste_loss

        data.append([
            day,
            sales,
            food_prepared,
            unsold_food,
            recoverable_food,
            extra_sales_from_markdown,
            potential_donation,
            accepted_by_food_bank,
            usable_donated_food,
            food_waste,
            daily_hunger_need,
            food_scarcity,
            revenue,
            production_cost,
            waste_loss,
            profit
        ])

    df = pd.DataFrame(data, columns=[
    "Day",
    "Sales",
    "Food_Prepared",
    "Unsold_Food",
    "Recoverable_Food",
    "Extra_Sales_From_Markdown",
    "Potential_Donation",
    "Accepted_By_Food_Bank",
    "Usable_Donated_Food",
    "Food_Waste",
    "Hunger_Need",
    "Food_Scarcity",
    "Revenue",
    "Production_Cost",
    "Waste_Loss",
    "Profit"
])

    return df

@st.cache_data
def get_fixed_baselines():
    food_waste_baseline_df = run_simulation(
        days=60,
        scale=0.10,
        base_sales=1200,
        sales_volatility=150,
        price=BASELINE["price"],
        elasticity=BASELINE["elasticity"],
        overproduction_rate=BASELINE["overproduction_rate"],
        markdown_efficiency=BASELINE["markdown_efficiency"],
        donation_rate=BASELINE["donation_rate"],
        food_bank_capacity=BASELINE["food_bank_capacity"],
        transport_efficiency=BASELINE["transport_efficiency"],
        spoilage_rate=BASELINE["spoilage_rate"],
        unit_cost=BASELINE["unit_cost"],
        base_price=BASELINE["base_price"],
        markdown_discount=BASELINE["markdown_discount"],
        waste_cost=BASELINE["waste_cost"]
)

    food_bank_baseline_df = run_simulation(
        days=60,
        scale=0.10,
        base_sales=1200,
        sales_volatility=150,
        price=1.00,
        elasticity=-1.2,
        overproduction_rate=0.25,
        markdown_efficiency=0.30,
        donation_rate=0.30,
        food_bank_capacity=600,
        transport_efficiency=0.70,
        spoilage_rate=0.15,
        unit_cost=3.0,
        base_price=8.0,
        markdown_discount=0.40,
        waste_cost=1.0
    )

    retail_baseline_df = run_simulation(
        days=60,
        scale=0.10,
        base_sales=1200,
        sales_volatility=150,
        price=1.00,
        elasticity=-1.2,
        overproduction_rate=0.25,
        markdown_efficiency=0.30,
        donation_rate=0.30,
        food_bank_capacity=600,
        transport_efficiency=0.70,
        spoilage_rate=0.15,
        unit_cost=3.0,
        base_price=8.0,
        markdown_discount=0.40,
        waste_cost=1.0
    )

    return food_waste_baseline_df, food_bank_baseline_df, retail_baseline_df

# Current user scenario
df = run_simulation(
    days,
    scale,
    base_sales,
    sales_volatility,
    price,
    elasticity,
    overproduction_rate,
    markdown_efficiency,
    donation_rate,
    food_bank_capacity,
    transport_efficiency,
    spoilage_rate,
    unit_cost,
    base_price,
    markdown_discount,
    waste_cost
)

food_waste_baseline_df, food_bank_baseline_df, retail_baseline_df = get_fixed_baselines()

# -----------------------------
# Totals
# -----------------------------
total_sales = df["Sales"].sum()
total_waste = df["Food_Waste"].sum()
total_donated = df["Usable_Donated_Food"].sum()
total_scarcity = df["Food_Scarcity"].sum()
total_revenue = df["Revenue"].sum()
total_profit = df["Profit"].sum()
total_hunger = df["Hunger_Need"].sum()

waste_tons = meals_to_tons(total_waste)
waste_lbs = waste_tons * TONS_TO_LBS
object_choice = pick_closest_object(waste_tons)
equivalent_objects = waste_tons / OBJECT_WEIGHTS_TONS[object_choice]

total_unsold = df["Unsold_Food"].sum()
total_recoverable = df["Recoverable_Food"].sum()
total_potential_donation = df["Potential_Donation"].sum()
total_accepted = df["Accepted_By_Food_Bank"].sum()

st.header("Simulation Results")

r1, r2 = st.columns(2)
r3, r4 = st.columns(2)

r1.metric("Sales", f"{total_sales:,.0f} meals")
r2.metric("Food Waste", f"{total_waste:,.0f} meals")
r3.metric("Food Rescued", f"{total_donated:,.0f} meals")
r4.metric("Scarcity", f"{total_scarcity:,.0f} meals")

r5, r6 = st.columns(2)

r5.metric("Revenue", f"${total_revenue:,.0f}")
r6.metric("Profit", f"${total_profit:,.0f}")

# -----------------------------
# Pipeline + Pie Charts HERE
# -----------------------------

pipeline_df = pd.DataFrame({
    "Stage": [
        "Unsold Food",
        "Recoverable Food",
        "Potential Donation",
        "Accepted by Food Bank",
        "Usable Donated Food",
        "Final Waste"
    ],
    "Meals": [
        total_unsold,
        total_recoverable,
        total_potential_donation,
        total_accepted,
        total_donated,
        total_waste
    ]
})

fig_pipeline = go.Figure()

fig_pipeline.add_trace(go.Bar(
    x=pipeline_df["Stage"],
    y=pipeline_df["Meals"],
    marker_color=[
        COLOR_RETAIL,
        COLOR_RESCUE,
        COLOR_RESCUE,
        COLOR_SCARCITY,
        COLOR_RESCUE,
        COLOR_WASTE
    ],
    text=[f"{x:,.0f}" for x in pipeline_df["Meals"]],
    textposition="auto"
))

fig_pipeline.update_layout(
    title="Where Surplus Food Is Lost or Saved",
    xaxis_title="Food Recovery Stage",
    yaxis_title="Meals",
    height=420
)



st.header("Final Allocation of Food Supply")

outcome_df = pd.DataFrame({
    "Outcome": ["Sales", "Donated", "Waste"],
    "Meals": [total_sales, total_donated, total_waste]
})

fig_pie = go.Figure(data=[
    go.Pie(
        labels=outcome_df["Outcome"],
        values=outcome_df["Meals"],
        hole=0.35,
        marker=dict(colors=[COLOR_RETAIL, COLOR_RESCUE, COLOR_WASTE])
    )
])

fig_pie.update_layout(
    title="How Total Store Food Supply Was Used"
)

st.caption("This chart shows the final split of total store food supply: sold, donated/recovered, or wasted.")

chart_col1, chart_col2 = st.columns([1.3, 1])

with chart_col1:
    st.subheader("Food Recovery Pipeline")
    st.plotly_chart(fig_pipeline, use_container_width=True)

with chart_col2:
    st.subheader("Food Outcome Mix")
    st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------------
# Baseline comparisons
# -----------------------------
food_waste_baseline_waste = food_waste_baseline_df["Food_Waste"].sum()
food_bank_baseline_rescue = food_bank_baseline_df["Usable_Donated_Food"].sum()
food_bank_baseline_scarcity = food_bank_baseline_df["Food_Scarcity"].sum()
retail_baseline_profit = retail_baseline_df["Profit"].sum()
retail_baseline_revenue = retail_baseline_df["Revenue"].sum()

waste_change = food_waste_baseline_waste - total_waste
rescue_change = total_donated - food_bank_baseline_rescue
scarcity_change = total_scarcity - food_bank_baseline_scarcity
profit_change = total_profit - retail_baseline_profit
revenue_change = total_revenue - retail_baseline_revenue


st.header("🌍 Food Waste Impact")
c1, c2, c3 = st.columns(3)
c1.metric("Food Waste", f"{total_waste:,.0f} meals", delta=f"{waste_change:,.0f} vs waste baseline", delta_color="inverse")
c2.metric("Waste Tons", f"{waste_tons:,.2f} tons")

st.header("🏦 Food Bank Operations")
c3, c4, c7 = st.columns(3)
c3.metric("Total Food Prepared", f"{total_sales + total_waste:,.0f} meals")
c4.metric("Remaining Scarcity", f"{total_scarcity:,.0f} meals", delta=f"{scarcity_change:,.0f} vs food bank baseline", delta_color="inverse")

st.header("🏪 Retail Operations")
c5, c6 = st.columns(2)
c5.metric("Revenue", f"${total_revenue:,.0f}", delta=f"${revenue_change:,.0f} vs retail baseline")
c6.metric("Profit", f"${total_profit:,.0f}", delta=f"${profit_change:,.0f} vs retail baseline")
c7.metric("Total Hunger Need", f"{total_hunger:,.0f} meals")

st.caption("Hunger need represents a total food demand; scarcity is unmet after distribution.")

# -----------------------------
# Top live dashboard
# -----------------------------


st.markdown("### 🌍 Food Waste Impact")

if total_scarcity == 0:
    st.success("You eliminated food scarcity in this simulation. Yay! Congrats! 🎉")
elif total_waste > total_donated:
    st.warning("More food is wasted than rescued. Try increasing donation rate, markdown effectiveness, or food bank capacity. And yikes.")
else:
    st.success("Nice! Your choices rescued more food than they wasted. Woah!")

if total_scarcity > food_bank_baseline_scarcity:
    st.warning("Food scarcity increased. Consider improving food bank capacity or logistics. Can you?")
elif total_waste > food_waste_baseline_waste:
    st.warning("Food waste increased. Maybe adjust pricing or markdown strategies.")
else:
    st.success("Balanced outcome: reduced waste and improved food access. Maybe or maybe not?")


# -----------------------------
# Split screen: impact + map
# -----------------------------
left_col, right_col = st.columns([1, 1.2])

# LEFT SIDE (meter)
with left_col:
    st.subheader("Food Waste Impact Level")

    waste_ratio = total_waste / max(total_sales + total_donated + total_waste, 1)

    if waste_ratio < 0.10:
        impact_label = "Low Impact"
        impact_color = "#2a9d8f"
        impact_message = "Most food is being sold or rescued."
    elif waste_ratio < 0.25:
        impact_label = "Moderate Impact"
        impact_color = "#f4a261"
        impact_message = "Some surplus is still being lost."
    else:
        impact_label = "High Impact"
        impact_color = "#e63946"
        impact_message = "A large share of food is becoming waste."

    st.markdown(f"""
    <div style="
        background-color:white;
        padding:20px;
        border-radius:18px;
        border-left:10px solid {impact_color};
        box-shadow:0 3px 10px rgba(0,0,0,0.08);
        margin-bottom:16px;
    ">
        <h3 style="margin-bottom:5px; color:{impact_color};">{impact_label}</h3>
        <h1 style="margin-top:0; margin-bottom:5px;">{waste_tons:,.2f} tons</h1>
        <p style="font-size:16px; margin-bottom:8px;">{impact_message}</p>
        <p style="margin-bottom:0;">
            That equals <b>{waste_lbs:,.0f} pounds</b>, or about 
            <b>{equivalent_objects:,.1f} {object_choice.lower()}s</b> by weight.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.progress(min(waste_ratio, 1.0))

    st.caption(
        f"Food waste is {waste_ratio:.1%} of total store food supply "
        "after sales and donations."
    )

    fig_impact = go.Figure()

    fig_impact.add_trace(go.Indicator(
        mode="gauge+number",
        value=waste_ratio * 100,
        number={"suffix": "%"},
        title={"text": "Waste Share of Food Supply"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": impact_color},
            "steps": [
                {"range": [0, 10], "color": "#d8f3dc"},
                {"range": [10, 25], "color": "#ffe8a3"},
                {"range": [25, 100], "color": "#ffd6d6"},
            ],
        }
    ))

    fig_impact.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig_impact, use_container_width=True)

    # -----------------------------
# Object image mapping
# -----------------------------
image_map = {
    "Average car": "https://img.icons8.com/color/96/car.png",
    "African elephant": "https://img.icons8.com/color/96/elephant.png",
    "School bus": "https://img.icons8.com/color/96/bus.png",
    "Blue whale": "https://img.icons8.com/color/96/whale.png",
    "Statue of Liberty": "https://img.icons8.com/color/96/statue-of-liberty.png"
}

img_url = image_map[object_choice]

# -----------------------------
# Animated visual comparison: Waste vs Scarcity
# -----------------------------
import time

st.subheader("Animated Scale: Waste vs Unmet Need")

# Waste icons use object weight comparison
waste_icon_count = int(min(equivalent_objects, 40))

# Scarcity icons: 1 icon = 1,000 unmet meals
MEALS_PER_ICON = 1000
scarcity_icon_count = int(min(total_scarcity / MEALS_PER_ICON, 40))

st.caption(
    f"Waste icons automatically use the closest object by weight: {object_choice}. "
    "Unmet need icons represent 1,000 unmet meals each."
)

waste_col, divider_col, scarcity_col = st.columns([1, 0.05, 1])


with waste_col:
    st.markdown("#### 🔴 Food Waste")
    waste_placeholder = st.empty()

with divider_col:
    st.markdown(
        """
        <div style="
            border-left: 3px solid #adb5bd;
            height: 260px;
            margin: 15px auto;
        "></div>
        """,
        unsafe_allow_html=True
    )
    
with scarcity_col:
    st.markdown("#### 🔵 Unmet Need")
    scarcity_placeholder = st.empty()

max_steps = max(waste_icon_count, scarcity_icon_count)

for step in range(1, max_steps + 1):

    with waste_placeholder.container():
        if waste_icon_count == 0:
            st.write("No waste icons to show.")
        else:
            shown_waste = min(step, waste_icon_count)
            cols = st.columns(8)
            for i in range(shown_waste):
                with cols[i % 8]:
                    st.image(img_url, width=42)

    with scarcity_placeholder.container():
        if scarcity_icon_count == 0:
            st.write("No unmet need icons to show.")
        else:
            shown_scarcity = min(step, scarcity_icon_count)
            cols = st.columns(8)
            for i in range(shown_scarcity):
                with cols[i % 8]:
                    st.image(img_url, width=42)

    time.sleep(0.025)

st.markdown(f"""
**Waste:** {waste_tons:,.2f} tons  
**Unmet need:** {total_scarcity:,.0f} meals  
""")


# -----------------------------
# Visual: Scarcity (Unmet Need)
# -----------------------------

scarcity_objects = total_scarcity / OBJECT_WEIGHTS_TONS[object_choice]

max_display = int(min(scarcity_objects, 40))
cols_per_row = 8

scarcity_img_url = "https://img.icons8.com/color/96/meal.png"

for row_start in range(0, max_display, cols_per_row):
    cols = st.columns(cols_per_row)
    for i in range(row_start, min(row_start + cols_per_row, max_display)):
        with cols[i % cols_per_row]:
            st.image(scarcity_img_url, width=42)

st.markdown(f"""
### Comparison Summary

- 🔴 **Waste:** {waste_tons:,.2f} tons  
- 🔵 **Unmet Need:** {total_scarcity:,.0f} meals  

≈ **{equivalent_objects:,.1f} {object_choice.lower()}s worth of food waste**
""")

# -----------------------------
# Visual car stacking
# -----------------------------
equivalent_text = format_object_equivalent(equivalent_objects, object_choice)

st.markdown(f"""
That’s about **{equivalent_text.replace('≈ ', '')}** by weight.
""")

import time


# Select image based on object
image_map = {
    "Average car": "https://img.icons8.com/color/96/car.png",
    "African elephant": "https://img.icons8.com/color/96/elephant.png",
    "School bus": "https://img.icons8.com/color/96/bus.png",
    "Blue whale": "https://img.icons8.com/color/96/whale.png",
    "Statue of Liberty": "https://img.icons8.com/color/96/statue-of-liberty.png"
}

img_url = image_map[object_choice]
img_url = image_map[object_choice]

# Limit for performance
max_display = int(min(equivalent_objects, 40))
cols_per_row = 8

placeholder = st.empty()

for step in range(1, max_display + 1):
    with placeholder.container():
        for row_start in range(0, step, cols_per_row):
            cols = st.columns(cols_per_row)
            for i in range(row_start, min(row_start + cols_per_row, step)):
                with cols[i % cols_per_row]:
                    st.image(img_url, width=45)

    time.sleep(speed)  # animation speed

# RIGHT SIDE (map)
with right_col:
    st.subheader("Massachusetts Map View")

    map_data = pd.DataFrame({
        "Location": [
            "Boston",
            "Worcester",
            "Springfield",
            "Lowell",
            "New Bedford",
            "Barnstable County",
            "Pittsfield",
            "North Adams",
            "Greenfield",
            "Northampton"
        ],
        "lat": [
            42.3601,
            42.2626,
            42.1015,
            42.6334,
            41.6362,
            41.7000,
            42.4501,
            42.7009,
            42.5879,
            42.3251
        ],
        "lon": [
            -71.0589,
            -71.8023,
            -72.5898,
            -71.3162,
            -70.9342,
            -70.3000,
            -73.2454,
            -73.1087,
            -72.5995,
            -72.6412

        ],
        "Estimated_Waste": [
            total_waste * 0.25,
            total_waste * 0.15,
            total_waste * 0.13,
            total_waste * 0.10,
            total_waste * 0.10,
            total_waste * 0.10,
            total_waste * 0.07,
            total_waste * 0.04,
            total_waste * 0.03,
            total_waste * 0.03

        ]
    })

    map_data["Percent_of_Total_Waste"] = (
    map_data["Estimated_Waste"] / max(total_waste, 1) * 100
    )

    map_data["radius"] = map_data["Estimated_Waste"] / map_data["Estimated_Waste"].max() * 50000

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color="[230, 57, 70, 150]",
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=42.2,
        longitude=-71.7,
        zoom=7
    )

    tooltip = {
    "html": """
    <b>{Location}</b><br/>
    🍽️ Waste: {Estimated_Waste} meals<br/>
    📊 Share of total waste: {Percent_of_Total_Waste}% 
    """,
    "style": {
        "backgroundColor": "white",
        "color": "black",
        "fontSize": "14px"
    }
    }

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    ))

    st.caption("Map values are simulated shares of the Massachusetts result, not official city-level waste measurements.")

#baselines2

st.header("Baseline Comparison by System")

comparison_df = pd.DataFrame({
    "Metric": ["Food Waste", "Food Rescued", "Remaining Scarcity"],
    "Baseline": [
        food_waste_baseline_waste,
        food_bank_baseline_rescue,
        food_bank_baseline_scarcity
    ],
    "Current Policy": [
        total_waste,
        total_donated,
        total_scarcity
    ]
})

fig_compare = go.Figure()

fig_compare.add_trace(go.Bar(
    x=comparison_df["Metric"],
    y=comparison_df["Baseline"],
    name="Baseline",
    marker_color="#adb5bd"
))

fig_compare.add_trace(go.Bar(
    x=comparison_df["Metric"],
    y=comparison_df["Current Policy"],
    name="Current Policy",
    marker_color=COLOR_RESCUE
))

fig_compare.update_layout(
    barmode="group",
    title="Baseline vs Your Current Policy Choices",
    yaxis_title="Meals"
)

st.plotly_chart(fig_compare, use_container_width=True)

st.header("Retail Trade-Off: Profit vs Waste")

fig_tradeoff = go.Figure()

fig_tradeoff.add_trace(go.Scatter(
    x=df["Food_Waste"],
    y=df["Profit"],
    mode="markers",
    marker=dict(color=COLOR_RETAIL, size=9),
    name="Daily trade-off"
))

fig_tradeoff.update_layout(
    title="Daily Profit vs Food Waste",
    xaxis_title="Food Waste",
    yaxis_title="Profit ($)"
)

st.plotly_chart(fig_tradeoff, use_container_width=True)

# -----------------------------
# Trend charts
# -----------------------------
st.header("Daily Trends")

trend1, trend2 = st.columns(2)

with trend1:
    fig_daily_waste = go.Figure()
    fig_daily_waste.add_trace(go.Scatter(
        x=df["Day"],
        y=df["Food_Waste"],
        mode="lines",
        name="Food Waste",
        line=dict(color=COLOR_WASTE, width=3)
    ))

    fig_daily_waste.add_trace(go.Scatter(
        x=df["Day"],
        y=df["Usable_Donated_Food"],
        mode="lines",
        name="Usable Donated Food",
        line=dict(color=COLOR_RESCUE, width=3)
    ))

    fig_daily_waste.update_layout(
        title="Waste vs Rescued Food Over Time",
        xaxis_title="Day",
        yaxis_title="Meals"
    )
    st.plotly_chart(fig_daily_waste, use_container_width=True)

with trend2:
    fig_scarcity = go.Figure()
    fig_scarcity.add_trace(go.Scatter(
        x=df["Day"],
        y=df["Food_Scarcity"],
        mode="lines",
        name="Food Scarcity",
        line=dict(color=COLOR_SCARCITY, width=3)
    ))
    fig_scarcity.add_trace(go.Scatter(
        x=df["Day"],
        y=df["Hunger_Need"],
        mode="lines",
        name="Hunger Need",
        line=dict(color=COLOR_RETAIL, width=3)
    ))
    fig_scarcity.update_layout(
        title="Food Scarcity Over Time",
        xaxis_title="Day",
        yaxis_title="Meals"
    )
    st.plotly_chart(fig_scarcity, use_container_width=True)

# -----------------------------
# Interpretation
# -----------------------------
st.header("What This Shows")

st.write("""
This simulator shows how food waste and food scarcity can happen at the same time as it is an ongoing issue.
Pricing decisions, overproduction, food rescue systems, transportation, spoilage,
and food bank capacity all affect the final outcome. How do we balance this system? From retail perspective, this can be challenging as the costs increases for products and managing sales.
""")

st.write("""
The before-vs-after chart compares a baseline policy to your ongoing slider choices.
The map gives a Massachusetts-focused visual, while the object comparison turns tons
and pounds into something easier to imagine such as car, elephant, or whale.
""")

# -----------------------------
# Data table + download
# -----------------------------
with st.expander("View Simulation Data"):
    st.dataframe(df)

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download simulation data as CSV",
    data=csv,
    file_name="massachusetts_food_waste_simulation.csv",
    mime="text/csv"
)
