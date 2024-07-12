from django.shortcuts import render, HttpResponse, redirect
from .models import My_Dash, data_decoded
import numpy as np
import pandas as pd
import base64
import io
import re
import plotly.graph_objects as go
import plotly.subplots as sp
import matplotlib.pyplot as plt
import plotly.io as pio
import plotly.express as px
import seaborn as sns
import json
from datetime import datetime, timedelta, date

# Create your views here.

dash = My_Dash()
    
def data_to_json(data):
    if data.isnull().any().any()>0:
        data = data.fillna('null')
        data = data.to_json(orient='columns')
        data = data.replace('"null"', 'null')
    else:
        data = data.to_json(orient='columns')
    return data

def process_reason(text):
    # 無異常的狀況
    text_to_replace = '1.調機(換線/首件):\n2.維修:\n3.製程異常:\n4.物料異常:\n5.借出:\n6.待料/.其他(交接班5S/收線):'
    
    # 替代成'無異常'
    if text.strip() == text_to_replace:
        return '無異常'
    
    # Define the patterns to look for
    patterns = {
        '調機': r'1\.調機\(換線/首件\):(.*?)(?=\s*\d\.)',
        '維修': r'2\.維修:(.*?)(?=\s*\d\.)',
        '製程異常': r'3\.製程異常:(.*?)(?=\s*\d\.)',
        '物料異常': r'4\.物料異常:(.*?)(?=\s*\d\.)',
        '借出': r'5\.借出:(.*?)(?=\s*\d\.)',
        '待料/.其他': r'6\.待料/\.其他\(交接班5S/收線\):(.*)'
    }
    results = []
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match and match.group(1).strip(): # match代表(.*?)有捕獲到東西
            results.append(f"{key}:{match.group(1).strip()}")  # match.group(1)回傳捕獲的內容
    return ', '.join(results) if results else '無異常'

def table_process(df):
    df = df.dropna(subset=['班別', '線別'], how='all')
    df = df[(df['線別'] != '公式')]
    df = df.fillna(0)
    columns_to_remove = ['Remark'] + df.filter(regex=r'^Unnamed').columns.tolist()
    df = df.drop(columns=columns_to_remove, errors='ignore')
    df['投產開始\n時間(起)'] = df['投產開始\n時間(起)'].replace('1900-01-01 00:00:00', '00:00:00')
    df['投產結束\n時間(迄)'] = df['投產結束\n時間(迄)'].replace('1900-01-01 00:00:00', '00:00:00')
    df['投產開始\n時間(起)'] = df['投產開始\n時間(起)'].astype(str).apply(lambda x: x if len(x) == 5 else x[:-3])
    df['投產結束\n時間(迄)'] = df['投產結束\n時間(迄)'].astype(str).apply(lambda x: x if len(x) == 5 else x[:-3])
    df = df.fillna(" ")
    df['未达成/異常原因'] = df['未达成/異常原因'].apply(process_reason)
    df = df.round(2)
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

def upload(request):
    current_year = int(datetime.now().year)
    years = [current_year - i for i in range(3)]
    months = list(range(1, 13))
    context = {
        'years': years, 
        'months': months, 
        'current_year': current_year,
    }
    return render(request, "page0_upload.html", context)

