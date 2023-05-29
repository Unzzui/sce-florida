import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import os
from flask import Flask, send_file
import calendar
from datetime import datetime as dt
import numpy as np
import io
from werkzeug.serving import run_simple
from dash.dependencies import Input, Output, State
import json
import plotly.io as pio
import matplotlib.colors as mcolors


# Leer el archivo CSV utilizando pandas
df = pd.read_csv('data/data.csv', delimiter=";")
with open('data/all.geojson', 'r') as f:
    data = json.load(f)
# Filtrar solo por Florida
df = df[df['Zonal'] == 'Florida']

# Convertir las fechas numéricas al formato adecuado
df['Fecha Ejecución del Ticket'] = pd.to_datetime(
    df['Fecha Ejecución del Ticket'], origin='1899-12-30', unit='D')
df['Fecha de Inspección'] = pd.to_datetime(
    df['Fecha de Inspección'], origin='1899-12-30', unit='D')


# Reemplazar las comas por puntos y eliminar caracteres no numéricos
df['Cumplimiento'] = df['Cumplimiento'].str.replace(
    ',', '.').replace('[^\d.]', '', regex=True)

# Convertir la columna 'Cumplimiento' a tipo numérico
df['Cumplimiento'] = pd.to_numeric(df['Cumplimiento'], errors='coerce')


opciones_mes = [{'label': mes.capitalize(), 'value': mes}
                for mes in df['Mes Ejecución del Ticket'].unique()]
opciones_ano = [{'label': str(ano), 'value': str(ano)}
                for ano in df['Año ejecución ticket'].unique()]

# Obtener el porcentaje de cumplimiento por fecha de ejecución del ticket
df_grouped = df.groupby('Fecha Ejecución del Ticket')[
    'Cumplimiento'].mean().reset_index()

# Obtener el porcentaje de cumplimiento por supervisor
df_grouped_supervisor = df.groupby('Jefe de Equipo')[
    'Cumplimiento'].mean().reset_index()

df_grouped_supervisor = df_grouped_supervisor.sort_values(
    by='Cumplimiento', ascending=True)

# Obtener el mes y año de cada una de las fechas
df['Mes'] = df['Fecha Ejecución del Ticket'].dt.month
df['Año'] = df['Fecha Ejecución del Ticket'].dt.year

# Se agrupa el mes y año relacionado a la ponderacion
df_grouped_month_year = df.groupby(['Mes', 'Año'])[
    'Cumplimiento'].mean().reset_index()

# Se adquiere la fecha maxima del registro
df_max_date = df["Fecha de Inspección"].max()
df_max_date_formatted = df_max_date.strftime('%d-%m-%Y')


# Número de inspecciones de trabajos ejecutados
num_inspecciones = len(df)

# Porcentaje de cumplimiento
porcentaje_cumplimiento = df['Cumplimiento'].mean()
porcentaje_cumplimiento_formatted = "{:.2%}".format(porcentaje_cumplimiento)

# Desviación estándar
desviacion_estandar = df['Cumplimiento'].std()
desviacion_estandar_formatted = "{:.2%}".format(desviacion_estandar)

# Coeficiente de variación

coeficiente_variacion = (desviacion_estandar / porcentaje_cumplimiento)
coeficiente_variacion_formatted = "{:.2%}".format(coeficiente_variacion)

# Obtener el mayor porcentaje de cumplimiento

mayor_cumplimiento = df['Cumplimiento'].max()
mayor_cumplimiento_formatted = "{:.0%}".format(mayor_cumplimiento)

numero_ticket_mayor = df.loc[df['Cumplimiento'].idxmax(), 'N Ticket']

# Obtener el menor porcentaje de cumplimiento
menor_cumplimiento = df['Cumplimiento'].min()
menor_cumplimiento_formatted = "{:.0%}".format(menor_cumplimiento)
numero_ticket_menor = df.loc[df['Cumplimiento'].idxmin(), 'N Ticket']


