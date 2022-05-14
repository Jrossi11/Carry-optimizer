import streamlit as st
import time
import pandas as pd
import plotly.express as px
import hmac
import requests
from algo_functions import *
st.set_page_config(layout="wide")


#col1, col2 = st.columns([1, 2])
st.title('Carry trade optimizer')
plot_slot = st.empty()
df_slot = st.empty()
deribit_slot = st.empty()
funding_rates_slot = st.empty()

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
        if days_to_delivery>0:
            rates.loc[f'{coin}-{maturity}', 'Annualized rate'] = (((1+rates.loc[f'{coin}-{maturity}', 'Direct rate']/100)**(365/days_to_delivery))-1)*100
    return rates

def market_data(df):
    response = pd.DataFrame(requests.get(url='https://test.deribit.com/api/v2/public/ticker?instrument_name=BTC-PERPETUAL').json())[['result']]
    timestamp = str(pd.to_datetime(str(response.loc['timestamp'][0]), unit='ms'))[:-7]
    df.loc[timestamp,'price'] = response.loc['last_price'][0]

def get_instruments(coin):
    response = pd.DataFrame(requests.get(url=f'https://test.deribit.com/api/v2/public/get_instruments?currency={coin}&expired=false&kind=future').json())[['result']]
    return [pd.DataFrame(response.loc[i, 'result'], index=[0])['instrument_name'].values[0] for i in range(len(response))]

def get_price(instrument, df):
    response = pd.DataFrame(requests.get(url=f'https://test.deribit.com/api/v2/public/ticker?instrument_name={instrument}').json())[['result']]
    df.loc[instrument,'price'] = response.loc['last_price'][0]
    return df

def deribit_rates(currencies):
    rates = pd.DataFrame()
    for currency in currencies:
        quotes = pd.DataFrame()
        instruments = get_instruments(currency)
        for instrument in instruments:
            get_price(instrument, quotes)
        for i in quotes.index:
            if 'PERPETUAL' not in i:
                rates.loc[i, 'Coin'] = currency
                rates.loc[i, 'Exchange'] = 'Deribit'
                rates.loc[i,'Direct rate'] = (quotes.loc[i,'price'] / quotes.loc[f'{currency}-PERPETUAL','price']-1)*100
                rates.loc[i, 'Maturity'] = pd.to_datetime(i.split('-')[1])
                rates.loc[i, 'Days to maturity'] = (rates.loc[i, 'Maturity']-pd.to_datetime('today')).days
                if rates.loc[i, 'Days to maturity']>0:
                    rates.loc[i, 'Annualized rate'] = (((1+rates.loc[i, 'Direct rate']/100)**(365/rates.loc[i, 'Days to maturity']))-1)*100
                
    rates = rates.sort_values(by='Annualized rate', ascending=False)
    rates['Instrument'] = rates.index
    rates.index = list(range(1,len(rates)+1))
    return  rates[['Coin', 'Days to maturity', 'Direct rate', 'Annualized rate', 'Instrument', 'Exchange']]


def main():
    while True:
        all_futures = all_markets[all_markets['type']=='future'][['price', 'underlying']]
        instruments = list(set([i.split('-')[0] for i in all_futures.index]))
        
        funding_rates = get_funding_rates()
        
        rates = pd.DataFrame()
        for coin in instruments:
            df = filter_availables(all_futures, coin)
            if len(df.index) > 1:
                rates = calculate_rates(df, coin, rates)
                
        top = rates.sort_values(by='Annualized rate', ascending=False)
        top['Instrument'] = top.index
        top['Coin'] = [i.split('-')[0] for i in top.index]
        top['Maturity'] = [pd.to_datetime(f'{i.split("-")[1][-2:]}-{i.split("-")[1][:2]}-2022') for i in top.index]
        top['Days to maturity'] = [(top['Maturity'][i]-pd.to_datetime('today')).days for i in range(len(top))]
        top['Maturity'] = [str(top['Maturity'][i])[2:10] for i in range(len(top))]
        top['Exchange'] = 'FTX'

        top.index = list(range(1,1+len(top)))
        top = top[['Coin', 'Days to maturity', 'Direct rate', 'Annualized rate', 'Instrument', 'Exchange']]

        d_rates = deribit_rates(['BTC', 'ETH'])
        top = top.append(d_rates)
        top = top.sort_values(by='Annualized rate', ascending=False)
        df_slot.dataframe(top, width=1500, height=600)
        
        funding_rates_slot.dataframe(funding_rates)
        
        principals = rates[(rates.index.str.contains('BTC')) | rates.index.str.contains('ETH')]

        fig = px.line(top[:10], x='Instrument', y= 'Annualized rate',# width=1000, height=600,
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
