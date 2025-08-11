import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Sample data
df = px.data.gapminder()

# Initialize Dash app
app = dash.Dash(__name__)

# Layout
app.layout = html.Div([
    html.H1("Dash Plotly Example"),
    dcc.Dropdown(
        id='country-dropdown',
        options=[{'label': country, 'value': country} for country in df['country'].unique()],
        value='India',
        clearable=False
    ),
    dcc.Graph(id='line-chart')
])

# Callback to update graph
@app.callback(
    Output('line-chart', 'figure'),
    [Input('country-dropdown', 'value')]
)
def update_graph(selected_country):
    filtered_df = df[df['country'] == selected_country]
    fig = px.line(filtered_df, x='year', y='gdpPercap', title=f'GDP per Capita of {selected_country}')
    fig.show()
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True,port=8050)