def supervisor_chart():
    figure = {
        'data': [
            go.Bar(
                x=df_grouped_supervisor['Jefe de Equipo'],
                y=df_grouped_supervisor['Cumplimiento'],
                orientation="v",
                marker=dict(color="rgba(56,250,251,1)"),
            )
        ],
        'layout': go.Layout(
            title="Porcentaje de Cumplimiento por Supervisor",
            xaxis=dict(
                title="Jefe de Equipo",
                tickangle=-45,
                tickfont=dict(size=8),
                gridcolor='#444444',
            ),
            yaxis=dict(
                title="Porcentaje de Cumplimiento %",
                gridcolor='#444444',
                tickformat='.0%',
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )
    }
    
    return figure



def map_fig():
    # Convertir la columna "Cumplimiento" a numérico y multiplicar por 100
    df['Cumplimiento'] = pd.to_numeric(
        df['Cumplimiento'], errors='coerce') * 100

    # Calcular el promedio de cumplimiento por comuna
    df_grouped_map = df.groupby('Comuna')['Cumplimiento'].mean().reset_index()

    # Redondear los valores de cumplimiento a 1 decimal
    df_grouped_map = df_grouped_map.round({'Cumplimiento': 1})

    # Ordenar el DataFrame por el valor de cumplimiento de manera descendente
    df_grouped_map = df_grouped_map.sort_values(
        by='Cumplimiento', ascending=False)

    # Obtener la lista de comunas presentes en el archivo CSV
    comunas_csv = df_grouped_map['Comuna'].tolist()

    # Generar la escala de colores manual con opacidad
    num_comunas = len(comunas_csv)
    color_start = (0, 255, 255)  # Cian brillante
    color_end = (255, 0, 0)  # Rojo
    colors = []
    for i in range(num_comunas):
        r = int(np.interp(i, [0, num_comunas-1],
                [color_start[0], color_end[0]]))
        g = int(np.interp(i, [0, num_comunas-1],
                [color_start[1], color_end[1]]))
        b = int(np.interp(i, [0, num_comunas-1],
                [color_start[2], color_end[2]]))
        color = f"rgba({r}, {g}, {b}, 0.4)"
        colors.append(color)

    # Crear el objeto de figura
    figure = go.Figure()

    # Iterar sobre cada comuna presente en el archivo CSV
    for i, comuna in enumerate(comunas_csv):
        # Buscar la correspondencia de la comuna en los datos GeoJSON
        for feature in data['features']:
            # Obtener el nombre de la comuna en la característica
            comuna_geojson = feature['properties']['NOM_COM']

            # Verificar si la comuna coincide
            if comuna == comuna_geojson:
                # Obtener el porcentaje de cumplimiento para la comuna
                cumplimiento = df_grouped_map.loc[df_grouped_map['Comuna']
                                                  == comuna, 'Cumplimiento'].values[0]

                # Obtener el color correspondiente al índice en la lista colors
                color = colors[i]

                # Extraer las coordenadas del polígono de la comuna
                coordinates = feature['geometry']['coordinates'][0]

                # Agregar el polígono a la figura con un color transparente para las comunas del archivo CSV
                figure.add_trace(go.Scattermapbox(
                    lat=[coord[1] for coord in coordinates],
                    lon=[coord[0] for coord in coordinates],
                    mode='lines',
                    line=dict(color='rgb(0, 0, 0)', width=2),  # Línea negra
                    fill='toself',
                    fillcolor=color,
                    hovertemplate=f'<b>{comuna}</b><br>Cumplimiento: {cumplimiento}%',
                ))
                break

    # Configurar el diseño del mapa
    figure.update_layout(
        mapbox=dict(
            accesstoken='pk.eyJ1IjoidW56enVpIiwiYSI6ImNsaHd2Y2t0ejBqd20zZ24wbjY1bHJoZWcifQ.7_2XYUlLBzkW6giVBSRC_Q',
            style='dark',
            center=dict(lat=-33.37, lon=-70.56),
            zoom=9,
        ),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )

    # Agregar la leyenda de colores como anotaciones
    min_cumplimiento = df_grouped_map['Cumplimiento'].min()
    max_cumplimiento = df_grouped_map['Cumplimiento'].max()
    annotations = [
        dict(
            xref='paper',
            yref='paper',
            x=1,
            y=0.8 - (i / 20),
            text=f'{comuna}: {cumplimiento}%',
            showarrow=False,
            font=dict(color="white")
        )
        for i, (comuna, cumplimiento) in enumerate(zip(comunas_csv, df_grouped_map['Cumplimiento']))
    ]
    figure.update_layout(annotations=annotations)

    return figure


# Application
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Dashboard SCE Florida"

server = app.server

external_stylesheets = ['styles.css']


# Define los KPIs
kpi1 = dbc.Card(
    dbc.CardBody([
        html.H4("N° Trabajos Ejecutados", className="card-title"),
        html.P(num_inspecciones, className="card-text h3")
    ]),
    color="primary",
    outline=True,
    className="mb-4"
)

kpi2 = dbc.Card(
    dbc.CardBody([
        html.H4("Porcentaje de Cumplimiento", className="card-title"),
        html.P(porcentaje_cumplimiento_formatted, className="card-text h3")
    ]),
    color="success",
    outline=True,
    className="mb-4"
)

kpi3 = dbc.Card(
    dbc.CardBody([
        html.H4("Desviación Estandar", className="card-title"),
        html.P(desviacion_estandar_formatted, className="card-text h3")
    ]),
    color="info",
    outline=True,
    className="mb-4"
)

kpi4 = dbc.Card(
    dbc.CardBody([
        html.H4("Coeficiente de variación", className="card-title"),
        html.P(coeficiente_variacion_formatted, className="card-text h3")
    ]),
    color="warning",
    outline=True,
    className="mb-4"
)

# Navbar
navbar = dbc.Navbar(
    children=[
        html.Script(src="https://code.jquery.com/jquery-3.5.1.min.js"),
        html.Script(
            src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(
            dbc.Nav(
                [
                    dbc.NavItem(dbc.NavLink(
                        html.A("Inicio", href="/#", className="nav-link-custom"))),
                    dbc.NavItem(dbc.NavLink(
                        html.A("Gráficos", href="/#charts", className="nav-link-custom"))),
                    dbc.NavItem(dbc.NavLink(html.A(
                        "Descargar Datos", href="/#descargar-seccion", className="nav-link-custom"))),
                    dbc.NavItem(dbc.NavLink(html.A(
                        "ODIS", href="https://odisdkp.firebaseapp.com", target="_blank", className="nav-link-custom"))),
                     dbc.NavItem(dbc.NavLink(html.A(
                        "OCA Global", href="https://ocaglobal.com/es", target="_blank", className="nav-link-custom"))),
                    dbc.NavItem(dbc.NavLink(html.A(
                        "Contacto", href="mailto:diego.bravo@ocaglobal.com?subject=Consulta%20SCE%20Florida", className="nav-link-custom"))),

                ],
                navbar=True,
                className="ml-auto mx-auto",
            ),
            id="navbar-collapse",
            navbar=True,
        ),
    ],
    color="dark",
    dark=True,
    sticky="top",
    className="w-100 h-1",


)

# Footer
footer_content = html.Div(
    [
        html.P("© 2023 OCA Global - ITO Enel. Todos los derechos reservados."),
        
        
        html.P(
        [
            "Información de contacto: ",
            html.A("diego.bravo@ocaglobal.com", href="mailto:diego.bravo@ocaglobal.com?subject=Consulta%20SCE%20Florida",style={'color': 'inherit', 'text-decoration': 'none'}),
            " | Teléfono: +56930532461"
        ]
    ),
        html.P(
            [
            "Dirección: " ,
            html.A("Av. Pedro de Valdivia 291, Santiago, Providencia, Región Metropolitana Piso 12.", href="https://goo.gl/maps/wHFFboKasQbkKVh28",target="_blank",style={'color': 'inherit', 'text-decoration': 'none'}),
               ],
        ),
    ]
)

# Aplica estilos al footer_content
footer_content_style = {
    'padding': '20px',
    'color': 'white',
    'background-color': '#303030',
    'text-align': 'center',
    'font-size': '14px',
}

# Define la función de callback para controlar el despliegue del menú
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


navbar_wrapper = html.Div(
    children=[
        navbar
    ],
    className="navbar-wrapper mx-auto text-center",

)


# Definir el diseño de la aplicación
app.layout = dbc.Container(
    id="app-container",
    fluid=True,
    style={'font-size':'18px'},
    children=[

        navbar_wrapper,
        html.Link(
            rel="icon",
            href="/assets/img/favicon.ico",
            type="image/x-icon"
        ),

        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Img(src=app.get_asset_url(
                            "../assets/img/log_oca.png"), style={"width": "50%"}),

                        html.Img(src=app.get_asset_url(
                            "../assets/img/log_enel.png"), style={"width": "40%", "margin-top": "-30px"}),
                    ],
                    style={"justify-content": "center", "margin-top": "40px"}
                ),
                width={"size": 6, "offset": 3}
            )
        ),

        dbc.Row(
            dbc.Col(html.H1("Servicio Calidad de Emergencias Florida",
                    className="text-center"),
                    width="auto"),
            justify="center",
            style={"margin-bottom": "2rem"},
        ),
        dbc.Col(
            html.P("El presente Dashboard muestra las inspecciones realizadas por OCA Global ITO Enel desde enero del año 2022. Incluye información sobre la cantidad de inspecciones a trabajos de cuadrillas de emergencia, el promedio ponderado del cumplimiento de las cuadrillas y la desviación estándar como criterio adicional para evaluar la variación de los datos en el periodo. Además, se presentan gráficos de cumplimiento por fecha, KPI's y cumplimiento por supervisor. También se ofrece la opción de descargar la información para realizar análisis personalizados y obtener una visión más detallada."),

        ),

        dbc.Row(
            dbc.Col(
                [
                    html.H2("KPIs"),
                    dbc.Row(
                        [
                            dbc.Col(kpi1, className="h-100",
                                    width=4, lg=4, sm=10, xs=10),
                            dbc.Col(kpi2, className="h-100",
                                    width=4, lg=4, sm=10, xs=10),
                            dbc.Col(kpi3, className="h-100",
                                    width=4, lg=4, sm=10, xs=10),
                        ],
                        justify="center",  # Centra los KPIs horizontalmente
                    ),
                ],
                className="mb-4 text-center",
            )
        ),
        dbc.Row(
            dbc.Col(
                [
                    html.H5(id='charts'),
                    html.P("1.- N° Trabajos Ejecutados: Este valor refleja la cantidad de inspecciones llevadas a cabo  en los trabajos realizados por las curadrillas de emergencia."),
                    html.P("2.- Porcentaje de Cumplimiento: Representa el promedio ponderado basado en diversos indicadores, evaluando el grado de cumplimiento de las cuadrillas en relación a los estándares establecidos."),
                    html.P("3.- Desviación Estándar: Esta medida indica la variación en el cumplimiento dentro del conjunto de datos. Una desviación estándar más cercana a 0% sugiere una menor variabilidad y consistencia en el cumplimiento de las cuadrillas."),
                    html.P(f"Datos actualizados al: {df_max_date_formatted}")
                ],
                width="auto"
            ),
            style={"margin-bottom": "2rem"}
        ),

          dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    [
                        dbc.Tab(label='Línea', tab_id='line-month'),
                        dbc.Tab(label="Barras", tab_id='bar-month'),
                    ],
                    id='grafico-type-month',
                    active_tab='line-month',
                ),
            ),
        ),
        dbc.Row(
            dbc.Col(
                dcc.Graph(id="month-figure"),
            )
        ),
            dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    [
                        dbc.Tab(label='Dispersión', tab_id='scatter'),
                        dbc.Tab(label='Línea', tab_id='line'),
                    ],
                    id='grafico-type',
                    active_tab='scatter',
                ),
            ),
        ),
        dbc.Row(
            dbc.Col(
                dcc.Graph(id="grafico-cumplimiento"),
            )
        ),
   
        dbc.Row(
            dbc.Col(html.H3(children="Records"), width="auto"),
            justify="center",
            style={"margin-top": "2rem", "margin-bottom": "1rem"}
        ),
        dbc.Row(
            html.P("En esta sección se encontraran los datos de menor y mayor ponderación correspondientes a las inspecciones realizadas. Estos registros representan los extremos en términos de cumplimiento dentro del conjunto de datos. Además, se proporciona el número de incidencia asociado a cada registro para facilitar su análisis y seguimiento correspondiente."),
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Menor Ponderación",
                                           className="text-center", ),
                            dbc.CardBody(
                                html.H2(
                                    children=menor_cumplimiento_formatted, className="text-center")
                            ),
                            dbc.CardFooter(children=numero_ticket_menor,)
                        ],
                        color="danger",
                    ),
                    width=3,
                    lg=3,
                    sm=5,
                    xs=7,
                    class_name="text-center",
                    style={"margin-top": "20px"},
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Mayor Ponderación",
                                           className="text-center"),
                            dbc.CardBody(
                                html.H2(
                                    children=mayor_cumplimiento_formatted, className="text-center")
                            ),
                            dbc.CardFooter(children=numero_ticket_mayor)
                        ],
                        color="info",
                    ),
                    width=3,
                    lg=3,
                    sm=5,
                    xs=7,
                    class_name="text-center",
                    style={"margin-top": "20px"},
                ),
            ],
            justify="center",
            class_name="mb-4"
        ),
        dbc.Row(
            dbc.Col(
                [
                    html.H3(children="Cumplimiento por Supervisores %"),
                    html.P(
                        "Es importante tener en cuenta que la información relacionada con los supervisores no abarca todos los datos, ya que se implementó después de marzo de 2023 el control de seguimiento de los trabajos realizados por cada supervisor. Por lo tanto, al tomar decisiones basadas en esta información, es necesario considerar que pueden existir desviaciones y se recomienda esperar al menos 6 meses para contar con datos más completos y precisos."
                    )
                ],
                width="auto",
                className="text-center",
            ),
            justify="center",
            style={"margin-bottom": "2rem", "margin-top": "40px"}
        ),
        dbc.Row(
        [
            dbc.Col(
                dcc.Graph(id="supervisor-figure", figure=supervisor_chart())
            )
        ]
    ),
        
        dbc.Row(
            dbc.Col(
                [
                    html.H3(children="Visualización del Cumplimiento por Comuna"),
                    html.P(
                        "El Mapa de Cumplimiento muestra el porcentaje de cumplimiento por comuna. Utiliza diferentes tonalidades de colores para resaltar las áreas con mayor y menor cumplimiento."
                    )
                ],
                width="auto",
                className="text-center",

            ),
            justify="center",
            style={"margin-bottom": "10px", "margin-top": "40px"}
        ),
        dbc.Row(
            dbc.Col(
                dcc.Graph(id="map-figure", figure=map_fig(),
                          style={'width': '100%', 'height': '90vh'}),
            )


        ),


        dbc.Row(
            dbc.Col(
                html.H3(children="Descargar Datos", id="descargar-seccion"),
                width="auto"
            ),
            justify="center",
            style={"margin-top": "5rem", "margin-bottom": "1rem"}
        ),
        dbc.Row(
            dbc.Col(
                html.P(
                    "Descarga la base de datos completa en formato CSV para acceder a todos los datos disponibles. Además, tienes la opción de descargar los datos en formato Excel, el cual corresponde al archivo adjunto enviado en el informe por correo."
                ),
                width="auto"
            ),
            justify="center",
            style={"margin-bottom": "1rem"}
        ),
        dbc.Row(
            dbc.Col(
                html.Div(
                    className="text-center my-4",
                    children=[
                        html.A(
                            html.Button(
                                "Descargar CSV", className="btn btn-info", style={"margin-right": "10px"}),
                            href="/download_csv"
                        ),
                        html.A(
                            html.Button("Descargar Excel",
                                        className="btn btn-info ml-10"),
                            href="/download_excel"
                        ),
                    ]
                ),
            ),
            justify="center"
        ),
        
        html.Div(
            footer_content,
            style=footer_content_style
        ),
    ],
    
)


