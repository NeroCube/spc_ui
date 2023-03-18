import os
import numpy as np
import plotly.express as px
import dash_bootstrap_components as dbc
from utils import get_history_data
from datetime import datetime, timedelta
from dash import Dash, dcc, html, Input, Output, ctx, dash_table

PAGE_SIZE = 5
dash_title = "SPC UI"
df = get_history_data(100,10)
debug = False if os.environ["DASH_DEBUG_MODE"] == "False" else True
external_stylesheets = [dbc.themes.BOOTSTRAP]
operators = [['ge ', '>='],
             ['le ', '<='],
             ['lt ', '<'],
             ['gt ', '>'],
             ['ne ', '!='],
             ['eq ', '='],
             ['contains '],
             ['datestartswith ']]

app = Dash(
    __name__, 
    title = dash_title, 
    suppress_callback_exceptions = True, 
    external_stylesheets = external_stylesheets
    )

app.layout = html.Div([
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H4(["Date Range"]), 
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        min_date_allowed=df["Inserted"].min().strftime('%Y-%m-%d'), 
                        max_date_allowed=df["Inserted"].max().strftime('%Y-%m-%d'),
                        initial_visible_month=df["Inserted"].min().strftime('%Y-%m-%d'),
                        start_date=df["Inserted"].min().strftime('%Y-%m-%d'),
                        end_date=df["Inserted"].max().strftime('%Y-%m-%d')
                    ), 
                ], width=3),
                dbc.Col([
                    html.H4(["Table"]),
                    dcc.Dropdown(id='dropdown-table',
                        options=df['Table'].sort_values().unique().tolist(),
                        multi=False,
                        value=df['Table'].sort_values().unique().tolist()[0],
                        placeholder='Select Table...',
                    ),
                ], width=3),
                dbc.Col([
                    html.Br(),
                    dbc.Button('Filter In', id='btn-filter-in', n_clicks=0),
                ], width=1),
                dbc.Col([
                    html.Br(),
                    dbc.Button('Filter Out', id='btn-filter-out', n_clicks=0),
                ], width=1),                
            ], align='center'), 
            html.Br(),
            dbc.Row([
                dbc.Col([
                    html.H4(["History Point"]), 
                    dcc.Graph(id = "fig-history", config={"displayModeBar": False})
                ]),
            ], align='center'), 
            html.Br(),
            dbc.Row([
                dbc.Col([
                    html.H4(["Selected Point"]), 
                    dash_table.DataTable(
                        id='table-selected',
                        columns=[
                            {"name": i, "id": i} for i in df.columns
                        ],
                        page_current=0,
                        page_size=PAGE_SIZE,
                        page_action='custom',
                        filter_action='custom',
                        filter_query='',
                        sort_action='custom',
                        sort_mode='multi',
                        sort_by=[]
                    )
                ]),
            ], align='center'),      
        ])
    )
])

def calculate_threshold(cdf):
    mean = cdf[cdf['Status']=='used']['Metric'].mean()
    std = cdf[cdf['Status']=='used']['Metric'].std()
    upper_limit = mean + 3 * std
    lower_limit = mean - 3 * std   
    return round(upper_limit, 2), round(lower_limit, 2)

