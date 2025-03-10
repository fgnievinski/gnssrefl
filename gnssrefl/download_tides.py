# -*- coding: utf-8 -*-
"""
downloads NOAA tide gauge files
kristine larson
"""
import argparse
import datetime
import matplotlib.pyplot as plt
import os
import requests
import subprocess
import sys
import gnssrefl.gps as g

from gnssrefl.utils import validate_input_datatypes, str2bool

def noaa_command(station,fout,year,month1,month2,datum,metadata,tt,obstimes,slevel,csv):
    """
    downloads/writes NOAA tidegauge data for one month

    Parameters
    ----------
    station : string
        station name

    year : integer
        full year

    month1 : integer
        starting month

    month2 : integer
        ending month

    datum : string
        water datum

    metadata : boolean
        whether you want the metadata printed to the screen

    tt : numpy array 
        modified julian date for water measurements

    obstimes : numpy array of datetimes
        time of the measurements

    slevel : numpy array of floats
        water level in meters

    csv : boolean
        True if csv output wanted (default is False)

    Returns
    -------
    tt : numpy array 
        modified julian date for water measurements

    obstimes : numpy array
        datetime format, updated with new data

    slevel : numpy array
        sea level (m) updated with new data

    """
    cyyyy = str(year)
    imeta = 0
    for m in range(month1,month2+1):
        cmm = '{:02d}'.format(m)
        d1 = cyyyy + cmm + '01'
        if m in [1,3,5,7,8,10,12]:
            d2 = cyyyy + cmm + '31'
        else:
            if m == 2:
                if (g.dec31(year) == 366): # leap year
                    d2 = cyyyy + cmm + '29'
                else:
                    d2 = cyyyy + cmm + '28'
            else:
                d2 = cyyyy + cmm + '30'

        print(d1,d2) # send whether imeta is equal to 0 ...  
        data, error = pickup_from_noaa(station,d1,d2,datum,imeta==0)
        if not error: # only write out if error not thrown. update the variables
            tt,obstimes,slevel = write_out_data(data,fout, tt,obstimes,slevel,csv)

        imeta = imeta + 1

    return tt,obstimes,slevel


def multimonthdownload(station,datum,fout,year1,year2,month1,month2,csv):
    """
    downloads NOAA water level measurements > one month

    Parameters
    ----------
    station : string
        NOAA station name

    datum : string
        definition of water level datum

    fout - fileID for writing results

    year1 : integer
        year when first measurements will be downloaded

    month1 : integer
        month when first measurements will be downloaded

    year2 : integer
        last year when measurements will be downloaded

    month2 : integer 
        last month when measurements will be downloaded

    csv : boolean 
        whether output file is csv format

    Returns
    -------
    tt : list of times 
        modified julian day
    obstimes : list of datetime objects 

    slevel : list or is it numpy ?? 
         water level in meters

    """
    # set variables for making the plot ... 
    tt = []; slevel = []; obstimes = []
    metadata = True  # set true for now

    imeta = 0
    if (year1 == year2):
        tt, obstimes, slevel = noaa_command(station,fout,year1,month1,month2,datum,metadata,tt,obstimes,slevel,csv)
    else:
        for y in range(year1,year2+1):
            if (y == year1):
                tt,obstimes,slevel = noaa_command(station,fout,y,month1,12,datum,metadata,tt,obstimes,slevel,csv)
            elif (y == year2):
                tt,obstimes,slevel = noaa_command(station,fout,y,1,month2,datum,metadata,tt,obstimes,slevel,csv)
            else:  # get whole year
                tt,obstimes,slevel = noaa_command(station,fout,y,1,12,datum,metadata,tt,obstimes,slevel,csv)

    return tt, obstimes, slevel

def noaa2me(date1):
    """
    converts NOAA type of date string to simple integers

    Parameters 
    ----------
    date1 : string
        time in format YYYYMMDD for year month and day

    Returns 
    -------
    year1 : integer
        full year

    month1 : integer
        month

    day1 : integer
        day of the month

    doy : integer  
        day of year

    modjulday : float
        modified julian date

    """
    year1 = int(date1[0:4]); 
    month1=int(date1[4:6]); 
    day1=int(date1[6:8])
    doy, cdoy, cyyyy, cyy =g.ymd2doy(year1, month1, day1)

    mj, fj = g.mjd(year1, month1, day1, 0, 0, 0)
    modjulday = mj + fj;

    return year1, month1, day1, doy, modjulday

