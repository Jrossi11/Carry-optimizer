import streamlit as st

from algo_functions import *
st.set_page_config(layout="wide")


#col1, col2 = st.columns([1, 2])
st.title('Carry trade optimizer')
plot_slot = st.empty()
df_slot = st.empty()
st.write('Top funding rates')

funding_rates_slot = st.empty()

def main():
    while True:
        basis_rates = comparison_df(get_futures())        
        
        df_slot.dataframe(basis_rates, width=1500, height=600)
        funding_rates_slot.dataframe(get_funding_rates())
        plot_slot.plotly_chart(px.line(basis_rates[:10], x='Instrument', y= 'Annualized rate',# width=1000, height=600,
                    color_discrete_sequence = ['orange','red'], title='Rates'))
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
