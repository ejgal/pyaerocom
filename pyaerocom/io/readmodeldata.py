#!/usr/bin/env python3

################################################################
# readmodeldata.py
#
# model data reading class
#
# this file is part of the aerocom_pt package
#
#################################################################
# Created 20171030 by Jan Griesfeller for Met Norway
#
# Last changed: See git log
#################################################################

#Copyright (C) 2017 met.no
#Contact information:
#Norwegian Meteorological Institute
#Box 43 Blindern
#0313 OSLO
#NORWAY
#E-mail: jan.griesfeller@met.no
#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 3 of the License, or
#(at your option) any later version.
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#GNU General Public License for more details.
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#MA 02110-1301, USA
import sys
from glob import glob
from re import match
from os.path import join, isdir, basename, dirname
from collections import OrderedDict as od
from warnings import warn
from numpy import arange
from pandas import Timestamp

from iris import Constraint, load_cube
from iris.cube import CubeList
from iris.experimental.equalise_cubes import equalise_attributes
from iris.util import unify_time_units

import pyaerocom.config as const
from pyaerocom.glob import FIRST_DATE, LAST_DATE, TS_TYPES, VERBOSE
from pyaerocom.exceptions import IllegalArgumentError
from pyaerocom.io.fileconventions import FileConventionRead
from pyaerocom.modeldata import ModelData

