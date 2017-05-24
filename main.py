from os.path import join, dirname
import datetime

import pandas as pd
import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource, DataRange1d, Select, Slider
from bokeh.palettes import Blues4
from bokeh.plotting import figure


def make_boat_tacks(df, boat_name):
    df2 = df[boat_name].copy()

    df2['CWD'] = df2['CourseWindDirection']

    df2['WC_DIFF'] = (df2['CWD'] - df2['COG']) #Wind Course difference
    #create a series named WC_DIFF180 that is the elementwise modulo 180 of WC_DIFF
    df2['WC_DIFF180'] = df2['WC_DIFF'] % 180
    df2['WC_DIFF360'] = df2['WC_DIFF'] % 360
    df2['GYB_DIFF'] = df2['WC_DIFF'] - 180
    df2['GYB_DIFF360'] = df2['GYB_DIFF'] % 360

    # every timestamp where WC_DIFF180 is less than 1
    tacks = df2[df2['WC_DIFF360'] <1].index.values
    #print tacks
    gybes = df2[df2['GYB_DIFF360'] <1].index.values
    return df2, tacks, gybes


def update_plot(tack_num, boat_name):
    df2, tacks, gybes = make_boat_tacks(full_df, boat_name)
    tstamp = tacks[tack_num]
    
    t_idx = df2.index.get_loc(tstamp)
    window_width = 100
    start, end = t_idx - window_width, t_idx + window_width
    start = np.max(start,0)
    df3 = df2.ix[start:end]
    idx_range = np.arange(window_width*2)
    df3.index = idx_range
    #fig = plt.figure(figsize=(8,5))
    #ax = fig.add_axes([0,0,1,1], polar=True)
    #COG_h, = ax.plot(df3.COG * (np.pi/180), idx_range, label='Boat Heading')
    #cwd_h, = ax.plot(df3.CWD * (np.pi/180), idx_range, color='green', label='CourseWindDirection')
    #cwd_180_h, = ax.plot((df3.CWD - 180) * (np.pi/180), idx_range, color='red', label='CourseWindDirection - 180')
    fig, ax = plt.subplots(ncols=3, figsize=(24,8))
    ax1, ax2, ax3 = ax
    
    #df3.CB_CWD.plot(title="%d" % tstamp, ax=ax1)
    #df3.CW_COG.plot(color='green', ax=ax1)
    #df3.WC_DIFF.plot(color='red', ax=ax1)

    df3.SOG.plot(legend="SOG", ax=ax1)
    df3.Heel.plot(legend="Heel", ax=ax1)
    
    ax2.plot(df3.Lon, df3.Lat )
    ax2.set_title("Tack Zoomed in")
    
    ax3.plot(df2.Lon, df2.Lat, color='blue')# legend="Full Course", title="Full Race COG")
    ax3.plot(df3.Lon, df3.Lat, color='red', linewidth=3.0) # legend="Tack Course", linewidth=3.0)

    ax3.set_title( "Full Race Cog")
    
    plt.figure()

def get_boat_cds(boat_name, tack_num):
    df2, tacks, gybes = make_boat_tacks(full_df, boat_name)
    tstamp = tacks[tack_num]
    
    t_idx = df2.index.get_loc(tstamp)
    window_width = 250
    start, end = t_idx - window_width, t_idx + window_width
    start = np.max(start,0)
    df3 = df2.ix[start:end]
    idx_range = np.arange(window_width*2)
    df3.index = idx_range
    #df3['IDX_COL'] = df3.index.values
    df3.loc[df3.index, 'IDX_COL'] = df3.index.values
    cds2 = ColumnDataSource(data=df3)
    return cds2




def make_plot(cds):
    boat_plot_opts = dict(plot_width=350, plot_height=350, min_border=0)
    p1 = figure(title='Speed and Heel', **boat_plot_opts)
    p2 = figure(title='Zoomed in COG', **boat_plot_opts)
    #p3 = figure(title='Full Race course', **boat_plot_opts)

    p1.line(x='IDX_COL', y='SOG', source=cds, legend='Speed')
    p1.line(x='IDX_COL', y='Heel', source=cds, legend='Heel', color='green')
    p2.line(x='Lon', y='Lat', source=cds)
    
    # p3.line(df2.Lon, df2.Lat, color='blue', line_alpha=.1)
    # p3.line(df3.Lon, df3.Lat, line_width=1, color='red')

    row_fig = row(p1, p2)
    #row_fig = row(p1, p2, p3))
    #t = show(row_fig)
    return row_fig


current_boat = 'JPN'
BOAT_NAMES = ['FRA', 'USA', 'JPN', 'SWE', 'GBR', 'NZL']
boat_select = Select(value=current_boat, title='Boat', options=BOAT_NAMES)


tack_slider = Slider(start=1, end=10, value=1, step=1,
                    title="Tack Num")

def update_plot(attrname, old, new):
    boat_name = boat_select.value
    tack_num = tack_slider.value
    src = get_boat_cds(boat_name, tack_num)
    global_source.data.update(src.data)



full_df = pd.read_hdf('race1.hd5')
global_source = get_boat_cds('USA', 5)
plot = make_plot(global_source)
boat_select.on_change('value', update_plot)
tack_slider.on_change('value', update_plot)
                      

controls = column(boat_select, tack_slider)

curdoc().add_root(row(plot, controls))
curdoc().title = "America's Cup tack analysis"
