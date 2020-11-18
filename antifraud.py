# coding: utf-8
# @author octopoulo <polluxyz@gmail.com>
# @version 2020-11-17

"""
Antifraud
"""

from collections import Counter
import csv
from datetime import datetime, timezone
import json
from logging import getLogger
from math import log10
import os
import re
from typing import Any, Dict, List, Tuple

import requests

from commoner import open_json_file, read_text_safe, save_json_file, write_text_safe


DATA_FOLDER = 'data'

# https://en.wikipedia.org/wiki/Benford%27s_law
BENFORDS = [
    [],
    [log10(1 + 1 / n) if n > 0 else 0 for n in range(10)],
    [0.12, 0.114, 0.109, 0.104, 0.10, 0.097, 0.093, 0.09, 0.088, 0.085],
    [0.102, 0.101, 0.101, 0.101, 0.100, 0.100, 0.099, 0.099, 0.099, 0.098],
]

# first row is the P-value, other rows are chi-square
CHI_SQUARES = [
    [0.0000, 0.0010, 0.0020, 0.0030, 0.0040, 0.0050, 0.0060, 0.0070, 0.0080, 0.0090, 0.0100, 0.0200, 0.0300, 0.0400, 0.0500, 0.0600, 0.0700, 0.0800, 0.0900, 0.1000, 0.1100, 0.1200, 0.1300, 0.1400, 0.1500, 0.1600, 0.1700, 0.1800, 0.1900, 0.2000, 0.2100, 0.2200, 0.2300, 0.2400, 0.2500, 0.2600, 0.2700, 0.2800, 0.2900, 0.3000, 0.3100, 0.3200, 0.3300, 0.3400, 0.3500, 0.3600, 0.3700, 0.3800, 0.3900, 0.4000, 0.4100, 0.4200, 0.4300, 0.4400, 0.4500, 0.4600, 0.4700, 0.4800, 0.4900, 0.5000, 0.5100, 0.5200, 0.5300, 0.5400, 0.5500, 0.5600, 0.5700, 0.5800, 0.5900, 0.6000, 0.6100, 0.6200, 0.6300, 0.6400, 0.6500, 0.6600, 0.6700, 0.6800, 0.6900, 0.7000, 0.7100, 0.7200, 0.7300, 0.7400, 0.7500, 0.7600, 0.7700, 0.7800, 0.7900, 0.8000, 0.8100, 0.8200, 0.8300, 0.8400, 0.8500, 0.8600, 0.8700, 0.8800, 0.8900, 0.9000, 0.9100, 0.9200, 0.9300, 0.9400, 0.9500, 0.9600, 0.9700, 0.9800, 0.9900, 0.9910, 0.9920, 0.9930, 0.9940, 0.9950, 0.9960, 0.9970, 0.9980, 0.9990, 0.9991, 0.9992, 0.9993, 0.9994, 0.9995, 0.9996, 0.9997, 0.9998, 0.9999, 0.99999, 0.999999],
    #
    [ 0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.290,  0.306,  0.323,  0.340,  0.357,  0.376,  0.394,  0.414,  0.434,  0.455,  0.477,  0.499,  0.522,  0.546,  0.571,  0.596,  0.623,  0.650,  0.679,  0.708,  0.739,  0.771,  0.804,  0.838,  0.873,  0.910,  0.949,  0.989,  1.031,  1.074,  1.120,  1.167,  1.217,  1.269,  1.323,  1.381,  1.441,  1.504,  1.571,  1.642,  1.718,  1.798,  1.883,  1.974,  2.072,  2.178,  2.293,  2.417,  2.554,  2.706,  2.874,  3.065,  3.283,  3.537,  3.841,  4.218,  4.709,  5.412,  6.635,  6.823,  7.033,  7.273,  7.550,  7.879,  8.284,  8.807,  9.550, 10.828, 11.023, 11.241, 11.489, 11.776, 12.116, 12.532, 13.070, 13.831, 15.137, 19.511, 23.895],
    [ 0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.000,  0.302,  0.325,  0.349,  0.373,  0.397,  0.421,  0.446,  0.471,  0.497,  0.523,  0.549,  0.575,  0.602,  0.629,  0.657,  0.685,  0.713,  0.742,  0.771,  0.801,  0.831,  0.862,  0.893,  0.924,  0.956,  0.989,  1.022,  1.055,  1.089,  1.124,  1.160,  1.196,  1.232,  1.270,  1.308,  1.347,  1.386,  1.427,  1.468,  1.510,  1.553,  1.597,  1.642,  1.688,  1.735,  1.783,  1.833,  1.883,  1.935,  1.989,  2.043,  2.100,  2.158,  2.217,  2.279,  2.342,  2.408,  2.476,  2.546,  2.619,  2.694,  2.773,  2.854,  2.939,  3.028,  3.121,  3.219,  3.321,  3.430,  3.544,  3.665,  3.794,  3.932,  4.080,  4.241,  4.415,  4.605,  4.816,  5.051,  5.319,  5.627,  5.991,  6.438,  7.013,  7.824,  9.210,  9.421,  9.657,  9.924, 10.232, 10.597, 11.043, 11.618, 12.429, 13.816, 14.026, 14.262, 14.529, 14.837, 15.202, 15.648, 16.223, 17.034, 18.421, 23.026, 27.595],
    [ 0.000,  0.024,  0.039,  0.051,  0.062,  0.072,  0.081,  0.090,  0.099,  0.107,  0.115,  0.185,  0.245,  0.300,  0.352,  0.401,  0.449,  0.495,  0.540,  0.584,  0.628,  0.671,  0.714,  0.756,  0.798,  0.839,  0.881,  0.922,  0.964,  1.005,  1.047,  1.088,  1.129,  1.171,  1.213,  1.254,  1.296,  1.339,  1.381,  1.424,  1.467,  1.510,  1.553,  1.597,  1.642,  1.686,  1.731,  1.777,  1.823,  1.869,  1.916,  1.964,  2.012,  2.060,  2.109,  2.159,  2.210,  2.261,  2.313,  2.366,  2.420,  2.474,  2.529,  2.586,  2.643,  2.701,  2.761,  2.821,  2.883,  2.946,  3.011,  3.076,  3.144,  3.213,  3.283,  3.355,  3.430,  3.506,  3.584,  3.665,  3.748,  3.834,  3.922,  4.014,  4.108,  4.207,  4.309,  4.415,  4.526,  4.642,  4.763,  4.890,  5.025,  5.167,  5.317,  5.477,  5.649,  5.833,  6.033,  6.251,  6.491,  6.759,  7.060,  7.407,  7.815,  8.311,  8.947,  9.837, 11.345, 11.573, 11.827, 12.115, 12.447, 12.838, 13.316, 13.931, 14.796, 16.266, 16.489, 16.738, 17.020, 17.346, 17.730, 18.200, 18.805, 19.656, 21.108, 25.902, 30.630],
    [ 0.000,  0.091,  0.129,  0.159,  0.184,  0.207,  0.228,  0.247,  0.264,  0.281,  0.297,  0.429,  0.535,  0.627,  0.711,  0.788,  0.862,  0.931,  0.999,  1.064,  1.127,  1.188,  1.249,  1.308,  1.366,  1.424,  1.481,  1.537,  1.593,  1.649,  1.704,  1.759,  1.814,  1.868,  1.923,  1.977,  2.031,  2.086,  2.140,  2.195,  2.249,  2.304,  2.359,  2.415,  2.470,  2.526,  2.582,  2.639,  2.696,  2.753,  2.811,  2.869,  2.928,  2.987,  3.047,  3.107,  3.169,  3.231,  3.293,  3.357,  3.421,  3.486,  3.552,  3.619,  3.687,  3.756,  3.826,  3.898,  3.971,  4.045,  4.120,  4.197,  4.276,  4.356,  4.438,  4.522,  4.607,  4.695,  4.786,  4.878,  4.974,  5.072,  5.173,  5.277,  5.385,  5.497,  5.613,  5.733,  5.858,  5.989,  6.125,  6.268,  6.418,  6.577,  6.745,  6.923,  7.114,  7.318,  7.539,  7.779,  8.043,  8.337,  8.666,  9.044,  9.488, 10.026, 10.712, 11.668, 13.277, 13.519, 13.789, 14.094, 14.446, 14.860, 15.366, 16.014, 16.924, 18.467, 18.700, 18.961, 19.256, 19.596, 19.997, 20.488, 21.118, 22.005, 23.513, 28.473, 33.344],
    [ 0.000,  0.210,  0.280,  0.332,  0.375,  0.412,  0.445,  0.475,  0.503,  0.530,  0.554,  0.752,  0.903,  1.031,  1.145,  1.250,  1.347,  1.439,  1.526,  1.610,  1.691,  1.770,  1.846,  1.921,  1.994,  2.066,  2.136,  2.206,  2.275,  2.343,  2.410,  2.477,  2.543,  2.609,  2.675,  2.740,  2.805,  2.870,  2.935,  3.000,  3.065,  3.130,  3.195,  3.260,  3.325,  3.391,  3.456,  3.522,  3.589,  3.655,  3.723,  3.790,  3.858,  3.927,  3.996,  4.066,  4.136,  4.207,  4.279,  4.351,  4.425,  4.499,  4.574,  4.651,  4.728,  4.806,  4.886,  4.966,  5.048,  5.132,  5.217,  5.303,  5.391,  5.481,  5.573,  5.667,  5.763,  5.861,  5.961,  6.064,  6.170,  6.279,  6.391,  6.507,  6.626,  6.749,  6.876,  7.009,  7.146,  7.289,  7.439,  7.595,  7.759,  7.932,  8.115,  8.309,  8.516,  8.738,  8.977,  9.236,  9.521,  9.837, 10.191, 10.596, 11.070, 11.644, 12.375, 13.388, 15.086, 15.341, 15.625, 15.946, 16.315, 16.750, 17.279, 17.958, 18.907, 20.515, 20.758, 21.029, 21.335, 21.689, 22.105, 22.614, 23.268, 24.185, 25.745, 30.856, 35.856],
    [ 0.000,  0.381,  0.486,  0.562,  0.623,  0.676,  0.722,  0.764,  0.803,  0.839,  0.872,  1.134,  1.330,  1.492,  1.635,  1.765,  1.885,  1.997,  2.103,  2.204,  2.301,  2.395,  2.486,  2.575,  2.661,  2.746,  2.829,  2.910,  2.991,  3.070,  3.148,  3.226,  3.303,  3.379,  3.455,  3.530,  3.605,  3.679,  3.753,  3.828,  3.902,  3.975,  4.049,  4.123,  4.197,  4.271,  4.346,  4.420,  4.495,  4.570,  4.646,  4.721,  4.798,  4.875,  4.952,  5.030,  5.108,  5.187,  5.267,  5.348,  5.430,  5.512,  5.595,  5.680,  5.765,  5.852,  5.940,  6.029,  6.119,  6.211,  6.304,  6.399,  6.496,  6.594,  6.695,  6.797,  6.902,  7.009,  7.119,  7.231,  7.346,  7.465,  7.586,  7.712,  7.841,  7.974,  8.112,  8.255,  8.404,  8.558,  8.719,  8.888,  9.064,  9.250,  9.446,  9.654,  9.875, 10.112, 10.368, 10.645, 10.948, 11.283, 11.660, 12.090, 12.592, 13.198, 13.968, 15.033, 16.812, 17.078, 17.375, 17.710, 18.095, 18.548, 19.099, 19.805, 20.791, 22.458, 22.709, 22.990, 23.307, 23.672, 24.103, 24.628, 25.303, 26.250, 27.856, 33.107, 38.228],
    [ 0.000,  0.598,  0.741,  0.841,  0.921,  0.989,  1.049,  1.103,  1.152,  1.197,  1.239,  1.564,  1.802,  1.997,  2.167,  2.320,  2.461,  2.592,  2.716,  2.833,  2.945,  3.054,  3.158,  3.260,  3.358,  3.455,  3.549,  3.642,  3.733,  3.822,  3.911,  3.998,  4.084,  4.170,  4.255,  4.339,  4.423,  4.506,  4.589,  4.671,  4.754,  4.836,  4.918,  5.000,  5.082,  5.164,  5.246,  5.328,  5.411,  5.493,  5.576,  5.660,  5.743,  5.828,  5.913,  5.998,  6.084,  6.170,  6.258,  6.346,  6.435,  6.525,  6.615,  6.707,  6.800,  6.894,  6.989,  7.086,  7.184,  7.283,  7.384,  7.487,  7.591,  7.698,  7.806,  7.917,  8.029,  8.145,  8.263,  8.383,  8.507,  8.634,  8.765,  8.899,  9.037,  9.180,  9.327,  9.480,  9.639,  9.803,  9.975, 10.154, 10.342, 10.540, 10.748, 10.968, 11.203, 11.454, 11.724, 12.017, 12.337, 12.691, 13.088, 13.540, 14.067, 14.703, 15.509, 16.622, 18.475, 18.752, 19.060, 19.408, 19.808, 20.278, 20.849, 21.580, 22.601, 24.322, 24.581, 24.870, 25.197, 25.574, 26.018, 26.559, 27.254, 28.227, 29.878, 35.259, 40.492],
    [ 0.000,  0.857,  1.038,  1.162,  1.261,  1.344,  1.417,  1.482,  1.541,  1.596,  1.646,  2.032,  2.310,  2.537,  2.733,  2.908,  3.068,  3.217,  3.357,  3.490,  3.616,  3.737,  3.855,  3.968,  4.078,  4.186,  4.291,  4.393,  4.494,  4.594,  4.691,  4.788,  4.883,  4.977,  5.071,  5.163,  5.255,  5.346,  5.437,  5.527,  5.617,  5.707,  5.797,  5.886,  5.975,  6.065,  6.154,  6.243,  6.333,  6.423,  6.513,  6.603,  6.694,  6.785,  6.877,  6.969,  7.062,  7.155,  7.249,  7.344,  7.440,  7.537,  7.634,  7.733,  7.833,  7.933,  8.036,  8.139,  8.244,  8.351,  8.459,  8.568,  8.680,  8.794,  8.909,  9.027,  9.148,  9.270,  9.396,  9.524,  9.656,  9.791,  9.930, 10.072, 10.219, 10.370, 10.526, 10.688, 10.856, 11.030, 11.212, 11.401, 11.599, 11.808, 12.027, 12.259, 12.506, 12.770, 13.054, 13.362, 13.697, 14.068, 14.484, 14.956, 15.507, 16.171, 17.010, 18.168, 20.090, 20.377, 20.696, 21.056, 21.469, 21.955, 22.545, 23.300, 24.352, 26.124, 26.391, 26.689, 27.025, 27.412, 27.868, 28.424, 29.137, 30.136, 31.828, 37.332, 42.672],
    [ 0.000,  1.152,  1.370,  1.519,  1.637,  1.735,  1.820,  1.897,  1.966,  2.029,  2.088,  2.532,  2.848,  3.105,  3.325,  3.521,  3.700,  3.866,  4.021,  4.168,  4.308,  4.442,  4.571,  4.696,  4.817,  4.934,  5.049,  5.162,  5.272,  5.380,  5.487,  5.592,  5.695,  5.798,  5.899,  5.999,  6.099,  6.198,  6.296,  6.393,  6.490,  6.587,  6.684,  6.780,  6.876,  6.972,  7.068,  7.164,  7.261,  7.357,  7.454,  7.550,  7.648,  7.745,  7.843,  7.942,  8.041,  8.141,  8.242,  8.343,  8.445,  8.548,  8.652,  8.757,  8.863,  8.971,  9.079,  9.189,  9.301,  9.414,  9.528,  9.645,  9.763,  9.883, 10.006, 10.131, 10.258, 10.388, 10.521, 10.656, 10.795, 10.938, 11.084, 11.234, 11.389, 11.548, 11.713, 11.883, 12.059, 12.242, 12.433, 12.632, 12.840, 13.058, 13.288, 13.531, 13.790, 14.066, 14.363, 14.684, 15.034, 15.421, 15.854, 16.346, 16.919, 17.608, 18.480, 19.679, 21.666, 21.962, 22.291, 22.663, 23.089, 23.589, 24.197, 24.974, 26.056, 27.877, 28.151, 28.456, 28.801, 29.198, 29.666, 30.236, 30.966, 31.989, 33.720, 39.341, 44.783],
    [ 0.000,  1.479,  1.734,  1.908,  2.043,  2.156,  2.254,  2.341,  2.419,  2.491,  2.558,  3.059,  3.412,  3.697,  3.940,  4.157,  4.353,  4.535,  4.705,  4.865,  5.018,  5.163,  5.304,  5.439,  5.570,  5.698,  5.822,  5.943,  6.062,  6.179,  6.294,  6.407,  6.518,  6.628,  6.737,  6.845,  6.952,  7.058,  7.163,  7.267,  7.371,  7.475,  7.578,  7.681,  7.783,  7.886,  7.988,  8.090,  8.193,  8.295,  8.398,  8.501,  8.605,  8.708,  8.812,  8.917,  9.022,  9.128,  9.235,  9.342,  9.450,  9.559,  9.669,  9.780,  9.892, 10.006, 10.120, 10.236, 10.354, 10.473, 10.594, 10.717, 10.841, 10.968, 11.097, 11.228, 11.362, 11.499, 11.638, 11.781, 11.927, 12.076, 12.229, 12.387, 12.549, 12.716, 12.888, 13.066, 13.251, 13.442, 13.641, 13.849, 14.066, 14.294, 14.534, 14.788, 15.057, 15.344, 15.653, 15.987, 16.352, 16.753, 17.203, 17.713, 18.307, 19.021, 19.922, 21.161, 23.209, 23.514, 23.853, 24.235, 24.673, 25.188, 25.813, 26.611, 27.722, 29.588, 29.869, 30.181, 30.535, 30.941, 31.420, 32.003, 32.750, 33.796, 35.564, 41.296, 46.836],
]