def get_figure(dff, start_date, end_date, table, selectedpoints, selectedpoints_local, x_col="Inserted", y_col="Metric", t_col="PID"):
    df = dff.copy()
    if selectedpoints_local and selectedpoints_local["range"]:
        ranges = selectedpoints_local["range"]
        selection_bounds = {
            "x0": ranges["x"][0],
            "x1": ranges["x"][1],
            "y0": ranges["y"][0],
            "y1": ranges["y"][1],
        }
    else:
        selection_bounds = {
            "x0": np.min(df[x_col]),
            "x1": np.max(df[x_col]),
            "y0": np.min(df[y_col]),
            "y1": np.max(df[y_col]),
        }
    df = df[(df['Table']==table)
            &(df['Inserted']>=datetime.strptime(start_date, '%Y-%m-%d'))
            &(df['Inserted']<datetime.strptime(end_date, '%Y-%m-%d'))]
    fig = px.scatter(df, 
                     x=df[x_col], 
                     y=df[y_col], 
                     text=df[t_col], 
                     color='Status',
                     color_discrete_map= {'used':'#0085fa','ignore':'#b4cbe0'},
                     range_x=[
                        datetime.strptime(start_date, '%Y-%m-%d')-timedelta(hours=1),
                        datetime.strptime(end_date, '%Y-%m-%d')+timedelta(hours=1) 
                        ])

    fig.update_traces(marker={'size': 20})

    fig.update_layout(
        margin={"l": 20, "r": 0, "b": 15, "t": 5},
        dragmode="select",
        hovermode=False,
        newselection_mode="gradual",
    )

    fig.add_shape(
        dict(
            {"type": "rect", "line": {"width": 1, "dash": "dot", "color": "darkgrey"}},
            **selection_bounds
        )
    )
    upper_limit, lower_limit = calculate_threshold(df)
    fig.add_hline(y=upper_limit, line_width=2, line_dash="dot", 
                  annotation_text=f"Upper Bound:{upper_limit}",
                  annotation_position="bottom right")
    fig.add_hline(y=lower_limit, line_width=2, line_dash="dot",
                  annotation_text=f"Lower Bound:{lower_limit}",
                  annotation_position="bottom right")
    return fig

def get_table(df, table, selectedpoints, page_current, page_size, sort_by, filter_query):
        df = df[(df['PID'].isin(selectedpoints)) & (df['Table']==table)] 

        filtering_expressions = filter_query.split(' && ')
        dff = df
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)

            if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
                # these operators match pandas series operator method names
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == 'contains':
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == 'datestartswith':
                # this is a simplification of the front-end filtering logic,
                # only works with complete fields in standard format
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]

        if len(sort_by):
            dff = dff.sort_values(
                [col['column_id'] for col in sort_by],
                ascending=[
                    col['direction'] == 'asc'
                    for col in sort_by
                ],
                inplace=False
            )

        return dff.iloc[
            page_current*page_size:(page_current+ 1)*page_size
        ].to_dict('records')

def update_status(btn_name, selectedpoints, table):
    selected_list = df[(df['PID'].isin(selectedpoints)) & (df['Table']==table)]['PID'].tolist()
    if btn_name == "btn-filter-in":
        df.loc[df['PID'].isin(selected_list), ['Status']] = 'used'
    elif btn_name == "btn-filter-out":
        df.loc[df['PID'].isin(selected_list), ['Status']] = 'ignore'

def split_filter_part(filter_part):
    for operator_type in operators:
        for operator in operator_type:
            if operator in filter_part:
                name_part, value_part = filter_part.split(operator, 1)
                name = name_part[name_part.find('{') + 1: name_part.rfind('}')]

                value_part = value_part.strip()
                v0 = value_part[0]
                if (v0 == value_part[-1] and v0 in ("'", '"', '`')):
                    value = value_part[1: -1].replace('\\' + v0, v0)
                else:
                    try:
                        value = float(value_part)
                    except ValueError:
                        value = value_part

                # word operators need spaces after them in the filter string,
                # but we don't want these later
                return name, operator_type[0].strip(), value

    return [None] * 3

@app.callback(
    Output("fig-history", "figure"),
    Output('table-selected', "data"),
    Output('table-selected', "page_current"),
    Input("fig-history", "selectedData"),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('dropdown-table', 'value'),
    Input('btn-filter-in', "n_clicks"),
    Input('btn-filter-out', "n_clicks"),
    Input('table-selected', "page_current"),
    Input('table-selected', "page_size"),
    Input('table-selected', "sort_by"),
    Input('table-selected', "filter_query")
)
def callback(selection, start_date, end_date, table, filter_in, filter_out, page_current, page_size, sort_by, filter_query):
    selectedpoints = df['PID']
    if ctx.triggered_id == 'dropdown-table':
        selection = None
    if ctx.triggered_id == 'fig-history':
        page_current = 0
    if selection and selection["points"]:
        selectedpoints = np.intersect1d(
            selectedpoints, [p["text"] for p in selection["points"]]
        )
    
    update_status(ctx.triggered_id, selectedpoints, table)
    
    return [
        get_figure(df, start_date, end_date, table, selectedpoints, selection),
        get_table(df, table, selectedpoints, page_current, page_size, sort_by, filter_query),
        page_current]
if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8050", debug=debug)