# Callback para actualizar el gráfico según la opción seleccionada
@app.callback(
    Output("month-figure", "figure"),
    Input("grafico-type-month", "active_tab")
)
def month_line_chart(active_tab):
    # Filtrar por año 2022
    df_2022 = df[df['Año'] == 2022]
    df_grouped_month_year_2022 = df_2022.groupby(
        ['Mes', 'Año'])['Cumplimiento'].mean().reset_index()

    # Filtrar por año 2023
    df_2023 = df[df['Año'] == 2023]
    df_grouped_month_year_2023 = df_2023.groupby(
        ['Mes', 'Año'])['Cumplimiento'].mean().reset_index()

    # Crear la columna 'Mes' para cada DataFrame
    df_grouped_month_year_2022['Mes'] = df_grouped_month_year_2022['Mes'].apply(
        lambda month: calendar.month_abbr[month])
    df_grouped_month_year_2023['Mes'] = df_grouped_month_year_2023['Mes'].apply(
        lambda month: calendar.month_abbr[month])
    df_grouped_month_year_2022['Cumplimiento'] /= 100  
    df_grouped_month_year_2023['Cumplimiento'] /= 100  

    if active_tab == 'line-month':
        
    # Crear el gráfico de líneas
        figure = go.Figure(data=[
            go.Scatter(x=df_grouped_month_year_2022['Mes'], y=df_grouped_month_year_2022['Cumplimiento'],
                    name='2022', mode='lines', line=dict(color="rgba(56,250,251,1)")),
            go.Scatter(x=df_grouped_month_year_2023['Mes'], y=df_grouped_month_year_2023['Cumplimiento'],
                    name='2023', mode='lines', line=dict(color="rgba(255,127,14,1)"))
        ])

        figure.update_layout(
            title={ 
                'text': "Porcentaje de Cumplimiento por Mes y Año",
                'x': 0.5,  # Alineación horizontal en el centro
                'y': 0.9,  # Alineación vertical en la parte superior
                'xanchor': 'center',  # Alineación horizontal en el centro
                'yanchor': 'top'  # Alineación vertical en la parte superior
            },
            xaxis=dict(
                title="Mes",
                tickangle=-45,
                tickfont=dict(size=9),
                gridcolor='#444444'
            ),
            yaxis=dict(
                title="Porcentaje de Cumplimiento %",
                tickformat='.0%',
                gridcolor='#444444',

            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white")
        )
    elif active_tab == 'bar-month':
        figure = go.Figure(data=[
        go.Bar(x=df_grouped_month_year_2022['Mes'], y=df_grouped_month_year_2022['Cumplimiento'],
            name='2022', marker=dict(color="rgba(56,250,251,1)")),
        go.Bar(x=df_grouped_month_year_2023['Mes'], y=df_grouped_month_year_2023['Cumplimiento'],
            name='2023', marker=dict(color="rgba(255,127,14,1)"))
    ])

    figure.update_layout(
        title={
            'text': "Porcentaje de Cumplimiento por Mes y Año",
            'x': 0.5,
            'y': 0.9,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis=dict(
            title="Mes",
            tickangle=-45,
            tickfont=dict(size=9),
            gridcolor='#444444'
        ),
        yaxis=dict(
            title="Porcentaje de Cumplimiento %",
            tickformat='.0%',
            gridcolor='#444444',
           
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )
    return figure


# Callback para actualizar el gráfico según la opción seleccionada
@app.callback(
    Output("grafico-cumplimiento", "figure"),
    Input("grafico-type", "active_tab")
)
def update_grafico_cumplimiento(active_tab):
    if active_tab == "scatter":

        # Gráfico de dispersión
        figure = {
            'data': [
                go.Scatter(
                    x=df_grouped['Fecha Ejecución del Ticket'],
                    y=df_grouped['Cumplimiento'],
                    mode='markers',
                    marker=dict(size=8, color="rgba(56,250,251,1)"),
                )
            ],
            'layout': go.Layout(
                title="Porcentaje de Cumplimiento por día",
                xaxis=dict(
                    title="Fecha de Ejecución del Ticket",
                    tickformat="%d-%b-%Y",
                    dtick="M1",
                    tickangle=-45,
                    tickfont=dict(size=8),
                    gridcolor='#444444',
                ),
                yaxis=dict(
                    title="Porcentaje de Cumplimiento %",
                    tickformat='.0%',
                    gridcolor='#444444',
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
        }
    elif active_tab == "line":
        # Gráfico de líneas
        figure = {
            'data': [
                go.Scatter(
                    x=df_grouped['Fecha Ejecución del Ticket'],
                    y=df_grouped['Cumplimiento'],
                    mode='lines',
                    line=dict(color="rgba(56,250,251,1)"),
                )
            ],
            'layout': go.Layout(
                title="Porcentaje de Cumplimiento por día",
                xaxis=dict(
                    title="Fecha de Ejecución del Ticket",
                    tickformat="%d-%b-%Y",
                    dtick="M1",
                    tickangle=-45,
                    tickfont=dict(size=8),
                    gridcolor='#444444',
                ),
                yaxis=dict(
                    title="Porcentaje de Cumplimiento %",
                    gridcolor='#444444',
                    tickformat='.0%',
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
        }

    return figure


@app.server.route("/download_csv")
def download_csv():
    # Guardar el DataFrame en un archivo CSV en memoria
    csv_data = df.to_csv(index=False)

    # Crear un objeto de archivo en memoria utilizando io.BytesIO
    mem_file = io.BytesIO()
    mem_file.write(csv_data.encode())
    mem_file.seek(0)
    now = dt.now().strftime("%d-%m-%y")

    # Configurar los encabezados y opciones de descarga

    # Devolver el archivo CSV generado como respuesta
    return send_file(mem_file, mimetype="text/csv", as_attachment=True, download_name=f"data_{now}.csv")


@app.server.route("/download_excel")
def download_excel():
    # Reemplaza con la ruta real de tu archivo CSV
    excel_path = "data/Reporte_Ponderaciones_SCE.xlsx"
    return send_file(excel_path, as_attachment=True)

# Ejecutar la aplicación

if __name__ == "__main__":
    app.run_server(debug=True)
