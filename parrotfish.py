from flask import Flask, Response
from bs4 import BeautifulSoup
import requests
import rfeed
from datetime import datetime

app = Flask(__name__)

has_data_xutime = { 'data-xutime': True }

@app.route('/feed/fanfic/<int:id>')
def fanfic_feed(id):
	story_url = f'https://www.fanfiction.net/s/{id}'
	
	resp = requests.get(story_url)
	if resp.status_code != 200:
		return f'No story with ID {id} could be found', 404
	
	soup = BeautifulSoup(resp.text, 'html.parser')
	
	header = soup.find(id='profile_top')
	if not header:
		return f'No story with ID {id} could be found', 404
	
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
	
	return Response(
		rfeed.Feed(
			title = f'{title.text} by {author.text}',
			link = story_url,
			description = description.text,
			lastBuildDate = updated_time,
			pubDate = updated_time,
			generator = 'Parrotfish v0.1',
			items = chapters).rss(),
		mimetype='application/rss+xml')

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8000)