# coding: utf-8
# @author octopoulo <polluxyz@gmail.com>
# @version 2020-11-12

"""
Antifraud
"""

from collections import Counter
import csv
from datetime import datetime
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

CHI_SCORES = [0.75, 0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.98, 0.99, 0.995, 0.9975, 0.998, 0.999, 0.9995]

CHI_SQUARES = [
    #  0.750   0.800   0.85   0.900   0.925   0.950   0.975   0.98   0.990   0.995  0.9975  0.998   0.999  0.9995
    [],
    [  1.323,  1.642,  2.07,  2.706,  3.170,  3.841,  5.024,  5.41,  6.635,  7.879,  9.14,  9.550, 10.828, 12.116],
    [  2.773,  3.219,  3.79,  4.605,  5.181,  5.991,  7.378,  7.82,  9.210, 10.597, 11.98, 12.429, 13.816, 15.202],
    [  4.108,  4.642,  5.32,  6.251,  6.905,  7.815,  9.348,  9.84, 11.345, 12.838, 14.32, 14.796, 16.266, 17.731],
    [  5.385,  5.989,  6.74,  7.779,  8.496,  9.488, 11.143, 11.67, 13.277, 14.860, 16.42, 16.924, 18.467, 19.998],
    [  6.626,  7.289,  8.12,  9.236, 10.008, 11.070, 12.833, 13.39, 15.086, 16.750, 18.39, 18.907, 20.515, 22.106],
    [  7.841,  8.558,  9.45, 10.645, 11.466, 12.592, 14.449, 15.03, 16.812, 18.548, 20.25, 20.791, 22.458, 24.104],
    [  9.037,  9.803, 10.75, 12.017, 12.883, 14.067, 16.013, 16.62, 18.475, 20.278, 22.04, 22.601, 24.322, 26.019],
    [ 10.219, 11.030, 12.03, 13.362, 14.270, 15.507, 17.535, 18.17, 20.090, 21.955, 23.77, 24.352, 26.125, 27.869],
    [ 11.389, 12.242, 13.29, 14.684, 15.631, 16.919, 19.023, 19.68, 21.666, 23.589, 25.46, 26.056, 27.877, 29.667],
    [ 12.549, 13.442, 14.53, 15.987, 16.971, 18.307, 20.483, 21.16, 23.209, 25.188, 27.11, 27.722, 29.588, 31.421],
]

