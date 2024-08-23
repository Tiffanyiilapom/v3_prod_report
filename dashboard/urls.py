"""
URL configuration for dashboard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from SMT import views as SMT_views 
from SMT_RT import views as SMT_RT_views
from EOL import views as EOL_views 
from EOL_RT import views as EOL_RT_views
from ASSY import views as ASSY_views
from WR import views as WR_views

urlpatterns = [
    path('error/', SMT_views.for_error, name="error"),  

    # SMT
    path('upload/', SMT_views.upload, name='upload'),
    path('daily/', SMT_views.daily, name='daily'),
    path('weekly/', SMT_views.weekly, name='weekly'),
    path('monthly/', SMT_views.monthly, name='monthly'),

    #EOL
    path('eol_upload/', EOL_views.upload, name='eol_upload'),
    path('eol_daily/', EOL_views.daily, name='eol_daily'),
    path('eol_weekly/', EOL_views.weekly, name='eol_weekly'),
    path('eol_monthly/', EOL_views.monthly, name='eol_monthly'),
    
    #ASSY
    path('assy_upload/', ASSY_views.upload, name='assy_upload'),
    path('assy_daily/', ASSY_views.daily, name='assy_daily'),
    path('assy_weekly/', ASSY_views.weekly, name='assy_weekly'),
    path('assy_monthly/', ASSY_views.monthly, name='assy_monthly'),

    #WR
    path('', WR_views.input, name="home"),  
    path('WR_input/', WR_views.input, name='WR_input'),
    path('WR_output/', WR_views.output, name='WR_output'),

]
