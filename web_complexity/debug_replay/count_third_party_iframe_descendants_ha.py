from argparse import ArgumentParser
from collections import defaultdict
from multiprocessing import Pool

import common
import json
import os

def Main():
    results = []
    pool = Pool()
    for d in os.listdir(args.root_dir):
        if 'allmusic' not in d:
            continue

        requests_filename = os.path.join(args.root_dir, d, 'requests.json')
        result = pool.apply_async(GetIframeDescForPage, args=(requests_filename, ))
        results.append((d, result))
    pool.close()
    pool.join()

    for pageurl, r in results:
        first_party, third_party = r.get()
        third_party_desc = sum([ len(v) for _, v in third_party.items() ])
        print('{0} {1}'.format(pageurl, third_party_desc))


def GetIframeDescForPage(requests_filename):
    '''Wrapper for multiprocessing.'''
    requests, main_frame_id = GetRequestsSortOnTime(requests_filename)
    first_party_resources, third_party_breakdown = common.GetFrameBreakdown(requests, main_frame_id)
    for url, resources in third_party_breakdown.items():
        print('iframe: {0} desc: {1}'.format(url, len(resources)))
    return (first_party_resources, third_party_breakdown)


def GetRequestsSortOnTime(requests_filename):
    requests_ts = []
    main_frame_id = None
    with open(requests_filename, 'r') as input_file:
        for l in input_file:
            entry = json.loads(l.strip())
            payload = json.loads(entry['payload'])
            page = entry['page']
            url = entry['url']
            frame_id = payload['_frame_id']
            started_time_ms = common.GetTimestampSinceEpochMs(payload['startedDateTime'])
            referer = common.ExtractRefererFromHAEntry(payload)
            requests_ts.append((url, started_time_ms, frame_id, referer))
            if main_frame_id is None and url == page:
                main_frame_id = (frame_id, referer)
    requests_ts.sort(key=lambda x: (x[2], x[1]))
    for r in requests_ts:
        print(r)
    print(main_frame_id)
    return (requests_ts, main_frame_id)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    args = parser.parse_args()
    Main()
