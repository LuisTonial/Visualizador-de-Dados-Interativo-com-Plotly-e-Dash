import base64
import io
from dash import Dash, html, dcc, Input, Output, State, callback_context
import plotly.express as px
import pandas as pd

# --- Inicialização do App ---
app = Dash(__name__)

# --- Layout do Aplicativo ---
app.layout = html.Div([
    # Componente para armazenar os dados do usuário em formato JSON
    dcc.Store(id='stored-data'),

    # Título
    html.H1("Visualizador de Dados Interativo", style={'textAlign': 'center'}),

    # --- Seção de Carregamento de Dados ---
    html.Div([
        html.H3("Passo 1: Carregue seus dados"),
        # Opção 1: Upload de um arquivo local
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Arraste e solte ou ', html.A('selecione um arquivo')]),
            style={
                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed',
                'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px 0'
            },
            multiple=False # Permitir apenas um arquivo por vez
        ),
        # Opção 2: Carregar um Link (URL)
        html.Div([
            dcc.Input(id='input-url', type='text', placeholder='Ou cole o link para um CSV aqui...', style={'width': '80%'}),
            html.Button('Carregar Link', id='load-url-button', n_clicks=0, style={'width': '19%', 'float': 'right'})
        ]),
        # Div para mostrar o status do carregamento
        html.Div(id='output-data-upload-status', style={'marginTop': '10px'})

    ], style={'width': '50%', 'margin': 'auto', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),


    # --- Seção de Visualização (só aparece depois que os dados são carregados) ---
    html.Div(id='visualization-container', children=[
        html.H3("Passo 2: Explore a visualização", style={'textAlign': 'center', 'marginTop': '20px'}),
        # Painel de Controle (Dropdowns para eixos e tipo de gráfico)
        html.Div([
            html.Div([
                html.Label("Eixo X:"),
                dcc.Dropdown(id='xaxis-dropdown'),
            ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Eixo Y:"),
                dcc.Dropdown(id='yaxis-dropdown'),
            ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Tipo de Gráfico:"),
                dcc.Dropdown(
                    id='chart-type-dropdown',
                    options=[
                        {'label': 'Dispersão', 'value': 'scatter'},
                        {'label': 'Linha', 'value': 'line'},
                        {'label': 'Barras', 'value': 'bar'},
                        {'label': 'Histograma', 'value': 'histogram'},
                        {'label': 'Pizza', 'value': 'pie'}
                    ],
                    value='scatter'
                ),
            ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        ], style={'textAlign': 'center'}),
        
        # O Gráfico Principal
        dcc.Graph(id='main-graph'),
    ], style={'display': 'none'}) # Começa invisível
])


# --- Funções Auxiliares ---
def parse_contents(contents, filename):
    """Função para processar o conteúdo do arquivo carregado."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume que é um arquivo CSV
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume que é um arquivo Excel
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None, f"Tipo de arquivo '{filename}' não suportado."
        return df, f"Arquivo '{filename}' carregado com sucesso!"
    except Exception as e:
        print(e)
        return None, "Ocorreu um erro ao processar o arquivo."


# --- Callbacks ---

# 1. Callback para carregar os dados (do upload ou URL) e guardá-los no dcc.Store
@app.callback(
    Output('stored-data', 'data'),
    Output('output-data-upload-status', 'children'),
    Input('upload-data', 'contents'),
    Input('load-url-button', 'n_clicks'),
    State('upload-data', 'filename'),
    State('input-url', 'value'),
    prevent_initial_call=True
)
def update_data_store(contents, n_clicks, filename, url):
    ctx = callback_context
    triggered_id = ctx.triggered_id

    df = None
    status_message = ""

    if triggered_id == 'upload-data' and contents is not None:
        df, status_message = parse_contents(contents, filename)
    elif triggered_id == 'load-url-button' and url:
        try:
            df = pd.read_csv(url)
            status_message = f"Dados carregados com sucesso do link!"
        except Exception as e:
            status_message = f"Erro ao carregar do link: {e}"
            
    if df is not None:
        # Converte o dataframe para JSON para poder ser armazenado no dcc.Store
        return df.to_json(date_format='iso', orient='split'), html.P(status_message, style={'color': 'green'})
    else:
        return None, html.P(status_message, style={'color': 'red'})


# 2. Callback para atualizar os menus dropdown e mostrar o container de visualização
@app.callback(
    Output('visualization-container', 'style'),
    Output('xaxis-dropdown', 'options'),
    Output('yaxis-dropdown', 'options'),
    Output('xaxis-dropdown', 'value'),
    Output('yaxis-dropdown', 'value'),
    Input('stored-data', 'data')
)
def update_dropdowns_and_visibility(jsonified_dataframe):
    if jsonified_dataframe is None:
        # Se não houver dados, esconde a área de visualização
        return {'display': 'none'}, [], [], None, None

    # Converte os dados JSON de volta para um dataframe
    df = pd.read_json(jsonified_dataframe, orient='split')
    columns = [{'label': i, 'value': i} for i in df.columns]
    
    # Define os valores iniciais para os eixos X e Y
    initial_x = df.columns[0] if len(df.columns) > 0 else None
    initial_y = df.columns[1] if len(df.columns) > 1 else None

    # Mostra a área de visualização e preenche os dropdowns
    return {'display': 'block'}, columns, columns, initial_x, initial_y


# 3. Callback para atualizar o gráfico principal
@app.callback(
    Output('main-graph', 'figure'),
    Input('stored-data', 'data'),
    Input('xaxis-dropdown', 'value'),
    Input('yaxis-dropdown', 'value'),
    Input('chart-type-dropdown', 'value')
)
def update_graph(jsonified_dataframe, xaxis_col, yaxis_col, chart_type):
    if jsonified_dataframe is None or not xaxis_col or not yaxis_col:
        # Retorna um gráfico vazio se não houver dados ou seleção
        return {}

    df = pd.read_json(jsonified_dataframe, orient='split')
    
    # Cria o gráfico com base no tipo selecionado
    if chart_type == 'scatter':
        fig = px.scatter(df, x=xaxis_col, y=yaxis_col)
    elif chart_type == 'line':
        fig = px.line(df, x=xaxis_col, y=yaxis_col)
    elif chart_type == 'bar':
        fig = px.bar(df, x=xaxis_col, y=yaxis_col)
    elif chart_type == 'histogram':
        # Histograma usa apenas o eixo X
        fig = px.histogram(df, x=xaxis_col)
    elif chart_type == 'pie':
        # Gráfico de pizza precisa de nomes e valores
        fig = px.pie(df, names=xaxis_col, values=yaxis_col)
    else:
        fig = {}

    fig.update_layout(transition_duration=500)
    return fig


# --- Executar o Aplicativo ---
if __name__ == '__main__':
    app.run(debug=True)