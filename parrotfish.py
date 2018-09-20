from sanic import Sanic
from sanic.response import json, redirect
from sanic.response import text as text_response
from sanic.exceptions import NotFound
from bs4 import BeautifulSoup
import aiohttp
import rfeed
from datetime import datetime

app = Sanic()

has_data_xutime = { 'data-xutime': True }

@app.route('/feed/fanfic/<id:int>')
async def fanfic_feed(request, id):
	story_url = f'https://www.fanfiction.net/s/{id}'
	async with aiohttp.request('GET', story_url) as resp:
		if resp.status != 200:
			raise NotFound(f'No story with ID {id} could be found')
		story_html = await resp.content.read()
	
	soup = BeautifulSoup(story_html, 'html.parser')
	
	header = soup.find(id='profile_top')
	if not header:
		raise NotFound(f'No story with ID {id} could be found')
	
	title = header.find('b')
	author = title.find_next_sibling('a')
	description = author.find_next_sibling('div')
	updated = description.find_next_sibling('span').find('span',
		attrs=has_data_xutime)
	updated_time = datetime.fromtimestamp(
		int(updated['data-xutime']))
	
	chapter_select = soup.find(id='chap_select')
	
	chapters = []
	for option in chapter_select.find_all('option'):
		chap_title = option.find(
			text=True, recursive=False).split('.', 1)[1].strip()
		i = option['value']
		chapters.append(rfeed.Item(
			title = chap_title,
			link = f'{story_url}/{i}',))
	
	chapters.reverse()
	
	return text_response(
		rfeed.Feed(
			title = f'{title.text} by {author.text}',
			link = story_url,
			description = description.text,
			lastBuildDate = updated_time,
			pubDate = updated_time,
			generator = 'Parrotfish v0.1',
			items = chapters).rss(),
		content_type='application/rss+xml; charset=utf-8')

if __name__ == '__main__':
	app.run(
		port=20550) # ASCII for 'PF'
