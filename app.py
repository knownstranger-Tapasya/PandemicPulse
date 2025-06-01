from flask import Flask
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
from datetime import datetime, timedelta

# Initialize Flask
server = Flask(__name__)

# Initialize the Dash app with Flask server
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[
        dbc.themes.DARKLY,  # Default theme
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css"  # Font Awesome icons
    ],
    url_base_pathname='/dash/',
    suppress_callback_exceptions=True  # Add this to handle dynamic callbacks
)
app.title = "COVID-19 Analytics Dashboard"

# Cache for storing fetched data
data_cache = {
    'data': None,
    'last_fetch': None
}

# Theme-specific styles
THEME_STYLES = {
    'DARKLY': {
        'bg_color': '#303030',
        'text_color': '#ffffff',
        'muted_color': '#888888',
        'card_bg': '#444444',
        'primary_color': '#375a7f',
        'success_color': '#00bc8c',
        'warning_color': '#f39c12',
        'danger_color': '#e74c3c',
        'info_color': '#3498db',
        'chart_bg': 'rgba(48, 48, 48, 0.8)',
        'hover_bg': 'rgba(255, 255, 255, 0.1)',
        'icon': 'fas fa-sun',  # Sun icon for light mode switch
        'theme': dbc.themes.DARKLY
    },
    'FLATLY': {
        'bg_color': '#ffffff',
        'text_color': '#2c3e50',
        'muted_color': '#95a5a6',
        'card_bg': '#f8f9fa',
        'primary_color': '#2c3e50',
        'success_color': '#18bc9c',
        'warning_color': '#f39c12',
        'danger_color': '#e74c3c',
        'info_color': '#3498db',
        'chart_bg': 'rgba(255, 255, 255, 0.8)',
        'hover_bg': 'rgba(0, 0, 0, 0.05)',
        'icon': 'fas fa-moon',  # Moon icon for dark mode switch
        'theme': dbc.themes.FLATLY
    }
}

def calculate_trend(current, previous):
    """Calculate percentage trend with proper error handling"""
    try:
        if previous == 0 or previous is None:
            return 0
        return ((current - previous) / previous) * 100
    except (TypeError, ZeroDivisionError):
        return 0

def safe_division(a, b, default=0):
    """Safely divide two numbers, returning default if division is not possible"""
    try:
        if b == 0 or b is None:
            return default
        return a / b
    except (TypeError, ZeroDivisionError):
        return default

