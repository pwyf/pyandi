from collections import OrderedDict, defaultdict
import json
from os.path import join
from os import makedirs, unlink as _unlink
import shutil
import logging
import zipfile

import requests
import unicodecsv as csv


def data(path=None):
    if not path:
        path = join('__pyandicache__', 'registry')
    # downloads from https://andylolz.github.io/iati-data-dump/
    data_url = 'https://www.dropbox.com/s/kkm80yjihyalwes/' + \
               'iati_dump.zip?dl=1'
    shutil.rmtree(path, ignore_errors=True)
    makedirs(path)
    zip_filepath = join(path, 'iati_dump.zip')

    logging.info('Downloading all IATI registry data...')
    request = requests.get(data_url, stream=True)
    with open(zip_filepath, 'wb') as handler:
        shutil.copyfileobj(request.raw, handler)
    logging.info('Unzipping data...')
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(path)
    logging.info('Cleaning up...')
    _unlink(zip_filepath)
    logging.info('Downloading zipfile metadata...')
    meta_filepath = join(path, 'metadata.json')
    meta = 'https://www.dropbox.com/s/6a3wggckhbb9nla/metadata.json?dl=1'
    zip_metadata = requests.get(meta)
    with open(meta_filepath, 'wb') as handler:
        handler.write(zip_metadata.content)


_VERY_OLD_IATI_VERSIONS = ['1.01', '1.02']
_VERY_OLD_CODELISTS_URL = 'http://codelists102.archive.iatistandard.org' + \
                         '/data/codelist.csv'
_VERY_OLD_CODELIST_TMPL = 'http://codelists102.archive.iatistandard.org' + \
                         '/data/codelist/{codelist_name}.csv'

_OLD_IATI_VERSIONS = ['1.03']
_OLD_CODELISTS_URL = 'http://codelists103.archive.iatistandard.org' + \
                    '/data/codelist.json'
_OLD_CODELIST_TMPL = 'http://codelists103.archive.iatistandard.org' + \
                    '/data/codelist/{codelist_name}.csv'

_NEW_CODELISTS_TMPL = 'http://reference.iatistandard.org/{version}/' + \
                     'codelists/downloads/clv2/codelists.json'
_NEW_CODELIST_TMPL = 'http://reference.iatistandard.org/{version}/' + \
                    'codelists/downloads/clv2/json/en/{codelist_name}.json'


def codelists(path=None):
    def get_iati_versions():
        versions_url = 'http://reference.iatistandard.org/codelists/' + \
                       'downloads/clv2/json/en/Version.json'
        versions = [d['code']
                    for d in requests.get(versions_url).json()['data']]
        versions.reverse()
        return versions

    def get_list_of_codelists(version):
        if version in _VERY_OLD_IATI_VERSIONS:
            request = requests.get(_VERY_OLD_CODELISTS_URL)
            list_of_codelists = [x['name'] for x in csv.DictReader(
                [x for x in request.iter_lines()])]
        elif version in _OLD_IATI_VERSIONS:
            j = requests.get(_OLD_CODELISTS_URL).json()
            list_of_codelists = [x['name'] for x in j['codelist']]
        else:
            codelists_url = _NEW_CODELISTS_TMPL.format(
                version=version.replace('.', ''))
            list_of_codelists = requests.get(codelists_url).json()
        return list_of_codelists

    def get_codelist(codelist_name, version):
        if version in _VERY_OLD_IATI_VERSIONS:
            codelist_url = _VERY_OLD_CODELIST_TMPL.format(
                codelist_name=codelist_name)
            request = requests.get(codelist_url)
            codes = list(csv.DictReader(
                [x for x in request.iter_lines()]))
            version_codelist = {'data': codes}
        elif version in _OLD_IATI_VERSIONS:
            codelist_url = _OLD_CODELIST_TMPL.format(
                codelist_name=codelist_name)
            request = requests.get(codelist_url)
            codes = list(csv.DictReader(
                [x for x in request.iter_lines()]))
            version_codelist = {'data': codes}
        else:
            codelist_url = _NEW_CODELIST_TMPL.format(
                codelist_name=codelist_name,
                version=version.replace('.', ''))
            version_codelist = requests.get(codelist_url).json()
        return version_codelist

    if not path:
        path = join('__pyandicache__', 'standard', 'codelists')

    shutil.rmtree(path, ignore_errors=True)
    makedirs(path)

    logging.info('Downloading IATI Standard codelists...')

    codelist_versions_by_name = defaultdict(list)
    for version in get_iati_versions():
        list_of_codelists = get_list_of_codelists(version)

        for codelist_name in list_of_codelists:
            codelist_versions_by_name[codelist_name].append(version)

    with open(join(path, 'codelists.json'), 'w') as handler:
        json.dump(codelist_versions_by_name, handler)

    for codelist_name, versions in codelist_versions_by_name.items():
        codelist = None
        for version in versions:
            version_codelist = get_codelist(codelist_name, version)

            if version_codelist.get('attributes', {}).get('embedded') == '0':
                codelist = version_codelist
                codelist['data'] = OrderedDict(
                    [(x['code'], x) for x in codelist['data']])
                break

            if codelist is None:
                codelist = {
                    'attributes': version_codelist.get('attributes'),
                    'metadata': version_codelist.get('metadata'),
                    'data': OrderedDict(),
                }

            for item in version_codelist['data']:
                if item['code'] not in codelist['data']:
                    item['from'] = version
                    item['until'] = version
                    codelist['data'][item['code']] = item
                else:
                    current_item = codelist['data'][item['code']]
                    if version < current_item['from']:
                        current_item['from'] = version
                    if version > current_item['until']:
                        current_item['until'] = version
                    codelist['data'][item['code']] = current_item

        with open(join(path, codelist_name + '.json'), 'w') as handler:
            json.dump(codelist, handler)


def schemas(path=None):
    if not path:
        path = join('__pyandicache__', 'standard', 'schemas')

    shutil.rmtree(path, ignore_errors=True)
    makedirs(path)

    versions_url = 'http://reference.iatistandard.org/codelists/' + \
                   'downloads/clv2/json/en/Version.json'
    versions = [d['code'] for d in requests.get(versions_url).json()['data']]
    versions.reverse()

    logging.info('Downloading IATI Standard schemas...')
    filenames = ['iati-activities-schema.xsd', 'iati-organisations-schema.xsd',
                 'iati-common.xsd', 'xml.xsd']
    tmpl = 'https://raw.githubusercontent.com/IATI/IATI-Schemas/' + \
           'version-{version}/{filename}'
    for version in versions:
        version_path = version.replace('.', '')
        makedirs(join(path, version_path))
        for filename in filenames:
            url = tmpl.format(version=version, filename=filename)
            request = requests.get(url)
            filepath = join(path, version_path, filename)
            with open(filepath, 'wb') as handler:
                handler.write(request.content)
