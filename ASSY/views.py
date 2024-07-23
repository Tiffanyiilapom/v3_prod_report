# Create your views here.
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
import seaborn as sns
from datetime import datetime, timedelta, date
import requests
import re
from bs4 import BeautifulSoup
from plotly.subplots import make_subplots

# Create your views here.

dash = My_Dash()

def process_reason(text):
    text = str(text)
    processed_text = text.replace('0', '無')
    return processed_text

def conditional_round(x):
    if pd.isna(x):  
        return x
    if isinstance(x, (int, float)):  
        if x < 1 or (x > 1 and x < 2 and x/10 != 0):
            return round(x, 4)
        else:
            return round(x, 2)
    return x

# 把表格清乾淨
def table_process(df):
    df.drop(index=0, inplace=True)
    df = df.dropna(subset=['班別', '線別'], how='all')
    df.loc[:,'制令號'] = df['制令號'].astype(str)
    df.loc[:,'制令號'] = df['制令號'].str.replace(r"^[\'\"]", "", regex=True)
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.fillna(0).infer_objects(copy=False)
    df = df[df['實際產量(PCS）'] != 0 ]
    columns_to_remove = ['綜整'] + ['Remark: (分鐘)'] + df.filter(regex=r'^Unnamed').columns.tolist()
    df = df.drop(columns=columns_to_remove, errors='ignore')
    df['投產開始\n時間(起)'] = df['投產開始\n時間(起)'].apply(lambda x: '00:00:00' if str(x).startswith('1900') else x)
    df['投產結束\n時間(迄)'] = df['投產結束\n時間(迄)'].apply(lambda x: '00:00:00' if str(x).startswith('1900') else x)
    df['投產開始\n時間(起)'] = df['投產開始\n時間(起)'].astype(str).apply(lambda x: x if len(x) == 5 else x[:-3])
    df['投產結束\n時間(迄)'] = df['投產結束\n時間(迄)'].astype(str).apply(lambda x: x if len(x) == 5 else x[:-3])
    df = df.fillna(" ")
    df['未达成/異常原因: (分鐘)'] = df['未达成/異常原因: (分鐘)'].apply(process_reason)
    df = df.map(conditional_round)
    return df

# 找所有的工作天 (for下拉選單)
def get_all_workdays(year,month,df):
    work_day, formatted_dates = [], []
    date_column = '日期'
    uph_column = '平均\n目標UPH\n（PCS）'
    for index, row in df.iterrows():
        if pd.notna(row[uph_column]) and pd.notna(row[date_column]):
            work_day.append(int(row[date_column]))
    for day in work_day:
        formatted_date = date(year, month, day).strftime('%Y-%m-%d')
        formatted_dates.append(formatted_date)
    return formatted_dates

