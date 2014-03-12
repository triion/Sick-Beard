# Author: triion <triion@gmail.com>
# Based on mediabrowser.py by Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import os
import re
import traceback

import sickbeard

import generic

from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek
from lib.tvdb_api import tvdb_api, tvdb_exceptions
from sickbeard.exceptions import ex

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree


class Mede8erMetadata(generic.GenericMetadata):
    """
    Metadata generation class for Mede8er (tested on X2 with V3 Firmware).

    The following file structure is used:

    show_root/series.xml                       (show metadata)
    show_root/folder.jpg                       (poster)
    show_root/fanart.jpg                       (fanart)
    show_root/Season ##/folder.jpg             (season thumb)
    show_root/Season ##/filename.ext           (*)
    show_root/Season ##/filename.xml           (episode metadata)
    show_root/Season ##/filename.jpg           (episode thumb)
    """

    def __init__(self,
                 show_metadata=False,
                 episode_metadata=False,
                 fanart=False,
                 poster=False,
                 banner=False,
                 episode_thumbnails=False,
                 season_posters=False,
                 season_banners=False,
                 season_all_poster=False,
                 season_all_banner=False):

        generic.GenericMetadata.__init__(self,
                                         show_metadata,
                                         episode_metadata,
                                         fanart,
                                         poster,
                                         banner,
                                         episode_thumbnails,
                                         season_posters,
                                         season_banners,
                                         season_all_poster,
                                         season_all_banner)

        self.name = "Mede8er"

        self._ep_nfo_extension = "xml"
        self._show_metadata_filename = "series.xml"

        self.fanart_name = "fanart.jpg"
        self.poster_name = "folder.jpg"

        # web-ui metadata template
        self.eg_show_metadata = "series.xml"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.xml"
        self.eg_fanart = "fanart.jpg"
        self.eg_poster = "folder.jpg"
        self.eg_banner = "banner.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.jpg"
        self.eg_season_posters = "Season##\\folder.jpg"
        self.eg_season_banners = "Season##\\banner.jpg"
        self.eg_season_all_poster = "<i>not supported</i>"
        self.eg_season_all_banner = "<i>not supported</i>"

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        # while show metadata is generated, it is not supported for our lookup
        return (None, None)

    def create_season_all_poster(self, show_obj):
        pass

    def create_season_all_banner(self, show_obj):
        pass

    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/metadata/episode.xml path for Mede8er
        episode metadata files

        ep_obj: a TVEpisode object to get the path for
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            xml_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), '')
            xml_file_path = ek.ek(os.path.join, metadata_dir_name, xml_file_name)
        else:
            logger.log(u"Episode location doesn't exist: " + str(ep_obj.location), logger.DEBUG)
            return ''

        return xml_file_path

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns a full show dir/episode.jpg path for Mede8er
        episode thumbs.

        ep_obj: a TVEpisode object to get the path from
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), 'jpg')
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), '')
            tbn_file_path = ek.ek(os.path.join, metadata_dir_name, tbn_file_name)
        else:
            return None

        return tbn_file_path

    def get_season_poster_path(self, show_obj, season):
        """
        Season thumbs for Mede8er go in Show Dir/Season X/folder.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in ek.ek(os.listdir, show_obj.location) if ek.ek(os.path.isdir, ek.ek(os.path.join, show_obj.location, x))]

        season_dir_regex = '^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            if season == 0 and cur_dir == "Specials":
                season_dir = cur_dir
                break

            match = re.match(season_dir_regex, cur_dir, re.I)
            if not match:
                continue

            cur_season = int(match.group(1))

            if cur_season == season:
                season_dir = cur_dir
                break

        if not season_dir:
            logger.log(u"Unable to find a season dir for season " + str(season), logger.DEBUG)
            return None

        logger.log(u"Using " + str(season_dir) + "/folder.jpg as season dir for season " + str(season), logger.DEBUG)

        return ek.ek(os.path.join, show_obj.location, season_dir, 'folder.jpg')

    def get_season_banner_path(self, show_obj, season):
        """
        Season thumbs for Mede8er go in Show Dir/Season X/banner.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in ek.ek(os.listdir, show_obj.location) if ek.ek(os.path.isdir, ek.ek(os.path.join, show_obj.location, x))]

        season_dir_regex = '^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            if season == 0 and cur_dir == "Specials":
                season_dir = cur_dir
                break

            match = re.match(season_dir_regex, cur_dir, re.I)
            if not match:
                continue

            cur_season = int(match.group(1))

            if cur_season == season:
                season_dir = cur_dir
                break

        if not season_dir:
            logger.log(u"Unable to find a season dir for season " + str(season), logger.DEBUG)
            return None

        logger.log(u"Using " + str(season_dir) + "/banner.jpg as season dir for season " + str(season), logger.DEBUG)

        return ek.ek(os.path.join, show_obj.location, season_dir, 'banner.jpg')

    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for a Mede8er-style series.xml
        returns the resulting data object.

        show_obj: a TVShow instance to create the XML-NFO for
        """

        logger.log("Starting Mede8er _show_data method", logger.MESSAGE)
        
        tvdb_lang = show_obj.lang
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if tvdb_lang and not tvdb_lang == 'en':
            ltvdb_api_parms['language'] = tvdb_lang

        t = tvdb_api.Tvdb(banners=True, actors=True, **ltvdb_api_parms)

        rootNode = etree.Element("details")
        movie_node = etree.SubElement(rootNode, "movie")
        movie_node.attrib["isExtra"] = "false"
        movie_node.attrib["isSet"] = "false"
        movie_node.attrib["isTV"] = "true"

        try:
            myShow = t[int(show_obj.tvdbid)]
        except tvdb_exceptions.tvdb_shownotfound:
            logger.log(u"Unable to find show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            raise

        except tvdb_exceptions.tvdb_error:
            logger.log(u"TVDB is down, can't use its data to make the XML", logger.ERROR)
            raise

        # check for title and id
        try:
            if myShow['seriesname'] == None or myShow['seriesname'] == "" or myShow['id'] == None or myShow['id'] == "":
                logger.log(u"Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
                return False
        except tvdb_exceptions.tvdb_attributenotfound:
            logger.log(u"Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            return False

        title = etree.SubElement(movie_node, "title")
        if myShow["seriesname"] != None:
            title.text = myShow["seriesname"]
        
        tvdbid = etree.SubElement(movie_node, "tvdbid")
        if myShow['id'] != None:
            tvdbid.text = myShow['id']

        imdbid = etree.SubElement(movie_node, "id")
        imdbid.attrib["moviedb"] = "imdb"
        if myShow["imdb_id"] != None:
            imdbid.text = myShow["imdb_id"]

        zap2id = etree.SubElement(movie_node, "id")
        zap2id.attrib["moviedb"] = "zap2it"
        if myShow["zap2it_id"] != None:
            zap2id.text = myShow["zap2it_id"]

        premiered = etree.SubElement(movie_node, "premiered")
        if myShow["firstaired"] != None:
            premiered.text = myShow["firstaired"]

        rating = etree.SubElement(movie_node, "rating")
        if myShow["rating"] != None:
            rating.text = str(int(float(myShow["rating"])*10))

        ratingcount = etree.SubElement(movie_node, "ratingcount")
        if myShow["ratingcount"] != None:
            ratingcount.text = myShow["ratingcount"]

        Status = etree.SubElement(movie_node, "status")
        if myShow['status'] != None:
            Status.text = myShow['status']

        Network = etree.SubElement(movie_node, "network")
        if myShow['network'] != None:
            Network.text = myShow['network']

        Runtime = etree.SubElement(movie_node, "runtime")
        if myShow["runtime"] != None:
            Runtime.text = myShow["runtime"]

        Airs_Time = etree.SubElement(movie_node, "Airs_Time")
        if myShow['airs_time'] != None:
            Airs_Time.text = myShow['airs_time']

        Airs_DayOfWeek = etree.SubElement(movie_node, "Airs_DayOfWeek")
        if myShow['airs_dayofweek'] != None:
            Airs_DayOfWeek.text = myShow['airs_dayofweek']

        MPAARating = etree.SubElement(movie_node, "mpaa")
        if myShow['contentrating'] != None:
            MPAARating.text = myShow['contentrating']

        Plot = etree.SubElement(movie_node, "plot")
        if myShow['overview'] != None:
            Plot.text = myShow['overview']

        ProductionYear = etree.SubElement(movie_node, "year")
        if myShow['firstaired'] != None:
            try:
                year_text = str(datetime.datetime.strptime(myShow['firstaired'], '%Y-%m-%d').year)
                if year_text:
                    ProductionYear.text = year_text
            except:
                pass

        Genres = etree.SubElement(movie_node, "genres")
        if myShow["genre"] != None:
            for genre in myShow['genre'].split('|'):
                if genre and genre.strip():
                    cur_genre = etree.SubElement(Genres, "genre")
                    cur_genre.text = genre.strip()

        Genre = etree.SubElement(movie_node, "genre")
        if myShow["genre"] != None:
            Genre.text = "|".join([x.strip() for x in myShow["genre"].split('|') if x and x.strip()])

        logger.log("Meantime xml: " + etree.tostring(rootNode), logger.DEBUG)

        cast = etree.SubElement(movie_node, "cast")
        if myShow["_actors"] != None:
            for actor in myShow['_actors']:
                cast_actor = etree.SubElement(cast, "actor")
                cast_actor.text = actor['name']

        try:
            seasons_container = []
            image_node = etree.SubElement(movie_node, "image")
            if myShow["_banners"] != None:
                for banner in myShow['_banners']:
                    logger.info("BANNER INFO: "+str(banner))
                    if banner['season'] != None:
                        seasons_container[int(banner["season"])].append(banner["_bannerpath"])
                    else:
                        type = banner["BannerType"]
                        if banner["BannerType"] == "series":
                            type = "banner"
                        image = etree.SubElement(image_node, type)
                        image.text = banner["BannerPath"]

            seasons = etree.SubElement(movie_node, "seasons")
            for i in len(seasons_container):
                season = etree.SubElement(seasons, "season")
                season.attrib["number"] = i
                for j in len(seasons_container[i]):
                    season_poster = etree.SubElement(season, "poster")
                    season_poster.text = seasons_container[i][j]
        except Exception, e:
            logger.log("INFO SEASON BANNERS : " + traceback.format_exc(), logger.ERROR)
            
        
        
        helpers.indentXML(rootNode)
        
        logger.log(u"Sending series-data: " + etree.tostring(rootNode), logger.DEBUG)

        data = etree.ElementTree(rootNode)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser style episode.xml
        and returns the resulting data object.

        show_obj: a TVShow instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.relatedEps

        persons_dict = {}
        persons_dict['Director'] = []
        persons_dict['GuestStar'] = []
        persons_dict['Writer'] = []

        tvdb_lang = ep_obj.show.lang

        try:
            # There's gotta be a better way of doing this but we don't wanna
            # change the language value elsewhere
            ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

            if tvdb_lang and not tvdb_lang == 'en':
                ltvdb_api_parms['language'] = tvdb_lang

            t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
            myShow = t[ep_obj.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(e.message)
        except tvdb_exceptions.tvdb_error, e:
            logger.log(u"Unable to connect to TVDB while creating meta files - skipping - " + ex(e), logger.ERROR)
            return False

        rootNode = etree.Element("Item")

        # write an MediaBrowser XML containing info for all matching episodes
        for curEpToWrite in eps_to_write:

            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log(u"Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None

            if curEpToWrite == ep_obj:
                # root (or single) episode

                # default to today's date for specials if firstaired is not set
                if myEp['firstaired'] == None and ep_obj.season == 0:
                    myEp['firstaired'] = str(datetime.date.fromordinal(1))

                if myEp['episodename'] == None or myEp['firstaired'] == None:
                    return None

                episode = rootNode

                EpisodeName = etree.SubElement(episode, "EpisodeName")
                if curEpToWrite.name != None:
                    EpisodeName.text = curEpToWrite.name
                else:
                    EpisodeName.text = ""

                EpisodeNumber = etree.SubElement(episode, "EpisodeNumber")
                EpisodeNumber.text = str(ep_obj.episode)

                if ep_obj.relatedEps:
                    EpisodeNumberEnd = etree.SubElement(episode, "EpisodeNumberEnd")
                    EpisodeNumberEnd.text = str(curEpToWrite.episode)

                SeasonNumber = etree.SubElement(episode, "SeasonNumber")
                SeasonNumber.text = str(curEpToWrite.season)

                if not ep_obj.relatedEps:
                    absolute_number = etree.SubElement(episode, "absolute_number")
                    absolute_number.text = myEp['absolute_number']

                FirstAired = etree.SubElement(episode, "FirstAired")
                if curEpToWrite.airdate != datetime.date.fromordinal(1):
                    FirstAired.text = str(curEpToWrite.airdate)
                else:
                    FirstAired.text = ""

                MetadataType = etree.SubElement(episode, "Type")
                MetadataType.text = "Episode"

                Overview = etree.SubElement(episode, "Overview")
                if curEpToWrite.description != None:
                    Overview.text = curEpToWrite.description
                else:
                    Overview.text = ""

                if not ep_obj.relatedEps:
                    Rating = etree.SubElement(episode, "Rating")
                    rating_text = myEp['rating']
                    if rating_text != None:
                        Rating.text = rating_text

                    IMDB_ID = etree.SubElement(episode, "IMDB_ID")
                    IMDB = etree.SubElement(episode, "IMDB")
                    IMDbId = etree.SubElement(episode, "IMDbId")
                    if myShow['imdb_id'] != None:
                        IMDB_ID.text = myShow['imdb_id']
                        IMDB.text = myShow['imdb_id']
                        IMDbId.text = myShow['imdb_id']

                TvDbId = etree.SubElement(episode, "TvDbId")
                TvDbId.text = str(curEpToWrite.tvdbid)

                Persons = etree.SubElement(episode, "Persons")

                Language = etree.SubElement(episode, "Language")
                Language.text = myEp['language']

                thumb = etree.SubElement(episode, "filename")
                # TODO: See what this is needed for.. if its still needed
                # just write this to the NFO regardless of whether it actually exists or not
                # note: renaming files after nfo generation will break this, tough luck
                thumb_text = self.get_episode_thumb_path(ep_obj)
                if thumb_text:
                    thumb.text = thumb_text

            else:
                # append data from (if any) related episodes
                EpisodeNumberEnd.text = str(curEpToWrite.episode)

                if curEpToWrite.name:
                    if not EpisodeName.text:
                        EpisodeName.text = curEpToWrite.name
                    else:
                        EpisodeName.text = EpisodeName.text + ", " + curEpToWrite.name

                if curEpToWrite.description:
                    if not Overview.text:
                        Overview.text = curEpToWrite.description
                    else:
                        Overview.text = Overview.text + "\r" + curEpToWrite.description

            # collect all directors, guest stars and writers
            if myEp['director']:
                persons_dict['Director'] += [x.strip() for x in myEp['director'].split('|') if x and x.strip()]
            if myEp['gueststars']:
                persons_dict['GuestStar'] += [x.strip() for x in myEp['gueststars'].split('|') if x and x.strip()]
            if myEp['writer']:
                persons_dict['Writer'] += [x.strip() for x in myEp['writer'].split('|') if x and x.strip()]

        # fill in Persons section with collected directors, guest starts and writers
        for person_type, names in persons_dict.iteritems():
            # remove doubles
            names = list(set(names))
            for cur_name in names:
                Person = etree.SubElement(Persons, "Person")
                cur_person_name = etree.SubElement(Person, "Name")
                cur_person_name.text = cur_name
                cur_person_type = etree.SubElement(Person, "Type")
                cur_person_type.text = person_type

        helpers.indentXML(rootNode)
        data = etree.ElementTree(rootNode)

        return data


# present a standard "interface" from the module
metadata_class = Mede8erMetadata
