from django.shortcuts import render
from datetime import datetime, timedelta, date
from .models import My_Dash
import requests
from bs4 import BeautifulSoup
import pandas as pd
from plotly.subplots import make_subplots
import plotly.io as pio
import plotly.graph_objects as go

dash = My_Dash()

def week_web_crawler(type, start, end, threshold):
    #default palceholder
    filtered_df = pd.DataFrame(columns=["No", "work" ,"report data", "found","This is usually because", "personnel did not", "report work", "during this period"])
    placeholder_fig = dash.placeholder_figure()
    fig_sub = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

    start_date = datetime.strptime(start,"%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)

    base_url = 'http://c1eip01:8081/TimeReportStatus/DayDetails'
    site = '1010'
    workcenter = type    
    work_centers = set()
    grouped_df = pd.DataFrame()
    
    for day in date_list:
        query_date = f'{day}'
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
        return filtered_df, fig_sub

    else:
        grouped_df['Std/Act'] = grouped_df['StdManHour']/grouped_df['ActManHour']
        work_centers = grouped_df.drop_duplicates(subset=['WorkCenter'])['WorkCenter'].tolist()
        num_centers = len(work_centers)
        rows = (num_centers // 3) + (num_centers % 3 > 0)
        cols = min(num_centers, 3)
        
        fig = make_subplots(rows=rows, cols=cols, subplot_titles=[f'{wc} Achievement Rate' for wc in work_centers])
        
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
        
        fig.update_layout(height=300 * rows, autosize=True, title_text="Achievement Rates for Different Work Centers", title_x=0.5)
        fig_sub = pio.to_html(fig)
    
    work_centers = list(grouped_df['WorkCenter'])
    base_url_wolist_details = 'http://c1eip01:8081/TimeReportStatus/WoListDetails'
    grouped_df = pd.DataFrame()
    
    for workcenter in work_centers:
        for day in date_list:
            query_date = f'{day}'  

            if type == "SMT" :
                if workcenter == "SMT":
                    workcenter_param = workcenter + "%20" * 5
                else:
                    workcenter_param = workcenter + "%20"
            elif type == "EOL" :
                if workcenter == "EOL-ATE" or "EOL-OPT":
                    workcenter_param = workcenter + "%20"
                else:
                    workcenter_param = workcenter + "%20" * 2
            elif type == "ASSY" :
                if workcenter == "ASSY-AE" or "ASSY-AL" or "ASSY-AS" or "ASSY-OE" or "ASSY-CO" or "ASSY-AW":
                    workcenter_param = workcenter + "%20"
                else:
                    workcenter_param = workcenter 
            
            query_string = f'site={site}&querymonth={query_date}&workcenter={workcenter_param}'
            url = f"{base_url_wolist_details}?{query_string}"
            
            try:
                response_wolist_details = requests.get(url)
                if response_wolist_details.status_code == 200:
                    soup_wolist_details = BeautifulSoup(response_wolist_details.text, 'html.parser')
                    details_table = soup_wolist_details.find('table')
                    if details_table:
                        details_headers = [header.text.strip().replace('\r', '').replace('\n', '') for header in details_table.find_all('th')]
                        details_rows = []
                        for row in details_table.find_all('tr'):
                            cells = row.find_all('td')
                            row_data = [cell.text.strip().replace('\r', '').replace('\n', '') for cell in cells]
                            if row_data:  
                                details_rows.append(row_data)
                        df_details = pd.DataFrame(details_rows, columns=details_headers, index=None)
                        df_details = df_details.iloc[:-1]  
                        grouped_df = pd.concat([grouped_df, df_details], axis=0)
            except requests.exceptions.RequestException as e:
                print(f"Request failed for {query_date} in workcenter {workcenter}: {e}")
                continue
        else:
            grouped_df['StdManHour'] = pd.to_numeric(grouped_df['StdManHour'], errors='coerce')
            grouped_df['ActManHour'] = pd.to_numeric(grouped_df['ActManHour'], errors='coerce')
            
            grouped_df = grouped_df.iloc[:-1]
            grouped_df = grouped_df.iloc[:, :-1]
            grouped_df['Std/Act'] = grouped_df['StdManHour'] / grouped_df['ActManHour']
            
            filtered_df = grouped_df[grouped_df['Std/Act'] < float(threshold)].copy()
            filtered_df['PostDate'] = pd.to_datetime(filtered_df['PostDate'], format='%Y%m%d').dt.strftime('%Y/%m/%d')
            filtered_df = filtered_df.reset_index(drop=True)
    return filtered_df, fig_sub
    

def input(request):
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    context = {
        'yesterday':yesterday,
    }
    return render(request, 'WR_p0.html',context)

def output(request):
    type = request.POST.get("typeSelect")
    start = request.POST.get("datePicker")
    end = request.POST.get("EndPicker")
    formatted_date = start + " ~ " + end 
    threshold = request.POST.get("customerRange")
    threshold_value = round(float(threshold) * 100)
    formatted_threshold = f"{threshold_value}%"

    dash.filtered, fig_sub = week_web_crawler(type, start, end, threshold) 

    context = {
        'formatted_threshold':formatted_threshold,
        'formatted_date': formatted_date,
        'placeholder_fig':fig_sub,
        'work_data' : dash.filtered.values.tolist(),
        'work_columns':dash.filtered.columns,
    }

    return render(request, 'WR_p1.html', context)