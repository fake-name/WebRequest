### WebRequest  [![Build Status](https://travis-ci.org/fake-name/WebRequest.svg?branch=master)](https://travis-ci.org/fake-name/WebRequest)[![Coverage Status](https://img.shields.io/coveralls/fake-name/WebRequest.svg)](https://coveralls.io/r/fake-name/WebRequest)

Like the `requests` library, but less good.

Provides convenience functions for writing web-scrapers and other web-interactive
things. Built-in support for working through CloudFlare's garbage JS browser
checks without any intervention, as well as some other [garbage web-application 
firewalls](https://sucuri.net/website-firewall/) that seem intent on 
breaking the internet.

Built-in user-agent randomization. Support for fetching rendered content via 
headless chrome. Built on top of my [ChromeController](https://github.com/fake-name/ChromeController) 
project, so it can avoid some of the [spectacularly stupid design 
decisions](https://github.com/seleniumhq/selenium-google-code-issue-archive/issues/141) in selenium.

Default support for compressed transfers. 

Basically, the overall goal is to have a simple library that acts *as much as 
possible* like a "real" browser. Ideally, it should be indistinguishable from 
an actual browser from the perspective of the remote HTTP(s) server.

Other useful bits:

API wrappers for 2captcha.com and anticaptcha.com which include automatic local 
reverse-proxy spinup for reflecting recaptcha requests through your local host 
address. This involves spinning up a transient SOCKS5 proxy, setting up a limited 
duration port-forward (10 minutes, via UPnP), and actual synchronous captcha 
solving calls.

The proxy setup/UPnP setup functions are generic enough that they should be 
useful for any captcha-solver-related tasks. If you'd like support for another 
solver site (and are willing to throw a few bucks of credit on a solver site to 
me), I can probably add that other site too.


Q: Why  
A: Because I started writing horrible web-scraper things in 2008, when the 
    requests library wasn't really a thing.  

Q: Why *still*, then?  
A: Anger and spite, mostly.  

Q: No, really, *why*  
A: Ok, Because I want to download the internet, and idiots post stuff, and then
    try to "protect" it from scraping with stupid jerberscript bullshit.

## Note: If your non-interactive webite requires me to execute javascript to view it, FUCK YOU, you are a horrible person who is actively ruining the internet.

License:
WTFPL



