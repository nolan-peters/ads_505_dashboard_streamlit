import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk

### Data Load ###
df = pd.read_csv('sales_order_items_processed.csv')
df['salesorderid'] = df['salesorderid'].astype(str)
df['createdat'] = pd.to_datetime(df['createdat'], format='%Y-%m-%d')

### Dashboard Styling ###
st.set_page_config(
    layout="wide",
    page_title="Treks Bike Sales Dashboard",
    page_icon=":bike:"
    )

### Title ###
st.title("Trek Bike Sales :bike:")
st.write("This dashboard provides insights on Trek Bike Sales. Filter by date range and company name to explore the data.")
st.caption("Data made available by [SAP Datasphere](https://github.com/SAP-samples/datasphere-content/tree/main/Sample_Bikes_Sales_content)")

### Filters ###
col1, col2 = st.columns(2)

with col1:
    try:
        start_date, end_date = st.date_input(
            'Select date range', 
            (df['createdat'].min(), df['createdat'].max()),
            min_value=df['createdat'].min(),
            max_value=df['createdat'].max()
        )
    except ValueError:
        start_date = df['createdat'].min()  # or another default value
        end_date = df['createdat'].max()


company = df['companyname'].unique().tolist()
company.insert(0, 'All')


with col2:
    company = st.selectbox('Select company', options = company)

    if company != 'All':
        filtered_df = df[df['companyname'] == company]
    else:
        filtered_df = df


filtered_df = filtered_df[
    (filtered_df['createdat'] >= pd.to_datetime(start_date)) & 
    (filtered_df['createdat'] <= pd.to_datetime(end_date))
]

### Median Time Frame ###
date_df = df[
    (df['createdat'] >= pd.to_datetime(start_date)) & 
    (df['createdat'] <= pd.to_datetime(end_date))
]

mean_transactions = date_df.groupby('companyname')['salesorderid'].count().mean()
mean_products = date_df.groupby('companyname')['quantity'].sum().mean()
mean_revenue = date_df.groupby('companyname')['grossamount_item'].sum().mean()

# Get top product
top_product = filtered_df.groupby('short_descr').agg({'quantity': 'sum'}).idxmax()[0]

st.markdown("---") 
### Second Title ###
if company != 'All':
    st.write(f"## {company} Overview")

### KPIs ####

st.write("### Performance")
st.caption("Shows the totals the selected company. Comparisons are made against the mean for the selected time frame.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if company != 'All':
        st.metric(label="Total Transactions", value=f"{len(filtered_df):,.0f}", delta=f"{len(filtered_df) - mean_transactions:,.0f}")
    else:
        st.metric(label="Total Transactions", value=f"{len(filtered_df):,.0f}")

with col2:
    if company != 'All':
        st.metric(label="Total Products Sold", value=f"{filtered_df['quantity'].sum():,.0f}", delta=f"{filtered_df['quantity'].sum() - mean_products:,.0f}")
    else:
        st.metric(label="Total Products Sold", value=f"{filtered_df['quantity'].sum():,.0f}")

with col3:
    if company != 'All':
        st.metric(label="Revenue", value=f"${filtered_df['grossamount_item'].sum():,.0f}", delta=f"{(filtered_df['grossamount_item'].sum() - mean_revenue):,.0f}")
    else:
        st.metric(label="Revenue", value=f"${filtered_df['grossamount_item'].sum():,.0f}")

with col4:
    st.metric(label="Top Product", value=top_product)

### Visualizations ###
st.markdown("---") 
col1, col2 = st.columns(2)


### Bar Chart ###
if company != 'All':
    bar_df = filtered_df.groupby('short_descr').agg({'quantity': 'sum'}).reset_index()
    bar_df = bar_df.sort_values('quantity', ascending=False)

    # Create the bar chart using Altair
    chart = alt.Chart(bar_df).mark_bar().encode(
        x=alt.X('quantity:Q', title='Quantity'),
        y=alt.Y('short_descr:N', title = 'Bike Type', sort='-x')  # Sort y-axis based on the quantity values
    ).properties(
        title="Quantity by Bike Type",
        height=400
    )
else:
    bar_df = filtered_df.groupby(['short_descr', 'companyname']).agg({'quantity': 'sum'}).reset_index()
    bar_df = bar_df.sort_values('quantity', ascending=False)

    # Create the bar chart using Altair
    chart = alt.Chart(bar_df).mark_bar().encode(
        x=alt.X('quantity:Q', title='Quantity'),
        y=alt.Y('companyname:N', title = "Company Name" , sort='-x'),
        color='short_descr:N'  # Sort y-axis based on the quantity values
    ).properties(
        title="Quantity by Company",
        height=400 
    )

with col1:
    st.altair_chart(chart, use_container_width=True)

### Area Chart ### 
area_df = filtered_df.groupby(['short_descr' ,'createdat']).agg({'grossamount_item': 'sum'}).reset_index()
area_df = area_df.sort_values(['createdat', 'short_descr'])
area_df['createdat'] = pd.to_datetime(area_df['createdat'])

area_df = area_df.set_index(['short_descr', 'createdat'])

min_date = area_df.index.get_level_values('createdat').min()
max_date = area_df.index.get_level_values('createdat').max()

# reindex by 'short_descr' for the full date range (needed for cumulative sum)
full_idx = pd.MultiIndex.from_product(
    [area_df.index.get_level_values('short_descr').unique(), 
     pd.date_range(min_date, max_date)],
    names=['short_descr', 'createdat']
)

area_df = area_df.reindex(full_idx, fill_value=0).reset_index()

area_df['cumulative_sum'] = area_df.groupby('short_descr')['grossamount_item'].cumsum()

chart = alt.Chart(area_df).mark_area(opacity=0.9).encode(
    x=alt.X('createdat:T', title='Date'),
    y=alt.Y('cumulative_sum:Q', title='Cumulative Revenue'),
    color='short_descr:N',
).properties(
    title="Cumulative Revenue by Bike Type",
    height=400
)

with col2:
    st.altair_chart(chart, use_container_width=True)

### Map ###
st.write("### Company Map")
st.caption("Shows the location of the companies. Size by amount spent. The selected company is highlighted in green.")
map_df = df.groupby(['latitude', 'longitude', 'companyname']).agg({'grossamount_item': 'sum', 'quantity': 'sum'}).reset_index()
map_df['highlight'] = map_df['companyname'].apply(lambda x: [170/255, 245/255, 66/255, 0.7] if x == company else [250/255, 95/255, 255/255, 0.5])
st.map(map_df, latitude='latitude', longitude='longitude', size='grossamount_item', color='highlight')

st.markdown("---")
### Table ###
st.write("### Data Table")
st.dataframe(filtered_df[['salesorderid', 'createdat', 'companyname', 'short_descr', 'quantity', 'grossamount_item']], use_container_width=True)
