from django.db import models
import plotly.graph_objects as go
import pandas as pd
import io
# Create your models here.
class My_Dash():
    def __init__(self):
        self.data = None # 整個活頁簿
        self.by_date = None # (sheet:SMT_BY日期總表) 給圓餅圖用

        self.day = None
        self.mass_production = None # 量產
        self.trial_production = None # 試產

        self.fig_fordaily = None # 保存每日的圓餅圖
        self.options = None # 保存日期選單

        self.week = None # 給每周的下方表格
        self.weekly_options = None # 保存周別選單
        self.fig_forweek = None # 保存每周的圓餅圖

        self.fig_formonth = None # 保存每月的圓餅圖
        self.sixplot_html = None # 保存每月的六工作站點效率圖
        self.flag = False # 用來判斷是不是有重新上傳其他月份
        
    
    def anyNone(self, *args):
        for i in args:
            if i is None:
                return True
        return False
    
    def placeholder_figure(self):
        placeholder_figure = go.Figure(data=[],
                                       layout=go.Layout(xaxis=dict(title='X Axis Title'),
                                                        yaxis=dict(title='Y Axis Title'),
                                                        margin=dict(l=75, r=75, t=10, b=20),
                                                        width=1000,
                                                        height=700))
        return placeholder_figure
    

class data_decoded():
    def __init__(self, data):
        self.data = data
    
    def file_decode(self):
        
        file_extension= self.data.name.split('.')[-1].lower()
        data = self.data.read()
        
        if file_extension == 'csv':
            data = pd.read_csv(io.StringIO(data.decode('utf-8')))
        elif file_extension == 'xlsx':
            data = pd.read_excel(io.BytesIO(data))
        elif file_extension == 'json':
            data = pd.read_json(data.decode('utf-8'))

        else:
            raise ValueError(f'File Type Unsupported: {file_extension}')
        
        return data
        
        