def fetch_covid_data(force=False):
    """Fetch data with caching and error handling"""
    now = datetime.now()
    
    # Return cached data if it's less than 15 minutes old (increased from 5 minutes)
    if not force and data_cache['data'] is not None and data_cache['last_fetch'] is not None:
        if (now - data_cache['last_fetch']).total_seconds() < 900:  # 15 minutes
            return data_cache['data']
    
    try:
        # Use a session for connection pooling
        session = requests.Session()
        
        # Set timeout for requests
        timeout = 10  # seconds
        
        # Current data
        url = "https://disease.sh/v3/covid-19/countries"
        response = session.get(url, timeout=timeout)
        data = response.json()
        
        # Yesterday's data for trends
        yesterday_url = "https://disease.sh/v3/covid-19/countries?yesterday=true"
        yesterday_response = session.get(yesterday_url, timeout=timeout)
        yesterday_data = yesterday_response.json()
        
        # Get global data for timestamp and trends
        global_data = session.get('https://disease.sh/v3/covid-19/all', timeout=timeout).json()
        global_yesterday = session.get('https://disease.sh/v3/covid-19/all?yesterday=true', timeout=timeout).json()
        
        # Close the session
        session.close()
        
        # Process data using numpy for better performance
        countries = []
        cases_data = []
        active_data = []
        recovered_data = []
        deaths_data = []
        tests_data = []
        population_data = []
        iso3_data = []
        
        # Pre-allocate numpy arrays for better performance
        n = len(data)
        cases = np.zeros(n)
        active = np.zeros(n)
        recovered = np.zeros(n)
        deaths = np.zeros(n)
        tests = np.zeros(n)
        population = np.ones(n)  # Default to 1 to avoid division by zero
        
        for i, item in enumerate(data):
            try:
                countries.append(item.get('country', 'Unknown'))
                cases[i] = item.get('cases', 0)
                active[i] = item.get('active', 0)
                recovered[i] = item.get('recovered', 0)
                deaths[i] = item.get('deaths', 0)
                tests[i] = item.get('tests', 0)
                population[i] = item.get('population', 1)
                iso3_data.append(item.get('countryInfo', {}).get('iso3', 'Unknown'))
            except (KeyError, TypeError):
                continue
        
        # Vectorized operations for per million calculations
        cases_per_million = np.divide(cases, population, where=population!=0) * 1_000_000
        deaths_per_million = np.divide(deaths, population, where=population!=0) * 1_000_000
        tests_per_million = np.divide(tests, population, where=population!=0) * 1_000_000
        
        # Calculate trends using numpy operations
        new_cases = global_data.get('todayCases', 0)
        new_deaths = global_data.get('todayDeaths', 0)
        new_recovered = global_data.get('todayRecovered', 0)
        
        cases_trend = calculate_trend(
            global_data.get('cases', 0),
            global_yesterday.get('cases', 0)
        )
        deaths_trend = calculate_trend(
            global_data.get('deaths', 0),
            global_yesterday.get('deaths', 0)
        )
        recovered_trend = calculate_trend(
            global_data.get('recovered', 0),
            global_yesterday.get('recovered', 0)
        )
        
        last_updated = datetime.fromtimestamp(
            global_data.get('updated', now.timestamp() * 1000) / 1000
        ).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        data = {
            'countries': countries,
            'cases': cases,
            'active': active,
            'recovered': recovered,
            'deaths': deaths,
            'iso3': iso3_data,
            'cases_per_million': cases_per_million,
            'deaths_per_million': deaths_per_million,
            'tests_per_million': tests_per_million,
            'last_updated': last_updated,
            'new_cases': new_cases,
            'new_deaths': new_deaths,
            'new_recovered': new_recovered,
            'cases_trend': cases_trend,
            'deaths_trend': deaths_trend,
            'recovered_trend': recovered_trend
        }
        
        data_cache['data'] = data
        data_cache['last_fetch'] = now
        return data
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        if data_cache['data'] is not None:
            return data_cache['data']
        
        # Return empty data structure with zeros
        return {
            'countries': [],
            'cases': np.array([]),
            'active': np.array([]),
            'recovered': np.array([]),
            'deaths': np.array([]),
            'iso3': [],
            'cases_per_million': np.array([]),
            'deaths_per_million': np.array([]),
            'tests_per_million': np.array([]),
            'last_updated': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'new_cases': 0,
            'new_deaths': 0,
            'new_recovered': 0,
            'cases_trend': 0,
            'deaths_trend': 0,
            'recovered_trend': 0
        }

def create_card(title, value, subtitle, trend=None, color="primary", theme='DARKLY'):
    styles = THEME_STYLES[theme]
    
    trend_element = None
    if trend is not None:
        trend_color = "success" if trend >= 0 else "danger"
        trend_icon = "↑" if trend >= 0 else "↓"
        trend_element = html.Div([
            html.I(trend_icon, className=f"fas fa-arrow-{trend_icon.lower()}"),
            f" {abs(trend):.1f}%"
        ], className=f"text-{trend_color} mt-2 small")

    return dbc.Card([
        dbc.CardBody([
            html.H4(title, 
                   className="card-title text-center",
                   style={'color': styles['muted_color']}),
            html.H2(f"{value:,}", 
                   className=f"card-text text-center text-{color}",
                   style={'fontWeight': '600'}),
            html.P(subtitle, 
                  className="text-center small mt-2",
                  style={'color': styles['muted_color']}),
            trend_element if trend_element else None
        ])
    ], className="mb-4 shadow-sm", style={'backgroundColor': styles['card_bg']})

