from flask import render_template, request
from app import app
from datetime import datetime
from geofun import * # Contains all the app-specific functions
import joblib

# Home page
@app.route('/')
@app.route('/cover')
def cover_page():
    return render_template("cover.html",
        )

# Video of the underlying traffic calculations
@app.route('/video')        
def video_page():
    return render_template("video.html",
        )

# Short bio
@app.route('/about')        
def about_page():
    return render_template("about.html",
        )

# Calculate prediction
@app.route('/future')
def future_page():
    # get arguments from previous webpage
    pickup = request.args.get('traj1')
    dropoff = request.args.get('traj2')
    form_datetime = request.args.get('datetime')   

    # If there is a problem with the input, do not calculate an output
    calc_output = True

    dt=0
    try:
        dt = datetime.strptime(form_datetime, "%m/%d/%Y %I:%M %p")
    except:
        calc_output = False
        est_time = 'Time input not valid'
        est_time_long = 'please use calendar'
        figname = 'no_fig'
        
    # week in year: dt.isocalendar()[1]
    # weekday: dt.weekday()
    # hour in day: dt.hour,

    # Query google API to get the best path between these two points
    directions = googleDirections(pickup, dropoff)
    if directions['status']=='ZERO_RESULTS' or directions['routes'] == []:
        calc_output = False
        est_time = 'Directions not found'
        est_time_long = 'please use a more precise location'
        figname = 'no_fig'
    # Check if the direction returned is sensible    
    
    if calc_output:
        # Load pre-calculated timeseries associated with each geo coordinate
        results = joblib.load('app/static/data/fulldata.joblib')
        # and associated standard deviations
        results_std = joblib.load('app/static/data/fulldata_std.joblib')
    
        # decode the route direction from google's encoded coordinate systems
        route = decode(directions['routes'][0]['overview_polyline']['points'])
        duration = directions['routes'][0]['legs'][0]['duration']['value']
        
        #loop on downloaded routes that have time series
        all_points = []
        
        for k3 in range(len(route)-1):
            # converts 1 segment (two pair of points) into the right units/decimals
            (x1, y1, x2, y2) = reshape_nb([route[k3][0], route[k3][1], route[k3+1][0], route[k3+1][1]],4)
            # apply Bresenham's line algorithm
            all_points.extend(get_line(x1,y1,x2,y2))
        
        # Some start/end overlap between the multiple segments, remove them
        lineset2 = pd.DataFrame(all_points) 
        lineset2.drop_duplicates(inplace=True)
        lineset2 = lineset2.T  
        
    
        # accumulate the total time required for the route
        n = 0.
        daily_curve = np.zeros((24,))
        daily_std = np.zeros((24,))
        for row in lineset2:
            coord = str(lineset2[row][0])+'_'+str(lineset2[row][1])
            if coord in results.index:
                daily_curve += results.ix[coord,dt.weekday()*6:dt.weekday()*6+23]
                daily_std += results_std.ix[coord,dt.weekday()*6:dt.weekday()*6+23]
                n+=1.
        # Normalize for missing points, if any.
        daily_curve = daily_curve*lineset2.shape[1]/n
        # Seasonal trends are negligible
        
        
        est_time = 'The route should take ' + str(round(daily_curve[dt.hour]/60,1)) + ' minutes'
        est_time_long = 'but plan ' + str(round(daily_curve[dt.hour]/60+daily_std[dt.hour]/60,1)) + '   minutes if you must not be late.'
        
        
        #generate figure and a random name    
        figname = plot_hist(range(24),daily_curve/60,daily_std/60,3,dt.hour)
        
    return render_template("future.html",
        est_time = est_time, est_time_long = est_time_long,
        figname = figname,
        )
        