COUNTRY_SYNONYMS = {
    'brunei darussalam': 'brunei',
    'cabo verde': 'cape verde',
    'china hong kong sar': 'hong kong',
    'china macao sar': 'macau',
    'congo': 'democratic republic of the congo',
    'cote d ivoire': 'ivory coast',
    'faeroe islands': 'faroe islands',
    'falkland islands malvinas': 'falkland islands',
    'holy see': 'vatican',
    'state of palestine': 'palestine',
    'timor leste': 'east timor',
    'uk': 'united kingdom',
    'us': 'united states',
    'wallis and futuna islands': 'wallis and futuna',
}

COVID_NAMES = {
    'Cases': 1,
    'Deaths': 2,
}

DOWNLOADS = {
    'covid': 'https://www.worldometers.info/coronavirus/',
    'covid-country': 'https://www.worldometers.info/coronavirus/country/{COUNTRY}',
    'nytimes':
        'https://static01.nyt.com/elections-assets/2020/data/api/2020-11-03/national-map-page/national/president.json',
}

CANDIDATES = {}
PARTIES = {
    'DEM': 0,
    'democrat': 0,
    'libertarian': 2,
    'REP': 1,
    'republican': 1,
}

ENOUGHS = [0, 17, 27]
MIN_COUNTS = [136, 270, 300]
SCORE_DOUBT = 0.7
TIMESTEP = 300

