# elections
Elections analysis, can detect fraud.

Benford's Law is used on counties + time series, with the 1st and 2nd digit, and χ2 tests are used for validation.

![Screenshot](/image/001.png?raw=true)

Install requirements
--------------------
```
pip3 install -r ./requirements.txt
```

Download data
-------------
```
python3 ./__main__.py --download
```

For now, only nytimes.com is supported, as this includes time series.
If you have more data, including older data from nytimes (in 2020), please contact me.


Analyse the data
----------------
```
python3 ./__main__.py --year 2020
```

This will generate a `data/2020.json` file.
This file can then be opened by the site on https://www.virtualcamera.net/elections/.


2016 and 2012 are supported as well, but then you must save the `.html` from the site as `data/2012-president.html` and `data/2016-president.html` then run:
```
python3 ./__main__.py --convert
```
