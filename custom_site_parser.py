import yaml
import re
import os.path
import rfeed
from itertools import chain
import aiohttp
from bs4 import BeautifulSoup

class CustomSafeYamlLoader(yaml.SafeLoader):
	pass

def parse_regex(loader, node):
	return re.compile(loader.construct_scalar(node))

CustomSafeYamlLoader.add_constructor('!re', parse_regex)


class Extraction:
	types_by_name = {}
	
	def __init_subclass__(cls, name):
		cls.types_by_name[name] = cls
	
	def __new__(cls, settings):
		source_type = cls.types_by_name[settings['from']]
		return super().__new__(source_type)
	
	def __init__(self, settings):
		pass # TODO: Regex extraction, etc.
	
	def extract(self, node):
		return self.get_base_text(node)

class AttrExtraction(Extraction, name='attribute'):
	def __init__(self, settings):
		super().__init__(settings)
		self.attribute_name = settings['attribute']
	
	def get_base_text(self, node):
		# TODO: Handle lists like class="a b"
		return node[self.attribute_name]

class ContentsExtraction(Extraction, name='contents'):
	def get_base_text(self, node):
		return node.get_text()


class ItemSource:
	types_by_name = {}
	
	def __init_subclass__(cls, name):
		cls.types_by_name[name] = cls
	
	def __new__(cls, settings):
		source_type = cls.types_by_name[settings['type']]
		return super().__new__(source_type)

class FromElementsSource(ItemSource, name='from_elements'):
	def __init__(self, settings):
		self.parent_selectors = settings.get('parent', ())
		self.element_selector = settings['elements']
		self.extractions = {
			name: Extraction(extr_settings)
			for name, extr_settings
			in settings.get('extractions', {}).items()
		}
		self.item_template = settings['feed_item']
		self.reverse_items = settings.get('reverse_items', False)
	
	def get_items(self, soup):
		
		parent_node = soup
		for sel in self.parent_selectors:
			parent_node = parent_node.find(**sel)
		
		items = []
		for el in parent_node.find_all(**self.element_selector):
			
			extractions = {
				name: extraction.extract(el)
				for name, extraction
				in self.extractions.items()
			}
			
			items.append(rfeed.Item(**{
				k: v.format_map(extractions)
				for k, v in self.item_template.items()
			}))
		
		if self.reverse_items:
			items.reverse()
		
		return items


class SiteParser:
	def __init__(self, name, settings, generator):
		self.name = name
		self.url = settings['source_url']
		self.http_method = settings.get('source_method', 'GET')
		
		self.feed_template = {
			'description': '',
			'link': self.url,
			'generator': generator,
		}
		self.feed_template.update(settings['feed'])
		
		self.item_sources = [
			ItemSource(source)
			for source
			in settings['item_sources']
		]
	
	def parse(self, soup):
		items = chain.from_iterable(
			source.get_items(soup) for source in self.item_sources)
		
		return rfeed.Feed(**self.feed_template, items=items)
	
	async def request_and_parse(self):
		async with aiohttp.request(self.http_method, self.url) as resp:
			if resp.status // 100 != 2:
				raise NotFound(f'The site at {self.url} failed to load')
			html = await resp.content.read()
		
		return self.parse(BeautifulSoup(html, 'html.parser'))


def load_parser(name, file, *, generator):
	settings = yaml.load(file, Loader=CustomSafeYamlLoader)
	return SiteParser(name, settings, generator)


if __name__ == '__main__':
	import asyncio
	
	with open('custom/blastwave.yaml') as file:
		parser = load_parser(file, generator="A")
	
	loop = asyncio.get_event_loop()
	feed = loop.run_until_complete(parser.request_and_parse())
	
	print(feed.rss())