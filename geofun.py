import json
import urllib
import pandas as pd
import numpy as np
import matplotlib
# To prevent server errors on AWS EC", avoid DISPLAY of figure (only save as png)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from random import randint

# Codes called by the website
#	make the plots
#	get coordinates+trajectory for start/end location
#	project vectors onto grid (Bresenham)
#	decode google's geo coordinate


def make_time_str(t):
# Converts an hour value into non-military american-style format 
    if t == 0:
        time_str = '12 a.m.'
    elif t < 12:
        time_str = str(t)+' a.m.'
    elif t == 12:
        time_str = '12 p.m.'
    else:
        time_str = str(t-12)+' p.m.'   
    return time_str
        
        
def plot_hist(x,avg,std,mavf,hour):
# Plot the daily traffic pattern with +/- 1 standard deviation as a semi-transparent zone
# Axes color changed to white and backgorund made transparent to accomodate website
# Save figure using a random filename to ensure each query returns the approriate figure

    fig = plt.figure(1, figsize=(5,5))
    fig.clear()
    # this is required to change the color of axes to white later
    ax  = fig.add_subplot(1, 1, 1)
    
    # Plot the mean +/- 1 standard deviation filled zone
    plt.fill_between(x, avg-std, avg+std, color=(0.5,0.5,1.0), lw=0, alpha=0.5)
	# Plot the mean as a thick red line
    plt.plot(x, avg, color='r', lw=2)  
	# Identify the requested hour on the graph using a big red circle  
    plt.plot(x[hour],avg[hour], 'o', color=(1,0.8,0.8), markeredgewidth=2, markeredgecolor='red', markersize=12)
    plt.xlim((0,23))
    xlab = plt.xlabel('Time of day', fontsize=16)
    ylab = plt.ylabel('Trip duration (min)', fontsize=16)
    tick_pos = range(2,23,5)
    plt.xticks(tick_pos, [make_time_str(t) for t in tick_pos])    
    
    # set all the axes in white    
    xlab.set_color("white")
    ylab.set_color("white")
    [i.set_color("white") for i in plt.gca().get_xticklabels()]
    [i.set_color("white") for i in plt.gca().get_yticklabels()]
    ax_list = ['bottom','top','right','left']
    for axpos in ax_list:
        ax.spines[axpos].set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    # Generate a random name for the figure to prevent it fro loading an old figure    
    figname = str(randint(0,1000000))
    plt.savefig('app/static/img/'+figname+'.png', bbox_inches='tight', transparent=True)
    return figname

def googleDirections(origin,destination):
    """This function takes an origin, a destination, and a mode of transportation
    and returns a result of a Google directions query as a json dict.
    Code from: https://github.com/jainsley/childHood/blob/master/website/googleAPIFunctions.py"""
    
    #origin = str(coords['pick_lat']) + ',' + str(coords['pick_lon'])
    #destination = str(coords['drop_lat']) + ',' + str(coords['drop_lon'])
    
    baseURL = 'https://maps.googleapis.com/maps/api/directions/json?'
    walkingURL = baseURL + 'origin=' + origin + '&destination=' + destination + '&components=administrative_area:NY|country:US'
    
    # prevent too many request per second
    attempts = 0
    success = False
    
    while success != True and attempts < 3:
        directions = json.loads(urllib.urlopen(walkingURL).read())
        attempts += 1
        # The GetStatus function parses the answer and returns the status code
        # This function is out of the scope of this example (you can use a SDK).
        status = directions['status']
        if status == "OVER_QUERY_LIMIT":
            time.sleep(2)
            # retry
            continue
        success = True
        
        if attempts == 3:
            # send an alert as this means that the daily limit has been reached
            print "Daily limit has been reached"
                
    return directions


# Code for Bresenham's line algorithm from:
# http://www.roguebasin.com/index.php?title=Bresenham%27s_Line_Algorithm#Python


