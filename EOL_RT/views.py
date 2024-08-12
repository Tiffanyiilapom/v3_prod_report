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

def for_error(request):
    # 把舊的東西清掉!
    dash.data = None 
    dash.by_date = None 
    dash.day = None 
    dash.sixplot_html = None 
    dash.flag = False 
    return render(request, "ERROR_Page.html")

def daily(request):
    return render(request,'EOL_RT_p1.html')

def weekly(request):
    return render(request,'EOL_RT_p2.html')

def monthly(request):
    return render(request,'EOL_RT_p3.html')