from django.shortcuts import render
from datetime import datetime, timedelta, date

# Create your views here.
def input(request):
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    context = {
        'yesterday':yesterday,
    }
    return render(request, 'WR_p0.html',context)

def output(request):
    return render(request, 'WR_p1.html')