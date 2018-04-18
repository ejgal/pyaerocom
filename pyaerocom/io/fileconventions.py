#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Low level classes and methods for io
"""
from collections import OrderedDict as od
from os.path import join, exists, basename
from warnings import warn
try:
    from ConfigParser import ConfigParser
except: 
    from configparser import ConfigParser

class FileConventionRead(object):
    """Class that represents a file naming convention for reading Aerocom files
    
    Attributes
    ----------
    name : str
        name of this convention (e.g. "aerocom3")
    file_sep : str
        filename delimiter for accessing different variables
    year_pos : int
        position of year information in filename after splitting using 
        delimiter :attr:`file_sep` 
    var_pos : int
        position of variable information in filename after splitting using 
        delimiter :attr:`file_sep` 
    ts_pos : int
        position of information of temporal resolution in filename after 
        splitting using delimiter :attr:`file_sep` 
    """
    def __init__(self, name="aerocom3", file_sep="", year_pos=-1,
                 var_pos=-1, ts_pos=-1):
       self.name = name
       self.file_sep = file_sep
       self.year_pos = year_pos
       self.var_pos = var_pos
       self.ts_pos = ts_pos
       
       try:
           self.import_default(self.name) 
       except:
           pass
      
    def from_file(self, file):
        """Identify convention from a file
        
        Currently only two conventions (aerocom2 and aerocom3) exist that are
        identified by the delimiter used.
        
        Parameters
        ----------
        file : str
            file path or file name
        
        Returns
        -------
        FileConventionRead
            this object (with updated convention)
            
        Raises
        ------
        NameError
            if convention cannot be identified
            
        Example
        -------
        >>> from pyaerocom.io import FileConventionRead
        >>> filename = 'aerocom_NCAR_CAM5.3_all_2000_rsntcsnoa_TOA_monthly.nc'
        >>> print(FileConventionRead().from_file(filename))
        pyaeorocom FileConventionRead
        name: aerocom3
        file_sep: _
        year_pos: -2
        var_pos: -4
        ts_pos: -1
        """
        
        if basename(file).count("_") >= 4:
            self.import_default("aerocom3")
        elif basename(file).count(".") >= 4:
            self.import_default("aerocom2")
        else:
            raise NameError("Could not identify convention from input file %s"
                            %basename(file))
        return self

    def get_info_from_file(self, file):
        """Identify convention from a file
        
        Currently only two conventions (aerocom2 and aerocom3) exist that are
        identified by the delimiter used.
        
        Parameters
        ----------
        file : str
            file path or file name
        
        Returns
        -------
        OrderedDict
            dictionary containing keys `year, var_name, ts_type` and 
            corresponding variables, extracted from the filename 
            
        Raises
        ------
        NameError
            if convention cannot be identified
            
        Example
        -------
        >>> from pyaerocom.io import FileConventionRead
        >>> filename = ('aerocom3_CAM5.3-Oslo_AP3-CTRL2016-PD_od550aer_Column_2010_monthly.nc')
        >>> conv = FileConventionRead("aerocom3")
        >>> info = conv.get_info_from_file(filename)
        >>> for item in info.items(): print(item)
        ('year', 2010)
        ('var_name', 'od550aer')
        ('ts_type', 'monthly.nc')
        """
        info = od(year=None, var_name=None, ts_type=None)
        spl = basename(file).split(self.file_sep)
        try:
            info["year"] = int(spl[self.year_pos])
        except:
            warn("Failed to extract year information")
        try:
            info["var_name"] = spl[self.var_pos]
        except:
            warn("Failed to extract variable information")
        try:
            info["ts_type"] = spl[self.ts_pos]
        except:
            warn("Failed to extract ts_type")
        return info
    
    def string_mask(self, var, year, ts_type):
        """Returns mask that can be used to identify files of this convention
        
        Parameters
        ----------
        var : str
            variable string ID (e.g. "od550aer")
        year : int
            desired year of observation (e.g. 2012)
        ts_type : str
            string specifying temporal resolution (e.g. "daily")
        
        Example
        -------
            
        import re
        conf_aero2 = FileConventionRead(name="aerocom2")
        conf_aero3 = FileConventionRead(name="aerocom2")
        
        var = od550aer
        year = 2012
        ts_type = "daily"
        
        match_str_aero2 = conf_aero2.string_mask(var, year, ts_type)
        
        match_str_aero3 = conf_aero3.string_mask(var, year, ts_type)
            
        """
        if self.name == "aerocom2":
            return ".".join(['.*',ts_type, var, str(year), 'nc'])
        elif self.name == "aerocom3":
            return "_".join(['.*',var, '.*',str(year), ts_type])+'.nc'
        else:
            raise NotImplementedError("File matching mask for convention %s "
                                      "not yet defined..." %self.name)
            
    def import_default(self, name):
        """Checks and load default information from database"""
        from pyaerocom import __dir__
        fpath = join(__dir__, "data", "file_conventions.ini")
        if not exists(fpath):
            raise IOError("File conventions ini file could not be found: %s"
                          %fpath)
        conf_reader = ConfigParser()
        conf_reader.read(fpath)
        if not name in conf_reader:
            raise NameError("No default available for %s" %name)
        self.name = name
        for key, val in conf_reader[name].items():
            if key in self.__dict__:
                try:
                    val = int(val)
                except:
                    pass
                self.__dict__[key] = val
                
    
    def from_dict(self, new_vals):
        """Load info from dictionary
        
        Parameters
        ----------
        new_vals : dict
            dictionary containing information
        
        Returns
        -------
        self
        """
        for k, v in new_vals.items():
            if k in self.__dict__:
                self.__dict__[k] = v
        return self
    
    def to_dict(self):
        """Convert this object to ordered dictionary"""
        return od(name = self.name,
                  file_sep = self.file_sep,
                  year_pos = self.year_pos,
                  var_pos = self.var_pos,
                  ts_pos = self.ts_pos)
      
    def __repr__(self):
       return ("%s %s" %(self.name, super(FileConventionRead, self).__repr__()))
   
    def __str__(self):
        s = "pyaeorocom FileConventionRead"
        for k, v in self.to_dict().items():
            s += "\n%s: %s" %(k, v)
        return s
    
if __name__=="__main__":
    conf = FileConventionRead()
    
    print(conf)
        
    d = od(name = "Fake",
           file_sep = 10,
           year_pos = -6,
           var_pos = 15,
           ts_pos = 3)
    print(conf.from_dict(d))
    try:
        conf.import_default("blaaa")
    except NameError:
        print("Works as expected")
    conf.import_default("aerocom3")
    print(conf)
    
    conf = FileConventionRead(name="aerocom2")
    print(conf)
    
    import doctest
    doctest.testmod()
    
    