import pandas as pd
import numpy as np
import requests

### Functions to get the data
def get_live_contracts():
    all_markets = requests.get('https://ftx.com/api/markets').json()
    all_markets = pd.DataFrame(all_markets['result'])
    all_markets.set_index('name', inplace=True)
    return all_markets

def get_expired():
    expired = requests.get('https://ftx.com/api/expired_futures').json()
    expired = pd.DataFrame(expired['result'])
    expired.set_index('name', inplace=True)
    return expired

def get_funding_rates():
    df = requests.get('https://ftx.com/api/funding_rates').json()
    df = pd.DataFrame(df['result'])
    df = df.set_index('time').sort_values(by='rate', ascending=False)
    df = df[df.index==max(df.index)]
    df = df[df.rate>0]
    return df