RE_COUNTRIES = re.compile(r'href="country/([\w-]+)/"')
RE_SCRIPT_2012 = re.compile(r'data: (\{.+\})')
RE_SCRIPT_2016 = re.compile(r'eln_races = (.+),')
RE_SCRIPT_2020 = re.compile(r'<script class="e-map-data".*?>(.*?)</script>', re.S)
RE_SERIE = re.compile(r"name: '(.*?)',.*?data: \[(.*?)\]", re.S)
RE_SERIES = re.compile(r'series: (\[\{.*?\}\])', re.S)


class Antifraud:
    def __init__(self, **kwargs):
        self.download = kwargs.get('download')          # type: str
        self.file = kwargs.get('file')                  # type: str
        self.year = kwargs.get('year')                  # type: int

        self.county_states = {}                         # type: Dict[str, List[str]]
        self.countries = {}                             # type: Dict[str, List[str]]
        self.lines = []                                 # type: List[str]
        self.logger = getLogger()

    def analyse_year(self, year: int):
        """Analyse a year
        """
        filename = self.file
        if not filename:
            if year == 2020:
                for suffix in ('-1519', ''):
                    filename = os.path.join(DATA_FOLDER, f'{year}-president-data{suffix}.json')
                    if os.path.isfile(filename):
                        break
                    else:
                        filename = None
        if not filename:
            filename = os.path.join(DATA_FOLDER, f'{year}-president-html.json')
        data = open_json_file(filename)
        if not data:
            self.logger.error({'status': 'analyse_year__error', 'filename': filename})
            return

        # 1) president: state
        meta = {}
        states = {}
        if isinstance(data, dict):
            meta = data.get('meta') or data
            data = data.get('data') or data
        if isinstance(data, dict):
            data = data.get('races') or data

        for i, state in enumerate(data):
            # a) counties
            cands, counties = self.collect_candidates(state)
            state_id = state.get('state_id')
            states[state_id] = cands

            fraud_chis = cands[9]
            fraud_scores = cands[10]
            frauds = cands[12]
            fraud_data = cands[13]

            for digit in (1, 2):
                for j, indices in enumerate([[0], [1], [2], [0, 1, 2]]):
                    total, chi, score, firsts, enough, enough2 = self.calculate_fraud(digit, counties, indices)
                    self.log(
                        f"CN {i:2} {digit} {str(indices).replace(', ', ''):5} {state_id} {total:3} {chi:6.2f}"
                        f" {str(score):5} {self.get_fraud(score, enough, enough2, 'X')} {firsts}")
                    if not enough:
                        continue
                    ichi = int(chi * 100) / 100
                    if score:
                        frauds[j] |= 1
                        if score > fraud_scores[0]:
                            fraud_chis[digit - 1] = ichi
                            fraud_scores[digit - 1] = int(score * 100) / 100
                    fraud_data.append([0, digit, indices, total, ichi, score, firsts])

            self.calculate_score(cands, fraud_data)

            # b) timeseries
            timeseries = state.get('timeseries')
            if not timeseries:
                continue
            cumuls = [0, 0, 0, 0]
            deltas = []
            prev_shares = [0, 0, 0, 0]
            for serie in timeseries:
                shares = serie.get('vote_shares')
                votes = serie.get('votes')
                cumuls[3] = votes
                vector = [0, 0, 0, 0, 0, 0]

                for key, value in shares.items():
                    cand = CANDIDATES.get(key)
                    if cand is None:
                        continue
                    value = int(value * votes + 0.5)
                    delta = value - prev_shares[cand]
                    vector[cand] = delta
                    cumuls[cand] += delta
                    prev_shares[cand] = value

                delta = votes - prev_shares[3]
                prev_shares[3] = votes
                vector[3] = delta
                vector[4] = serie.get('timestamp')
                vector[5] = cumuls[:]
                deltas.append(vector)

            for digit in (1, 2):
                for indices in [[0], [1], [3]]:
                    total, chi, score, firsts, enough, enough2 = self.calculate_fraud(digit, deltas, indices)
                    self.log(
                        f"TS {i:2} {digit} {str(indices):5} {state_id} {total:3} {chi:6.2f} {str(score):5}"
                        f" {self.get_fraud(score, enough, enough2, 'X')} {firsts}")
                    if not enough:
                        continue
                    ichi = int(chi * 100) / 100
                    if score:
                        frauds[indices[0]] |= 2
                        if score > fraud_scores[1]:
                            fraud_chis[digit + 1] = ichi
                            fraud_scores[digit + 1] = int(score * 100) / 100
                    fraud_data.append([1, digit, indices, total, ichi, score, firsts])

                    # fraud detected => try to isolate the time with a sliding window
                    # - find worst case = high number surrounded by high numbers too
                    if score < SCORE_DOUBT or not enough:
                        continue
                    length = len(deltas)
                    if length < TIMESTEP * 1.3:
                        continue

                    best = 0
                    betas = []

                    for steps in (2, 3):
                        alphas = []
                        highest = -1
                        interval = length / steps
                        lowest = 101
                        min_count = MIN_COUNTS[digit]
                        delta = min_count - interval

                        for i in range(steps):
                            # interval
                            start = i * interval
                            end = start + interval
                            if delta > 0:
                                start -= delta / 2
                                end += delta / 2
                            if start < 0:
                                end -= start
                                start = 0
                            if end > length:
                                start += length - end
                                end = length
                            start = int(start)
                            end = int(end + 0.5)

                            # fraud
                            # increase the interval if total is too low
                            while 1:
                                total, chi, score, firsts, enough, enough2 = \
                                    self.calculate_fraud(digit, deltas[start: end], indices)
                                if total < min_count and (start > 0 or end < length):
                                    if start > 0:
                                        start -= 1
                                    if end < length:
                                        end += 1
                                else:
                                    break

                            if score > highest:
                                highest = score
                            if score < lowest:
                                lowest = score

                            # first date is wrong => get the second one
                            first = deltas[start]
                            second = deltas[start + 1]
                            second_date = second[4]
                            first_date = min(first[4], second[4])

                            last = deltas[end - 1]
                            time_start = int(datetime.fromisoformat(first_date.replace('Z', '+00:00')).timestamp())
                            time_end = int(datetime.fromisoformat(last[4].replace('Z', '+00:00')).timestamp())
                            alphas.append([
                                3, digit, indices, total, int(chi * 100) / 100, score, firsts, start, end, time_start,
                                time_end, first[5], last[5]])

                        if highest < best * 1.02:
                            break
                        if highest > best:
                            best = highest
                        # not much difference between highest & lowest => not interesting
                        if highest > lowest + 0.15:
                            betas = alphas[:]

                    # show results
                    for _, _, _, total, ichi, score, firsts, start, end, time_start, time_end, first, last in betas:
                        self.log(
                            f"      {digit}  {start:3}-{end:3} {total:3} {chi:6.2f} {str(score):5}"
                            f" {self.get_fraud(score, enough, enough2, '.')} {str(firsts):48}"
                            f" {time_start} -> {time_end} {first}-> {last}")

                    if best >= 0.9:
                        fraud_data.extend(betas)

            self.calculate_score(cands, fraud_data)

        # 2) finish + total + timestamp
        total = [0] * 9
        for i, (code, state) in enumerate(states.items()):
            for j in range(8):
                total[j] += state[j]
            print(i, code, state)

        stamp = meta.get('timestamp')
        if stamp:
            total[8] = int(datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp())

        states['00'] = total
        print(total)

        # save json
        output = os.path.join(DATA_FOLDER, f'{year}.json')
        save_json_file(output, states, indent=2, sort=True)
        # log
        output = os.path.join(DATA_FOLDER, f'{year}.log')
        write_text_safe(output, '\n'.join(self.lines))
        self.lines = []

    def calculate_fraud(
            self,
            benford_id: int,        # 1 or 2
            data: List[int],
            indices: List[int],     # data[index]
        ) -> Tuple[int, float, float, List[int], bool, bool]:
        """Calculate the probability to have a fraud
        """
        benfords = BENFORDS[benford_id]

        # 1) get the 1st and 2nd digits
        counts = Counter()
        total = 0
        for datum in data:
            for index in indices:
                item = datum[index] if index >= 0 else datum
                if item < 1:
                    continue
                text = str(item)
                if len(text) >= benford_id:
                    counts[int(text[benford_id - 1])] += 1
                    total += 1

        counts = [counts[i] for i in range(10)]
        num_digit = 9 if benford_id == 1 else 10

        # 2) calculate chi-square
        chi = 0
        expects = [benfords[i] * total for i in range(10)]
        if total:
            for i in range(10 - num_digit, 10):
                chi += (counts[i] - expects[i]) ** 2 / expects[i]

        score = 0
        for (square, xscore) in zip(CHI_SQUARES[num_digit - 1], CHI_SQUARES[0]):
            if chi > square:
                score = xscore

        # need enough data, magic number = 30
        enough = total >= ENOUGHS[1] * num_digit
        enough2 = total >= ENOUGHS[2] * num_digit
        if score and enough and False:
            print(counts)
            print(expects)
        return total, chi, score, counts, enough, enough2

    def calculate_score(self, cands: List[Any], data: List[Any]):
        """Calculate the final fraud score for presentation (colors)
        cands: [0, digit, indices, total, int(chi * 100) / 100, score, firsts]
        """
        alphas = [item for item in data if item[3] >= MIN_COUNTS[item[1]]]
        alphas = sorted(alphas, key=lambda x: x[5], reverse=True)

        best = 0
        count = 0
        total = 0

        if len(alphas):
            alpha = alphas[0]
            count += alpha[3]
            best = alpha[5]
            total = count * best

            if len(alphas) > 1:
                beta = alphas[1]
                if beta[5] > best * 0.9:
                    count += beta[3]
                    total += beta[3] * beta[5]

        score = total / (120 + count) if count else 0
        cands[8] = best
        cands[11] = int(score * 100) / 100

    def collect_candidates(self, dico: Dict[str, Any]) -> Tuple[Any]:
        """Collect candidates: democrat + republican, in that order
        """
        # 1) state votes
        cands = dico.get('candidates') or dico.get('results')
        state_total = self.create_empty()
        state_total[3] = dico.get('votes') or 0
        state_total[7] = dico.get('absentee_votes') or 0
        state_total[15] = dico.get('electoral_votes')

        missing_votes = (state_total[3] == 0)
        missing_absentees = (state_total[7] == 0)

        # 2) candidates
        for cand in cands:
            party = PARTIES.get(cand.get('party_id'))
            if party is None:
                continue
            CANDIDATES[cand.get('candidate_key')] = party
            if cand.get('winner'):
                state_total[14] = party
            #
            votes = cand.get('votes') or cand.get('vote_count') or 0
            state_total[party] += votes
            if missing_votes:
                state_total[3] += votes
            #
            absentees = cand.get('absentee_votes') or 0
            state_total[party + 4] += absentees
            if missing_absentees:
                state_total[7] += absentees

        # 3) counties votes
        county_total = []
        verify_total = [0, 0, 0, 0]
        counties = dico.get('counties') or []
        for county in counties:
            vector = [0, 0, 0, county.get('votes'), county.get('fips'), county.get('name')]

            results = county.get('results') or []
            for key, value in results.items():
                cand = CANDIDATES.get(key)
                if cand is None:
                    continue
                vector[cand] = value
                verify_total[cand] += value

            county_total.append(vector)

        # 4) check for mismatch
        if any(state_total[i] != verify_total[i] for i in (0, 1, 2, 3)) and False:
            print(dico.get('state_id'))
            print(state_total)
            print(verify_total)
            print()

        return state_total, county_total

    def convert_file(self, filename: str):
        """Convert an HTML to JSON
        """
        print(filename)
        text = read_text_safe(filename)
        for regexp in [RE_SCRIPT_2012, RE_SCRIPT_2016, RE_SCRIPT_2020]:
            rematch = regexp.search(text)
            if rematch:
                break

        if not rematch:
            self.logger.warning({'status': 'convert_file__script_error', 'filename': filename})
            return

        data = rematch.group(1)
        dico = None
        try:
            dico = json.loads(data)
            if isinstance(dico, dict):
                races = dico.get('races')
                if races:
                    dico = races
        except Exception as e:
            self.logger.warning({'status': 'convert_file__json_error', 'error': e, 'filename': filename})
            return

        if not dico:
            return
        base, ext = os.path.splitext(filename)
        output = f'{base}-html.json'
        save_json_file(output, dico, indent=2, sort=True)

    def convert_folder(self):
        """Convert HTML to JSON
        """
        folder = DATA_FOLDER
        sources = os.listdir(folder)
        for source in sources:
            base, ext = os.path.splitext(source)
            if ext != '.html':
                continue
            filename = os.path.join(folder, source)
            if os.path.isfile(filename):
                self.convert_file(filename)

    def create_empty(self) -> List[Any]:
        """Create an empty vector for results
        """
        return [
            0, 0, 0, 0,             # 0-3: D/R/L/* president
            0, 0, 0, 0,             # 4-7: D/R/L/* president absentee
            0,                      # 8: fraud
            [0, 0, 0, 0],           # 9: fraud_chis
            [0, 0, 0, 0],           # 10: fraud_scores
            0,                      # 11: fraud %
            [0, 0, 0, 0],           # 12: frauds
            [],                     # 13: fraud_data
            -1,                     # 14: winner
            0,                      # 15: electoral
        ]

    def download_covid(self):
        """Download covid-19 data
        + calculate Benford + chi2
        """
        # 0) not enough data so far => modify ENOUGHS + MIN_COUNTS
        for i, count in enumerate(ENOUGHS):
            ENOUGHS[i] = count // 2
        for i, count in enumerate(MIN_COUNTS):
            MIN_COUNTS[i] = count // 2

        url = DOWNLOADS.get('covid')
        text = self.request_text(url)
        countries = sorted(set(RE_COUNTRIES.findall(text)))
        stats = {}

        for name in countries:
            # 1) identify the country
            country = self.find_country(name)
            if not country:
                continue

            # 2) get country data
            url = DOWNLOADS.get('covid-country').replace('{COUNTRY}', name)
            text = self.request_text(url)
            series = RE_SERIES.findall(text)
            covid_cases = [[], [], []]
            dones = set()

            for serie in series:
                rematch = RE_SERIE.search(serie)
                if not rematch:
                    continue
                name = rematch.group(1)
                if name in dones:
                    continue
                if not (covid_id := COVID_NAMES.get(name)):
                    continue

                dones.add(name)
                data = [int(x) for x in rematch.group(2).split(',')]
                cases = covid_cases[covid_id]
                prev = 0
                for item in data:
                    if item == prev:
                        continue
                    delta = item - prev
                    covid_cases[0].append(delta)
                    cases.append(delta)
                    prev = item

            if not covid_cases[0]:
                continue

            cands = self.create_empty()
            fraud_chis = cands[9]
            fraud_scores = cands[10]
            frauds = cands[12]
            fraud_data = cands[13]

            for digit in (1, 2):
                total, chi, score, firsts, enough, enough2 = self.calculate_fraud(digit, covid_cases[0], [-1])
                self.log(
                    f"{country[1]} {country[5]:3} {digit} 2 {total:3} {chi:6.2f}"
                    f" {str(score):5} {self.get_fraud(score, enough, enough2, 'X')} {firsts}")
                ichi = int(chi * 100) / 100
                if score:
                    frauds[3] |= 1
                    if score > fraud_scores[0]:
                        fraud_chis[digit - 1] = ichi
                        fraud_scores[digit - 1] = int(score * 100) / 100
                fraud_data.append([0, digit, [2], total, ichi, score, firsts])

            self.calculate_score(cands, fraud_data)
            stats[country[5]] = cands

        # 3) totals
        total = [0] * 9
        total[8] = int(datetime.now(tz=timezone.utc).timestamp())
        stats['00'] = total

        output = os.path.join(DATA_FOLDER, 'covid.json')
        save_json_file(output, stats, indent=2, sort=True)

    def download_president(self):
        """Download data from a source
        """
        url = DOWNLOADS.get(self.download)
        text = self.request_text(url)
        output = os.path.join(DATA_FOLDER, f'2020-president-data.json')
        print(f'downloaded {len(text)} bytes to {output}')
        write_text_safe(output, text)

    def find_country(self, name: str) -> List[str] or None:
        """Find a country from the .csv list
        """
        lower = name.lower()
        lower = COUNTRY_SYNONYMS.get(lower, lower)
        if country := self.countries.get(lower):
            return country
        lower = lower.replace('-', ' ')
        lower = COUNTRY_SYNONYMS.get(lower, lower)
        if country := self.countries.get(lower):
            return country
        lower = lower.replace(' ', '')
        lower = COUNTRY_SYNONYMS.get(lower, lower)
        if country := self.countries.get(lower):
            return country
        return None

    def get_fraud(self, score: float, enough: bool, enough2: bool, marker: str) -> str:
        """Get a FRAUD text
        """
        if score > 0.9 and enough:
            fraud = 'FRAUD'
            if not enough2:
                fraud = fraud.lower()
        else:
            fraud = '     '
        return f"{fraud} {' ' if enough2 else marker}"

    def go(self):
        """Go!
        """
        print(f'Go {self.year}')
        self.analyse_year(self.year)

    def initialise(self):
        """Initialise some structures
        """
        county_states = open_json_file(os.path.join(DATA_FOLDER, 'county_states.json'))

        # file exported from countrycode.org
        filename = os.path.join(DATA_FOLDER, 'countrycode.csv')
        names = {}
        with open(filename, newline='') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in spamreader:
                code = row[5]
                if code.isdigit():
                    self.countries[code] = row
                    self.countries[row[0].lower()] = row
                    names[code] = row[0]

    def log(self, text: str):
        """Log on console + file
        """
        print(text)
        self.lines.append(text)

    def pennsylvania(self):
        """Count data from PA
        """
        DATE_INDICES = (2, 4, 5, 6, 7)
        filename = os.path.join(DATA_FOLDER, '2020_General_Election_Mail_Ballot_Requests_Department_of_State.csv')
        i = 0
        county_stats = {}
        dates = Counter()
        parties = {}
        stats = [0, 0]
        with open(filename, newline='') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in spamreader:
                # skip first + all non D/R
                if i == 0 or row[1] not in {'D', 'R'}:
                    i += 1
                    continue

                # fix the dates
                for date_id in DATE_INDICES:
                    date = row[date_id]
                    if date:
                        items = date.split('/')
                        row[date_id] = '/'.join([items[2], items[0], items[1]])

                date = row[7]
                county_stat = county_stats.setdefault(row[0], [0, 0, 0, 0, 0, 0])
                is_dem = (row[1] == 'D')
                party = parties.setdefault(row[1], [0, 0])

                county_stat[0] += 1
                county_stat[2 if is_dem else 4] += 1

                party[0] += 1
                stats[0] += 1
                if date:
                    county_stat[1] += 1
                    county_stat[3 if is_dem else 5] += 1
                    party[1] += 1
                    stats[1] += 1
                    dates[date] += 1
                if i % 10000 == 0:
                    print(i, ', '.join(row))
                i += 1
                # if i > 100:
                #     break

        print(parties)
        print(stats)
        print(dates)
        print(county_stats)

    def request_text(self, url: str) -> str or None:
        """Get text data from an URL
        """
        if not url:
            return None
        res = requests.get(url)
        if res.status_code != 200:
            self.logger.error({'status': 'download__error', 'status_code': res.status_code})
            return None
        return res.text
