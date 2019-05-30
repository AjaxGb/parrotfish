import aiohttp
from datetime import datetime
import re
import html
import rfeed
from parrotfish import generator_name

async def make_feed():
	base_url = 'http://www.bogleech.com/awfulhospital/archive.html'
	async with aiohttp.request('GET', base_url) as resp:
		if resp.status != 200:
			raise NotFound(f'Awful Hospital seems to be down right now')
		story_html = await resp.text()
		last_modified = resp.headers.get('Last-Modified')
		if last_modified:
			last_modified = datetime.strptime(
				last_modified,
				'%a, %d %b %Y %H:%M:%S %Z')
		else:
			last_modified = datetime.now()
	
	# The HTML is so gunked up even BeautifulSoup won't cut it
	# I'm pretty sure Bogleech updates it directly in Notepad
	# May the old gods forgive me
	
	layers = []
	
	for match in re.finditer(r'<a href="(.*?)">(.*?)<br>', story_html):
		link, title = match.group(1, 2)
		title = html.unescape(
			re.sub(r'<.*?>',
				lambda m: '' if m.group() == '</a>' else None,
				title))
		
		layers.append(rfeed.Item(
			title=title,
			link=link))
	
	layers.reverse()
	
	return rfeed.Feed(
			title='Awful Hospital',
			description='Seriously the worst ever.',
			link='http://www.bogleech.com/awfulhospital/',
			lastBuildDate=last_modified,
			pubDate=last_modified,
			generator=generator_name,
			items=layers)

if __name__ == '__main__':
	import asyncio
	
	loop = asyncio.get_event_loop()
	feed = loop.run_until_complete(make_feed())
	print(feed.rss())
