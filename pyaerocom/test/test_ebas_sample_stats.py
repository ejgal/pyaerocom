#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
High level test methods that check EBAS time series data for selected stations
Created on Thu Apr 12 14:45:43 2018

@author: jonasg
"""
import pytest
import numpy.testing as npt
import numpy as np
from pyaerocom.test.settings import lustre_unavail
from pyaerocom.io import ReadEbas

def _make_data():
    r = ReadEbas()
    return r.read('scatc550aer', station_names='Jungfrau*')

@pytest.fixture(scope='module')
def data_scat_jungfraujoch():
    return _make_data()

@lustre_unavail
def test_ungriddeddata_jungfraujoch(data_scat_jungfraujoch):
    data = data_scat_jungfraujoch
    
    assert data.shape == (245448, 12)# (227928, 12)
    assert len(data.metadata) == 28
    
    unique_coords = []
    unique_coords.extend(np.unique(data.latitude))
    unique_coords.extend(np.unique(data.longitude))
    unique_coords.extend(np.unique(data.altitude))
    assert len(unique_coords) == 4
    npt.assert_allclose(unique_coords, [46.5475, 7.985, 3578.0, 3580.0],
                        rtol=1e-2)
    
    vals = data._data[:, data.index['data']]
    check = [np.nanmean(vals), 
             np.nanstd(vals),
             np.nanmax(vals),
             np.nanmin(vals)]

    npt.assert_allclose(check, 
                        [4.35, 7.24, 182.7, -5.57], rtol=1e-1)
    
    

@lustre_unavail   
def test_scat_jungfraujoch(data_scat_jungfraujoch):
    stat = data_scat_jungfraujoch.to_station_data('Jung*')
    
    assert 'scatc550aer' in stat
    assert 'scatc550aer' in stat.overlap
    assert len(stat.overlap['scatc550aer']) == 25787 #17466
    assert stat['stat_merge_pref_attr'] == 'revision_date'
    assert int(stat['data_level']) == 2
    
    npt.assert_array_equal([stat.dtime.min(), stat.dtime.max()],
                            [np.datetime64('1995-07-08T23:00:00'), 
                             np.datetime64('2018-12-31T23:00:00')])
    
    vals = [stat['instrument_name'], stat['ts_type'], stat['PI'],
            len(stat.filename.split(';'))]
    
    npt.assert_array_equal(vals,
                           ['Ecotech_Aurora3000_JFJ_dry; TSI_3563_JFJ_dry; IN3563',
                            'hourly',
                            'Bukowiecki, Nicolas; Baltensperger, Urs; Weingartner, Ernest',
                            28])
    
    d = stat.scatc550aer
    vals = [d.mean(), d.std(), d.min(), d.max()]
    npt.assert_allclose(vals, [4.66, 7.60, -5.57, 182.7], rtol=1e-1)
    
    d = stat.overlap['scatc550aer']
    vals = [d.mean(), d.std(), d.min(), d.max()]
    npt.assert_allclose(vals,
                        [2.91, 4.58, -3.47, 97.65], rtol=1e-1)

@lustre_unavail   
def test_scat_jungfraujoch_lev3(data_scat_jungfraujoch):
    data_scat_jungfraujoch = data_scat_jungfraujoch.apply_filters(
            set_flags_nan=True, remove_outliers=True, data_level=2)
    stat = data_scat_jungfraujoch.to_station_data('Jung*')
    
    assert 'scatc550aer' in stat
    assert 'scatc550aer' in stat.overlap
    assert len(stat.overlap['scatc550aer']) == 25787 #17466
    assert stat['stat_merge_pref_attr'] == 'revision_date'
    assert int(stat['data_level']) == 2
    
    npt.assert_array_equal([stat.dtime.min(), stat.dtime.max()],
                            [np.datetime64('1995-07-08T23:00:00'), 
                             np.datetime64('2018-12-31T23:00:00')])
    
    vals = [stat['instrument_name'], stat['ts_type'], stat['PI'],
            len(stat.filename.split(';'))]
    
    npt.assert_array_equal(vals,
                           ['Ecotech_Aurora3000_JFJ_dry; TSI_3563_JFJ_dry; IN3563',
                            'hourly',
                            'Bukowiecki, Nicolas; Baltensperger, Urs; Weingartner, Ernest',
                            28])
    
    d = stat.scatc550aer
    vals = [d.mean(), d.std(), d.min(), d.max()]
    npt.assert_allclose(vals, [4.66, 7.60, -5.57, 182.7], rtol=1e-1)
    
    d = stat.overlap['scatc550aer']
    vals = [d.mean(), d.std(), d.min(), d.max()]
    npt.assert_allclose(vals,
                        [2.91, 4.58, -3.47, 97.65], rtol=1e-1)
    
@lustre_unavail   
def test_scat_jungfraujoch_subset(data_scat_jungfraujoch):
    
    stat = data_scat_jungfraujoch.to_station_data('Jung*', 
                                                  start=2008, stop=2011, 
                                                  freq='monthly')
    
    assert stat.dtime.min() == np.datetime64('2008-01-15')
    assert stat.dtime.max() == np.datetime64('2010-12-15')
    assert stat.ts_type == 'monthly'
    assert stat.ts_type_src == 'hourly'
    
    d = stat['scatc550aer']
    vals = [d.mean(), d.std(), d.min(), d.max()]

    npt.assert_allclose(vals, [4.37, 3.48, 0.46, 11.93], rtol=1e-1)
    
if __name__=="__main__":
   # pya.change_verbosity('info')
    #import sys
    d = _make_data()
    test_ungriddeddata_jungfraujoch(d)
    test_scat_jungfraujoch(d)
    test_scat_jungfraujoch_lev3(d)
    
    test_scat_jungfraujoch_subset(d)
# =============================================================================
#     
#     d = _make_data()
#     stat = d.to_station_data('Jung*', start=2008, stop=2011, freq='monthly')
#     stat.plot_timeseries('scatc550aer')
#     
# =============================================================================
    #pytest.main(sys.argv)