def create_map_figure(map_data, theme):
    styles = THEME_STYLES[theme]
    
    # Calculate distribution breaks for better visualization
    max_cases = max(map_data['cases'])
    breaks = [
        0,
        20_000_000,  # 20M
        40_000_000,  # 40M
        60_000_000,  # 60M
        80_000_000,  # 80M
        100_000_000, # 100M
        max_cases
    ]
    
    # Create normalized color stops
    color_stops = []
    for i, value in enumerate(breaks):
        normalized = i / (len(breaks) - 1)
        color_stops.append([normalized, get_color_for_value(normalized)])
    
    # Create choropleth map
    map_fig = px.choropleth(
        map_data,
        locations='iso3',
        color='cases',
        hover_name='country',
        range_color=[0, max_cases],
        color_continuous_scale=color_stops,
        custom_data=['cases_per_million']
    )
    
    # Add border around the map
    border_color = styles['muted_color']
    border_style = {
        'type': 'rect',
        'xref': 'paper',
        'yref': 'paper',
        'x0': -0.05,
        'y0': -0.05,
        'x1': 1.05,
        'y1': 1.05,
        'line': {
            'color': border_color,
            'width': 2,
        },
        'fillcolor': 'rgba(0,0,0,0)',
        'layer': 'below'
    }
    
    # Update layout for better visibility
    map_fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        geo=dict(
            showframe=True,
            framecolor=styles['muted_color'],
            framewidth=2,
            showcoastlines=True,
            projection_type='equirectangular',
            coastlinecolor=styles['text_color'],
            showland=True,
            landcolor=styles['bg_color'],
            showocean=True,
            oceancolor=styles['bg_color'],
            showcountries=True,
            countrycolor=styles['muted_color'],
            countrywidth=0.5,
            showlakes=False,
            showrivers=False,
            resolution=50
        ),
        shapes=[border_style],
        font=dict(color=styles['text_color']),
        hoverlabel=dict(
            bgcolor=styles['hover_bg'],
            font_size=12,
            font_family="Arial"
        ),
        coloraxis_colorbar=dict(
            title="Total Cases",
            titleside="right",
            thicknessmode="pixels",
            thickness=20,
            lenmode="pixels",
            len=300,
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=0.95,
            bgcolor='rgba(0,0,0,0)',
            tickcolor=styles['text_color'],
            tickfont=dict(color=styles['text_color']),
            titlefont=dict(color=styles['text_color']),
            tickvals=breaks,
            ticktext=[
                '0',
                '20M',
                '40M',
                '60M',
                '80M',
                '100M',
                f'{int(max_cases/1_000_000)}M'
            ],
            tickmode='array'
        )
    )
    
    map_fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                     "Total Cases: %{z:,.0f}<br>" +
                     "Cases per Million: %{customdata[0]:,.0f}"
    )
    
    return map_fig

def get_color_for_value(value):
    """Get color for normalized value between 0 and 1"""
    colors = [
        '#4a148c',  # Deep purple
        '#7b1fa2',  # Purple
        '#9c27b0',  # Light purple
        '#e91e63',  # Pink
        '#f44336',  # Red
        '#ff5722'   # Deep Orange
    ]
    
    # Calculate which color pair to use
    num_colors = len(colors) - 1
    segment = value * num_colors
    i = int(segment)
    
    # Handle edge cases
    if i >= num_colors:
        return colors[-1]
    if i < 0:
        return colors[0]
    
    # Interpolate between colors
    t = segment - i
    c1 = colors[i]
    c2 = colors[i + 1]
    
    # Convert hex to RGB and interpolate
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    
    r = int(r1 * (1 - t) + r2 * t)
    g = int(g1 * (1 - t) + g2 * t)
    b = int(b1 * (1 - t) + b2 * t)
    
    return f'#{r:02x}{g:02x}{b:02x}'

