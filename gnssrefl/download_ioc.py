# -*- coding: utf-8 -*-
import argparse
import datetime
import numpy as np
import os
import requests
import subprocess
import sys
import gnssrefl.gps as g
import matplotlib.pyplot as plt

from gnssrefl.utils import validate_input_datatypes, str2bool


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("station", help="station name", type=str)
    parser.add_argument("date1", help="first-date, 20150101", type=str)
    parser.add_argument("date2", help="end-date, 20150101", type=str)
    parser.add_argument("-output", default=None, help="Optional output filename", type=str)
    parser.add_argument("-plt", default=None, help="Optional plot to screen", type=str)
    parser.add_argument("-outliers", default=None, help="attempt to remove outliers", type=str)
    parser.add_argument("-sensor", default=None, help="Various: flt, prs or rad, default is rad. If there are multiple sensors, they are all written to the file.", type=str)
    parser.add_argument("-subdir", default=None, help="subdirectory for output file", type=str)
    args = parser.parse_args().__dict__


    # convert all expected boolean inputs from strings to booleans
    boolean_args = ['plt','outliers']
    args = str2bool(args, boolean_args)


    # only return a dictionary of arguments that were added from the user - all other defaults will be set in code below
    return {key: value for key, value in args.items() if value is not None}


def download_ioc(station: str, date1: str, date2: str, output: str = None, plt: bool = False, outliers: bool = False, sensor= None, subdir: str=None):
    """
    Downloads and saves IOC tide gauge files

    Parameters
    ----------
    station : str
        IOC station name 

    date1 : str
        begin date in yyyymmdd.
        Example value: 20150101

    date2 : str
        end date in yyyymmdd.
        Example value: 20150101

    output : str 
        Optional output filename
        default is None
        The file will be written to REFL_CODE/Files

    plt: bool, optional
        plot comes to the screen
        default is None

    outliers: bool, optional
        tried to remove outliers, but it doesn't work as yet
        default is No

    sensor: str, optional
        type of sensor, prs(for pressure), rad (for radar), flt (for float)
        default is None, which means it will print out what is there.
        if there is more than one sensor you should specifically ask for the one
        you want

    """
    # set up the address for the API call
    url1 = 'http://www.ioc-sealevelmonitoring.org/service.php?query=data&code='
    url2 = '&format=json'

    if len(date1) != 8:
        print('date1 must have 8 characters', date1); sys.exit()
    if len(date2) != 8:
        print('date2 must have 8 characters', date1); sys.exit()
    # should check for < 30 days
    if (date1[0:4] != date2[0:4]):
        print('This code does not collect data across different years.'); sys.exit()

    g.check_environ_variables()

    xdir = os.environ['REFL_CODE']
    if not os.path.exists(xdir):
        print('The REFL_CODE environment variable must be set')
        print('This will tell the code where to put the output.')
        sys.exit()

    outdir = xdir  + '/Files/'
    if not os.path.exists(outdir) :
        subprocess.call(['mkdir', outdir])

    if subdir is None:
        print('Using this output directory: ', outdir)
    else:
        outdir = xdir  + '/Files/' + subdir + '/'
        print('Using this output directory: ', outdir)
        if not os.path.exists(outdir) :
            subprocess.call(['mkdir', outdir])

    csv = False
    if output is None:
        outfile = outdir + station + '_' + 'ioc.txt' # use the default
    else:
        outfile = outdir + output
        if output[-3:] == 'csv':
            csv = True


    month1 = int(date1[4:6])
    month2 = int(date2[4:6])
    year = int(date1[0:4])

    if (month1 == month2):
        newurl = url1 + station + '&timestart=' + date1 + '&timestop=' + date2 + url2
        print(newurl)
        data = requests.get(newurl).json()
        NV = len(data)
        if (len(data) <= 1):
            print('No data. Exiting')
            sys.exit()
    else: 
        ij = 0
        for m in range(month1, month2+1):
            d1, d2 = find_start_stop(year, m)
            print(d1,d2)
            newurl = url1 + station + '&timestart=' + d1 + '&timestop=' + d2 + url2
            print(newurl)
            tdata = requests.get(newurl).json()
            if ij == 0:
                data = tdata
            else:
            # ? https://www.askpython.com/python/dictionary/merge-dictionaries
                data.extend(tdata)
            ij = ij + 1

        NV = len(data)
        print('number of records', NV, ij)
        if (NV <= ij):
            print('No data. Could be station does not exist.  In any case, I am exiting')
            sys.exit()

    fout = open(outfile,'w+')
    print('Writing IOC data to ', outfile)

    if csv:
        fout.write("# YYYY,MM,DD,HH,MM,Water(m),DOY, MJD, SS \n")
    else:
        fout.write("%YYYY MM DD  HH MM   Water(m) DOY  MJD     SS \n")
        fout.write("% 1   2  3   4  5     6        7    8      9  \n")
    i = 1

