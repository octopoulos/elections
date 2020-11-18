# coding: utf-8
# @author octopoulo <polluxyz@gmail.com>
# @version 2020-11-17

"""
Main
"""

from argparse import ArgumentParser
from time import time

from antifraud import Antifraud


def main():
    parser = ArgumentParser(description='Antifraud', prog='python __main__.py')
    add = parser.add_argument

    add('--convert', action='store_true', help='convert html to json')
    add('--covid', action='store_true', help='get covid data')
    add('--download', nargs='?', default='', const='nytimes', help='download new data', choices=['nytimes'])
    add('--file', nargs='?', help='input filename, ex: 2020-president-data.json')
    add('--pa', action='store_true', help='count data from Pennsylvania')
    add('--year', nargs='?', default=None, type=int, help='year to analyse', choices=[2012, 2016, 2020])

    # configure args
    args = parser.parse_args()
    args_dict = vars(args)
    args_set = set(item for item, value in args_dict.items() if value)

    # create the Antifraud
    antifraud = Antifraud(**args_dict)
    antifraud.initialise()
    if args.convert:
        antifraud.convert_folder()
    elif args.covid:
        antifraud.download_covid()
    elif args.download:
        antifraud.download_president()
    elif args.pa:
        antifraud.pennsylvania()
    else:
        antifraud.go()


if __name__ == '__main__':
    start = time()
    main()
    print(f'\nELAPSED: {time() - start:.3f} seconds')
