from sanic import Sanic
from sanic.response import json, redirect
from sanic.response import text as text_response
from sanic.exceptions import NotFound
from bs4 import BeautifulSoup
import aiohttp
import rfeed
from datetime import datetime
from custom_site_parser import load_parser as load_site_parser
from importlib import import_module
import os

GENERATOR_NAME = 'Parrotfish v0.1'
parrotfish_path = os.path.dirname(os.path.realpath(__file__))


print("Loading custom parsers...")

custom_folder = os.path.join(parrotfish_path, 'custom')
custom_parsers = {}

with os.scandir(custom_folder) as it:
	
	for entry in it:
		
		if not entry.is_file():
			continue
		
		name, extension = os.path.splitext(entry.name)
		if extension != '.yaml':
			continue
		
		with open(entry.path) as file:
			try:
				parser = load_site_parser(name, file,
					generator=GENERATOR_NAME)
			except Exception as e:
				print("Failed to load parser ", entry.name)
				print(e)
				continue
		
		custom_parsers[name] = parser

print("Done. Loaded", len(custom_parsers), "custom parser(s).")


app = Sanic()

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
		attrs={ 'data-xutime': True })
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
			generator = GENERATOR_NAME,
			items = chapters).rss(),
		content_type='application/rss+xml; charset=utf-8')

@app.route('/feed/mangarock/manga/<oid:string>')
async def mangarock_manga_feed(request, oid):
	base_url = 'https://api.mangarockhd.com/query/web401/info'
	async with aiohttp.request('GET', base_url, params={'oid': oid}) as resp:
		if resp.status != 200:
			raise NotFound(f'No manga with ID {id} could be found')
		data = await resp.json()
	
	if data.get('code') != 0:
		raise NotFound(f'No manga with ID {id} could be found')
	else:
		data = data.get('data', {})
	
	chapters = [
		rfeed.Item(
			title = c.get('name'),
			link = f'https://mangarock.com/manga/{oid}/chapter/{c["oid"]}',
			# pubDate = datetime.fromtimestamp(c['updatedAt']),
			# Ignore pubDate so that chapters will be displayed
			# in the right order.
			)
		for c in data.get('chapters', ())]
	
	chapters.reverse()
	
	updated_time = datetime.fromtimestamp(data['last_update'])
	
	return text_response(
		rfeed.Feed(
			title = data.get('name'),
			link = f'https://mangarock.com/manga/{oid}',
			description = data.get('description'),
			lastBuildDate = updated_time,
			pubDate = updated_time,
			generator = GENERATOR_NAME,
			items = chapters).rss(),
		content_type='application/rss+xml; charset=utf-8')

@app.route('/feed/custom/<name>')
async def custom_feed(request, name):
	parser = custom_parsers.get(name)
	if parser:
		feed = await parser.request_and_parse()
	else:
		try:
			parser = import_module(
				f'custom.{name.replace("-", "_")}')
		except ModuleNotFoundError:
			raise NotFound(f'No custom parser with ID `{name}` could be found')
		
		feed = await parser.make_feed(request, GENERATOR_NAME)
	
	return text_response(feed.rss(),
		content_type='application/rss+xml; charset=utf-8')

if __name__ == '__main__':
	app.run(
		port=20550) # ASCII for 'PF'
