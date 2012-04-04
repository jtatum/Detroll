Trolls in your channel using a URL shortener to link to objectionable sites?
Tired of blindly clicking on YouTube links and being sent unsuspecting to
the latest by Rebecca Black? Try Detroll!

[After copying the Detroll directory to your bot's plugins directory]
admin: @load Detroll
abot: The operation succeeded.

user: http://www.youtube.com/watch?v=HU2ftCitvyQ
abot: Title: [Shatner Of The Mount by Fall On Your Sword - YouTube]

user: http://infolab.stanford.edu/pub/papers/google.pdf
abot: Content type: [application/pdf] Size: [120.7KB]

The bot will show you if the link was redirected, and what domain it was
redirected to:

user: http://bit.ly/LmvF
abot: [R: www.google.com] Title: [Google]

If the server returns an unusual status code, the bot shows that too:

user: http://bit.ly/ySK2w9
abot: [404 R: youtube.com] Title: [404 Not Found]

This plugin requires the following Python modules:

- BeautifulSoup*
- lxml (optional - improves parsing of title attribute)

* I recommend avoiding BeautifulSoup version 3.1 as it has serious problems
dealing with pages that contain some common JavaScript. If your Linux
distribution includes the 3.1 version of BeautifulSoup, remove it and use
easy_install to install 3.2 or newer.

Todo:
    * Config options to activate/deactivate by channel

It turns out that safely and correctly loading arbitrary links is non-trivial.
This results in bugs. If you find a URL that won't parse properly, file a bug
on github with the problem URL and I'll do my level best to resolve the issue.
