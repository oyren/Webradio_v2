import urllib
try:
    import xml.etree.cElementTree as ETree
except:
    import xml.etree.ElementTree as ETree


class LastFMDownloader(object):
    def __init__(self, album_name, artist_name):
        """ Initializes LastFM Downloader """

        self.LASTFM_API_KEY = "a42ead6d2dcc2938bec2cda08a03b519" # Please use your OWN LastFM API key
        self.LASTFM_URL = "http://ws.audioscrobbler.com/2.0/?method=album.search&album={album_name}&api_key=" + self.LASTFM_API_KEY
        self.album_name = album_name
        self.artist_name = artist_name
        self.url = self.format_url()

    def format_url(self):
        """ Sanitize and format URL for Last FM search """
        return self.LASTFM_URL.format(album_name=self.album_name.encode('utf8'))


    def search_for_image(self):
        """ Use LastFM's API to obtain a URL for the album cover art """

        response = urllib.urlopen(self.url).read() # Send HTTP request to LastFM
        xml_data = ETree.fromstring(response) # Read in XML data

        for element in xml_data.getiterator("album"):
            if (element.find('artist').text.lower() == self.artist_name.lower().encode("utf-8")):
                for elmnt in element.findall('image'):
                    if (elmnt.attrib['size'] == 'extralarge'):
                        url = elmnt.text
                        if url:
                            return url
                        else:
                            return None

if __name__ == "__main__":

    searchFunktion = LastFMDownloader("Unplugged in New York", "Nirvana")
    print(searchFunktion.search_for_image())