# App layout with theme switching
app.layout = html.Div([
    dcc.Store(id='theme-store', data='DARKLY'),
    
    # Theme toggle button with icon
    html.Div([
        dbc.Button(
            html.I(className="fas fa-sun", id="theme-icon"),
            id="theme-toggle",
            n_clicks=0,  # Initialize n_clicks
            className="position-fixed rounded-circle",
            style={
                'top': '20px',
                'right': '20px',
                'zIndex': 1000,
                'width': '50px',
                'height': '50px',
                'padding': '0',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center',
                'fontSize': '1.5rem',
                'transition': 'all 0.3s ease',
                'backgroundColor': 'transparent',
                'border': 'none',
                'cursor': 'pointer',
                'boxShadow': '0 2px 5px rgba(0,0,0,0.2)'
            }
        )
    ]),
    
    # Main content
    html.Div(id='themed-content', children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("COVID-19 Analytics Dashboard", 
                           id="main-title",
                           className="text-center my-4 display-4"),
                    html.H6(id="last-updated", 
                           className="text-center mb-4 font-italic")
                ])
            ]),
            
            # Global stats cards
            dbc.Row([
                dbc.Col(id="total-cases-card", width=12, lg=3),
                dbc.Col(id="active-cases-card", width=12, lg=3),
                dbc.Col(id="recovered-card", width=12, lg=3),
                dbc.Col(id="deaths-card", width=12, lg=3),
            ]),
            
            # New daily stats
            dbc.Row([
                dbc.Col(id="new-cases-card", width=12, lg=4),
                dbc.Col(id="new-recovered-card", width=12, lg=4),
                dbc.Col(id="new-deaths-card", width=12, lg=4),
            ]),
            
            # Charts
            dbc.Row([
                dbc.Col([
                    html.H3("Global Distribution", 
                           className="text-center my-4",
                           id="map-title"),
                    dbc.Spinner(
                        dcc.Graph(id="cases-map",
                                 config={'displayModeBar': False}),
                        color="primary",
                        type="grow",
                        fullscreen=False
                    )
                ], width=12),
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Top 10 Most Affected Countries", 
                           className="text-center my-4",
                           id="bar-title"),
                    dbc.Spinner(
                        dcc.Graph(id="top-countries-bar",
                                 config={'displayModeBar': False}),
                        color="primary",
                        type="grow",
                        fullscreen=False
                    )
                ], width=12, lg=6),
                
                dbc.Col([
                    html.H3("Case Distribution", 
                           className="text-center my-4",
                           id="pie-title"),
                    dbc.Spinner(
                        dcc.Graph(id="cases-pie",
                                 config={'displayModeBar': False}),
                        color="primary",
                        type="grow",
                        fullscreen=False
                    )
                ], width=12, lg=6),
            ]),
            
            # Footer
            dbc.Row([
                dbc.Col([
                    html.Hr(id="footer-hr"),
                    html.P([
                        "Data source: ",
                        html.A("disease.sh API", 
                              href="https://disease.sh/",
                              target="_blank",
                              className="text-info"),
                        " • Built with Dash and Flask • ",
                        html.A("View Source",
                              href="https://github.com/knownstranger-Tapasya/PandemicPulse",
                              target="_blank",
                              className="text-info")
                    ], className="text-center", id="footer-text")
                ])
            ]),
        ], fluid=True, className="px-4 py-3")
    ], style={'transition': 'all 0.3s ease'}),  # Add transition to content
    
    dcc.Interval(
        id='interval-component',
        interval=300000,  # Update every 5 minutes
        n_intervals=0
    )
])

