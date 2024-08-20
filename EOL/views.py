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
from datetime import datetime, timedelta, date
import requests
import re
from bs4 import BeautifulSoup
from plotly.subplots import make_subplots

# Create your views here.

dash = My_Dash()

def process_reason(text):
    # 無異常的狀況
    text_to_replace = '1. 維修:\n2. 製程:\n3. 待料:\n4. 物料:'
    if text.strip() == text_to_replace:
        return ''
    
    # Define the patterns to look for
    patterns = {
        '維修': r'1\. 維修:\s*(.*?)(?=\s*\d\.)',
        '製程': r'2\. 製程:\s*(.*?)(?=\s*\d\.)',
        '待料': r'3\. 待料:\s*(.*?)(?=\s*\d\.)',
        '物料': r'4\. 物料:\s*(.*?)(?=\s*\d\.)',
    }
    results = []
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match and match.group(1).strip(): # match代表(.*?)有捕獲到東西
            results.append(f"{key}:{match.group(1).strip()}")  # match.group(1)回傳捕獲的內容
    return ', '.join(results) if results else '無異常'

def conditional_round(x):
    if pd.isna(x):  
        return x
    if isinstance(x, (int, float)):  
        if x < 1 or (x > 1 and x < 2 and x/10 != 0):
            return round(x, 4)
        else:
            return round(x, 2)
    return x

def clean_time_format(time_str):
    if str(time_str).startswith('1900'):
        return '00:00'
    time_str = str(time_str)
    return time_str if len(time_str) == 5 else time_str[:-3]

