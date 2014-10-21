import dateutil.parser
import time
#import numpy as np
from itertools import tee, izip
#from sklearn import preprocessing
#from sklearn.cluster import KMeans
import requests

def vectors_from_points(points):
    
    import numpy as np
    
    next_points, last_points = tee(points)
    next(next_points,None)
        
    for next_point, last_point in izip(next_points,last_points):
        
        #print next_point
        
        lat = next_point[0]
        lon = next_point[1]
        last_lat = last_point[0]
        last_lon = last_point[1]

        dt = (next_point[2] - last_point[2]).total_seconds() / 3600.0
                
        d_lat = (lat-last_lat)
        d_lon = (lon-last_lon)
        
        
        
        yield np.array([ lat, lon,  d_lat/dt, d_lon/dt ])

def cluster(points):
    
    import numpy as np
    from sklearn import preprocessing
    from sklearn.cluster import KMeans
    
    
    scaler = preprocessing.StandardScaler(copy=False)
    
    data_points, vector_points = tee(points)
    
    data = scaler.fit_transform(np.array([ i for i in vectors_from_points(vector_points) ]))
    

    
    if data.size == 0:
        return []
    
    mean_centroid_dist = {} 
    for n_clusters in range(2,30):
        k = KMeans(n_clusters=n_clusters)
        k.fit(data)
        #print "k = ",n_clusters
        #print "mean centroid distance = ", k.inertia_
        mean_centroid_dist[n_clusters] = k.inertia_
        last_mcd = mean_centroid_dist.get(n_clusters-1,False)
        if last_mcd:
            improve = int(100 * k.inertia_ / last_mcd)
            #print "percentage of previous mean centroid distance ",improve
            if improve >= 90:       
                break
    
    cluster_times = dict([(i,[]) for i in range(n_clusters) ])
    
    data_points.next()
    
    for i, point in enumerate(data_points):    
        cluster_times[k.labels_[i]].append(point[2])
                
    total_days = {}
    early_hours = {}
    late_hours = {}

    common_days = {}
    
    days = dict([ (i,d) for i,d in enumerate(['Mondays','Tuesdays','Wednesdays','Thursdays','Fridays', 'Saturdays', 'Sundays']) ])
    
    day_ratio = 7.0
    other_ratio = 7.0 / 6.0
    week_ratio  = 7.0 / 5.0
    weekend_ratio = 7.0 / 2.0
    
    for i in range(n_clusters):
        
        total_days[i] = len(set([ t.date().toordinal() for t in cluster_times[i] ]))
        
        hour_hist = np.histogram([t.hour for t in cluster_times[i]], bins=24, density=False, range=(0,23))[0]
        if 0 not in hour_hist:
            early, late = (0,23)
        else:    
            thresh = max(hour_hist) / 5.0
            above_thresh = [ hour_hist > thresh for h in hour_hist ][0]
            transitions= np.diff(above_thresh).nonzero()[0] + 1
            transitions += 1
            if above_thresh[0]:
                transitions = np.r_[0, transitions]
            if above_thresh[-1]:
                transitions = np.r_[transitions, transitions.size]
            transitions.shape = (-1,2)
            if transitions.size <> 0:
                early, late = transitions[np.argmax([ t[1]-t[0] for t in transitions ])]
            else:
                 early, late = (0,23)
        early_hours[i] = early
        late_hours[i] = late
        
        day_hist = np.histogram([ t.isoweekday() for t in cluster_times[i] ], bins=7, density=False, range=(1,7) )[0]
        
        for day in range(7):
            if day_ratio * day_hist[day] > 5 * other_ratio * sum([day_hist[j] for j in range(7) if j <> day ]):
                common_days[i] = days[day]
                break
        if common_days.get(i,False):
            continue
        w_days = week_ratio * sum([ day_hist[j] for j in range(5) ])
        we_days = weekend_ratio * sum([ day_hist[j] for j in range(5,7) ])
        if w_days > 5 * we_days:
            common_days[i] = "weekdays"
            continue
        if we_days > 5 * w_days:
            common_days[i] = "weekends"
            continue
        common_days[i] = "all days"
              
    cluster_sets = []
    
    for i,c in enumerate(k.cluster_centers_):
        if len(cluster_times[i]):
            point = scaler.inverse_transform(c)
            pars = {'format':'json', 'zoom':18, 'addressdetails':1, 'lat':"{:12.8f}".format(point[0]), 'lon':"{:12.8f}".format(point[1])}
            try:
                resp = requests.get('http://nominatim.openstreetmap.org/reverse',params=pars)
                place = resp.json().get('display_name','not found')
                osm_id = str(resp.json().get('osm_id','not found'))
            except:
                place = 'not found'
                osm_id = 'not found'
            cluster_sets.append({'lat':point[0], 'lon':point[1], 'lat_rate':point[2], 'lon_rate':point[2],
                'place':place, 'osm_id':osm_id, 'measurements':len(cluster_times[i]),
                'early_hour':early_hours[i], 'late_hour':late_hours[i],
                'day_range':int((max(cluster_times[i])-min(cluster_times[i])).total_seconds()/86400.0), 'total_days':total_days[i],
                'weekdays':common_days.get(i,"None") })
            
    return cluster_sets
            
 
      
      