def write_out_data(data,fout, tt,obstimes,slevel,csv):
    """
    writes out the NOAA water level data to a file 

    Parameters
    ----------
    data : dictionary from NOAA API

    fout : file ID 
        for output

    tt : ??

    obstimes : list of datetimes
        times of water level measurements

    slevel : numpy array of floats
        water level in meters

    csv : boolean
        whether csv format or not 

    Returns
    -------
    tt :  same as input, but larger

    obstimes : list of datetimes
        times for waterlevels

    slevel : list of floats
        water levels in meters

    """
    NV = len(data['data'])

    for i in range(0, NV):
        t = data['data'][i]['t']
        slr = data['data'][i]['v']
        slf = data['data'][i]['f']
        if slr == '':
            aa=1
            #print('no data')
        else:
            sl = float(data['data'][i]['v'])
            year = int(t[0:4]); mm = int(t[5:7]); dd = int(t[8:10])
            hh = int(t[11:13]); minutes = int(t[14:16])
            # seconds are zero
            ss = 0
            today = datetime.datetime(year, mm, dd)
            doy = (today - datetime.datetime(today.year, 1, 1)).days + 1
            m, f = g.mjd(year, mm, dd, hh, minutes, ss)
            mjd = m + f;
            tt.append(mjd)
            bigT = datetime.datetime(year=year, month=mm, day=dd, hour=hh, minute=minutes, second=ss)
            obstimes.append(bigT)

            slevel.append(sl)
            if csv:
                fout.write(" {0:4.0f},{1:2.0f},{2:2.0f},{3:2.0f},{4:2.0f},{5:7.3f},{6:3.0f},{7:15.6f},{8:2.0f} \n".format(year, mm, dd, hh, minutes, sl, doy, mjd,ss))
            else:
                fout.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:2.0f} {4:2.0f} {5:7.3f} {6:3.0f} {7:15.6f} {8:2.0f} \n".format(year, mm, dd, hh, minutes, sl, doy, mjd,ss))

    return tt,obstimes,slevel


def pickup_from_noaa(station,date1,date2,datum, printmeta):
    """
    pickup up NOAA data between date1 and date2, which can be 
    longer than one month (NOAA API restriction) 

    Parameters
    ----------
    station: str
        station name

    date1: str 
        beginning time, 20120101 is January 1, 2012

    date2: str
        end time , same format

    datum: str
        what kind of datum is requested

    printmeta : bool
        print metadata to screen 

    Returns
    -------
    data : dictionary in NOAA format

    error : bool

    """

    error = False
    urlL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
    # add the datum - i think
    endL = "&product=water_level&datum=" + datum + "&units=metric&time_zone=gmt&application=web_services&format=json"
    url = urlL + "begin_date=" + date1 + "&end_date=" + date2 + "&station=" + station + endL
    data = requests.get(url).json()
    if 'error' in data.keys():
        print(data['error'])
        error = True
    else:
        if printmeta:
            print(data['metadata'])

    return data, error

def quickp(station,t,sealevel,noaa_name):
    """
    makes a quick plot to the screen of the NOAA tide gauge data

    Parameters
    ----------
    station : str
        NOAA station name

    t : datetime
        times of the water level measurements

    sealevel : numpy array of floats
        water level in meters

    noaa_name : str
        long name of the NOAA tide gauge site 

    """
    fs = 10
    fig,ax=plt.subplots()
    ax.plot(t, sealevel, '-')
    plt.title('Water Levels at ' + noaa_name + ':' + station)
    plt.xticks(rotation =45,fontsize=fs);
    plt.ylabel('meters')
    plt.grid()
    fig.autofmt_xdate()

    plt.show()
    return


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("station", help="station name", type=str)
    parser.add_argument("date1", help="start-date, 20150101", type=str)
    parser.add_argument("date2", help="end-date, 20150110", type=str)
    parser.add_argument("-output", default=None, help="Optional output filename", type=str)
    parser.add_argument("-plt", default=None, help="quick plot to screen", type=str)
    parser.add_argument("-datum", default=None, help="datum (lwd for lakes?)", type=str)
    parser.add_argument("-subdir", default=None, help="optional subdirectory name for output", type=str)
    args = parser.parse_args().__dict__

    # convert all expected boolean inputs from strings to booleans
    boolean_args = ['plt']
    args = str2bool(args, boolean_args)


    # only return a dictionary of arguments that were added from the user - all other defaults will be set in code below
    return {key: value for key, value in args.items() if value is not None}