# 把表格清乾淨
def table_process(df):
    df.drop(index=0, inplace=True)
    df = df.dropna(subset=['班別', '機台編號'], how='all')
    df = df[~((df['班別'] == '班別') & (df['機台編號'] == '機台編號'))]
    df.loc[:,'製令編號'] = df['製令編號'].astype(str)
    df.loc[:,'製令編號'] = df['製令編號'].str.replace(r"^[\'\"]", "", regex=True)
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.fillna(0).infer_objects(copy=False)
    df = df[df['實際產量'] != 0 ]
    columns_to_remove = ['綜整'] + df.filter(regex=r'^Unnamed').columns.tolist()
    df = df.drop(columns=columns_to_remove, errors='ignore')
    time_columns = ['投產開始\n時間(起)', '投產結束\n時間(迄)']
    for col in time_columns:
        df[col] = df[col].apply(clean_time_format)
    df = df.fillna(" ")
    df['未達成/異常原因'] = df['未達成/異常原因'].apply(process_reason)
    df = df.map(conditional_round)
    cols = list(df.columns)
    index1, index2 = cols.index('投入工時'), cols.index('實際UPH')
    cols[index1], cols[index2] = cols[index2], cols[index1]
    df = df[cols]
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

    def get_week_start(date):
        return date - timedelta(days=date.weekday())

    def get_week_end(date):
        return date + timedelta(days=(6 - date.weekday()))

    week_start = get_week_start(start_date)
    week_end = get_week_end(end_date)

    for current_date in dates[1:]:
        current_week_start = get_week_start(current_date)
        current_week_end = get_week_end(current_date)
        
        if current_week_start == week_start:
            end_date = current_date
            week_end = current_week_end
        else:
            result.append(f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            start_date = current_date
            end_date = current_date
            week_start = current_week_start
            week_end = current_week_end

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
    pie_data = pie_data.loc[:, ['計畫投產工時\n(Hrs)','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
            '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間Idel（min）']].astype(float).squeeze()
    labels = ['调机工时 Setup (Hrs)', '機台維修時間 Down (Hrs)', '製程異常時間 Hold (Hrs)', '物料異常時間 Hold (Hrs)', '借出工時 RD (Hrs)', '待料時間 Idel (Hrs)','稼動時間 (Hrs)']
    # 分鐘的換成小時
    pie_data['调机工时Setup(min)'] /= 60
    pie_data['機台維修時間\n  Down(min)'] /= 60
    pie_data['製程異常\n時間Hold(min)'] /= 60
    pie_data['物料異常\n時間Hold(min)'] /= 60
    pie_data['借出工時RD(min)'] /= 60
    pie_data['待料時間Idel（min）'] /= 60
    pie_data['稼動時間\n(Hrs)'] = pie_data['計畫投產工時\n(Hrs)']-pie_data['调机工时Setup(min)']-pie_data['機台維修時間\n  Down(min)']-pie_data['製程異常\n時間Hold(min)']-pie_data['物料異常\n時間Hold(min)']-pie_data['借出工時RD(min)']-pie_data['待料時間Idel（min）']
    if pie_data.ndim == 1: # 如果只有一天的資料 e.g. 每日/該月第一天
        pie_data = pie_data.drop('計畫投產工時\n(Hrs)')
    else:
        pie_data = pie_data.drop('計畫投產工時\n(Hrs)', axis=1)
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
    try:
        current_year = int(datetime.now().year)
        years = [current_year - i for i in range(2)]
        months = list(range(1, 13))
        context = {
            'years': years, 
            'months': months, 
            'current_year': current_year,
        }
        return render(request, "EOL_p0.html", context)
    except:
       return render(request, "ERROR_Page.html")
    
def daily(request):
    try:
        global dash
        # 預設呈現最新的工作天
        if request.method == "POST" and 'data_upload_button' in request.POST:
            dash.flag = False # 代表有新上傳資料
            data = request.FILES.get('data')
            dash.data = data.read()
            data_bydate = pd.read_excel(io.BytesIO(dash.data), sheet_name='EOL BY日期總表', skiprows=3, usecols='H:AI')
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
            title = str(last_workday)+' EOL Production Time Distribution'
            dash.fig_fordaily = func_for_pie(pie_data, title)

            # 下方表格
            data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=3, usecols='A:AE', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
            dash.day = table_process(data_day)
            dash.mass_production = dash.day[dash.day['製令編號'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['製令編號'].str.startswith('3', na=False)]

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

            return render(request, 'EOL_p1.html',context)
        
        # 若上傳非當月資料
        elif request.method == "POST" and 'old_data_upload' in request.POST:
            dash.flag = False
            data = request.FILES.get('old_data')
            year = int(request.POST.get("select_old_year"))
            month = int(request.POST.get("select_old_month"))
            dash.data = data.read()
            data_bydate = pd.read_excel(io.BytesIO(dash.data), sheet_name='EOL BY日期總表', skiprows=3, usecols='H:AI')

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
            title = str(last_workday) +' EOL Production Time Distribution'
            dash.fig_fordaily = func_for_pie(pie_data, title)

            # 下方表格
            data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=3, usecols='A:AE', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
            dash.day = table_process(data_day)
            dash.mass_production = dash.day[dash.day['製令編號'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['製令編號'].str.startswith('3', na=False)]

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

            return render(request, 'EOL_p1.html',context)
        
        # 若選擇非預設的日期
        elif request.method == "POST" and 'eol_select_button' in request.POST and 'eol_select1' in request.POST:
            select_day = request.POST.get("eol_select1")
            last_two_digits = nozero(select_day[-2:])

            # 取出要畫圓餅圖的資料及欄位
            pie_data = dash.by_date[dash.by_date['日期'] == int(last_two_digits)]
            title = select_day +' EOL Production Time Distribution'
            dash.fig_fordaily = func_for_pie(pie_data, title)

            # 下方表格
            data_day = pd.read_excel(io.BytesIO(dash.data), sheet_name=last_two_digits, skiprows=3, usecols='A:AE', dtype={'投產開始\n時間(起)': str, '投產結束\n時間(迄)': str})
            dash.day = table_process(data_day)
            dash.mass_production = dash.day[dash.day['製令編號'].str.startswith('1', na=False)]
            dash.trial_production = dash.day[dash.day['製令編號'].str.startswith('3', na=False)]

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

            return render(request, 'EOL_p1.html',context)
            
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
            
            return render(request, 'EOL_p1.html',context)
        
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
            return render(request, 'EOL_p1.html',context)
    except:
        for_error(request)
        return render(request, 'ERROR_Page.html')
    

def weekly(request):
    try:
        global dash
        # 選擇別週
        if request.method == "POST" and 'select_week' in request.POST and 'eol_select2' in request.POST and not dash.anyNone(dash.by_date):
            select_week = request.POST.get("eol_select2")
            start = int(nozero(select_week[8:10])) # 該周的開始
            end = int(nozero(select_week[-2:])) # 該周的結束
            dates = list(range(start, end+1)) # 取出該周的每一天
            # 表格資料
            table_data = dash.by_date[(dash.by_date['日期'].isin(dates)) & (dash.by_date['平均\n目標UPH\n（PCS）'].notna()) & (dash.by_date['計畫投產工時\n(Hrs)'].notna())]
            table_data = table_data.loc[:, ['日期','平均\n目標UPH\n（PCS）','計畫投產工時\n(Hrs)','目標產量     （PCS）','實際產量\n(PCS）','產能\n效率*','稼動時間        Run（H）','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
                '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間Idel（min）','未開線\nOff(min）','檢驗報廢數', '待判&不良品數','報廢數', '不良率', '直通率\n%']]
            week_data = table_data.copy()
            week_data ['稼動率'] = week_data ['稼動時間        Run（H）'].astype(float)/week_data ['計畫投產工時\n(Hrs)'].astype(float)
            week_data ['產能\n效率*'] = week_data ['實際產量\n(PCS）'].astype(float)/week_data ['目標產量     （PCS）'].astype(float)
            dash.week = process_date(week_data)
            # 圓餅圖資料
            pie_data = dash.by_date[dash.by_date['日期'].isin(dates)]
            title = select_week +' EOL Production Time Distribution'
            dash.fig_forweek = func_for_pie(pie_data, title)

            context = {
                'data': dash.week.values.tolist(),
                'columns': dash.week.columns,
                'placeholder_fig': dash.fig_forweek,
                'options': dash.weekly_options,
            }

            return render(request, 'EOL_p2.html',context)
        
        # 預設跳轉至當周
        elif not dash.anyNone(dash.by_date) : 
            # 設定選單內容
            dates = dash.options
            options = find_date_ranges(dates)
            dash.weekly_options = options
            select_week = options[-1] # 取出最新周次
            start = int(nozero(select_week[8:10])) # 該周的開始
            end = int(nozero(select_week[-2:])) # 該周的結束
            dates = list(range(start, end+1)) # 取出該周的每一天
            # 表格資料
            table_data = dash.by_date[(dash.by_date['日期'].isin(dates)) & (dash.by_date['平均\n目標UPH\n（PCS）'].notna()) & (dash.by_date['計畫投產工時\n(Hrs)'].notna())]
            table_data = table_data.loc[:, ['日期','平均\n目標UPH\n（PCS）','計畫投產工時\n(Hrs)','目標產量     （PCS）','實際產量\n(PCS）','產能\n效率*','稼動時間        Run（H）','调机工时Setup(min)','機台維修時間\n  Down(min)','製程異常\n時間Hold(min)', 
                '物料異常\n時間Hold(min)','借出工時RD(min)','待料時間Idel（min）','未開線\nOff(min）','檢驗報廢數', '待判&不良品數','報廢數', '不良率', '直通率\n%']]
            week_data = table_data.copy()
            week_data ['稼動率'] = week_data ['稼動時間        Run（H）'].astype(float)/week_data ['計畫投產工時\n(Hrs)'].astype(float)
            week_data ['產能\n效率*'] = week_data ['實際產量\n(PCS）'].astype(float)/week_data ['目標產量     （PCS）'].astype(float)
            dash.week = process_date(week_data)
            
            # 圓餅圖資料
            pie_data = dash.by_date[dash.by_date['日期'].isin(dates)]
            title = select_week +' EOL Production Time Distribution'
            dash.fig_forweek = func_for_pie(pie_data, title)

            context = {
                'data': dash.week.values.tolist(),
                'columns': dash.week.columns,
                'placeholder_fig': dash.fig_forweek,
                'options': dash.weekly_options,
            }
            
            return render(request, 'EOL_p2.html',context)
        
        else: # 如果還沒上傳資料就點過來
            placeholder_df = pd.DataFrame(columns=['Please', 'Upload', 'Data', 'First'])
            placeholder_fig = dash.placeholder_figure()
            placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

            context = {
                'data': placeholder_df.values.tolist(),
                'columns': placeholder_df.columns,
                'placeholder_fig': placeholder_fig,
            }
            return render(request, 'EOL_p2.html',context)
    except:
        for_error(request)
        return render(request, 'ERROR_Page.html')
    
def monthly(request):
    try:
        if not dash.anyNone(dash.by_date, dash.sixplot_html) and dash.flag:   # 點回來留住資料

            context = {
                'placeholder_fig': dash.fig_formonth,
                'six_plot': dash.sixplot_html,
            }
            
            return render(request, 'EOL_p3.html',context)
        
        elif not dash.anyNone(dash.by_date): # 初始畫面
            dates = dash.options # 2024-07-18
            year_month = dates[0][:7] # 2024-07
            days = [date.split('-')[2] for date in dates] # 01.02.03.04...17.18
            processed_days = [int(nozero(day)) for day in days] # 1.2.3.4...17.18
            dates = pd.to_datetime(dates).strftime('%Y%m%d') #20240718
            head = pd.to_datetime(year_month).strftime('%Y%m') # 202407

            # 爬蟲
            base_url = 'http://c1eip01:8081/TimeReportStatus/DayDetails'
            site = '1010'
            workcenter = 'EOL'
            grouped_df = pd.DataFrame()

            for day in range(processed_days[0], processed_days[-1]+1):
                query_date = head+f'{day:02d}'
                params = {
                    'site': site,
                    'querymonth': query_date,
                    'workcenter': workcenter
                }

                try:
                    url = requests.get(base_url, params=params)
                    if url.status_code == 200:
                        soup = BeautifulSoup(url.text, 'html.parser')
                        table = soup.find('table')
                        if table:
                            headers = [header.text.strip().replace('\r', '').replace('\n', '') for header in table.find_all('th')]
                            rows = []
                            for row in table.find_all('tr'):
                                cells = row.find_all('td')
                                row_data = [cell.text.strip().replace('\r', '').replace('\n', '') for cell in cells]
                                if row_data:  
                                    rows.append(row_data)
                            df = pd.DataFrame(rows, columns=headers, index=None)
                            df = df.iloc[:-1]
                            df = df.iloc[:, :-1]
                            df = df.drop('WorkOrderType', axis=1)
                            df['PostDate'] = pd.to_datetime(df['PostDate'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
                            df['ActManHour'] = df['ActManHour'].astype(float)
                            df['StdManHour'] = df['StdManHour'].astype(float)
                            df = df.groupby(['PostDate', 'WorkCenter']).sum().reset_index()
                            grouped_df = pd.concat([grouped_df, df], axis=0)
                except requests.exceptions.RequestException as e:
                    continue

            if grouped_df.empty:  # 若報工平台尚無該月資料 e.g. 8/2時報工可能只到7/31
                placeholder_fig = dash.placeholder_figure()
                placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

            else:
                grouped_df['Std/Act'] = grouped_df['StdManHour']/grouped_df['ActManHour']
                work_centers = grouped_df.drop_duplicates(subset=['WorkCenter'])['WorkCenter'].tolist()
                num_centers = len(work_centers)
                rows = (num_centers // 2) + (num_centers % 2 > 0)
                cols = min(num_centers, 2)

                fig = make_subplots(rows=rows, cols=cols, subplot_titles=[f'{wc} Achievement Rate' for wc in work_centers], horizontal_spacing=0.15)

                showlegend_bar = True
                showlegend_line = True

                for index, wc in enumerate(work_centers):
                    filtered_data = grouped_df[grouped_df['WorkCenter'] == wc]
                
                    row = index // cols + 1
                    col = index % cols + 1

                    shape = dict(
                        type="line",
                        x0=filtered_data['PostDate'].min(), y0=1, x1=filtered_data['PostDate'].max(), y1=1,
                        line=dict(color="red", width=3, dash="dashdot"),
                        xref=f'x{index+1}', yref=f'y{index+1}')
                    
                    fig.add_shape(shape, row=row, col=col)
                    fig.add_trace(go.Bar(x=filtered_data['PostDate'],y=filtered_data['Std/Act'],name='Std/Act',marker_color='rgba(65, 105, 225, 0.6)',showlegend=showlegend_bar), row=row, col=col)
                    fig.add_trace(go.Scatter(x=filtered_data['PostDate'],y=filtered_data['Std/Act'],mode='lines+markers',name='Std/Act Line',line=dict(color='darkslateblue'),showlegend=showlegend_line), row=row, col=col)
                    fig.update_xaxes(title_text='PostDate', row=row, col=col)

                    lb = filtered_data['Std/Act'].min()
                    ub =filtered_data['Std/Act'].max()
                    lb = min(lb, 0.5)
                    ub = max(ub, 1.5)
                    fig.update_yaxes(title_text='Std/Act', range=[lb-0.1, ub+0.1], row=row, col=col)
                    fig.update_xaxes(tickformat='%b %d', row=row, col=col)
                    
                    showlegend_bar = False
                    showlegend_line = False

                fig.update_layout(height=300 * rows, width=350 * cols, title_text="Achievement Rates for Different Work Centers",title_x=0.5)
                dash.sixplot_html = pio.to_html(fig)
                dash.flag = True


            # 圓餅圖資料
            pie_data = dash.by_date[dash.by_date['日期'].isin(processed_days)]
            title = year_month +' EOL Production Time Distribution'
            dash.fig_formonth = func_for_pie(pie_data, title)

            context = {
                'placeholder_fig': dash.fig_formonth,
                'six_plot': dash.sixplot_html,
            }
            
            return render(request, 'EOL_p3.html',context)
        
        else: # 如果還沒上傳資料就點過來
            placeholder_fig = dash.placeholder_figure()
            placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

            context = {
                'placeholder_fig': placeholder_fig,
                'six_plot': placeholder_fig,
            }
            return render(request, 'EOL_p3.html',context)
    except:
        for_error(request)
        return render(request, 'ERROR_Page.html')
   