def daily(request):
    global dash
    if request.method == "POST" and 'data_upload_button' in request.POST:
        data = request.FILES.get('data')
        dash.data = data.read()
        data_bydate = pd.read_excel(io.BytesIO(dash.data), sheet_name='SMT_BY日期總表', skiprows=3, usecols='H:AI')
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
        last_two_digits = last_workday[-2:]
        if last_two_digits.startswith('0'):
            last_two_digits = last_two_digits[1:]

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        pie_data = pie_data.loc[:, ['計畫投產工時\n(Hrs)','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
            '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間/其它Idel(min)']].astype(float).squeeze()
        labels = ['调机工时 Setup (Hrs)', '機台維修時間 Down (Hrs)', '製程異常時間 Hold (Hrs)', '物料異常時間 Hold (Hrs)', '借出工時 RD (Hrs)', '待料時間/其它 Idel (Hrs)','稼動時間 (Hrs)']
        # 確認取出的資料只有一筆
        if pie_data.ndim == 1:
            # 分鐘的換成小時
            pie_data['调机工时Setup(min)'] /= 60
            pie_data['機台維修時間\n  Down(min)'] /= 60
            pie_data['製程異常\n時間Hold(min)'] /= 60
            pie_data['物料異常\n時間Hold(min)'] /= 60
            pie_data['借出工時RD(min)'] /= 60
            pie_data['待料時間/其它Idel(min)'] /= 60
        pie_data['稼動時間\n(Hrs)'] = pie_data['計畫投產工時\n(Hrs)']-pie_data['调机工时Setup(min)']-pie_data['機台維修時間\n  Down(min)']-pie_data['製程異常\n時間Hold(min)']-pie_data['物料異常\n時間Hold(min)']-pie_data['借出工時RD(min)']-pie_data['待料時間/其它Idel(min)']
        pie_data = pie_data.drop('計畫投產工時\n(Hrs)')
        title = str(last_workday)+' SMT Production Time Distribution'

        fig = px.pie(names=labels, values=pie_data.values, title=title)
        fig.update_layout(height=600, width=1000)
        fig_html = pio.to_html(fig, full_html=False)
        dash.fig_fordaily = fig_html

        # 下方表格
        data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=8, usecols='A:AK', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
        dash.day = table_process(data_day)

        context = {
            'data': dash.day.values.tolist(),
            'columns': dash.day.columns,
            'placeholder_fig': fig_html,
            'options': dash.options,
        }

        return render(request, 'page1_daily.html',context)
    
    elif request.method == "POST" and 'old_data_upload_button' in request.POST:
        data = request.FILES.get('data_old')
        year = int(request.POST.get("select_year"))
        month = int(request.POST.get("select_month"))
        dash.data = data.read()
        data_bydate = pd.read_excel(io.BytesIO(dash.data), sheet_name='SMT_BY日期總表', skiprows=3, usecols='H:AI')
        dash.by_date = data_bydate

        # 得到已發生的所有工作天
        options = get_all_workdays(year, month, data_bydate)
        dash.options = options
        # 取出最後一個工作天
        last_workday = options[-1]
        # 有0的話去0
        last_two_digits = last_workday[-2:]
        if last_two_digits.startswith('0'):
            last_two_digits = last_two_digits[1:]

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        pie_data = pie_data.loc[:, ['計畫投產工時\n(Hrs)','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
            '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間/其它Idel(min)']].astype(float).squeeze()
        labels = ['调机工时 Setup (Hrs)', '機台維修時間 Down (Hrs)', '製程異常時間 Hold (Hrs)', '物料異常時間 Hold (Hrs)', '借出工時 RD (Hrs)', '待料時間/其它 Idel (Hrs)','稼動時間 (Hrs)']
        # 確認取出的資料只有一筆
        if pie_data.ndim == 1:
            # 分鐘的換成小時
            pie_data['调机工时Setup(min)'] /= 60
            pie_data['機台維修時間\n  Down(min)'] /= 60
            pie_data['製程異常\n時間Hold(min)'] /= 60
            pie_data['物料異常\n時間Hold(min)'] /= 60
            pie_data['借出工時RD(min)'] /= 60
            pie_data['待料時間/其它Idel(min)'] /= 60
        pie_data['稼動時間\n(Hrs)'] = pie_data['計畫投產工時\n(Hrs)']-pie_data['调机工时Setup(min)']-pie_data['機台維修時間\n  Down(min)']-pie_data['製程異常\n時間Hold(min)']-pie_data['物料異常\n時間Hold(min)']-pie_data['借出工時RD(min)']-pie_data['待料時間/其它Idel(min)']
        pie_data = pie_data.drop('計畫投產工時\n(Hrs)')
        title = str(last_workday) +' SMT Production Time Distribution'

        fig = px.pie(names=labels, values=pie_data.values, title=title)
        fig.update_layout(height=600, width=1000)
        fig_html = pio.to_html(fig, full_html=False)
        dash.fig_fordaily = fig_html

        # 下方表格
        data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=8, usecols='A:AK', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
        dash.day = table_process(data_day)

        context = {
            'data': dash.day.values.tolist(),
            'columns': dash.day.columns,
            'placeholder_fig': fig_html,
            'options': dash.options,
        }

        return render(request, 'page1_daily.html',context)
    
    elif request.method == "POST" and 'select_button' in request.POST:
        select_day = request.POST.get("select1")
        last_two_digits = select_day[-2:]
        if last_two_digits.startswith('0'):
            last_two_digits = last_two_digits[1:]

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        pie_data = pie_data.loc[:, ['計畫投產工時\n(Hrs)','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
            '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間/其它Idel(min)']].astype(float).squeeze()
        labels = ['调机工时 Setup (Hrs)', '機台維修時間 Down (Hrs)', '製程異常時間 Hold (Hrs)', '物料異常時間 Hold (Hrs)', '借出工時 RD (Hrs)', '待料時間/其它 Idel (Hrs)','稼動時間 (Hrs)']
        # 確認取出的資料只有一筆
        if pie_data.ndim == 1:
            # 分鐘的換成小時
            pie_data['调机工时Setup(min)'] /= 60
            pie_data['機台維修時間\n  Down(min)'] /= 60
            pie_data['製程異常\n時間Hold(min)'] /= 60
            pie_data['物料異常\n時間Hold(min)'] /= 60
            pie_data['借出工時RD(min)'] /= 60
            pie_data['待料時間/其它Idel(min)'] /= 60
        pie_data['稼動時間\n(Hrs)'] = pie_data['計畫投產工時\n(Hrs)']-pie_data['调机工时Setup(min)']-pie_data['機台維修時間\n  Down(min)']-pie_data['製程異常\n時間Hold(min)']-pie_data['物料異常\n時間Hold(min)']-pie_data['借出工時RD(min)']-pie_data['待料時間/其它Idel(min)']
        pie_data = pie_data.drop('計畫投產工時\n(Hrs)')
        title = select_day +' SMT Production Time Distribution'

        fig = px.pie(names=labels, values=pie_data.values, title=title)
        fig.update_layout(height=600, width=1000)
        fig_html = pio.to_html(fig, full_html=False)
        dash.fig_fordaily = fig_html

        # 下方表格
        data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=8, usecols='A:AK', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
        dash.day = table_process(data_day)

        context = {
            'data': dash.day.values.tolist(),
            'columns': dash.day.columns,
            'placeholder_fig': fig_html,
            'options': dash.options,
        }

        return render(request, 'page1_daily.html',context)
        
    
    
    elif not dash.anyNone(dash.day): # 從別頁點回來的話把資料留住
        
        context = {
            'data': dash.day.values.tolist(),
            'columns': dash.day.columns,
            'placeholder_fig': dash.fig_fordaily,
            'options': dash.options,
        }
        
        return render(request, 'page1_daily.html',context)
    
    else:
        placeholder_df = pd.DataFrame(columns=['Please', 'Upload', 'Data', 'First'])
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

        context = {
            'data': placeholder_df.values.tolist(),
            'columns': placeholder_df.columns,
            'placeholder_fig': placeholder_fig,
            #'options': dash.options,
        }
        return render(request, 'page1_daily.html',context)


