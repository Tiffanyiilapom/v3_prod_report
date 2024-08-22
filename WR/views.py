from django.shortcuts import render
from datetime import datetime, timedelta, date
from .models import My_Dash
import requests
from bs4 import BeautifulSoup
import pandas as pd

dash = My_Dash()

def week_web_crawler(type, start, end, threshold):
    filtered_df = pd.DataFrame(columns=["No", "work" ,"report data", "found","This is usually because", "personnel did not", "report work", "during this period"])
    start_date = datetime.strptime(start,"%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    print(date_list)

    base_url = 'http://c1eip01:8081/TimeReportStatus/DayDetails'
    site = '1010'
    workcenter = type    
    work_centers = set()
    
    for day in date_list:
        query_date = f'{day}'
        params = {
            'site': site,
            'querymonth': query_date,
            'workcenter': workcenter
        }
        
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                if table:
                    headers = [header.text.strip().replace('\r', '').replace('\n', '') for header in table.find_all('th')]
                    
                    if 'WorkCenter' in headers:
                        workcenter_index = headers.index('WorkCenter')
                    
                        for row in table.find_all('tr'):
                            cells = row.find_all('td')
                            if cells:
                                work_center_value = cells[workcenter_index].text.strip()
                                if work_center_value:  
                                    work_centers.add(work_center_value)
        except requests.exceptions.RequestException as e:
            continue
    
    if not work_centers:
        return filtered_df
    
    work_centers = list(work_centers)
    base_url_wolist_details = 'http://c1eip01:8081/TimeReportStatus/WoListDetails'
    grouped_df = pd.DataFrame()
    
    for workcenter in work_centers:
        for day in date_list:
            query_date = f'{day}'  
            if workcenter == "SMT":
                workcenter_param = workcenter + "%20" * 5
            else:
                workcenter_param = workcenter + "%20"
            
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
        
        if grouped_df.empty:
            filtered_df = []
        else:
            grouped_df['StdManHour'] = pd.to_numeric(grouped_df['StdManHour'], errors='coerce')
            grouped_df['ActManHour'] = pd.to_numeric(grouped_df['ActManHour'], errors='coerce')
            
            grouped_df = grouped_df.iloc[:-1]
            grouped_df = grouped_df.iloc[:, :-1]
            grouped_df['Std/Act'] = grouped_df['StdManHour'] / grouped_df['ActManHour']
            
            filtered_df = grouped_df[grouped_df['Std/Act'] < float(threshold)].copy()
            filtered_df['PostDate'] = pd.to_datetime(filtered_df['PostDate'], format='%Y%m%d').dt.strftime('%Y/%m/%d')
            filtered_df = filtered_df.reset_index(drop=True)
    return filtered_df
    

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
    
    placeholder_fig = dash.placeholder_figure()
    placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

    dash.filtered = week_web_crawler(type, start, end, threshold) 

    context = {
        'formatted_threshold':formatted_threshold,
        'formatted_date': formatted_date,
        'placeholder_fig':placeholder_fig,
        'work_data' : dash.filtered.values.tolist(),
        'work_columns':dash.filtered.columns,
    }

    return render(request, 'WR_p1.html', context)