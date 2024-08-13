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

test_data = {
    'Machine':['L01','L01','L04'],
    'WorkOrder':['130000021577','130000021578','130000021594'],
    'Product No':['TR-MC4209-D','TR-MC4210-D','TR-MC4142-E'],
    'Product Name':['20_SAE_C1YC_2 HL BASE,LED,3F,LH','20_SAE_C1YC_2 HL BASE,LED,3F,RH','22_Volta RPV SAE,Module,SL/R-T,LR'],
    'WorkCenter':['SMT','SMT','SMT-BOT'],
    'StartTime':['07:00','13:00','8:00'],
    'EndTime':['13:00','24:00','24:00'],
    'Target Qty':[516, 880, 2352],
    'AOI Output':[285, 462, 1880],
    'SPI Output':[289, 478, 1912]
}
test_data = pd.DataFrame(test_data)
test_data['Performance'] =  test_data['AOI Output'] / test_data['Target Qty']


test2_data = {
    'Machine':['ICT03','ICT03','ICT04','ICT01'],
    'WorkOrder':['130000021455','130000021456','130000021560','360000001475'],
    'Product No':['TR-MC4238-L','TR-MC4245-L','TR-MC4276-J','TR-MC4179-A'],
    'Product Name':['20_C1YC_2 RCL BASE SAE,LDM,3F,LH','20_C1YC_2 RCL BASE SAE,LDM,3F,RH', '20_Porsche,Module,TL,RH', '20_T1xGH MCM,LED,LED,3F_PCB2,LH'],
    'StartTime':['08:00','11:00','12:00','13:00'],
    'EndTime':['09:00','12:00','13:00','14:00'],
    'Target Qty':[109, 109, 300, 348],
    'Output':[1, 1, 2, 1]
}
test2_data = pd.DataFrame(test2_data)
test2_data['Performance'] =  test2_data['Output'] / test2_data['Target Qty']


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

def get_week_dates(date_str):
    selected_date = datetime.strptime(date_str, '%Y-%m-%d')
    start_of_week = selected_date - timedelta(days=selected_date.weekday()) 
    end_of_week = start_of_week + timedelta(days=6)

    start_date_str = start_of_week.strftime('%Y-%m-%d')
    end_date_str = end_of_week.strftime('%Y-%m-%d')
    
    return start_date_str, end_date_str

def for_error(request):
    # 把舊的東西清掉!
    dash.data = None 
    dash.by_date = None 
    dash.sixplot_html = None 
    dash.flag = False 
    return render(request, "ERROR_Page.html")

