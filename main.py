from os.path import join, dirname
import datetime

import pandas as pd
import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource, DataRange1d, Select, Slider, Range1d
from bokeh.palettes import Blues4
from bokeh.plotting import figure
from datetime import datetime as dtdt

def profile(f):
    def ret_f(*args, **kwargs):
        t_start = dtdt.now()
        ret_val = f(*args, **kwargs)
        t_end = dtdt.now()
        print t_end - t_start, f.__name__
        return ret_val
    return ret_f

def cb_profile(f):
    def ret_f(attr, old, new):
        t_start = dtdt.now()
        ret_val = f(attr, old, new)
        t_end = dtdt.now()
        print t_end - t_start, f.__name__
        return ret_val
    return ret_f

@profile
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

    df3 = pd.DataFrame(
        {
            'Lat':df2.Lat, 'Lon':df2.Lon,
            'SOG':df2.SOG, 'Heel':df2.Heel})
    
    return df3, tacks, gybes




current_boat = 'JPN'
BOAT_NAMES = ['FRA', 'USA', 'JPN', 'SWE', 'GBR', 'NZL']

@profile
def make_plots(cds, tack_im): #, full_race_cds):
    """cds is only used for the zoomed in portion of the map,
    full_race_cds is used for p1 and p3
    """
    boat_plot_opts = dict(plot_width=350, plot_height=350, min_border=0)
    min_, max_ = tack_im.get_tstamps(0)
    x_range = Range1d(min_, max_)
    # x_range.start = t_start
    # x_range.end = t_end
    #x_range.bounds = [0, 50]

    p1 = figure(title='Speed and Heel', x_range=x_range, **boat_plot_opts)
    p2 = figure(title='Zoomed in COG', **boat_plot_opts)
    #p3 = figure(title='Full Race course', **boat_plot_opts)

    p1.line(x='time_col', y='SOG', source=cds, legend='Speed')
    p1.line(x='time_col', y='Heel', source=cds, legend='Heel', color='green')
    #p2.line(x='Lon', y='Lat', source=cds)
    
    # p3.line(df2.Lon, df2.Lat, color='blue', line_alpha=.1)
    # p3.line(df3.Lon, df3.Lat, line_width=1, color='red')

    #row_fig = row(p1, p2)
    #row_fig = row(p1, p2, p3))
    #return x_range, row_fig
    return x_range, p1

@profile
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


class IntervalManager(object):
    def __init__(self, event_list, orig_index):
        self.event_list = event_list
        self.orig_index = orig_index
    
    def __len__(self):
        return len(self.event_list)

    @profile
    def get_tstamps(self, idx, window_size=150):
        t_idx = self.orig_index.get_loc(self.event_list[idx])
        start, end = t_idx - window_size, t_idx + window_size
        start = np.max([start, 0])
        orig_index_len = len(self.orig_index)
        end = np.min( [orig_index_len - 1, end])
        start_tstamp = self.orig_index[start]
        end_tstamp = self.orig_index[end]
        return start_tstamp, end_tstamp

global_tack_im = None
@profile
def update_boat(boat_name):
    global global_tack_im
    df2, tacks, gybes = make_boat_tacks(full_df, boat_name)

    df2['time_col'] = df2.index.values
    full_cds = ColumnDataSource(data=df2)
    global_tack_im = IntervalManager(tacks, df2.index)
    return full_cds, global_tack_im

@profile
def update_ranges(tack_num, tack_im, x_range):
    start, end = tack_im.get_tstamps(tack_num)
    x_range.start = start
    x_range.end = end
    

boat_select = Select(value=current_boat, title='Boat', options=BOAT_NAMES)


tack_slider = Slider(start=1, end=10, value=1, step=1,
                    title="Tack Num")
@cb_profile
def update_plot(attrname, old, new):
    global global_source
    boat_name = boat_select.value
    tack_num = tack_slider.value
    #src = get_boat_cds(boat_name, tack_num)
    src, tack_im = update_boat(boat_name)
    global_source.data.update(src.data)

@cb_profile
def update_tack_slider(attrname, old, new):
    global global_tack_im
    tack_num = tack_slider.value
    update_ranges(tack_num, global_tack_im, global_x_range)
    


full_df = pd.read_hdf('race1.hd5')
global_source, global_tack_im = update_boat('USA')

global_x_range, plot = make_plots(global_source, global_tack_im)
update_ranges(3, global_tack_im, global_x_range)

boat_select.on_change('value', update_plot)
tack_slider.on_change('value', update_tack_slider)

                      

controls = column(boat_select, tack_slider)

curdoc().add_root(row(plot, controls))
curdoc().title = "America's Cup tack analysis"