#    All values X where abs(X – median) > tolerance are hidden.
#    With tolerance = 3*abs(percentile90 - median)
#    The statistics (median and percentile90) are calculated on the data being plotted (12h, 1d, 7d, 30d)
    s = []
    for i in range(0, NV):
        s.append(float(data[i]['slevel']))
    medv = np.median(s) 
    print('median',medv)
    sv = np.sort(np.abs(s-medv))
    percent90 = sv[int(NV*0.9)]  

    print('Your sensor choice:', sensor)
    if outliers:
        criteria = np.abs(percent90*3)
        print('outlier criteria:',round(criteria,2), ' meters')
    else:
        criteria = 100000000

    all_sensors = []
    thetime = []; sealevel = [] ; obstimes = [] ; pt = 0
    for i in range(0, NV):
        slr = data[i]['slevel']
        instrument = data[i]['sensor']
        if instrument not in all_sensors:
            all_sensors.append(instrument)
            print('Found this sensor', instrument)
        t = data[i]['stime']
        sl = float(slr)
        if ((np.abs(sl-medv)) < criteria) and ((sensor == None) or (instrument == sensor)):
            year = int(t[0:4]); mm = int(t[5:7]); dd = int(t[8:10])
            hh = int(t[11:13]); minutes = int(t[14:16])
            sec =  int(t[17:19]) # cannot assume seconds is zero ... cause
            today = datetime.datetime(year, mm, dd)
            doy = (today - datetime.datetime(today.year, 1, 1)).days + 1
            m, f = g.mjd(year, mm, dd, hh, minutes, sec)
            mjd = m + f;
            thetime.append(mjd); sealevel.append(sl)
            #print(year,mm,dd,hh,minutes,sec)
            bigT = datetime.datetime(year=year, month=mm, day=dd, hour=hh, minute=minutes, second=sec)
            obstimes.append(bigT)

            if csv:
                fout.write(" {0:4.0f},{1:2.0f},{2:2.0f},{3:2.0f},{4:2.0f},{5:7.3f},{6:3.0f},{7:15.6f},{8:3.0f}\n".format(year, mm, dd, hh, minutes, sl, doy, mjd,sec))
            else:
                fout.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:2.0f} {4:2.0f} {5:7.3f} {6:3.0f} {7:15.6f} {8:3.0f}\n".format(year, mm, dd, hh, minutes, sl, doy, mjd,sec))
        else:
            pt = pt + 1
    fout.close()

    if plt:
        quickp(station,obstimes,sealevel)


def find_start_stop(year,m):
    """
    finds the start and stop times for each month of the IOC download

    Parameters
    ----------
    year : int
        full year
    m : int
        month number 

    Returns
    -------
    d1 : str
        yyyymmdd for first day of requested month
    d2 : str
        yyyymmdd for last day of requested month

    """
    cyyyy = str(year)
    cmm = '{:02d}'.format(m)
    d1 = cyyyy + cmm + '01'
    # IOC if you ask for data thru nov30, it stops at midnite nov29,
    # which is not what NOAA does - 

    if m == 12:
        d2 = str(year+1) +  '0101'
    else:
        cmm = '{:02d}'.format(m+1)
        d2 = cyyyy + cmm + '01'

    return d1, d2


def quickp(station,t,sealevel):
    """
    makes a quick plot of sea level for station s
    prints to the screen - does not save it.

    Parameters
    -----------
    station : string
        station name

    t : numpy array in datetime format 
        time of the sea level observations

    sealevel : numpy array, float 
        meters (relative - not defined in a datum)
    
    """
    fs = 10
    if (len(t) > 0):
        fig,ax=plt.subplots()
        ax.plot(t, sealevel, '-')
        plt.title('Tides at ' + station)
        plt.xticks(rotation =45,fontsize=fs);
        plt.ylabel('meters')
        plt.grid()
        fig.autofmt_xdate()
        plt.show()
    else:
        print('no data found - so no plot')
    return

def main():
    args = parse_arguments()
    download_ioc(**args)


if __name__ == "__main__":
    main()
