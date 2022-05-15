import time
import pandas as pd
import plotly.express as px
import hmac
import requests

### Functions to get the data
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

def get_futures():
    endpoint = 'https://ftx.com/api'
    all_markets = requests.get(f'{endpoint}/markets').json()
    all_markets = pd.DataFrame(all_markets['result'])
    all_markets.set_index('name', inplace=True)
    all_futures = all_markets[all_markets['type']=='future'][['price', 'underlying']]
    return all_futures

def market_data(df):
    response = pd.DataFrame(requests.get(url='https://test.deribit.com/api/v2/public/ticker?instrument_name=BTC-PERPETUAL').json())[['result']]
    timestamp = str(pd.to_datetime(str(response.loc['timestamp'][0]), unit='ms'))[:-7]
    df.loc[timestamp,'price'] = response.loc['last_price'][0]
    
def d_rates(currencies):
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
    return rates[['Coin', 'Days to maturity', 'Direct rate', 'Annualized rate', 'Instrument', 'Exchange']]

def comparison_df(all_futures):
    rates = pd.DataFrame()
    for coin in list(set([i.split('-')[0] for i in all_futures.index])):
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
    deribit_rates = d_rates(['BTC', 'ETH', 'SOL'])
    top = top.append(deribit_rates)
    return top.sort_values(by='Annualized rate', ascending=False)
    
def get_instruments(coin):
    response = pd.DataFrame(requests.get(url=f'https://deribit.com/api/v2/public/get_instruments?currency={coin}&expired=false&kind=future').json())[['result']]
    return [pd.DataFrame(response.loc[i, 'result'], index=[0])['instrument_name'].values[0] for i in range(len(response))]

def get_price(instrument, df):
    response = pd.DataFrame(requests.get(url=f'https://deribit.com/api/v2/public/ticker?instrument_name={instrument}').json())[['result']]
    df.loc[instrument,'price'] = response.loc['last_price'][0]
    return df

def get_funding_rates():
    df = requests.get('https://ftx.com/api/funding_rates').json()
    df = pd.DataFrame(df['result'])
    df = df.set_index('time').sort_values(by='rate', ascending=False)
    df = df[df.index==max(df.index)]
    df = df[df.rate>0]
    df['Daily rate'] = df['rate']
    return df