def download_tides(station: str, date1: str, date2: str, output: str = None, plt: bool = False, datum: str = 'mllw', subdir: str = None):
    """
    Downloads NOAA tide gauge files and stores locally
    If you ask for 31 days of data or less, it will download exactly what you ask for.
    But if you want a longer time series, this code needs to query the NOAA API every month.
    To make the code easier to write, I start with the first day of the first month you ask for and end with
    last day in the last month.

    Output is written to REFL_CODE/Files/ unless subdir optional input is set
    Plot is sent to the screen if requested.

    Parameters 
    ----------
    station : str
        7 character ID of the station.

    date1 : str
        start date.
        Example value: 20150101

    date2 : str
        end date.
        Example value: 20150110

    output : string, optional
        Optional output filename
        default is None

    plt: boolean, optional
        plot comes to the screen
        default is None

    datum: string, optional
        set to lwd for lakes?
        default is mllw

    subdir : str, optional
        subdirectory for output in the $REFL_CODE/Files area

    """
    g.check_environ_variables()

    xdir = os.environ['REFL_CODE']
    outdir = xdir  + '/Files/'
    if not os.path.exists(outdir) :
        subprocess.call(['mkdir', outdir])

    if (subdir is None):
        print('Using regular output directory',outdir )
    else:
        outdir = xdir  + '/Files/' + subdir + '/'
        print('User requested a subdirectory for output', outdir)
        if not os.path.exists(outdir):
            subprocess.call(['mkdir', outdir])

    if len(station) != 7:
        print('station must have 7 characters ', station); sys.exit()
    if len(date1) != 8:
        print('date1 must have 8 characters', date1); sys.exit()
    if len(date2) != 8:
        print('date2 must have 8 characters', date2); sys.exit()


    csv = False
    # use the default, which is plain text
    if output is None:
        outfile = outdir + station + '_' + 'noaa.txt'
    else:
        if output[-3:] == 'csv':
            csv = True
        outfile = outdir + output

    print('Writing contents to: ', outfile)
    fout = open(outfile, 'w+')
    if csv:
        fout.write("#YYYY,MM,DD,HH,MM, Water(m),DOY,   MJD, Seconds\n")
    else:
        fout.write("%YYYY MM DD HH MM  Water(m) DOY    MJD      Seconds\n")
        fout.write("% 1    2  3  4  5    6       7       8         9\n")


    year1, month1, day1, doy1,modjul1 = noaa2me(date1)
    year2, month2, day2, doy2,modjul2 = noaa2me(date2)
    deltad = int(modjul2-modjul1)
    if deltad < 1:
        print('second time is later than first time OR time is less than one day.')
        sys.exit()

    metadata = True
    if (deltad) > 31:
        tt,obstimes,slevel = multimonthdownload(station,datum,fout,year1,year2,month1,month2,csv)
        noaa_name = station # this is not hte right one ... but 
    else:
        tt = []; slevel = []; obstimes = []
        # 'data' are stored in the dictionary data
        data,error = pickup_from_noaa(station,date1,date2,datum,True)
        if not error:
            noaa_name = data['metadata']['name']
            tt,obstimes,slevel = write_out_data(data,fout, tt,obstimes,slevel,csv)

    fout.close()
    if plt:
        quickp(station,obstimes,slevel,noaa_name)

def main():
    args = parse_arguments()
    download_tides(**args)


if __name__ == "__main__":
    main()

