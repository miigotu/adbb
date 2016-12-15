#!/usr/bin/env python
#
# This file is part of adbb.
#
# adbb is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# adbb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with adbb.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import difflib
import gzip
import os
import sys
import tempfile
import time
import xml.etree.ElementTree as etree

if sys.version_info[0] < 3:
    import urllib as local_urllib
    urllib = local_urllib
    urllib.error = local_urllib
    urllib.request = local_urllib
else:
    import urllib
    import urllib.error
    import urllib.request

import adbb.animeobjs
from adbb.errors import AniDBError

_animetitles_url="http://anidb.net/api/animetitles.xml.gz"
iso_639_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "ISO-639-2_utf-8.txt")

xml = None
languages = None


def update_animetitles(only_if_needed=False):
    global xml

    file_name = _animetitles_url.split('/')[-1]
    if os.name == 'posix':
        animetitles_file = os.path.join('/var/tmp', file_name)
    else:
        animetitles_file = os.path.join(tempfile.gettempdir(), file_name)

    tmp_dir = os.path.dirname(animetitles_file)
    if not os.access(tmp_dir, os.W_OK):
        raise AniDBError("Cant get writeable temp path: %s" % tmp_dir)

    if os.path.isfile(animetitles_file):
        stat = os.stat(animetitles_file)

        if only_if_needed and stat.st_mtime > (time.time()-604800): # update after one week
            if xml is None:
                xml = _read_anidb_xml(animetitles_file)
            return

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.%f")
    tmp_file = os.path.join(os.path.dirname(animetitles_file), ".animetitles{}.xml.gz".format(now))

    try:
        with open(tmp_file, "bw") as f:
            res = urllib.request.urlopen(_animetitles_url)
            f.write(res.read())
    except (IOError, urllib.error.URLError) as err:
        adbb.log.error("Failed to fetch animetitles.xml: {}".format(err))
        file_exist = os.path.isfile(animetitles_file)
        if not xml and file_exist:
            xml = _read_anidb_xml(animetitles_file)
        return
    
    if not _verify_animetitles_file(tmp_file):
        adbb.log.error("Failed to verify xml file: {}".format(tmp_file))
        return

    os.rename(tmp_file, animetitles_file)
    tmp_xml = _read_anidb_xml(animetitles_file)
    if tmp_xml:
        xml = tmp_xml
    

def _verify_animetitles_file(path):
    if not os.path.isfile(path):
        return False
    
    try:
        tmp_xml = _read_anidb_xml(path)
    except Exception as e:
        adbb.log.error("Exception when reading xml file: {}".format(e))
        return False

    if len(tmp_xml.findall('anime')) < 8000:
        return False
    
    return True
        

def _read_anidb_xml(filePath):
    return _read_xml_into_etree(filePath)


def _read_xml_into_etree(filePath):
        if not filePath:
            return None
        
        with gzip.open(filePath, "rb") as f:
            data = f.read()

        xmlASetree = etree.fromstring(data)
        return xmlASetree


def _read_language_file():
    global languages
    languages = {}
    with open(iso_639_file, "r") as f:
        for line in f:
            three, tree2, two, eng, fre = line.strip().split('|')
            if two:
                languages[two] = three


def get_lang_code(short):
    if not languages:
        _read_language_file()

    if short in languages:
        return languages[short]
    return None
    

def get_titles(name=None, aid=None, max_results=10, score_for_match=0.6):
    res = []
    
    update_animetitles(only_if_needed=True)

    lastAid = None
    for anime in xml.findall('anime'):
        score=0
        best_title_match=None
        exact_match=None
        if aid and aid == int(anime.get('aid')):
            exact_match=anime.get('aid')

        if name:
            for title in anime.findall('title'):
                if name.lower() in title.text.lower():
                    exact_match=title.text
                diff = difflib.SequenceMatcher(a=name, b=title.text)
                title_score = diff.ratio()
                if title_score > score:
                    score = title_score
                    best_title_match=title.text

        if score > score_for_match or exact_match:
            titles = [
                    adbb.animeobjs.AnimeTitle(
                        x.get('type'),
                        get_lang_code(x.get('{http://www.w3.org/XML/1998/namespace}lang')),
                        x.text) for x in anime.findall('title')]
            res.append((int(anime.get('aid')), titles, score, best_title_match))

    res.sort(key=lambda x: x[2], reverse=True)
    
    # response is a list of tuples in the form:
    #(<aid>, <list of titles>, <score of best title>, <best title>)
    return res[:max_results]

