from quart import Quart, Response, jsonify
from bs4 import BeautifulSoup
import aiohttp
import rfeed
from datetime import datetime
from parrotfish import generator_name
from parrotfish.custom import load_yaml_parser
from importlib import import_module
import os

app = Quart(__name__)

custom_yaml_parsers = {}

def text_response(text):
	return Response(text, mimetype='text/plain; charset=utf-8')

def rss_response(feed):
	return Response(feed.rss(), mimetype='application/rss+xml; charset=utf-8')

@app.route('/feed/fanfic/<int:id>')
async def fanfic_feed(id):
	story_url = f'https://www.fanfiction.net/s/{id}'
	async with aiohttp.request('GET', story_url) as resp:
		if resp.status != 200:
			return text_response(f'No story with ID {id} could be found'), 404
		story_html = await resp.content.read()
	
	soup = BeautifulSoup(story_html, 'html.parser')
	
	header = soup.find(id='profile_top')
	if not header:
		return text_response(f'No story with ID {id} could be found'), 404
	
	title = header.find('b')
	author = title.find_next_sibling('a')
	description = author.find_next_sibling('div')
	updated = description.find_next_sibling('span').find('span',
		attrs={ 'data-xutime': True })
	updated_time = datetime.fromtimestamp(
		int(updated['data-xutime']))
	
	chapter_select = soup.find(id='chap_select')
	if not chapter_select:
		return text_response(f'No story with ID {id} could be found'), 404
	
	chapters = []
	for option in chapter_select.find_all('option'):
		chap_title = option.find(
			text=True, recursive=False).split('.', 1)[1].strip()
		i = option['value']
		chapters.append(rfeed.Item(
			title = chap_title,
			link = f'{story_url}/{i}',))
	
	chapters.reverse()
	
	return rss_response(rfeed.Feed(
		title=f'{title.text} by {author.text}',
		link=story_url,
		description=description.text,
		lastBuildDate=updated_time,
		pubDate=updated_time,
		generator=generator_name,
		items=chapters))

@app.route('/feed/mangarock/manga/<string:oid>')
async def mangarock_manga_feed(oid):
	base_url = 'https://api.mangarockhd.com/query/web401/info'
	async with aiohttp.request('GET', base_url, params={'oid': oid}) as resp:
		if resp.status != 200:
			return text_response(f'No manga with ID {id} could be found'), 404
		data = await resp.json()
	
	if data.get('code') != 0:
		return text_response(f'No manga with ID {id} could be found'), 404
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
	
	return rss_response(rfeed.Feed(
		title=data.get('name'),
		link=f'https://mangarock.com/manga/{oid}',
		description=data.get('description'),
		lastBuildDate=updated_time,
		pubDate=updated_time,
		generator=generator_name,
		items=chapters))

@app.route('/feed/custom/<string:name>')
async def custom_feed(name):
	parser = custom_yaml_parsers.get(name)
	if not parser:
		# Check for a Python parser
		try:
			parser = import_module(
				f'parrotfish.custom.{name.replace("-", "_")}')
		except ModuleNotFoundError:
			return text_response(f'No custom parser with ID `{name}` could be found'), 404
	
	feed = await parser.make_feed()
	return rss_response(feed)

def run_server(port=20550): # ASCII for 'PF'
	print()
	print(f'Welcome to {generator_name}!')
	print()
	print('Loading custom YAML parsers...')
	
	parrotfish_path = os.path.dirname(os.path.realpath(__file__))
	custom_folder = os.path.join(parrotfish_path, 'custom')
	
	with os.scandir(custom_folder) as it:
		
		for entry in it:
			
			if not entry.is_file():
				continue
			
			name, extension = os.path.splitext(entry.name)
			if extension != '.yaml':
				continue
			
			with open(entry.path) as file:
				try:
					parser = load_yaml_parser(name, file,
						generator=generator_name)
				except Exception as e:
					print('Failed to load parser ', entry.name)
					print(e)
					continue
			
			custom_yaml_parsers[name] = parser
	
	print('Done. Loaded', len(custom_yaml_parsers), 'custom parser(s).')
	print()

	app.run(port=port)
