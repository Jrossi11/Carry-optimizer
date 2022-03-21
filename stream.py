import streamlit as st
import time
import pandas as pd
import plotly.express as px
import hmac
import requests
st.set_page_config(layout="wide")


#col1, col2 = st.columns([1, 2])
st.title('FTX Carry trade optimizer')
plot_slot = st.empty()
df_slot = st.empty()

endpoint = 'https://ftx.com/api'
all_markets = requests.get(f'{endpoint}/markets').json()
all_markets = pd.DataFrame(all_markets['result'])
all_markets.set_index('name', inplace=True)

def filter_availables(df, inst):
    df = df[(df.index.str.contains(inst)) & (df.underlying == inst)]
    df = df[~df.index.str.contains('MOVE')][['price']]
    return df

def calculate_rates(df, coin, rates):
    mats = [i.split('-')[1] for i in df.index]
    for maturity in mats[1:]:
        delivery_date = pd.to_datetime(f'{maturity[-2:]}-{maturity[:2]}-2022')
        days_to_delivery = (delivery_date - pd.to_datetime('today')).days
        rates.loc[f'{coin}-{maturity}', 'Direct rate'] = (df.loc[f'{coin}-{maturity}','price']/df.loc[f'{coin}-PERP','price'] - 1) * 100
        rates.loc[f'{coin}-{maturity}', 'Annualized rate'] = (((1+rates.loc[f'{coin}-{maturity}', 'Direct rate']/100)**(365/days_to_delivery))-1)*100
    return rates

def main():
    while True:
        all_futures = all_markets[all_markets['type']=='future'][['price', 'underlying']]
        instruments = list(set([i.split('-')[0] for i in all_futures.index]))

        rates = pd.DataFrame()
        for coin in instruments:
            df = filter_availables(all_futures, coin)
            if len(df.index) > 2:
                rates = calculate_rates(df, coin, rates)
                
        top = rates.sort_values(by='Annualized rate', ascending=False)
        top['Instrument'] = top.index
        top['Coin'] = [i.split('-')[0] for i in top.index]
        top['Maturity'] = [pd.to_datetime(f'{i.split("-")[1][-2:]}-{i.split("-")[1][:2]}-2022') for i in top.index]
        top['Days to maturity'] = [(top['Maturity'][i]-pd.to_datetime('today')).days for i in range(len(top))]
        top['Maturity'] = [str(top['Maturity'][i])[2:10] for i in range(len(top))]

        top.index = list(range(1,1+len(top)))
        top = top[['Coin', 'Days to maturity', 'Direct rate', 'Annualized rate', 'Instrument']]

        df_slot.dataframe(top, width=1500, height=600)
        principals = rates[(rates.index.str.contains('BTC')) | rates.index.str.contains('ETH')]

        fig = px.line(top[:10], x='Instrument', y= 'Annualized rate', width=1000, height=600,
                    color_discrete_sequence = ['orange','red'], title='Rates')
        #fig.update_xaxes(showgrid=False)  
        #fig.update_yaxes(showgrid=False)

        plot_slot.plotly_chart(fig)
        time.sleep(10)
        yield

def event_loop(tareas):
    while tareas:
        actual = tareas.pop(0)
        try:
            next(actual)
            tareas.append(actual)
        except StopIteration:
            pass
        
event_loop([main()])