class ReadModelData:
    """Class that stores read import results for model data
    
    Attributes
    ----------
    model_id : str
        string ID for model (see Aerocom interface map plots lower left corner)
    data : ModelData
        imported data object 
    model_dir : str
        directory containing result files for this model
    start_time : pandas.Timestamp
        start time for data import
    stop_time : pandas.Timestamp
        stop time for data import
    file_convention : FileConventionRead
        class specifying details of the file naming convention for the model
    files : list
        list containing all filenames that were found.
        Filled, e.g. in :func:`ReadModelData.get_model_files`
    from_files : list
        List of all netCDF files that were used to concatenate the current 
        data cube (i.e. that can be based on certain matching settings such as
        var_name or time interval). 
    vars : list
        list containing all variable names that were found
        
    Parameters
    ----------
    model_id : str
        string ID of model (e.g. "AATSR_SU_v4.3","CAM5.3-Oslo_CTRL2016")
    start_time : :obj:`pandas.Timestamp` or :obj:`str`, optional
        desired start time of dataset (note, that strings are passed to 
        :class:`pandas.Timestamp` without further checking)
    stop_time : :obj:`pandas.Timestamp` or :obj:`str`, optional
        desired stop time of dataset (note, that strings are passed to 
        :class:`pandas.Timestamp` without further checking)
    file_convention : str
        string ID specifying the file convention of this model (cf. 
        installation file `file_conventions.ini <https://github.com/metno/
        pyaerocom/blob/master/pyaerocom/data/file_conventions.ini>`__)
    init : bool
        if True, the model directory is searched (:func:`search_model_dir`) on
        instantiation and if it is found, all valid files for this model are 
        searched using :func:`search_all_files`.
    verbose : bool
        if True, output is printed
        
    Examples
    --------
    
    """
    _MODELDIRS = const.MODELDIRS
    _start_time = FIRST_DATE
    _stop_time = LAST_DATE
    # Directory containing model data for this species
    _model_dir = ""
    _USE_SUBDIR_RENAMED = True
    def __init__(self, model_id="", start_time=None, stop_time=None, 
                 file_convention="aerocom3", init=True, verbose=VERBOSE):
        # model ID
        if not isinstance(model_id, str):
            if isinstance(model_id, list):
                msg = ("Input for model_id is list. You might want to use "
                       "class ReadMultiModelData for import?")
            else:
                msg = ("Invalid input for model_id. Need str, got: %s"
                       %type(model_id))
            raise TypeError(msg)
                
        self.model_id = model_id
        
        # only overwrite if there is input, note that the attributes
        # start_time and stop_time are defined below as @property getter and
        # setter methods, that ensure that the input is convertible to 
        # pandas.Timestamp
        if start_time is not None:
            self.start_time = start_time
        if stop_time is not None:
            self.stop_time = stop_time
        
        self.verbose = verbose
        
        # Dictionary containing loaded results for different variables
        self.data = od()
        
        # file naming convention. Default is aerocom3 file convention, change 
        # using self.file_convention.import_default("aerocom2"). Is 
        # automatically updated in class ReadModelData
        self.file_convention = FileConventionRead(file_convention)
        
        # All files that were found for this model (updated, e.g. in class
        # ReadModelData, method: `get_model_files`
        self.files = []
        
        self.vars = []
        
        if init:
            if self.search_model_dir():
                self.search_all_files()
      
    @property
    def model_dir(self):
        """Model directory"""
        dirloc = self._model_dir
        if self._USE_SUBDIR_RENAMED:
            dirloc = join(dirloc, "renamed")
        if not isdir(dirloc):
            raise IOError("Model directory for ID %s not available or does "
                          "not exist" %self.model_id)
        return dirloc
    
    @model_dir.setter
    def model_dir(self, value):
        if isinstance(value, str) and isdir(value):
            self._model_dir = value
        else:
            raise ValueError("Could not set directory: %s" %value)
        
    
    @property
    def start_time(self):
        """Start time of the dataset
        
        Note      
        ----
        If input is not :class:`pandas.Timestamp`, it must be convertible 
        into :class:`pandas.Timestamp` (e.g. "2012-1-1")
        """
        t = self._start_time
        if not isinstance(t, Timestamp):
            raise ValueError("Invalid value encountered for start time "
                             "in reading engine: %s" %t)
        return t
    
    @start_time.setter
    def start_time(self, value):
        if not isinstance(value, Timestamp):    
            try:
                value = Timestamp(value)
            except:
                raise ValueError("Failed to convert input value to pandas "
                                  "Timestamp: %s" %value)
        self._start_time = value
            
    @property
    def stop_time(self):
        """Stop time of the dataset
        
        Note      
        ----
        If input is not :class:`pandas.Timestamp`, it must be convertible 
        into :class:`pandas.Timestamp` (e.g. "2012-1-1")
        
        """
        t = self._stop_time
        if not isinstance(t, Timestamp):
            raise ValueError("Invalid value encountered for stop time "
                             "in reading engine: %s" %t)
        return t
    
    @stop_time.setter
    def stop_time(self, value):
        if not isinstance(value, Timestamp):  
            try:
                value = Timestamp(value)
            except:
                raise ValueError("Failed to convert input value to pandas "
                                  "Timestamp: %s" %value)
        self._stop_time = value
    
    @property
    def years_to_load(self):
        """Array containing year numbers that are supposed to be loaded
        
        Returns
        -------
        ndarray
        """
        return arange(self.start_time.year, self.stop_time.year + 1, 1)
    
    def search_model_dir(self):
        """Search the directory of this model
        
        Returns
        -------
        bool
            True, if directory was found, else False
        """
        for search_dir in self._MODELDIRS:
            if self.verbose:
                print('Searching dir for ID %s in: %s' 
                      %(self.model_id, search_dir))
            # get the directories
            if isdir(search_dir):
                chk_dir = glob(search_dir + self.model_id)
                if len(chk_dir) > 0:
                    self.model_dir = chk_dir[0]
                    if self.verbose:
                        sys.stderr.write('Found: '+ chk_dir[0] + '\n')
                    return True
            else:
                if self.verbose:
                    sys.stderr.write('directory: %s does not exist\n'
                                     %search_dir)
        return False
    
    # get the model directory (note that the folder "renamed" is used)
    def search_all_files(self, update_file_convention=True):
        """Search all valid model files for this model
        
        
        This method 
        
        Parameters
        ----------
        update_file_convention : bool
            if True, the first file in `model_dir` is used to identify the 
            file naming convention (cf. :class:`FileConventionRead`)
            
        Note
        ----
        This function does not seperate by variable or time, it gets you all
        valid files for all variables and times for this model.
        """
        # get all netcdf files in folder
        nc_files = glob(self.model_dir + '/*.nc')
        if update_file_convention:
            # Check if the found file has a naming according the aerocom conventions
            # and set the convention for all files (maybe this need to be 
            # updated in case there can be more than one file naming convention
            # within one model directory)
            first_file_name = basename(nc_files[0])
            if first_file_name.count("_") >= 4:
                self.file_convention.import_default("aerocom3")
            elif first_file_name.count(".") >= 4:
                self.file_convention.import_default("aerocom2")
        else:
            raise TypeError("Failed to identify file naming convention "
                            "from first file in model directory for model "
                            "%s\nmodel_dir: %s\nFile name: %s"
                            %(self.model_id, self.model_dir, first_file_name))
        _vars_temp = []
        for _file in nc_files:
            # split file based on delimiter specified in file naming 
            # convention
            spl = _file.split(self.file_convention.file_sep)
            # aerocom3 convention
            if basename(_file).count('_') >= 4:
                data_types = ['surface', 'column', 'modellevel']
                # phase 3 file naming convention
                
                # include vars for the surface
                if spl[-3].lower() in data_types:
                    _vars_temp.append(spl[self.file_convention.var_pos])
                    self.files.append(_file)
                # also include 3d vars that provide station based data
                # and contain the string vmr
                # in this case the variable name has to slightly changed to the 
                # aerocom phase 2 naming
                elif spl[-3].lower() == 'modellevelatstations':
                    if 'vmr' in spl[-4]:
                        _vars_temp.append(spl[-4].replace('vmr', 'vmr3d'))
                        self.files.append(_file)
            # aerocom2 convention
            elif basename(_file).count('.') >= 4:
                # phase 2
                _vars_temp.append(spl[self.file_convention.var_pos])
                self.files.append(_file)

            # unknown file convention
            else:
                warn("Ignoring file: %s" %_file)

        # make sorted list of unique vars
        self.vars = sorted(od.fromkeys(_vars_temp))
        
    def update(self, **kwargs):
        """Update one or more valid parameters
        
        Parameters
        ----------
        **kwargs
            keyword args that will be used to update (overwrite) valid class 
            attributes such as `data, model_dir, files`
        """
        for k, v in kwargs.items():
            if k in self.__dict__:
                print("Updating %s in ModelImportResult for model %s"
                      "New value: %s" %(k, self.model_id, v))
                self.__dict__[k] = v
            else:
                print("Ignoring key %s in ModelImportResult.update()"  %k)
                
    def read_var(self, var_name, start_time=None, stop_time=None, 
                 ts_type='daily'):
        """Read model data for a specific variable
        
        Parameters
        ----------
        var_name : str
            variable name that is supposed to be plotted (e.g. )
            Must be in :attr:`vars`
        start_time : :obj:`Timestamp` or :obj:`str`, optional
            start time of data import (if valid input, then the current 
            :attr:`start_time` will be overwritten)
        stop_time : :obj:`Timestamp` or :obj:`str`, optional
            stop time of data import (if valid input, then the current 
            :attr:`start_time` will be overwritten)
        ts_type : str
            string specifying temporal resolution (choose from 
            "hourly", "3hourly", "daily", "monthly")
        """
        if not ts_type in TS_TYPES:
            raise ValueError("Invalid input for ts_type, got: %s, "
                             "allowed values: %s" %(ts_type, TS_TYPES))
        if start_time is not None:
            self.start_time = start_time
        if stop_time is not None:
            self.stop_time = stop_time
        
        if var_name not in self.vars:
            raise ValueError("Error: variable %s not found in files contained "
                             "in model directory: %s" 
                             %(var_name, self.model_dir))
        
        match_files = []
        for year in self.years_to_load:
            # search for filename in self.files using ts_type as default ts size
            for _file in self.files:
                #new file naming convention (aerocom3)
                match_mask = self.file_convention.string_mask(var_name,
                                                                year, 
                                                                ts_type)
                if match(match_mask, _file):
                    match_files.append(_file)
                    if self.verbose:
                        print("FOUND MATCH: %s" %basename(_file))
                else:
                    # This should never be called
                    warn("Ignoring file %s in directory:\n%s"
                         %(basename(_file), dirname(_file)))
