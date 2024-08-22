from django.db import models
import plotly.graph_objects as go
import pandas as pd
import io

# Create your models here.
class My_Dash():
    def __init__(self):
        self.text = None 
        self.fig_sub = None 
        self.filtered = None
        
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
    

        