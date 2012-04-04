###
# Copyright (c) 2012, James Tatum
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

import re
import urllib2
import urlparse
from BeautifulSoup import BeautifulSoup
try:
    import lxml.html
except ImportError:
    pass

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


# Control characters to skip from HTML prints
CONTROL_CHARS = dict.fromkeys(range(32))
# Maximum size of page or file to open
MAXSIZE = 100*1024
# Maximum number of meta http-equiv refresh redirects to unspool
MAX_HTML_REDIRECTS = 3
# Maximum time for meta http-equiv redirects to be considered redirects,
# rather than just periodic refreshes
MAX_HTML_REDIRECT_TIME = 10
# User agent to spoof
USERAGENT = ('Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; '
             'Win64; x64; Trident/5.0')
# Encoding for IRC output
ENCODING = 'utf8'


class Detroll(callbacks.Plugin):
    """When loaded, this plugin will display some information about URLs
       entered into any channel where the plugin is enabled.
    """
    threaded = True


    def clean(self, msg):
        cleaned = msg.translate(CONTROL_CHARS).strip()
        return re.sub(r'\s+', ' ', cleaned)


    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        channel = msg.args[0]
        if irc.isChannel(channel):
            if ircmsgs.isAction(msg):
                text = ircmsgs.unAction(msg)
            else:
                text = msg.args[1]
            for url in utils.web.urlRe.findall(text):
                self.fetch_url(irc, channel, url)

    def fetch_url(self, irc, channel, url):
        bold = ircutils.bold

        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', USERAGENT)]
        orig_url = url
        for iteration in xrange(MAX_HTML_REDIRECTS):
            # Split fragment from URL due to python bug 11703
            url = urlparse.urlunsplit(urlparse.urlsplit(url)[0:4]+('',))
            try:
                response = opener.open(url)
            except urllib2.HTTPError, e:
                # This is raised due to an unusual status code. Often, it's
                # raised in conjunction with some html, so let's ignore and
                # try to parse it anyhow.
                response = e
            except urllib2.URLError, e:
                reply = 'Error opening URL: [{0}]'.format(bold(e.reason))
                irc.queueMsg(ircmsgs.privmsg(channel, reply))
                return
            html = response.read(MAXSIZE)
            contenttype = response.info().getheader('Content-Type')
            if 'text/html' in contenttype:
                # Scrub potentially malformed HTML with lxml first
                try:
                    html = lxml.html.tostring(lxml.html.fromstring(html))
                except NameError:
                    # lxml isn't installed, just try the html as is
                    pass
                # Here's where we check to see if this is a meta tag redirect
                # urllib2 does 301/302 redirects but not meta tag ones.
                new_url = self.meta_redirect(html)
                if new_url:
                    url = new_url
                    continue
            reply = self.parse(orig_url, response, html)
            irc.queueMsg(ircmsgs.privmsg(channel, reply))
            return
        reply = 'Error opening URL: [{0}]'.format(bold('Too many redirects'))
        irc.queueMsg(ircmsgs.privmsg(channel, reply))

    def parse(self, url, response, html):
        code = response.code
        finalurl = response.url
        contenttype = response.info().getheader('Content-Type')
        size = self.sizeof_fmt(response.info().getheader('Content-Length'))
        options = {}
        charset = contenttype.split('charset=')
        if len(charset) == 2:
            options['fromEncoding'] = charset[-1]

        statusinfo = []
        statusstring = ''
        extradata = []
        extradatastring = ''

        bold = ircutils.bold

        if code != 200:
            statusinfo.append(str(code))

        if url != finalurl:
            finalurl = urlparse.urlparse(finalurl).hostname
            statusinfo.append('R: {0}'.format(finalurl))

        if statusinfo:
            statusstring = '[{0}] '.format(bold(' '.join(statusinfo)))

        if 'text/html' in contenttype:
            soup = BeautifulSoup(html,
                                 convertEntities=BeautifulSoup.HTML_ENTITIES,
                                 **options)
            try:
                title = self.clean(soup.first('title').string)
            except AttributeError:
                title = 'Error reading title'

            reply = '{0}Title: [{1}]'.format(statusstring,
                                             bold(title.encode(ENCODING)))
        else:
            if size:
                extradata.append('Size: [{0}]'.format(bold(size)))

            if extradata:
                extradatastring = ' '.join(extradata)
            reply = '{0}Content type: [{1}] {2}'.format(statusstring,
                                                        bold(contenttype),
                                                        extradatastring)

        return reply

    def meta_redirect(self, content):
        soup  = BeautifulSoup(content)

        result=soup.find('meta',
                         attrs={'http-equiv':re.compile('^refresh$', re.I)})
        if result:
            try:
                wait,text=result['content'].split(';')
            except ValueError:
                # Tag like <meta http-equiv="refresh" content="86400" />
                return None
            if int(wait) <= MAX_HTML_REDIRECT_TIME:
                if text.lower().startswith('url='):
                    url=text[4:]
                    return url
        return None

    def sizeof_fmt(self, num):
        if num is None:
            return 'No size'
        num = int(num)
        for x in ['bytes','KB','MB','GB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'TB')


Class = Detroll


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