# =============================================================================
#                         raise IOError("Fatal: invalid file encountered in: %s"
#                                       %_file)
# =============================================================================
        if len(match_files) == 0:
            raise IOError("No files could be found for variable %s, and %s "
                          "data in specified time interval\n%s-%s"
                          %(self.model_id, ts_type, self.start_time,
                            self.stop_time))
        # Define Iris var_constraint -> ensures that only the current 
        # variable is extracted from the netcdf file 
        var_constraint = Constraint(cube_func=lambda c: c.var_name==var_name)
        
        # read files using iris
        cubes = CubeList()
        loaded_files = []
        for _file in match_files:
            try:
                cubes.append(load_cube(_file, var_constraint))
                loaded_files.append(_file)
            except:
                warn("Failed to load %s as Iris cube" %_file)
        
        if len(loaded_files) == 0:
            raise IOError("None of the found files for variable %s, and %s "
                          "in specified time interval\n%s-%s\n"
                          "could be loaded"
                          %(self.model_id, ts_type, self.start_time,
                            self.stop_time))
        #now put the CubeList together and form one cube
        #1st equalise the cubes (remove non common attributes)
        equalise_attributes(cubes)
        #unify time units
        unify_time_units(cubes)

        #now concatenate the cube list to one cube
        cube_concat = cubes.concatenate()[0]
        
        #create instance of pyaerocom.ModelData
        data = ModelData(input=cube_concat, from_files=loaded_files,
                         model_id=self.model_id)
        # crop cube in time (if applicable)
        if not self.start_time == FIRST_DATE or not self.stop_time == LAST_DATE:
            if self.verbose:
                print("Applying temporal cropping of result cube")
            try:
                t_constraint = data.get_time_constraint(self.start_time, 
                                                        self.stop_time)
                data = data.extract(t_constraint)
            except Exception as e:
                warn("Failed to crop data for %s in time, error: %s"
                     %(var_name, repr(e)))
        
        if var_name in self.data:
            warn("Loaded data for variable %s already exists and will be "
                 "overwritten" %var_name)
        self.data[var_name] = data
        return data
    
    def read_all_vars(self, **kwargs):
        """Read all variables that could be found 
        
        Reads all variables that are available (i.e. in :attr:`vars`)
        
        Parameters
        ----------
        **kwargs
            see :func:`read_var` for valid input arguments.
        """
        _vars_read = []
        for var in self.vars:
            try:
                self.read_var(var, **kwargs)
                _vars_read.append(var)
            except:
                warn("Failed to read variable %s" %var)
        self.vars = _vars_read
        
