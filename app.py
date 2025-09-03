import streamlit as st
import pandas as pd
import plotly.express as px
car_data = pd.read_csv('vehicles_us.csv')  # leer los datos
st.header('Exploratory Data Analysis')
st.write(car_data)
hist_button = st.button('Construir histograma')  # crear un botón
if hist_button:
    st.write(
        'Creación de un histograma para el conjunto de datos de anuncios de venta de coches')

    # crear un histograma
fig = px.histogram(car_data, x="odometer")

# mostrar un gráfico Plotly interactivo
st.plotly_chart(fig, use_container_width=True)
disp_button = st.button('Construir diagrama de dispersión')
if disp_button:
    st.write(
        'Creación de un diagrama de dispersión para el conjunto de datos de anuncios de venta de coches')

    # crear un diagrama de dispersión
    fig = px.scatter(car_data, x="odometer", y="price")

    # mostrar un gráfico Plotly interactivo
    st.plotly_chart(fig, use_container_width=True)