# 把不同周的日期分開
def find_date_ranges(dates):
    dates = sorted([datetime.strptime(date, '%Y-%m-%d') for date in dates])
    result = []
    start_date = dates[0]
    end_date = dates[0]

    # 把斷掉的切開
    for current_date in dates[1:]:
        if current_date == end_date + timedelta(days=1):
            end_date = current_date
        else:
            result.append(f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            start_date = current_date
            end_date = current_date

    result.append(f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    return result

# 去首0
def nozero(str):
    if str.startswith('0'):
        str = str[1:]
    return str

def process_date(data):
    dates = data['日期'].astype(str).str.replace(r'\.0$',"",regex=True)
    numeric_data = data.drop('日期',axis=1).astype(float).map(conditional_round)
    final_data = numeric_data.copy()
    with pd.option_context("future.no_silent_downcasting", True):
        final_data = final_data.fillna(0).infer_objects(copy=False)
    final_data['日期'] = dates
    final_data = final_data[['日期'] + [col for col in numeric_data.columns]]
    return final_data

# 圓餅圖function
def func_for_pie(pie_data, title):
    pie_data = pie_data.loc[:, ['投產工時\n(Hrs)','调机工时Setup(min)', '機台維修時間\n  Down(min)', '製程異常\n時間Hold(min)', 
                                '物料異常\n時間Hold(min)', '借出工時RD(min)','待料時間Idel\n（min）']].astype(float).squeeze()
    labels = ['调机工时 Setup (Hrs)', '機台維修時間 Down (Hrs)', '製程異常時間 Hold (Hrs)', '物料異常時間 Hold (Hrs)', '借出工時 RD (Hrs)', '待料時間 Idel (Hrs)','稼動時間 (Hrs)']
    # 分鐘的換成小時
    pie_data['调机工时Setup(min)'] /= 60
    pie_data['機台維修時間\n  Down(min)'] /= 60
    pie_data['製程異常\n時間Hold(min)'] /= 60
    pie_data['物料異常\n時間Hold(min)'] /= 60
    pie_data['借出工時RD(min)'] /= 60
    pie_data['待料時間Idel\n（min）'] /= 60
    pie_data['稼動時間\n(Hrs)'] = pie_data['投產工時\n(Hrs)']-pie_data['调机工时Setup(min)']-pie_data['機台維修時間\n  Down(min)']-pie_data['製程異常\n時間Hold(min)']-pie_data['物料異常\n時間Hold(min)']-pie_data['借出工時RD(min)']-pie_data['待料時間Idel\n（min）']
    if pie_data.ndim == 1: # 如果只有一天的資料 e.g. 每日/該月第一天
        pie_data = pie_data.drop('投產工時\n(Hrs)')
    else:
        pie_data = pie_data.drop('投產工時\n(Hrs)', axis=1)
        pie_data = pie_data.sum()

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=pie_data.values,
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
    

def upload(request):
    current_year = int(datetime.now().year)
    years = [current_year - i for i in range(2)]
    months = list(range(1, 13))
    context = {
        'years': years, 
        'months': months, 
        'current_year': current_year,
    }
    return render(request, "ASSY_p0.html", context)
    #except:
    #   return render(request, "ERROR_Page.html")
    
def daily(request):
    global dash
    # 預設呈現最新的工作天
    if request.method == "POST" and 'data_upload_assy' in request.POST:
        dash.flag = False # 代表有新上傳資料
        data = request.FILES.get('data')
        dash.data = data.read()
        data_bydate = pd.read_excel(io.BytesIO(dash.data), sheet_name='組裝BY日期總表', skiprows=3, usecols='H:AI')
        dash.by_date = data_bydate
        now = datetime.now()
        year = now.year
        month = now.month

        # 得到已發生的所有工作天
        options = get_all_workdays(year, month, data_bydate)
        dash.options = options
        # 取出最後一個工作天
        last_workday = options[-1]
        # 有0的話去0
        last_two_digits = nozero(last_workday[-2:])

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        title = str(last_workday)+' ASSY Production Time Distribution'
        dash.fig_fordaily = func_for_pie(pie_data, title)

        # 下方表格
        data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=3, usecols='A:AN', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
        dash.day = table_process(data_day)
        dash.mass_production = dash.day[dash.day['制令號'].str.startswith('1', na=False)]
        dash.trial_production = dash.day[dash.day['制令號'].str.startswith('3', na=False)]

        context = {
            'all_data': dash.day.values.tolist(),
            'all_columns': dash.day.columns,
            'mass_data': dash.mass_production.values.tolist(),
            'mass_columns': dash.mass_production.columns,
            'trial_data': dash.trial_production.values.tolist(),
            'trial_columns': dash.trial_production.columns,
            'placeholder_fig': dash.fig_fordaily,
            'options': dash.options,
        }

        return render(request, 'ASSY_p1.html',context)
    
    # 若上傳非當月資料
    elif request.method == "POST" and 'old_data_upload_assy' in request.POST:
        dash.flag = False
        data = request.FILES.get('old_data')
        year = int(request.POST.get("assy_old_year"))
        month = int(request.POST.get("assy_old_month"))
        dash.data = data.read()
        data_bydate = pd.read_excel(io.BytesIO(dash.data), sheet_name='組裝BY日期總表', skiprows=3, usecols='H:AI')

        dash.by_date = data_bydate

        # 得到已發生的所有工作天
        options = get_all_workdays(year, month, data_bydate)
        dash.options = options
        # 取出最後一個工作天
        last_workday = options[-1]
        # 有0的話去0
        last_two_digits = nozero(last_workday[-2:])

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        title = str(last_workday) +' ASSY Production Time Distribution'
        dash.fig_fordaily = func_for_pie(pie_data, title)

        # 下方表格
        data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=3, usecols='A:AN', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
        dash.day = table_process(data_day)
        dash.mass_production = dash.day[dash.day['制令號'].str.startswith('1', na=False)]
        dash.trial_production = dash.day[dash.day['制令號'].str.startswith('3', na=False)]

        context = {
            'all_data': dash.day.values.tolist(),
            'all_columns': dash.day.columns,
            'mass_data': dash.mass_production.values.tolist(),
            'mass_columns': dash.mass_production.columns,
            'trial_data': dash.trial_production.values.tolist(),
            'trial_columns': dash.trial_production.columns,
            'placeholder_fig': dash.fig_fordaily,
            'options': dash.options,
        }

        return render(request, 'ASSY_p1.html',context)
    
    # 若選擇非預設的日期
    elif request.method == "POST" and 'assy_select_button' in request.POST:
        select_day = request.POST.get("assy_select1")
        last_two_digits = nozero(select_day[-2:])

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        title = select_day +' ASSY Production Time Distribution'
        dash.fig_fordaily = func_for_pie(pie_data, title)

        # 下方表格
        data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=3, usecols='A:AN', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
        print(data_day.head(15))
        dash.day = table_process(data_day)
        dash.mass_production = dash.day[dash.day['制令號'].str.startswith('1', na=False)]
        dash.trial_production = dash.day[dash.day['制令號'].str.startswith('3', na=False)]

        context = {
            'all_data': dash.day.values.tolist(),
            'all_columns': dash.day.columns,
            'mass_data': dash.mass_production.values.tolist(),
            'mass_columns': dash.mass_production.columns,
            'trial_data': dash.trial_production.values.tolist(),
            'trial_columns': dash.trial_production.columns,
            'placeholder_fig': dash.fig_fordaily,
            'options': dash.options,
        }

        return render(request, 'ASSY_p1.html',context)
        
    # 從別頁點回來的話把資料留住
    elif not dash.anyNone(dash.day): 
        
        context = {
            'all_data': dash.day.values.tolist(),
            'all_columns': dash.day.columns,
            'mass_data': dash.mass_production.values.tolist(),
            'mass_columns': dash.mass_production.columns,
            'trial_data': dash.trial_production.values.tolist(),
            'trial_columns': dash.trial_production.columns,
            'placeholder_fig': dash.fig_fordaily,
            'options': dash.options,
        }
        
        return render(request, 'ASSY_p1.html',context)
    
    # 尚未上傳資料
    else:
        placeholder_df = pd.DataFrame(columns=['Please', 'Upload', 'Data', 'First'])
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

        context = {
            'all_data': placeholder_df.values.tolist(),
            'all_columns': placeholder_df.columns,
            'placeholder_fig': placeholder_fig,
        }
        return render(request, 'ASSY_p1.html',context)
    
def weekly(request):
    try:
        return render(request, "ASSY_p2.html")
    except:
        return render(request, "ERROR_Page.html")
    
def monthly(request):
    try:
        return render(request, "ASSY_p3.html")
    except:
        return render(request, "ERROR_Page.html")