class ReadMultiModelData:
    """Class that can be used to import model data from multiple models
    
    This class provides an interface to import model results from an arbitrary
    number of models and specific for a certain time interval (that can be 
    defined, but must not be defined). The actual
    
    Attributes
    ----------
    model_ids : list
        list containing string IDs of all models that should be imported
    results : dict
        dictionary containing :class:`ReadModelData` instances for each 
        model_id 
    
    Examples
    --------
    >>> import pyaerocom, pandas
    >>> start, stop = pandas.Timestamp("2012-1-1"), pandas.Timestamp("2012-5-1")
    >>> models = ["AATSR_SU_v4.3", "CAM5.3-Oslo_CTRL2016"]
    >>> read = pyaerocom.io.ReadMultiModelData(models, start, stop, verbose=False)
    >>> print(read.model_ids)
    ['AATSR_SU_v4.3', 'CAM5.3-Oslo_CTRL2016']
    >>> read_cam = read['CAM5.3-Oslo_CTRL2016']
    >>> assert type(read_cam) == pyaerocom.io.ReadModelData
    >>> for var in read_cam.vars: print(var)
    abs550aer
    deltaz3d
    humidity3d
    od440aer
    od550aer
    od550aer3d
    od550aerh2o
    od550dryaer
    od550dust
    od550lt1aer
    od870aer
    """
    # "private attributes (defined with one underscore). These may be 
    # controlled using getter and setter methods (@property operator, see 
    # e.g. definition of def start_time below)
    _start_time = FIRST_DATE
    _stop_time = LAST_DATE
    def __init__(self, model_ids, start_time=None, stop_time=None, 
                 verbose=VERBOSE):
        
        if isinstance(model_ids, str):
            model_ids = [model_ids]
        if not isinstance(model_ids, list) or not all([isinstance(x, str) for x in model_ids]):
            raise IllegalArgumentError("Please provide string or list of strings")
    
        self.model_ids = model_ids
        # dictionary containing instances of ModelImportResult for each model
        # is initiated in method `init_results` at end of __init__
        self.results = None
        
        self.verbose = verbose
        
        # only overwrite if there is input, note that the attributes
        # start_time and stop_time are defined below as @property getter and
        # setter methods, that ensure that the input is convertible to 
        # pandas.Timestamp
        if start_time is not None:
            self.start_time = start_time
        if stop_time is not None:
            self.stop_time = stop_time
        
        self.init_results()
        self.search_model_dirs()
        self.search_all_files()
        
    @property
    def start_time(self):
        """Start time for the data import
        
        Note      
        ----
        If input is not :class:`pandas.Timestamp`, it must be convertible 
        into :class:`pandas.Timestamp` (e.g. "2012-1-1")
        """
        t = self._start_time
        if not isinstance(t, Timestamp):
            raise ValueError("Invalid value encountered for start time "
                             "in reading engine: %s" %t)
        return t
    
    @start_time.setter
    def start_time(self, value):
        if not isinstance(value, Timestamp):    
            try:
                value = Timestamp(value)
            except:
                raise ValueError("Failed to convert input value to pandas "
                                  "Timestamp: %s" %value)
        self._start_time = value
            
    @property
    def stop_time(self):
        """Stop time for the data import
        
        Note      
        ----
        If input is not :class:`pandas.Timestamp`, it must be convertible 
        into :class:`pandas.Timestamp` (e.g. "2012-1-1")
        
        """
        t = self._stop_time
        if not isinstance(t, Timestamp):
            raise ValueError("Invalid value encountered for stop time "
                             "in reading engine: %s" %t)
        return t
    
    @stop_time.setter
    def stop_time(self, value):
        if not isinstance(value, Timestamp):  
            try:
                value = Timestamp(value)
            except:
                raise ValueError("Failed to convert input value to pandas "
                                  "Timestamp: %s" %value)
        self._stop_time = value
        
    
    
    def init_results(self):
        """Initiate the import result attributes
        
        Creates and initiates :class:`ModelImportResult` object for each 
        model specified in :attr:`model_ids` and stores it in the dictionary
        :attr:`results` using the `model_id`.
        """
        self.results = od()
        for model_id in self.model_ids:
            self.results[model_id] = ReadModelData(model_id,
                                                   self.start_time, 
                                                   self.stop_time, 
                                                   init=False,
                                                   verbose=self.verbose)
    
    def search_model_dirs(self):
        """Get the directory where model data for a given model resides in
        
        Returns
        -------
        bool
            True, if directory could be found, else False
        """
        #remember only the model IDs for which a directory could be found
        model_ids_new = []
        for model_id in self.model_ids:
            # loop through the list of models
            if self.results[model_id].search_model_dir():
                model_ids_new.append(model_id)
        if len(model_ids_new) == 0:
            raise AttributeError("Failed to find model directories for all "
                                 "model IDs specified (%s)" %self.model_ids)
        self.model_ids = model_ids_new
        return model_ids_new
    
    def search_all_files(self):
        """Search all valid model files for each model
        
        See also :func:`ReadModelData.search_all_files`
        
        Note
        ----
        This function does not seperate by variable or time.
        
        """
        # unfortunately there's more than one file naming convention
        # examples
        # aerocom3_CAM5.3-Oslo_AP3-CTRL2016-PD_od550aer_Column_2010_monthly.nc
        # aerocom.AATSR_ensemble.v2.6.daily.od550aer.2012.nc
        # loop through the list of models
        for model_id in self.model_ids:
            self.results[model_id].search_all_files()
    
        
    def read(self, var_ids, model_ids=None, start_time=None, stop_time=None,
             ts_type="daily"):
        """High level method to import data for multiple variables and models
        
        Parameters
        ----------
        var_ids : :obj:`str` or :obj:`list`
            string IDs of all variables that are supposed to be imported
        model_ids : :obj:`str` or :obj:`list`, optional
            string IDs of all models that are supposed to be imported
        start_time : :obj:`Timestamp` or :obj:`str`, optional
            start time of data import (if valid input, then the current 
            :attr:`start_time` will be overwritten)
        stop_time : :obj:`Timestamp` or :obj:`str`, optional
            stop time of data import (if valid input, then the current 
            :attr:`start_time` will be overwritten)
        ts_type : str
            string specifying temporal resolution (choose from 
            "hourly", "3hourly", "daily", "monthly")
        """
        if not ts_type in TS_TYPES:
            raise ValueError("Invalid input for ts_type, got: %s, "
                             "allowed values: %s" %(ts_type, TS_TYPES))
        if start_time is not None:
            self.start_time = start_time
        if stop_time is not None:
            self.stop_time = stop_time

        if model_ids is None: #use all models if unspecified
            model_ids = self.model_ids
        elif isinstance(model_ids, str):
            model_ids = [model_ids]
        if isinstance(var_ids, str):
            var_ids = [var_ids]
            
        warnings = []
        for model_id in model_ids:
            if model_id in self.results:
                read = self.results[model_id]
                for var in var_ids:
                    if var in read.vars:
                        read.read_var(var, start_time, stop_time, ts_type)
                    else:
                        warnings.append("Variable %s not available for model "
                                        "%s" %(var, model_id))
                    
                
            else:
                warnings.append("Failed to import model %s" %model_id)
        for msg in warnings:
            warn(msg)
        return self.results
    
    def __getitem__(self, model_id):
        """Try access import result for one of the models
        
        Parameters
        ----------
        model_id : str
            string specifying model that is supposed to be extracted
        
        Returns
        -------
        ReadModelData
            the corresponding read class for this model
            
        Raises
        -------
        ValueError
            if results for ``model_id`` are not available
        """
        if not model_id in self.results:
            raise ValueError("No data found for model_id %s" %model_id)
        return self.results[model_id]

if __name__=="__main__":
    import doctest
    doctest.testmod()


    
