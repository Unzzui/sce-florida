import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import csv
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from flask import send_file
import calendar
from datetime import datetime as dt
import numpy as np
import io
from app import initial_app

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Img(src="assets/logo_1.png", style={"width": "50%"}),
                        html.Img(src="assets/logo_enel.png", style={"width": "40%", "margin-top": "-30px"}),
                    ],
                    style={"justify-content": "center"}
                ),
                width={"size": 6, "offset": 3}
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H2('Inicio de sesión', className='text-center mb-4'),
                        dbc.Input(
                            id='input-usuario',
                            type='text',
                            placeholder='Nombre de usuario',
                            className='mb-3',
                        ),
                        dbc.Input(
                            id='input-contrasena',
                            type='password',
                            placeholder='Contraseña',
                            className='mb-3',
                        ),
                        dbc.Button(
                            'Iniciar sesión',
                            id='boton-iniciar',
                            color='primary',
                            className='text-center mb-3 btn-block',
                        ),
                        html.Div(id='mensaje', className='text-center'),
                        dcc.Location(id='url', refresh=False),  # Agregado: Location para redirección
                    ],
                    style={'max-width': '400px', 'margin': '0 auto'},
                ),
                width={'size': 6, 'offset': 3},
                className='mt-5',
            )
        ),
    ]
)

@app.callback(
    Output('url', 'pathname'),  # Cambiado: Redireccionar a la propiedad 'pathname' de dcc.Location
    [Input('boton-iniciar', 'n_clicks')],
    [State('input-usuario', 'value'), State('input-contrasena', 'value')]
)
def gestionar_sesion(n_clicks_iniciar, usuario, contrasena):
    if n_clicks_iniciar:
        with open('usuarios.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Correo'] == usuario and row['Contraseña'] == contrasena:
                    # Iniciar sesión exitosa, redirigir al dashboard
                    return '/dashboard'
        
        return PreventUpdate #Evitar actualización si no se cumple la condición


@app.callback(Output('mensaje', 'children'), [Input('url', 'pathname')])
def render_page_content(pathname):
    if pathname == '/dashboard':
        return initial_app()
    else:
        return html.Div()


if __name__ == '__main__':
    app.run_server(debug=True)
