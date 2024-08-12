from django.shortcuts import render, HttpResponse, redirect
from .models import My_Dash, data_decoded
import numpy as np
import pandas as pd
import base64
import io
import re
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import plotly.io as pio
import plotly.express as px
from datetime import datetime, timedelta, date
import requests
import re
from bs4 import BeautifulSoup
from plotly.subplots import make_subplots

# Create your views here.

dash = My_Dash()

def func_for_pie(pie_data, title):
    labels = pie_data['labels'].tolist()
    values = pie_data['values'].tolist()

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        rotation=300  # Rotates the pie chart slices
    )])

    fig.update_layout(title=title)
    fig_html = pio.to_html(fig, full_html=False)
    return fig_html

def for_error(request):
    # 把舊的東西清掉!
    dash.data = None 
    dash.by_date = None 
    dash.day = None 
    dash.sixplot_html = None 
    dash.flag = False 
    return render(request, "ERROR_Page.html")

def daily(request):
    try:
        selected_tab = request.GET.get('tab', 'SMT')
        if selected_tab == 'ICT':
            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'ENG', 'DOWN', 'PM', 'HOLD_M'],
                'values': [996, 13, 21, 24, 4, 7, 18]
            }
            title = '2024-08-12 SMT : ICT Production Time Distribution'
        else:
            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'WAIT_M', 'FAC', 'PM', 'HOLD_M'],
                'values': [985, 13, 21, 32, 4, 7, 58]
            }
            title = '2024-08-12 SMT : SMT Production Time Distribution'

        pie_data = pd.DataFrame(chart_data)
        placeholder_fig = func_for_pie(pie_data, title)
        
    except :
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

    today = date.today().strftime('%Y-%m-%d')
    context = {
        'placeholder_fig': placeholder_fig,
        'today':today,
    }

    return render(request, 'SMT_RT_p1.html', context)

    
def weekly(request):
    return render(request,'SMT_RT_p2.html')

def monthly(request):
    return render(request,'SMT_RT_p3.html')

