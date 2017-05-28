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
def make_plots(cds, zoom_cds, tack_im): #, full_race_cds):
    """cds is only used for the zoomed in portion of the map,
    full_race_cds is used for p1 and p3
    """
    boat_plot_opts = dict(plot_width=350, plot_height=350, min_border=0)
    min_, max_ = tack_im.get_tstamps(0)
    x_range = Range1d(min_, max_)

    lat_min, lat_max, lon_min, lon_max = tack_im.get_lat_long_extents(0)
    lat_range = Range1d(lat_min, lat_max)
    lon_range = Range1d(lon_min, lon_max)

    p1 = figure(title='Speed and Heel', x_range=x_range, **boat_plot_opts)
    p2 = figure(title='Zoomed in COG', x_range=lon_range, y_range=lat_range,
                **boat_plot_opts)
    p3 = figure(title='Full Race course', **boat_plot_opts)

    p1.line(x='time_col', y='SOG', source=cds, legend='Speed')
    p1.line(x='time_col', y='Heel', source=cds, legend='Heel', color='green')
    p2.line(x='zoomed_Lon', y='zoomed_Lat', source=zoom_cds, color='red')
    
    p3.line(x='Lon', y='Lat', source=cds, color='blue', line_alpha=.1)
    p3.line(x='zoomed_Lon', y='zoomed_Lat', source=zoom_cds, color='red')
    row_fig = row(p1, p2, p3)
    return x_range, lat_range, lon_range, row_fig

@profile
class IntervalManager(object):
    def __init__(self, event_list, orig_df, window_size=150):
        self.event_list = event_list
        self.orig_df = orig_df
        self.orig_index = orig_df.index
        self.window_size = window_size
    
    def __len__(self):
        return len(self.event_list)

    @profile
    def get_tstamps(self, idx):
        t_idx = self.orig_index.get_loc(self.event_list[idx])
        start, end = t_idx - self.window_size, t_idx + self.window_size
        start = np.max([start, 0])
        orig_index_len = len(self.orig_index)
        end = np.min( [orig_index_len - 1, end])
        start_tstamp = self.orig_index[start]
        end_tstamp = self.orig_index[end]
        return start_tstamp, end_tstamp

    @profile
    def get_lat_long_extents(self, idx):
        t_idx = self.orig_index.get_loc(self.event_list[idx])
        start, end = t_idx - self.window_size, t_idx + self.window_size
        start = np.max([start, 0])
        orig_index_len = len(self.orig_index)
        end = np.min( [orig_index_len - 1, end])
        lat = self.orig_df.Lat[start:end]
        lon = self.orig_df.Lon[start:end]
        lat_min, lat_max = lat.min(), lat.max()
        lon_min, lon_max = lon.min(), lon.max()
        return (lat_min, lat_max, lon_min, lon_max)

    @profile
    def get_lat_lon_cds(self, idx):
        t_idx = self.orig_index.get_loc(self.event_list[idx])
        start, end = t_idx - self.window_size, t_idx + self.window_size
        start = np.max([start, 0])
        orig_index_len = len(self.orig_index)
        end = np.min( [orig_index_len - 1, end])
        lat = self.orig_df.Lat[start:end]
        lon = self.orig_df.Lon[start:end]
        df2 = pd.DataFrame({'zoomed_Lat':lat, 'zoomed_Lon':lon})
        ll_cds = ColumnDataSource(data=df2)
        return ll_cds


global_tack_im = None
@profile
def update_boat(boat_name):
    global global_tack_im
    df2, tacks, gybes = make_boat_tacks(full_df, boat_name)
    df2['time_col'] = df2.index.values
    full_cds = ColumnDataSource(data=df2)
    global_tack_im = IntervalManager(gybes, df2)
    zoom_cds = global_tack_im.get_lat_lon_cds(0)
    return full_cds, zoom_cds, global_tack_im

@profile
def update_ranges(tack_num, tack_im, x_range, lat_range, lon_range, source):
    start, end = tack_im.get_tstamps(tack_num)
    x_range.start = start
    x_range.end = end
    lat_min, lat_max, lon_min, lon_max = tack_im.get_lat_long_extents(tack_num)
    lat_range.start = lat_min
    lat_range.end = lat_max
    lon_range.start = lon_min
    lon_range.end = lon_max

    ll_cds = tack_im.get_lat_lon_cds(tack_num)
    source.data.update(ll_cds.data)

boat_select = Select(value=current_boat, title='Boat', options=BOAT_NAMES)
tack_slider = Slider(start=1, end=10, value=1, step=1,
                    title="Tack Num")
@cb_profile
def update_plot(attrname, old, new):
    global global_source, zoom_source
    boat_name = boat_select.value
    tack_num = tack_slider.value
    src, zsrc, tack_im = update_boat(boat_name)
    global_source.data.update(src.data)
    zoom_source.data.update(zsrc.data)

@cb_profile
def update_tack_slider(attrname, old, new):
    global global_tack_im
    tack_num = tack_slider.value
    update_ranges(tack_num, global_tack_im, global_x_range,
                  global_lat_range, global_lon_range, zoom_source)
    


full_df = pd.read_hdf('race1.hd5')
global_source, zoom_source, global_tack_im = update_boat('USA')

global_x_range, global_lat_range, global_lon_range,  plot = make_plots(global_source, zoom_source,  global_tack_im)
update_ranges(3, global_tack_im, global_x_range, global_lat_range, global_lon_range, zoom_source)

boat_select.on_change('value', update_plot)
tack_slider.on_change('value', update_tack_slider)

                      

controls = column(boat_select, tack_slider)

curdoc().add_root(row(plot, controls))
curdoc().title = "America's Cup tack analysis"