# Theme toggle callback
@app.callback(
    [Output("theme-store", "data"),
     Output("theme-icon", "className"),
     Output("theme-toggle", "style"),
     Output("themed-content", "style")],
    [Input("theme-toggle", "n_clicks")],
    [State("theme-store", "data")]
)
def toggle_theme(n_clicks, current_theme):
    if n_clicks is None:
        n_clicks = 0
    
    # Toggle theme
    new_theme = 'FLATLY' if current_theme == 'DARKLY' else 'DARKLY'
    styles = THEME_STYLES[new_theme]
    
    # Update button style
    button_style = {
        'top': '20px',
        'right': '20px',
        'zIndex': 1000,
        'width': '50px',
        'height': '50px',
        'padding': '0',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'fontSize': '1.5rem',
        'transition': 'all 0.3s ease',
        'backgroundColor': styles['card_bg'],
        'color': styles['text_color'],
        'border': 'none',
        'boxShadow': '0 2px 5px rgba(0,0,0,0.2)',
        'cursor': 'pointer',
        'borderRadius': '50%',  # Ensure circular shape
        'transform': 'scale(1)',  # Add hover effect
        ':hover': {
            'transform': 'scale(1.1)'
        }
    }
    
    # Update content style
    content_style = {
        'backgroundColor': styles['bg_color'],
        'color': styles['text_color'],
        'transition': 'all 0.3s ease',
        'minHeight': '100vh'  # Ensure full height
    }
    
    # Update external stylesheets
    if current_theme != new_theme:
        app.css.append_css({
            "external_url": styles['theme']
        })
    
    return new_theme, styles['icon'], button_style, content_style

# Additional callback for updating card styles
@app.callback(
    [Output("total-cases-card", "style"),
     Output("active-cases-card", "style"),
     Output("recovered-card", "style"),
     Output("deaths-card", "style"),
     Output("new-cases-card", "style"),
     Output("new-recovered-card", "style"),
     Output("new-deaths-card", "style")],
    [Input("theme-store", "data")]
)
def update_card_styles(theme):
    styles = THEME_STYLES[theme]
    card_style = {
        'backgroundColor': styles['card_bg'],
        'color': styles['text_color'],
        'transition': 'all 0.3s ease',
        'border': 'none',
        'borderRadius': '10px',
        'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'
    }
    return [card_style] * 7  # Return same style for all cards