DOWNLOADS = {
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

MIN_COUNTS = [0, 240, 270]
TIME_STEP = 250

RE_SCRIPT_2012 = re.compile(r'data: (\{.+\})')
RE_SCRIPT_2016 = re.compile(r'eln_races = (.+),')
RE_SCRIPT_2020 = re.compile(r'<script class="e-map-data".*?>(.*?)</script>', re.S)


class Antifraud:
    def __init__(self, **kwargs):
        self.download = kwargs.get('download')          # type: str
        self.file = kwargs.get('file')                  # type: str
        self.year = kwargs.get('year')                  # type: int

        self.county_states = {}                         # type: Dict[str, List[str]]
        self.lines = []                                 # type: List[str]
        self.logger = getLogger()

    def analyse_year(self, year: int):
        """Analyse a year
        """
        filename = self.file
        if not filename:
            if year == 2020:
                for suffix in ('-1202', ''):
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
        states = {}
        if isinstance(data, dict):
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

            for digit in range(1, 3):
                for j, indices in enumerate([[0], [1], [2], [0, 1, 2]]):
                    total, chi, score, firsts, enough = self.calculate_fraud(digit, counties, indices)
                    self.log(
                        f"CN {i:2} {digit} {str(indices).replace(', ', ''):5} {state_id} {total:3} {chi:6.2f}"
                        f" {str(score):5} {'FRAUD' if score > 0.9 and enough else '     '}"
                        f" {' ' if enough else 'X'} {firsts}")
                    if not enough:
                        continue
                    if score:
                        frauds[j] |= 1
                        if score > fraud_scores[0]:
                            fraud_chis[digit - 1] = chi
                            fraud_scores[digit - 1] = score
                    if score or len(indices) > 1:
                        fraud_data.append([0, digit, indices, total, int(chi * 100) / 100, score, firsts])

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

            for digit in range(1, 3):
                for indices in [[0], [1], [3]]:
                    total, chi, score, firsts, enough = self.calculate_fraud(digit, deltas, indices)
                    self.log(
                        f"TS {i:2} {digit} {str(indices):5} {state_id} {total:3} {chi:6.2f} {str(score):5}"
                        f" {'FRAUD' if score > 0.9 and enough else '     '} {' ' if enough else 'X'} {firsts}")
                    if not enough:
                        continue
                    if score:
                        frauds[indices[0]] |= 2
                        if score > fraud_scores[1]:
                            fraud_chis[digit + 1] = chi
                            fraud_scores[digit + 1] = score
                    if score or indices == 3:
                        fraud_data.append([1, digit, indices, total, int(chi * 100) / 100, score, firsts])

                    # fraud detected => try to isolate the time with a sliding window
                    if score and enough:
                        length = len(deltas)
                        start = 0
                        while start < length - TIME_STEP:
                            total, chi, score, firsts, enough = \
                                self.calculate_fraud(digit, deltas[start: start + 180], indices)
                            first = deltas[start]
                            last = deltas[start + TIME_STEP - 1]
                            time_start = int(datetime.fromisoformat(first[4].replace('Z', '+00:00')).timestamp())
                            time_end = int(datetime.fromisoformat(last[4].replace('Z', '+00:00')).timestamp())
                            self.log(
                                f"      {digit}  {start:3}-{start + TIME_STEP:3} {total:3} {chi:6.2f} {str(score):5}"
                                f" {'FRAUD' if score > 0.9 else '     '} {' ' if enough else '.'} {str(firsts):48}"
                                f" {time_start} -> {time_end} {first[5]}-> {last[5]}")
                            start += 10

            self.calculate_score(cands, fraud_data)

        # 2) finish + total
        total = [0] * 8
        for i, (code, state) in enumerate(states.items()):
            for j in range(8):
                total[j] += state[j]
            print(i, code, state)

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
        ) -> Tuple[int, float, float, List[int], bool]:
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
        for (square, xscore) in zip(CHI_SQUARES[num_digit - 1], CHI_SCORES):
            if chi > square and xscore >= 0.70:
                score = xscore

        # need enough data, magic number = 30, but let's do 25
        enough = total >= 17 * num_digit
        if score and enough and False:
            print(counts)
            print(expects)
        return total, chi, score, counts, enough

    def calculate_score(self, cands: List[Any], data: List[Any]):
        """Calculate the final fraud score for presentation (colors)
        cands: [0, digit, indices, total, int(chi * 100) / 100, score, firsts]
        """
        best = 0
        count = 0
        total = 0
        for item in data:
            number = item[3]
            score = item[5]
            if not score:
                continue

            total += number * score
            count += number
            if score > best and number >= MIN_COUNTS[item[1]]:
                best = score

        score = total / (160 + count) if count else 0
        cands[8] = best
        cands[11] = int(score * 100) / 100

    def collect_candidates(self, dico: Dict[str, Any]) -> Tuple[Any]:
        """Collect candidates: democrat + republican, in that order
        """
        # 1) state votes
        cands = dico.get('candidates') or dico.get('results')
        state_total = [
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
        try:
            json = json.loads(data)
            if isinstance(json, dict):
                races = json.get('races')
                if races:
                    json = races
        except Exception as e:
            self.logger.warning({'status': 'convert_file__json_error', 'error': e, 'filename': filename})
            return

        base, ext = os.path.splitext(filename)
        output = f'{base}-html.json'
        save_json_file(output, json, indent=2, sort=True)

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

    def download_json(self):
        """Download data from a source
        """
        url = DOWNLOADS.get(self.download)
        if not url:
            return
        res = requests.get(url)
        if res.status_code != 200:
            self.logger.error({'status': 'download__error', 'status_code': res.status_code})
            return
        output = os.path.join(DATA_FOLDER, f'2020-president-data.json')
        print(f'downloaded {len(res.text)} bytes to {output}')
        write_text_safe(output, res.text)

    def go(self):
        """Go!
        """
        print(f'Go {self.year}')
        self.analyse_year(self.year)

    def initialise(self):
        """Initialise some structures
        """
        county_states = open_json_file(os.path.join(DATA_FOLDER, 'county_states.json'))

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