def daily(request):
    try:
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        selected_tab = request.POST.get('tab', request.GET.get('tab', 'SMT')) # POST:提交表單(go)中的hidden input, GET:只是點擊選項卡
        if selected_tab == 'ICT':
            if request.method == "POST" and 'date_button' in request.POST and 'datePicker' in request.POST:
                selected_date = request.POST.get("datePicker")
                selected_date = datetime.strptime(selected_date, '%Y-%m-%d')
                title = f"{selected_date.strftime('%Y-%m-%d')} SMT : ICT Production Time Distribution"
            else:   # 預設:昨天
                title = f"{yesterday} SMT : ICT Production Time Distribution"

            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'ENG', 'DOWN', 'PM', 'HOLD_M'],
                'values': [996, 13, 21, 24, 4, 7, 18]
            }
            dash.day = test2_data
            dash.mass_production = dash.day[dash.day['WorkOrder'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['WorkOrder'].str.startswith('3', na=False)]

        else:
            if request.method == "POST" and 'date_button' in request.POST and 'datePicker' in request.POST:
                selected_date = request.POST.get("datePicker")
                selected_date = datetime.strptime(selected_date, '%Y-%m-%d')
                title = f"{selected_date.strftime('%Y-%m-%d')} SMT : SMT Production Time Distribution"
            else:   # 預設:昨天
                title = f"{yesterday} SMT : SMT Production Time Distribution"

            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'WAIT_M', 'FAC', 'PM', 'HOLD_M'],
                'values': [985, 13, 21, 32, 4, 7, 58]
            }
            dash.day = test_data
            dash.mass_production = dash.day[dash.day['WorkOrder'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['WorkOrder'].str.startswith('3', na=False)]

        pie_data = pd.DataFrame(chart_data)
        placeholder_fig = func_for_pie(pie_data, title)
        
    except :
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

    context = {
        'placeholder_fig': placeholder_fig,
        'yesterday':yesterday,
        'selected_tab': selected_tab,
        'all_data': dash.day.values.tolist(),
        'all_columns': dash.day.columns,
        'mass_data': dash.mass_production.values.tolist(),
        'mass_columns': dash.mass_production.columns,
        'trial_data': dash.trial_production.values.tolist(),
        'trial_columns': dash.trial_production.columns,
    }

    return render(request, 'SMT_RT_p1.html', context)

    
def weekly(request):
    try:
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        selected_tab = request.POST.get('tab', request.GET.get('tab', 'SMT')) # POST:提交表單(go)中的hidden input, GET:只是點擊選項卡
        if selected_tab == 'ICT':
            if request.method == "POST" and 'date_button' in request.POST and 'datePicker' in request.POST:
                selected_date = request.POST.get("datePicker")
                start_date, end_date = get_week_dates(selected_date)
            else:   # 預設:昨天的那周
                start_date, end_date = get_week_dates(yesterday)
            title = f"{start_date} ~ {end_date} SMT : ICT Production Time Distribution"

            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'ENG', 'DOWN', 'PM', 'HOLD_M'],
                'values': [996, 13, 21, 24, 4, 7, 18]
            }
            dash.day = test2_data
            dash.mass_production = dash.day[dash.day['WorkOrder'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['WorkOrder'].str.startswith('3', na=False)]

        else:
            if request.method == "POST" and 'date_button' in request.POST and 'datePicker' in request.POST:
                selected_date = request.POST.get("datePicker")
                start_date, end_date = get_week_dates(selected_date)
            else:   # 預設:昨天的那周
                start_date, end_date = get_week_dates(yesterday)
            title = f"{start_date} ~ {end_date} SMT : ICT Production Time Distribution"

            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'WAIT_M', 'FAC', 'PM', 'HOLD_M'],
                'values': [985, 13, 21, 32, 4, 7, 58]
            }
            dash.day = test_data
            dash.mass_production = dash.day[dash.day['WorkOrder'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['WorkOrder'].str.startswith('3', na=False)]

        pie_data = pd.DataFrame(chart_data)
        placeholder_fig = func_for_pie(pie_data, title)
        
    except :
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

    context = {
        'placeholder_fig': placeholder_fig,
        'yesterday':yesterday,
        'selected_tab': selected_tab,
        'all_data': dash.day.values.tolist(),
        'all_columns': dash.day.columns,
        'mass_data': dash.mass_production.values.tolist(),
        'mass_columns': dash.mass_production.columns,
        'trial_data': dash.trial_production.values.tolist(),
        'trial_columns': dash.trial_production.columns,
    }

    return render(request,'SMT_RT_p2.html', context)

def monthly(request):
    try:
        today = datetime.today()
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        first_day_of_month = today.replace(day=1).strftime('%Y-%m-%d')
        selected_tab = request.POST.get('tab', request.GET.get('tab', 'SMT')) # POST:提交表單(go)中的hidden input, GET:只是點擊選項卡
        if selected_tab == 'ICT':
            if request.method == "POST" and 'date_button' in request.POST and 'datePicker' in request.POST:
                start_date = request.POST.get("datePicker")
                end_date = request.POST.get("EndPicker")
            else:   # 預設:當月第一天到昨天
                start_date = first_day_of_month
                end_date = yesterday
            title = f"{start_date} ~ {end_date} SMT : ICT Production Time Distribution"

            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'ENG', 'DOWN', 'PM', 'HOLD_M'],
                'values': [996, 13, 21, 24, 4, 7, 18]
            }
        else:
            if request.method == "POST" and 'date_button' in request.POST and 'datePicker' in request.POST:
                start_date = request.POST.get("datePicker")
                end_date = request.POST.get("EndPicker")
            else:   # 預設:當月第一天到昨天
                start_date = first_day_of_month
                end_date = yesterday
            title = f"{start_date} ~ {end_date} SMT : ICT Production Time Distribution"

            chart_data = {
                'labels': ['RUN', 'FAI', 'IDLE', 'WAIT_M', 'FAC', 'PM', 'HOLD_M'],
                'values': [985, 13, 21, 32, 4, 7, 58]
            }

        pie_data = pd.DataFrame(chart_data)
        placeholder_fig = func_for_pie(pie_data, title)

    except:
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)
    
    context = {
        'placeholder_fig': placeholder_fig,
        'six_plot': None,
        'yesterday':yesterday,
        'selected_tab': selected_tab,
    }

    return render(request,'SMT_RT_p3.html', context)