def weekly(request):
    global dash
    # 先暫時不要用圖
    placeholder_fig = dash.placeholder_figure()
    placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)
    # 預設跳轉至當周
    if not dash.anyNone(dash.by_date): 
        
        dates = dash.options
        options = find_date_ranges(dates)
        dash.weekly_options = options
        context = {
            'placeholder_fig': placeholder_fig,
            'options': dash.weekly_options,
        }
        
        return render(request, 'page2_weekly.html',context)
    
    # 選擇別週
    elif request.method == "POST" and 'select_week_button' in request.POST:
        select_week = request.POST.get("select2")
        '''

        # 取出要畫圓餅圖的資料及欄位
        pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
        pie_data = pie_data.loc[:, ['計畫投產工時\n(Hrs)','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
            '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間/其它Idel(min)']].astype(float).squeeze()
        labels = ['调机工时 Setup (Hrs)', '機台維修時間 Down (Hrs)', '製程異常時間 Hold (Hrs)', '物料異常時間 Hold (Hrs)', '借出工時 RD (Hrs)', '待料時間/其它 Idel (Hrs)','稼動時間 (Hrs)']
        # 確認取出的資料只有一筆
        if pie_data.ndim == 1:
            # 分鐘的換成小時
            pie_data['调机工时Setup(min)'] /= 60
            pie_data['機台維修時間\n  Down(min)'] /= 60
            pie_data['製程異常\n時間Hold(min)'] /= 60
            pie_data['物料異常\n時間Hold(min)'] /= 60
            pie_data['借出工時RD(min)'] /= 60
            pie_data['待料時間/其它Idel(min)'] /= 60
        pie_data['稼動時間\n(Hrs)'] = pie_data['計畫投產工時\n(Hrs)']-pie_data['调机工时Setup(min)']-pie_data['機台維修時間\n  Down(min)']-pie_data['製程異常\n時間Hold(min)']-pie_data['物料異常\n時間Hold(min)']-pie_data['借出工時RD(min)']-pie_data['待料時間/其它Idel(min)']
        pie_data = pie_data.drop('計畫投產工時\n(Hrs)')
        title = select_day +' SMT Production Time Distribution'

        fig = px.pie(names=labels, values=pie_data.values, title=title)
        fig.update_layout(height=600, width=1000)
        fig_html = pio.to_html(fig, full_html=False)
        dash.fig_fordaily = fig_html
        '''

        context = {
            'placeholder_fig': placeholder_fig,
            'options': dash.weekly_options,
        }

        return render(request, 'page2_weekly.html',context)
    
    else: # 如果還沒上傳資料就點過來
        placeholder_fig = dash.placeholder_figure()
        placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

        context = {
            'placeholder_fig': placeholder_fig,
        }
        return render(request, 'page2_weekly.html',context)

def monthly(request):
    return render(request, "page3_monthly.html")

