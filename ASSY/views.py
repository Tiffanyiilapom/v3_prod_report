from django.shortcuts import render

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
        return render(request, "p0_ASSY.html", context)
    except:
        return render(request, "page_for_error.html")
    
def daily(request):
    try:
        return render(request, "p1_ASSY.html")
    except:
        return render(request, "page_for_error.html")
    
def weekly(request):
    try:
        return render(request, "p2_ASSY.html")
    except:
        return render(request, "page_for_error.html")
    
def monthly(request):
    try:
        return render(request, "p3_ASSY.html")
    except:
        return render(request, "page_for_error.html")