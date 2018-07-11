#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abstract base class for reading ungridded data. All classes based on this
"""

import abc
import numpy as np
import glob, os

from pyaerocom.io.helpers import get_obsnetwork_dir
from pyaerocom.utils import _BrowserDict


# TODO: implement dict-like class for output of read_file method, that avoids 
# creating pandas.Series instances in the first place but keeps the individual 
# data columns
class UngriddedFileData(_BrowserDict):
    """Dict-like class that can be used to store results from single file reads
    
    Note
    ----
    Not in use currently
    """
    def plot_variable(varname):
        raise NotImplementedError()
    

class ReadUngriddedBase(abc.ABC):
    """Abstract base class template for reading of ungridded data"""
    verbose = False
    
    @abc.abstractproperty
    def REVISION_FILE(self):
        """Location of data revision file
        
        Note
        ----
        1. May be implemented as global constant in header of derieved class
        
        """
        pass
    @abc.abstractproperty
    def DATASET_NAME(self):
        """Name of dataset (OBS_ID)
        
        Note
        ----
        1. May be implemented as global constant in header of derieved class
        2. May be multiple that can be specified on init (see example below)
        
        """
        pass
    
    @abc.abstractproperty
    def PROVIDES_VARIABLES(self):
        """List of variables that are provided by this dataset
        
        Note
        ----
        May be implemented as global constant in header
        """
        pass
    
    @abc.abstractproperty
    def _FILEMASK(self):
        """Mask for identifying datafiles (e.g. '*.txt')
        
        Note
        ----
        May be implemented as global constant in header
        """
        pass
    
    @abc.abstractproperty
    def __version__(self):
        """Version of reading class
        
        Keep track of changes in derived reading class (e.g. to assess whether 
        potential cache-files are outdated)
        
        Note
        ----
        May be implemented as global constant in header
        """
        pass
    
    
    @property
    def DATASET_PATH(self):
        return get_obsnetwork_dir(self.DATASET_NAME)
     
        
    @abc.abstractmethod
    def read_file(self, filename):
        """Method that reads a single data file and returns the result
        
        Parameters
        ----------
        filename : str
            string specifying filename
        
        Returns
        -------
        dict
            dictionary containing results 
        """
        pass
    
    @abc.abstractmethod
    def read(self, vars_to_read=None):
        """Method that reads a single data file and returns the result
        
        Parameters
        ----------
        filename : str
            string specifying filename
        
        """
        pass

    ### Concrete implementations of methods that are the same for all (or most)
    # of the derived reading classes
    def get_file_list(self):
        """Search all files to be read"""

        if self.verbose:
            print('searching for data files. This might take a while...')
        return glob.glob(os.path.join(self.DATASET_PATH, self._FILEMASK))

    ###################################################################################
    
    @property
    def data_revision(self):
        """Revision string from the file Revision.txt in the main data directory
        
        Returns
        -------
        
        """
        try:
            revision_file = os.path.join(self.DATASET_PATH, self.REVISION_FILE)
            if os.path.isfile(revision_file):
                with open(revision_file, 'rt') as in_file:
                    revision = in_file.readline().strip()
                    in_file.close()
    
                return revision
        except Exception as e:
            raise IOError("Failed to access revision info for dataset {}. "
                          "Error message: {}".format(self.DATASET_NAME,
                                          repr(e)))

class ReadAeronetSunV2:
    """Interface for reading Aeronet direct sun version 2 Level 2.0 data

    Attributes
    ----------
    data : numpy array of dtype np.float64 initially of shape (10000,8)
        data point array
    metadata : dict
        meta data dictionary

    Parameters
    ----------
    verbose : Bool
        if True some running information is printed

    """
    _FILEMASK = '*.lev20'
    __version__ = "0.07"
    DATASET_NAME = const.AERONET_SUN_V2L2_AOD_DAILY_NAME
    DATASET_PATH = const.OBSCONFIG[const.AERONET_SUN_V2L2_AOD_DAILY_NAME]['PATH']
    # Flag if the dataset contains all years or not
    DATASET_IS_YEARLY = False

    _METADATAKEYINDEX = 0
    _TIMEINDEX = 1
    _LATINDEX = 2
    _LONINDEX = 3
    _ALTITUDEINDEX = 4
    _VARINDEX = 5
    _DATAINDEX = 6

    _COLNO = 11
    _ROWNO = 10000
    _CHUNKSIZE = 1000
    PROVIDES_VARIABLES = ['od500aer', 'od440aer', 'od870aer', 'ang4487aer', 'od550aer']

    def __init__(self, index_pointer=0, verbose=False):
        self.verbose = verbose
        self.metadata = {}
        self.data = []
        self.index = len(self.metadata)
        self.files = []
        #set the revision to the one from Revision.txt if that file exist
        self.revision = self.get_data_revision()

        # pointer to 1st free row in self.data
        # can be externally set so that in case the super class wants to read more than one data set
        # no data modification is needed to bring several data sets together
        self.index_pointer = index_pointer

    def __iter__(self):
        return self

    def __next__(self):
        if self.index == 0:
            raise StopIteration
        self.index = self.index - 1
        return self.metadata[float(self.index)]

    def __str__(self):
        stat_names = []
        for key in self.metadata:
            stat_names.append(self.metadata[key]['station name'])

        return ','.join(stat_names)

    ###################################################################################

    def read_file(self, filename, vars_to_read=['od550aer'], verbose=False):
        """method to read an Aeronet Sun V2 level 2 file and return it in a dictionary
        with the data variables as pandas time series

        Parameters
        ----------
        filename : str
            absolute path to filename to read
        vars_to_read : list
            list of str with variable names to read; defaults to ['od550aer']
        verbose : Bool
            set to True to increase verbosity

        Example
        -------
        >>> import pyaerocom.io.read_aeronet_sunv2
        >>> obj = pyaerocom.io.read_aeronet_sunv2.ReadAeronetSunV2()
        >>> filedata = obj.read_file('/lustre/storeA/project/aerocom/aerocom1/AEROCOM_OBSDATA/AeronetRaw2.0/renamed/920801_170401_Zambezi.lev20')
        >>> print(filedata)
{'latitude': -13.533, 'longitude': 23.107, 'altitude': 1040.0, 'station name': 'Zambezi', 'PI': 'Brent Holben', 'od550aer': 1996-08-10    0.801845
1996-08-11    1.062833
1996-08-12    0.850586
1996-08-13    0.839460
                ...
2000-09-22    1.304724
2000-09-23    1.197722
2000-09-24    1.035123
Length: 223, dtype: float64}
        """

        # Level 2.0. Quality Assured Data.<p>The following data are pre and post field calibrated, automatically cloud cleared and manually inspected.
        # Version 2 Direct Sun Algorithm
        # Location=Zvenigorod,long=36.775,lat=55.695,elev=200,Nmeas=11,PI=Brent_Holben,Email=Brent.N.Holben@nasa.gov
        # AOD Level 2.0,Daily Averages,UNITS can be found at,,, http://aeronet.gsfc.nasa.gov/data_menu.html
        # Date(dd-mm-yy),Time(hh:mm:ss),Julian_Day,AOT_1640,AOT_1020,AOT_870,AOT_675,AOT_667,AOT_555,AOT_551,AOT_532,AOT_531,AOT_500,AOT_490,AOT_443,AOT_440,AOT_412,AOT_380,AOT_340,Water(cm),%TripletVar_1640,%TripletVar_1020,%TripletVar_870,%TripletVar_675,%TripletVar_667,%TripletVar_555,%TripletVar_551,%TripletVar_532,%TripletVar_531,%TripletVar_500,%TripletVar_490,%TripletVar_443,%TripletVar_440,%TripletVar_412,%TripletVar_380,%TripletVar_340,%WaterError,440-870Angstrom,380-500Angstrom,440-675Angstrom,500-870Angstrom,340-440Angstrom,440-675Angstrom(Polar),N[AOT_1640],N[AOT_1020],N[AOT_870],N[AOT_675],N[AOT_667],N[AOT_555],N[AOT_551],N[AOT_532],N[AOT_531],N[AOT_500],N[AOT_490],N[AOT_443],N[AOT_440],N[AOT_412],N[AOT_380],N[AOT_340],N[Water(cm)],N[440-870Angstrom],N[380-500Angstrom],N[440-675Angstrom],N[500-870Angstrom],N[340-440Angstrom],N[440-675Angstrom(Polar)]
        # 16:09:2006,00:00:00,259.000000,-9999.,0.036045,0.036734,0.039337,-9999.,-9999.,-9999.,-9999.,-9999.,0.064670,-9999.,-9999.,0.069614,-9999.,0.083549,0.092204,0.973909,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,-9999.,1.126095,0.973741,1.474242,1.135232,1.114550,-9999.,-9999.,11,11,11,-9999.,-9999.,-9999.,-9999.,-9999.,11,-9999.,-9999.,11,-9999.,11,11,11,11,11,11,11,11,-9999.

        # define some row numbers. not all of them are used at this point
        date_index = 0
        time_index = 1
        julien_day_index = 2
        od1640_index = 3
        od1020index = 4
        od870_index = 5
        od675index = 6
        od667index = 7
        od555index = 8
        od551index = 9
        od532index = 10
        od531index = 11
        od500_index = 12
        od440_index = 15
        od380index = 17
        od340index = 18

        # This value is later put to a np.nan
        nan_val = np.float_(-9999.)

        data_out = {}
        # Iterate over the lines of the file
        if verbose:
            sys.stderr.write(filename + '\n')
        with open(filename, 'rt') as in_file:
            c_head_line = in_file.readline()
            c_algorithm = in_file.readline()
            c_dummy = in_file.readline()
            # re.split(r'=|\,',c_dummy)
            i_dummy = iter(re.split(r'=|\,', c_dummy.rstrip()))
            dict_loc = dict(zip(i_dummy, i_dummy))

            data_out['latitude'] = float(dict_loc['lat'])
            data_out['longitude'] = float(dict_loc['long'])
            data_out['altitude'] = float(dict_loc['elev'])
            data_out['station name'] = dict_loc['Location']
            data_out['PI'] = dict_loc['PI']
            c_dummy = in_file.readline()
            c_Header = in_file.readline()

            #
            #DataArr = {}
            dtime = []
            for var in self.PROVIDES_VARIABLES:
                data_out[var] = []

            for line in in_file:
                # process line
                dummy_arr = line.split(',')
                # the following uses the standatd python datetime functions
                day, month, year = dummy_arr[date_index].split(':')
                hour, minute, second = dummy_arr[time_index].split(':')

                # This uses the numpy datestring64 functions that e.g. also support Months as a time step for timedelta
                # Build a proper ISO 8601 UTC date string
                day, month, year = dummy_arr[date_index].split(':')
                # pdb.set_trace()
                datestring = '-'.join([year, month, day])
                datestring = 'T'.join([datestring, dummy_arr[time_index]])
                datestring = '+'.join([datestring, '00:00'])
                dtime.append(np.datetime64(datestring))

                data_out['od500aer'].append(np.float_(dummy_arr[od500_index]))
                if data_out['od500aer'][-1] == nan_val: data_out['od500aer'][-1] = np.nan
                data_out['od440aer'].append(np.float_(dummy_arr[od440_index]))
                if data_out['od440aer'][-1] == nan_val: data_out['od440aer'][-1] = np.nan
                data_out['od870aer'].append(np.float_(dummy_arr[od870_index]))
                if data_out['od870aer'][-1] == nan_val: data_out['od870aer'][-1] = np.nan

                data_out['ang4487aer'].append(
                    -1.0 * np.log(data_out['od440aer'][-1] / data_out['od870aer'][-1]) / np.log(0.44 / .870))
                data_out['od550aer'].append(
                    data_out['od500aer'][-1] * (0.55 / 0.50) ** (np.float_(-1.) * data_out['ang4487aer'][-1]))
                # ;fill up time steps of the now calculated od550_aer that are nans with values calculated from the
                # ;440nm wavelength to minimise gaps in the time series
                if np.isnan(data_out['od550aer'][-1]):
                    temp = data_out['od440aer'][-1] * (0.55 / 0.44) ** (np.float_(-1.) * data_out['ang4487aer'][-1])
                    if not np.isnan(temp) and temp > 0.:
                        data_out['od550aer'][-1] = (data_out['od440aer'][-1] * (0.55 / 0.44) **
                                                    (np.float_(-1.) * data_out['ang4487aer'][-1]))
                if data_out['od550aer'][-1] < const.VAR_PARAM['od550aer']['lower_limit']:
                   data_out['od550aer'][-1] = np.nan

        # convert  the vars in vars_to_read to pandas time series
        # and delete the other ones
        for var in self.PROVIDES_VARIABLES:
            if var in vars_to_read:
                data_out[var] = pd.Series(data_out[var], index=dtime)
            else:
                del data_out[var]

        return data_out

    ###################################################################################

    def read(self, vars_to_read=['od550aer'], verbose=False):
        """method to read all files in self.files into self.data and self.metadata

        Example
        -------
        >>> import pyaerocom.io.read_aeronet_sunv2
        >>> obj = pyaerocom.io.read_aeronet_sunv2.ReadAeronetSunV2()
        >>> obj.read(verbose=True)
        """

        # Metadata key is float because the numpy array holding it is float

        met_data_key = 0.
        self.files = self.get_file_list()
        self.data = np.empty([self._ROWNO, self._COLNO], dtype=np.float64)

        for _file in sorted(self.files):
            if self.verbose:
                sys.stdout.write(_file+"\n")
            stat_obs_data = self.read_file(_file, vars_to_read = vars_to_read)
            # Fill the metatdata dict
            self.metadata[met_data_key] = {}
            self.metadata[met_data_key]['station name'] = stat_obs_data['station name']
            self.metadata[met_data_key]['latitude'] = stat_obs_data['latitude']
            self.metadata[met_data_key]['longitude'] = stat_obs_data['longitude']
            self.metadata[met_data_key]['altitude'] = stat_obs_data['altitude']
            self.metadata[met_data_key]['PI'] = stat_obs_data['PI']
            self.metadata[met_data_key]['dataset_name'] = self.DATASET_NAME

            # this is a list with indexes of this station for each variable
            # not sure yet, if we really need that or if it speeds up things
            self.metadata[met_data_key]['indexes'] = {}
            start_index = self.index_pointer
            # variable index
            obs_var_index = 0
            for var in sorted(vars_to_read):
                for time, val in stat_obs_data[var].iteritems():
                    self.data[self.index_pointer, self._DATAINDEX] = val
                    # pd.TimeStamp.value is nano seconds since the epoch!
                    self.data[self.index_pointer, self._TIMEINDEX] = np.float64(time.value / 1.E9)
                    self.index_pointer += 1
                    if self.index_pointer >= self._ROWNO:
                        # add another array chunk to self.data
                        self.data = np.append(self.data, np.zeros([self._CHUNKSIZE, self._COLNO], dtype=np.float64), axis=0)
                        self._ROWNO += self._CHUNKSIZE
    
                end_index = self.index_pointer
                # print(','.join([stat_obs_data['station name'], str(start_index), str(end_index), str(end_index - start_index)]))
                self.metadata[met_data_key]['indexes'][var] = np.arange(start_index, end_index)
                self.data[start_index:end_index, self._VARINDEX] = obs_var_index
                self.data[start_index:end_index, self._LATINDEX] = stat_obs_data['latitude']
                self.data[start_index:end_index, self._LONINDEX] = stat_obs_data['longitude']
                self.data[start_index:end_index, self._ALTITUDEINDEX] = stat_obs_data['altitude']
                self.data[start_index:end_index, self._METADATAKEYINDEX] = met_data_key
                start_index = self.index_pointer
                obs_var_index += 1
            met_data_key = met_data_key + 1.
    
        # shorten self.data to the right number of points
        self.data = self.data[0:end_index]


    ###################################################################################

    def get_file_list(self):
        """search for files to read """

        if self.verbose:
            print('searching for data files. This might take a while...')
        files = glob.glob(os.path.join(self.DATASET_PATH,
                                       self._FILEMASK))
        return files

    ###################################################################################

    def get_data_revision(self):
        """method to read the revision string from the file Revision.txt in the main data directory"""

        revision_file = os.path.join(self.DATASET_PATH, const.REVISION_FILE)
        revision = 'unset'
        if os.path.isfile(revision_file):
            with open(revision_file, 'rt') as in_file:
                revision = in_file.readline().strip()
                in_file.close()

            self.revision = revision
            
class ReadAeronetSunV3:
    """Interface for reading Aeronet direct sun version 3 Level 1.5 and 2.0 data

    Attributes
    ----------
    data : numpy array of dtype np.float64 initially of shape (10000,8)
        data point array
    metadata : dict
        meta data dictionary

    Parameters
    ----------
    verbose : Bool
        if True some running information is printed

    """
    _FILEMASK = '*.lev30'
    __version__ = "0.01"
    DATASET_NAME = const.AERONET_SUN_V3L15_AOD_DAILY_NAME
    DATASET_PATH = const.OBSCONFIG[const.AERONET_SUN_V3L15_AOD_DAILY_NAME]['PATH']
    # Flag if the dataset contains all years or not
    DATASET_IS_YEARLY = False

    _METADATAKEYINDEX = 0
    _TIMEINDEX = 1
    _LATINDEX = 2
    _LONINDEX = 3
    _ALTITUDEINDEX = 4
    _VARINDEX = 5
    _DATAINDEX = 6

    _COLNO = 11
    _ROWNO = 10000
    _CHUNKSIZE = 1000

    # data vars
    # will be stored as pandas time series
    DATA_COLNAMES = {}
    DATA_COLNAMES['od340aer'] = 'AOD_340nm'
    DATA_COLNAMES['od440aer'] = 'AOD_440nm'
    DATA_COLNAMES['od500aer'] = 'AOD_500nm'
    # DATA_COLNAMES['od865aer'] = 'AOD_865nm'
    DATA_COLNAMES['od870aer'] = 'AOD_870nm'
    DATA_COLNAMES['ang4487aer'] = '440-870_Angstrom_Exponent'

    # meta data vars
    # will be stored as array of strings
    METADATA_COLNAMES = {}
    METADATA_COLNAMES['data_quality_level'] = 'Data_Quality_Level'
    METADATA_COLNAMES['instrument_number'] = 'AERONET_Instrument_Number'
    METADATA_COLNAMES['station name'] = 'AERONET_Site'
    METADATA_COLNAMES['latitude'] = 'Site_Latitude(Degrees)'
    METADATA_COLNAMES['longitude'] = 'Site_Longitude(Degrees)'
    METADATA_COLNAMES['altitude'] = 'Site_Elevation(m)'
    METADATA_COLNAMES['date'] = 'Date(dd:mm:yyyy)'
    METADATA_COLNAMES['time'] = 'Time(hh:mm:ss)'
    METADATA_COLNAMES['day_of_year'] = 'Day_of_Year'

    # additional vars
    # calculated
    AUX_COLNAMES = []
    AUX_COLNAMES.append('ang4487aer_calc')
    AUX_COLNAMES.append('od550aer')

    PROVIDES_VARIABLES = list(DATA_COLNAMES.keys())
    for col in AUX_COLNAMES:
        PROVIDES_VARIABLES.append(col)

    # COLNAMES_USED = {y:x for x,y in AUX_COLNAMES.items()}

    def __init__(self, index_pointer=0, dataset_to_read=None, verbose=False):
        self.verbose = verbose
        self.metadata = {}
        self.data = []
        self.index = len(self.metadata)
        self.files = []
        # the reading actually works for all V3 direct sun data sets
        # so just adjust the name and the path here
        # const.AERONET_SUN_V3L15_AOD_DAILY_NAME is the default
        if dataset_to_read is None:
            pass
            # self.dataset_name = const.AERONET_SUN_V3L15_AOD_DAILY_NAME
            # self.dataset_path = const.OBSCONFIG[const.AERONET_SUN_V3L15_AOD_DAILY_NAME]['PATH']
        elif dataset_to_read == const.AERONET_SUN_V3L15_AOD_ALL_POINTS_NAME:
            self.DATASET_NAME = const.AERONET_SUN_V3L15_AOD_ALL_POINTS_NAME
            self.DATASET_PATH = const.OBSCONFIG[const.AERONET_SUN_V3L15_AOD_ALL_POINTS_NAME]['PATH']
        elif dataset_to_read == const.AERONET_SUN_V3L2_AOD_DAILY_NAME:
            self.DATASET_NAME = const.AERONET_SUN_V3L2_AOD_DAILY_NAME
            self.DATASET_PATH = const.OBSCONFIG[const.AERONET_SUN_V3L2_AOD_DAILY_NAME]['PATH']
        elif dataset_to_read == const.AERONET_SUN_V3L2_AOD_ALL_POINTS_NAME:
            self.DATASET_NAME = const.AERONET_SUN_V3L2_AOD_ALL_POINTS_NAME
            self.DATASET_PATH = const.OBSCONFIG[const.AERONET_SUN_V3L2_AOD_ALL_POINTS_NAME]['PATH']


        # set the revision to the one from Revision.txt if that file exist
        self.revision = self.get_data_revision()

        # pointer to 1st free row in self.data
        # can be externally set so that in case the super class wants to read more than one data set
        # no data modification is needed to bring several data sets together
        self.index_pointer = index_pointer

    def __iter__(self):
        return self

    def __next__(self):
        if self.index == 0:
            raise StopIteration
        self.index = self.index - 1
        return self.metadata[float(self.index)]

    def __str__(self):
        stat_names = []
        for key in self.metadata:
            stat_names.append(self.metadata[key]['station name'])

        return ','.join(stat_names)

    ###################################################################################

    def read_file(self, filename, vars_to_read=['od550aer'], verbose=False):
        """method to read an Aeronet Sun V3 level 1.5 file and return it in a dictionary
        with the data variables as pandas time series

        Parameters
        ----------
        filename : str
            absolute path to filename to read
        vars_to_read : list
            list of str with variable names to read; defaults to ['od550aer']
        verbose : Bool
            set to True to increase verbosity

        Example
        -------
        >>> import pyaerocom.io.read_aeronet_sunv3
        >>> obj = pyaerocom.io.read_aeronet_sunv3.ReadAeronetSunV3()
        >>> filename = '/lustre/storeA/project/aerocom/aerocom1/AEROCOM_OBSDATA/AeronetSunV3Lev1.5.daily/renamed/Karlsruhe.lev30'
        >>> filename = '/lustre/storeA/project/aerocom/aerocom1/AEROCOM_OBSDATA/AeronetSunV3Lev1.5.AP/renamed/Karlsruhe.lev30'
        >>> filedata = obj.read_file(filename)
        >>> print(filedata)
{'PI': 'Brent_Holben', 'PI_email': 'Brent.N.Holben@nasa.gov\n', 'od550aer': 2005-03-21 12:00:00    0.238024
2005-03-23 12:00:00    0.268991
2005-03-24 12:00:00    0.641364
                         ...
2018-04-28 12:00:00         NaN
2018-04-29 12:00:00    0.161189
2018-04-30 12:00:00    0.058717
2018-05-01 12:00:00    0.083875
2018-05-03 12:00:00    0.326524
2018-05-04 12:00:00    0.277096
2018-05-05 12:00:00    0.272977
2018-05-06 12:00:00    0.083989
2018-05-07 12:00:00    0.084507
2018-05-08 12:00:00    0.078192
2018-05-09 12:00:00    0.172097
2018-05-11 12:00:00    0.326830
2018-05-12 12:00:00    0.311610
Length: 1424, dtype: float64, 'data_quality_level': ['lev15', 'l...
        """

        # DAILY DATA:
        # ===========
        # AERONET Version 3;
        # Cuiaba
        # Version 3: AOD Level 1.5
        # The following data are cloud cleared and quality controls have been applied but these data may not have final calibration applied.  These data may change.
        # Contact: PI=Brent_Holben; PI Email=Brent.N.Holben@nasa.gov
        # Daily Averages,UNITS can be found at,,, https://aeronet.gsfc.nasa.gov/new_web/units.html
        # AERONET_Site,Date(dd:mm:yyyy),Time(hh:mm:ss),Day_of_Year,AOD_1640nm,AOD_1020nm,AOD_870nm,AOD_865nm,AOD_779nm,AOD_675nm,AOD_667nm,AOD_620nm,AOD_560nm,AOD_555nm,AOD_551nm,AOD_532nm,AOD_531nm,AOD_510nm,AOD_500nm,AOD_490nm,AOD_443nm,AOD_440nm,AOD_412nm,AOD_400nm,AOD_380nm,AOD_340nm,Precipitable_Water(cm),AOD_681nm,AOD_709nm,AOD_Empty,AOD_Empty,AOD_Empty,AOD_Empty,AOD_Empty,440-870_Angstrom_Exponent,380-500_Angstrom_Exponent,440-675_Angstrom_Exponent,500-870_Angstrom_Exponent,340-440_Angstrom_Exponent,440-675_Angstrom_Exponent[Polar],N[AOD_1640nm],N[AOD_1020nm],N[AOD_870nm],N[AOD_865nm],N[AOD_779nm],N[AOD_675nm],N[AOD_667nm],N[AOD_620nm],N[AOD_560nm],N[AOD_555nm],N[AOD_551nm],N[AOD_532nm],N[AOD_531nm],N[AOD_510nm],N[AOD_500nm],N[AOD_490nm],N[AOD_443nm],N[AOD_440nm],N[AOD_412nm],N[AOD_400nm],N[AOD_380nm],N[AOD_340nm],N[Precipitable_Water(cm)],N[AOD_681nm],N[AOD_709nm],N[AOD_Empty],N[AOD_Empty],N[AOD_Empty],N[AOD_Empty],N[AOD_Empty],N[440-870_Angstrom_Exponent],N[380-500_Angstrom_Exponent],N[440-675_Angstrom_Exponent],N[500-870_Angstrom_Exponent],N[340-440_Angstrom_Exponent],N[440-675_Angstrom_Exponent[Polar]],
        # Data_Quality_Level,AERONET_Instrument_Number,AERONET_Site_Name,Site_Latitude(Degrees),Site_Longitude(Degrees),Site_Elevation(m)
        # Karlsruhe,21:03:2005,12:00:00,80,-999.,0.222846,0.222462,-999.,-999.,0.224444,-999.,-999.,-999.,-999.,-999.,-999.,-999.,-999.,0.242872,-999.,-999.,0.256999,-999.,-999.,0.276636,0.283760,0.733243,-999.,-999.,-999.,-999.,-999.,-999.,-999.,0.211561,0.473610,0.306976,0.161805,0.391631,-999.,0,2,2,0,0,2,0,0,0,0,0,0,0,0,2,0,0,2,0,0,2,2,2,0,0,0,0,0,0,0,2,2,2,2,2,0,lev15,325,Karlsruhe,49.093300,8.427900,140.000000

        # ALL POINT DATA
        # ==============
        # AERONET Version 3;
        # Cuiaba
        # Version 3: AOD Level 1.5
        # The following data are cloud cleared and quality controls have been applied but these data may not have final calibration applied.  These data may change.
        # Contact: PI=Brent_Holben; PI Email=Brent.N.Holben@nasa.gov
        # All Points,UNITS can be found at,,, https://aeronet.gsfc.nasa.gov/new_web/units.html
        # AERONET_Site,Date(dd:mm:yyyy),Time(hh:mm:ss),Day_of_Year,Day_of_Year(Fraction),AOD_1640nm,AOD_1020nm,AOD_870nm,AOD_865nm,AOD_779nm,AOD_675nm,AOD_667nm,AOD_620nm,AOD_560nm,AOD_555nm,AOD_551nm,AOD_532nm,AOD_531nm,AOD_510nm,AOD_500nm,AOD_490nm,AOD_443nm,AOD_440nm,AOD_412nm,AOD_400nm,AOD_380nm,AOD_340nm,Precipitable_Water(cm),AOD_681nm,AOD_709nm,AOD_Empty,AOD_Empty,AOD_Empty,AOD_Empty,AOD_Empty,Triplet_Variability_1640,Triplet_Variability_1020,Triplet_Variability_870,Triplet_Variability_865,Triplet_Variability_779,Triplet_Variability_675,Triplet_Variability_667,Triplet_Variability_620,Triplet_Variability_560,Triplet_Variability_555,Triplet_Variability_551,Triplet_Variability_532,Triplet_Variability_531,Triplet_Variability_510,Triplet_Variability_500,Triplet_Variability_490,Triplet_Variability_443,Triplet_Variability_440,Triplet_Variability_412,Triplet_Variability_400,Triplet_Variability_380,Triplet_Variability_340,Triplet_Variability_Precipitable_Water(cm),Triplet_Variability_681,Triplet_Variability_709,Triplet_Variability_AOD_Empty,Triplet_Variability_AOD_Empty,Triplet_Variability_AOD_Empty,Triplet_Variability_AOD_Empty,Triplet_Variability_AOD_Empty,440-870_Angstrom_Exponent,380-500_Angstrom_Exponent,440-675_Angstrom_Exponent,500-870_Angstrom_Exponent,340-440_Angstrom_Exponent,440-675_Angstrom_Exponent[Polar],Data_Quality_Level,AERONET_Instrument_Number,AERONET_Site_Name,Site_Latitude(Degrees),Site_Longitude(Degrees),Site_Elevation(m),Solar_Zenith_Angle(Degrees),Optical_Air_Mass,Sensor_Temperature(Degrees_C),Ozone(Dobson),NO2(Dobson),Last_Date_Processed,Number_of_Wavelengths,Exact_Wavelengths_of_AOD(um)_1640nm,Exact_Wavelengths_of_AOD(um)_1020nm,Exact_Wavelengths_of_AOD(um)_870nm,Exact_Wavelengths_of_AOD(um)_865nm,Exact_Wavelengths_of_AOD(um)_779nm,Exact_Wavelengths_of_AOD(um)_675nm,Exact_Wavelengths_of_AOD(um)_667nm,Exact_Wavelengths_of_AOD(um)_620nm,Exact_Wavelengths_of_AOD(um)_560nm,Exact_Wavelengths_of_AOD(um)_555nm,Exact_Wavelengths_of_AOD(um)_551nm,Exact_Wavelengths_of_AOD(um)_532nm,Exact_Wavelengths_of_AOD(um)_531nm,Exact_Wavelengths_of_AOD(um)_510nm,Exact_Wavelengths_of_AOD(um)_500nm,Exact_Wavelengths_of_AOD(um)_490nm,Exact_Wavelengths_of_AOD(um)_443nm,Exact_Wavelengths_of_AOD(um)_440nm,Exact_Wavelengths_of_AOD(um)_412nm,Exact_Wavelengths_of_AOD(um)_400nm,Exact_Wavelengths_of_AOD(um)_380nm,Exact_Wavelengths_of_AOD(um)_340nm,Exact_Wavelengths_of_PW(um)_935nm,Exact_Wavelengths_of_AOD(um)_681nm,Exact_Wavelengths_of_AOD(um)_709nm,Exact_Wavelengths_of_AOD(um)_Empty,Exact_Wavelengths_of_AOD(um)_Empty,Exact_Wavelengths_of_AOD(um)_Empty,Exact_Wavelengths_of_AOD(um)_Empty,Exact_Wavelengths_of_AOD(um)_Empty
        # Karlsruhe,21:03:2005,16:35:13,80,80.691123,-999.000000,0.217930,0.217887,-999.000000,-999.000000,0.220243,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,0.238660,-999.000000,-999.000000,0.252361,-999.000000,-999.000000,0.271864,0.278779,0.733072,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,0.009736,0.009758,-999.000000,-999.000000,0.008882,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,0.008965,-999.000000,-999.000000,0.007377,-999.000000,-999.000000,0.007786,0.005861,0.040874,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,-999.000000,0.215628,0.474049,0.309065,0.167603,0.393740,-999.000000,lev15,325,Karlsruhe,49.093300,8.427900,140.000000,80.094832,5.635644,19.000000,0.368148,0.434568,07:12:2017,8,-999.,1.019300,0.870200,-999.,-999.,0.674800,-999.,-999.,-999.,-999.,-999.,-999.,-999.,-999.,0.500400,-999.,-999.,0.439600,-999.,-999.,0.380000,0.340000,0.941100,-999.,-999.,-999.,-999.,-999.,-999.,-999.


        # This value is later put to a np.nan
        nan_val = np.float_(-9999.)
        
        data_out = {}
        dict_loc={}
        # Iterate over the lines of the file
        if verbose:
            sys.stderr.write(filename + '\n')
        with open(filename, 'rt') as in_file:
            line_1 = in_file.readline()
            line_2 = in_file.readline()
            line_3 = in_file.readline()
            line_4 = in_file.readline()
            # PI line
            dummy_arr = in_file.readline().strip().split(';')
            data_out['PI'] = dummy_arr[0].split('=')[1]
            data_out['PI_email'] = dummy_arr[1].split('=')[1]

            data_type_comment = in_file.readline()
            # line_7 = in_file.readline()
            # put together a dict with the header string as key and the index number as value so that we can access
            # the index number via the header string
            headers = in_file.readline().strip().split(',')
            index_str = {}
            _index = 0
            for header in headers:
                index_str[header] = _index
                _index += 1

            data_line_no = 1
            dtime = []
            for var in self.PROVIDES_VARIABLES:
                data_out[var] = []
            # add time variable location
            for var in self.METADATA_COLNAMES:
                data_out[var] = []

            for line in in_file:
                # process line
                dummy_arr = line.split(',')
                # the following uses the standard python datetime functions
                # date_index = index_str[COLNAMES['date']]
                # hour, minute, second = dummy_arr[index_str[COLNAMES['time']].split(':')

                # This uses the numpy datestring64 functions that e.g. also support Months as a time step for timedelta
                # Build a proper ISO 8601 UTC date string
                day, month, year = dummy_arr[index_str[self.METADATA_COLNAMES['date']]].split(':')
                datestring = '-'.join([year, month, day])
                datestring = 'T'.join([datestring, dummy_arr[index_str[self.METADATA_COLNAMES['time']]]])
                datestring = '+'.join([datestring, '00:00'])
                dtime.append(np.datetime64(datestring))

                # copy the meta data (array of type string)
                for var in self.METADATA_COLNAMES:
                    if len(self.METADATA_COLNAMES[var]) == 0: continue
                    data_out[var].append(dummy_arr[index_str[self.METADATA_COLNAMES[var]]])

                # copy the data fields (array type np.float_; will be converted to pandas.Series later)
                for var in self.DATA_COLNAMES:
                    data_out[var].append(np.float_(dummy_arr[index_str[self.DATA_COLNAMES[var]]]))
                    if data_out[var][-1] == nan_val: data_out[var][-1] = np.nan

                # some stuff needs to be calculated
                data_out['ang4487aer_calc'].append(
                    -1.0 * np.log(data_out['od440aer'][-1] / data_out['od870aer'][-1]) / np.log(0.44 / .870))
                data_out['od550aer'].append(
                    data_out['od500aer'][-1] * (0.55 / 0.50) ** (np.float_(-1.) * data_out['ang4487aer'][-1]))
                # fill up time steps of the now calculated od550aer that are nans with values calculated from the
                # 440nm wavelength to minimise gaps in the time series
                if np.isnan(data_out['od550aer'][-1]):
                    temp = data_out['od440aer'][-1] * (0.55 / 0.44) ** (np.float_(-1.) * data_out['ang4487aer'][-1])
                    if not np.isnan(temp) and temp > 0.:
                        data_out['od550aer'][-1] = (data_out['od440aer'][-1] * (0.55 / 0.44) **
                                                    (np.float_(-1.) * data_out['ang4487aer'][-1]))
                # apply the lower limit for od550aer
                if data_out['od550aer'][-1] < const.VAR_PARAM['od550aer']['lower_limit']:
                    data_out['od550aer'][-1] = np.nan
                data_line_no += 1

        # convert the vars in vars_to_read to pandas time series
        # and delete the other ones
        for var in self.PROVIDES_VARIABLES:
            if var in vars_to_read:
                data_out[var] = pd.Series(data_out[var], index=dtime)
            else:
                del data_out[var]

        return data_out

    ###################################################################################

    def read(self, vars_to_read=['od550aer'], verbose=False):
        """method to read all files in self.files into self.data and self.metadata

        Example
        -------
        >>> import pyaerocom.io.read_aeronet_sunv3
        >>> obj = pyaerocom.io.read_aeronet_sunv3.ReadAeronetSunV3()
        >>> obj.read(verbose=True)
        """

        # Metadata key is float because the numpy array holding it is float

        met_data_key = 0.
        self.files = self.get_file_list()
        self.data = np.empty([self._ROWNO, self._COLNO], dtype=np.float_)

        for _file in sorted(self.files):
            if self.verbose:
                sys.stdout.write(_file + "\n")
            stat_obs_data = self.read_file(_file, vars_to_read=vars_to_read)
            # Fill the metatdata dict
            # the location in the data set is time step dependant!
            # use the lat location here since we have to choose one location
            # in the time series plot
            self.metadata[met_data_key] = {}
            self.metadata[met_data_key]['station name'] = stat_obs_data['station name'][-1]
            self.metadata[met_data_key]['latitude'] = stat_obs_data['latitude'][-1]
            self.metadata[met_data_key]['longitude'] = stat_obs_data['longitude'][-1]
            self.metadata[met_data_key]['altitude'] = stat_obs_data['altitude'][-1]
            self.metadata[met_data_key]['PI'] = stat_obs_data['PI']
            self.metadata[met_data_key]['dataset_name'] = self.DATASET_NAME

            # this is a list with indexes of this station for each variable
            # not sure yet, if we really need that or if it speeds up things
            self.metadata[met_data_key]['indexes'] = {}
            start_index = self.index_pointer
            # variable index
            obs_var_index = 0
            for var in sorted(vars_to_read):
                for time, val in stat_obs_data[var].iteritems():
                    self.data[self.index_pointer, self._DATAINDEX] = val
                    # pd.TimeStamp.value is nano seconds since the epoch!
                    self.data[self.index_pointer, self._TIMEINDEX] = np.float64(time.value / 1.E9)
                    self.index_pointer += 1
                    if self.index_pointer >= self._ROWNO:
                        # add another array chunk to self.data
                        self.data = np.append(self.data, np.zeros([self._CHUNKSIZE, self._COLNO], dtype=np.float64),
                                              axis=0)
                        self._ROWNO += self._CHUNKSIZE

                # end_index = self.index_pointer - 1
                # This is right because numpy leaves out the lat index number at array ops
                end_index = self.index_pointer
                # print(','.join([stat_obs_data['station name'], str(start_index), str(end_index), str(end_index - start_index)]))
                # NOTE THAT THE LOCATION KEPT THE TIME STEP DEPENDENCY HERE
                self.metadata[met_data_key]['indexes'][var] = np.arange(start_index, end_index)
                self.data[start_index:end_index, self._VARINDEX] = obs_var_index
                self.data[start_index:end_index, self._LATINDEX] = stat_obs_data['latitude']
                self.data[start_index:end_index, self._LONINDEX] = stat_obs_data['longitude']
                self.data[start_index:end_index, self._ALTITUDEINDEX] = stat_obs_data['altitude']
                self.data[start_index:end_index, self._METADATAKEYINDEX] = met_data_key
                start_index = self.index_pointer
                obs_var_index += 1
            met_data_key = met_data_key + 1.

        # shorten self.data to the right number of points
        self.data = self.data[0:end_index]

    ###################################################################################

    def get_file_list(self):
        """search for files to read """

        if self.verbose:
            print('searching for data files. This might take a while...')
        files = glob.glob(os.path.join(self.DATASET_PATH,
                                       self._FILEMASK))
        return files

    ###################################################################################

    def get_data_revision(self):
        """method to read the revision string from the file Revision.txt in the main data directory"""

        revision_file = os.path.join(self.DATASET_PATH, const.REVISION_FILE)
        revision = 'unset'
        if os.path.isfile(revision_file):
            with open(revision_file, 'rt') as in_file:
                revision = in_file.readline().strip()
                in_file.close()

            self.revision = revision
###################################################################################
            
if __name__=="__main__":
    
    from pyaerocom import const
    class ReadUngriddedImplementationExample(ReadUngriddedBase):
        _FILEMASK = ".txt"
        DATASET_NAME = "Blaaa"
        __version__ = "0.01"
        PROVIDES_VARIABLES = ["od550aer"]
        REVISION_FILE = const.REVISION_FILE
        
        def __init__(self, dataset_to_read=None):
            if dataset_to_read is not None:
                self.DATASET_NAME = dataset_to_read
        
        def read(self):
            raise NotImplementedError
            
        def read_file(self):
            raise NotImplementedError
            
    c = ReadUngriddedImplementationExample(dataset_to_read='AeronetSunV2Lev1.5.daily')
    print(c.DATASET_PATH)