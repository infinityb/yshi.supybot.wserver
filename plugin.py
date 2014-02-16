###
# Copyright (c) 2013, Stacey Ell
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

#import supybot.utils as utils
from supybot.commands import wrap
#import supybot.plugins as plugins
#import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('PrinterStatus')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

from urlparse import urlparse, urljoin
from collections import namedtuple
import requests


ServerRecord = namedtuple('ServerRecord', ['host', 'wserver'])
RedirectRecord = namedtuple('RedirectRecord', ['host', 'destination'])
TooManyRedirects = namedtuple('TooManyRedirects', [])


class CouldNotConnect(Exception):
    pass


def wserver(place, max_redirects=3):
    for _ in xrange(max_redirects):
        uri = urlparse(place)
        try:
            response = requests.get(place, allow_redirects=False, timeout=1.2)
        except requests.ConnectionError:
            yield CouldNotConnect(uri.netloc)
            break
        except requests.Timeout as e:
            yield CouldNotConnect(uri.netloc, e)
            break
        server = None
        if 'server' in response.headers:
            server = response.headers['server']
        yield ServerRecord(uri.netloc, server)
        if response.status_code in [301, 302]:
            newuri = urlparse(response.headers['location'])
            if not newuri.netloc:
                break
            place = urljoin(place, response.headers['location'])
            dest = '{0.scheme}://{0.netloc}'.format(urlparse(place))
            yield RedirectRecord(uri.netloc, dest)
        else:
            break
    else:
        yield TooManyRedirects()


class WServer(callbacks.Plugin):
    """Add the help for "@plugin help WServer" here
    This should describe *how* to use this plugin."""
    threaded = True

    def wserver(self, irc, msg, args, server_uri):
        """<server>

        Finds out what webserver is running"""
        if server_uri.find('://') < 0:
            server_uri = 'http://{}'.format(server_uri)
        uri = urlparse(server_uri)
        result_recs = wserver(server_uri)
        for result_rec in result_recs:
            fmt = None
            if isinstance(result_rec, ServerRecord):
                fmt = "{0.host} is running {0.wserver}"
                if result_rec.wserver is None:
                    fmt = u"couldn't tell what {0.host} is running"
            elif isinstance(result_rec, RedirectRecord):
                fmt = "{0.host} redirects to {0.destination}"
            elif isinstance(result_rec, TooManyRedirects):
                fmt = "Too many redirects."
            elif isinstance(result_rec, CouldNotConnect):
                fmt = "couldn't connect to {0[0]} :("
                if len(args) > 1:
                    fmt = "couldn't connect to {0[0]} ({0[1]}) :("
            irc.reply(fmt.format(result_rec), prefixNick=False)
    wserver = wrap(wserver, ['text'])

Class = WServer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