# Main dashboard callback
@app.callback(
    [Output("last-updated", "children"),
     Output("total-cases-card", "children"),
     Output("active-cases-card", "children"),
     Output("recovered-card", "children"),
     Output("deaths-card", "children"),
     Output("new-cases-card", "children"),
     Output("new-recovered-card", "children"),
     Output("new-deaths-card", "children"),
     Output("cases-map", "figure"),
     Output("top-countries-bar", "figure"),
     Output("cases-pie", "figure")],
    [Input("interval-component", "n_intervals"),
     Input("theme-store", "data")]
)
def update_dashboard(_, theme):
    data = fetch_covid_data()
    styles = THEME_STYLES[theme]
    
    last_updated_text = f"Last Updated: {data['last_updated']}"
    
    # Calculate global stats
    total_cases = np.sum(data['cases'])
    active_cases = np.sum(data['active'])
    recovered = np.sum(data['recovered'])
    deaths = np.sum(data['deaths'])
    
    # Create cards with current theme
    total_card = create_card(
        "Total Cases",
        total_cases,
        "Cumulative cases worldwide",
        data['cases_trend'],
        "primary",
        theme
    )
    active_card = create_card(
        "Active Cases",
        active_cases,
        "Currently infected patients",
        None,
        "warning",
        theme
    )
    recovered_card = create_card(
        "Recovered",
        recovered,
        "Total recovered patients",
        data['recovered_trend'],
        "success",
        theme
    )
    deaths_card = create_card(
        "Deaths",
        deaths,
        "Total fatalities",
        data['deaths_trend'],
        "danger",
        theme
    )
    
    new_cases_card = create_card(
        "New Cases",
        data['new_cases'],
        "Cases reported today",
        None,
        "info",
        theme
    )
    new_recovered_card = create_card(
        "New Recoveries",
        data['new_recovered'],
        "Recoveries reported today",
        None,
        "success",
        theme
    )
    new_deaths_card = create_card(
        "New Deaths",
        data['new_deaths'],
        "Deaths reported today",
        None,
        "danger",
        theme
    )
    
    # Create world map
    map_data = {
        'country': data['countries'],
        'iso3': data['iso3'],
        'cases': data['cases'],
        'cases_per_million': data['cases_per_million']
    }
    map_fig = create_map_figure(map_data, theme)
    
    # Create top 10 countries bar chart
    top_10_indices = np.argsort(data['cases'])[-10:][::-1]
    bar_data = {
        'country': [data['countries'][i] for i in top_10_indices],
        'cases': [data['cases'][i] for i in top_10_indices],
        'cases_per_million': [data['cases_per_million'][i] for i in top_10_indices]
    }
    bar_fig = px.bar(
        bar_data,
        x='country',
        y='cases',
        color='cases',
        color_continuous_scale="Viridis",
        custom_data=['cases_per_million']
    )
    bar_fig.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=40, b=0),
        xaxis_tickangle=-45,
        yaxis_title="Total Cases",
        xaxis_title="",
        font=dict(color=styles['text_color']),
        hoverlabel=dict(
            bgcolor=styles['hover_bg'],
            font_size=12,
            font_family="Arial"
        )
    )
    bar_fig.update_traces(
        hovertemplate="<b>%{x}</b><br>" +
                     "Total Cases: %{y:,.0f}<br>" +
                     "Cases per Million: %{customdata[0]:,.0f}"
    )
    
    # Create pie chart
    pie_fig = go.Figure(data=[go.Pie(
        labels=['Active', 'Recovered', 'Deaths'],
        values=[active_cases, recovered, deaths],
        hole=.4,
        marker=dict(colors=[styles['warning_color'], styles['success_color'], styles['danger_color']])
    )])
    pie_fig.update_layout(
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=styles['text_color'])
        ),
        font=dict(color=styles['text_color']),
        hoverlabel=dict(
            bgcolor=styles['hover_bg'],
            font_size=12,
            font_family="Arial"
        )
    )
    pie_fig.update_traces(
        textinfo='percent+value',
        hoverinfo='label+percent+value',
        textfont=dict(color=styles['text_color'])
    )
    
    return (
        last_updated_text,
        total_card,
        active_card,
        recovered_card,
        deaths_card,
        new_cases_card,
        new_recovered_card,
        new_deaths_card,
        map_fig,
        bar_fig,
        pie_fig
    )

# Flask routes
@server.route('/')
def index():
    return """
    <html>
        <head>
            <title>COVID-19 Analytics Dashboard</title>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Poppins', sans-serif;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: white;
                    text-align: center;
                    padding: 50px;
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 40px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                }
                h1 {
                    font-size: 2.5em;
                    margin-bottom: 20px;
                    color: #ffffff;
                }
                p {
                    font-size: 1.2em;
                    margin-bottom: 30px;
                    color: rgba(255, 255, 255, 0.8);
                }
                .button {
                    display: inline-block;
                    padding: 15px 40px;
                    background: linear-gradient(45deg, #2196F3 0%, #64B5F6 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 30px;
                    font-size: 1.2em;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                }
                .button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                }
                .features {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    margin-top: 40px;
                }
                .feature {
                    background: rgba(255, 255, 255, 0.1);
                    padding: 20px;
                    border-radius: 15px;
                    flex: 1;
                }
                .feature h3 {
                    color: #64B5F6;
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>COVID-19 Analytics Dashboard</h1>
                <p>An interactive visualization platform for real-time COVID-19 statistics worldwide</p>
                <a href="/dash/" class="button">Launch Dashboard</a>
                <div class="features">
                    <div class="feature">
                        <h3>Real-time Data</h3>
                        <p>Live updates every 5 minutes</p>
                    </div>
                    <div class="feature">
                        <h3>Interactive Maps</h3>
                        <p>Global visualization</p>
                    </div>
                    <div class="feature">
                        <h3>Detailed Analytics</h3>
                        <p>Comprehensive statistics</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    server.run(debug=True) 