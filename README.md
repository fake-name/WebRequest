### WebRequest

Like the `requests` library, but shittier.

Provides convenience functions for writing web-scrapers and other web-interactive
things. Built-in support for working through CloudFlare's garbage JS browser
checks without any intervention, as well as some other [garbage web-application 
firewall shits](https://sucuri.net/website-firewall/) that seem intent on 
breaking the internet.

Built-in user-agent randomization. Support for fetching rendered content via 
headless chrome.

Default support for compressed transfers. 

Basically, the overall goal is to have a simple library that acts *as much as 
possible* like a "real" browser. Ideally, it should be indistinguishable from 
an actual browser from the perspective of the remote HTTP(s) server.

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