def get_line(x1, y1, x2, y2):
    points = []
    issteep = abs(y2-y1) > abs(x2-x1)
    if issteep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    rev = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        rev = True
    deltax = x2 - x1
    deltay = abs(y2-y1)
    error = int(deltax / 2)
    y = y1
    ystep = None
    if y1 < y2:
        ystep = 1
    else:
        ystep = -1
    for x in range(x1, x2 + 1):
        if issteep:
            points.append((y, x))
        else:
            points.append((x, y))
        error -= deltay
        if error < 0:
            y += ystep
            error += deltax
    # Reverse the list if the coordinates were reversed
    if rev:
        points.reverse()
    return points

'''Provides utility functions for encoding and decoding linestrings using the 
Google encoded polyline algorithm.
Code from: https://gist.github.com/signed0/2031157#file-gistfile1-py
Thanks!
'''

def encode_coords(coords):
    '''Encodes a polyline using Google's polyline algorithm
    
    See http://code.google.com/apis/maps/documentation/polylinealgorithm.html 
    for more information.
    
    :param coords: Coordinates to transform (list of tuples in order: latitude, 
    longitude).
    :type coords: list
    :returns: Google-encoded polyline string.
    :rtype: string    
    '''
    
    result = []
    
    prev_lat = 0
    prev_lng = 0
    
    for x, y in coords:        
        lat, lng = int(y * 1e5), int(x * 1e5)
        
        d_lat = _encode_value(lat - prev_lat)
        d_lng = _encode_value(lng - prev_lng)        
        
        prev_lat, prev_lng = lat, lng
        
        result.append(d_lat)
        result.append(d_lng)
    
    return ''.join(c for r in result for c in r)
    
def _split_into_chunks(value):
    while value >= 32: #2^5, while there are at least 5 bits
        
        # first & with 2^5-1, zeros out all the bits other than the first five
        # then OR with 0x20 if another bit chunk follows
        yield (value & 31) | 0x20 
        value >>= 5
    yield value

def _encode_value(value):
    # Step 2 & 4
    value = ~(value << 1) if value < 0 else (value << 1)
    
    # Step 5 - 8
    chunks = _split_into_chunks(value)
    
    # Step 9-10
    return (chr(chunk + 63) for chunk in chunks)

def decode(point_str):
    '''Decodes a polyline that has been encoded using Google's algorithm
    http://code.google.com/apis/maps/documentation/polylinealgorithm.html
    
    This is a generic method that returns a list of (latitude, longitude) 
    tuples.
    
    :param point_str: Encoded polyline string.
    :type point_str: string
    :returns: List of 2-tuples where each tuple is (latitude, longitude)
    :rtype: list
    
    '''
            
    # sone coordinate offset is represented by 4 to 5 binary chunks0
    coord_chunks = [[]]
    for char in point_str:
        
        # convert each character to decimal from ascii
        value = ord(char) - 63
        
        # values that have a chunk following have an extra 1 on the left
        split_after = not (value & 0x20)         
        value &= 0x1F
        
        coord_chunks[-1].append(value)
        
        if split_after:
                coord_chunks.append([])
        
    del coord_chunks[-1]
    
    coords = []
    
    for coord_chunk in coord_chunks:
        coord = 0
        
        for i, chunk in enumerate(coord_chunk):                    
            coord |= chunk << (i * 5) 
        
        #there is a 1 on the right if the coord is negative
        if coord & 0x1:
            coord = ~coord #invert
        coord >>= 1
        coord /= 100000.0
                    
        coords.append(coord)
    
    # convert the 1 dimensional list to a 2 dimensional list and offsets to 
    # actual values
    points = []
    prev_x = 0
    prev_y = 0
    for i in xrange(0, len(coords) - 1, 2):
        if coords[i] == 0 and coords[i + 1] == 0:
            continue
        
        prev_x += coords[i + 1]
        prev_y += coords[i]
        # a round to 6 digits ensures that the floats are the same as when 
        # they were encoded
        points.append((round(prev_x, 6), round(prev_y, 6)))
    
    return points    

def reshape_nb(x,n):
    # x is the array of numbers, n the number of decimals to preserve
    new_values = []
    for value in x:
        new_values.append(int(round(value*(10**n))))
    return new_values

def check_xy(x,y,lim):
    return not (x<lim[0] or x>=lim[1] or y<lim[2] or y>=lim[3])
