from django.shortcuts import render
from datetime import datetime, timedelta, date
from .models import My_Dash

dash = My_Dash()


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
    start_date = datetime.strptime(start,"%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    print(date_list)
    placeholder_fig = dash.placeholder_figure()
    placeholder_fig = placeholder_fig.to_html(full_html=False, default_height=500, default_width=1200)

    context = {
        'formatted_threshold':formatted_threshold,
        'formatted_date': formatted_date,
        'placeholder_fig':placeholder_fig,
    }

    return render(request, 'WR_p1.html', context)