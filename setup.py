from setuptools import setup
from parrotfish import version

setup(
	name='parrotfish',
	version=version,
	description="Scrape beatiful RSS coral from the internet's rocky HTML",
	url='https://github.com/AjaxGb/parrotfish',
	author='Sol Toder',
	author_email='soldevlintoder@gmail.com',
	license='MIT',
	packages=['parrotfish'],
	install_requires=[
		'quart',
		'aiohttp',
		'beautifulsoup4',
		'rfeed',
		'pyyaml',
	],
	include_package_data=True,
	zip_safe=False,
)