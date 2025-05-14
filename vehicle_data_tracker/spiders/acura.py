"""
Handles the scraping and processing of data from the Acura website.

Author: Tyler Jaafari

Version: 1.4
	1.4 - Rewrote acura.py
"""
import pathlib

import scrapy
import json
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *


class AcuraSpider(scrapy.Spider):
	name = 'acura'
	allowed_domains = ['www.acura.com']
	start_urls = ['https://www.acura.com/']

	output_format = 'csv'
	output_file = 'individual_outputs/' + name + '_output.' + output_format

	custom_settings = {
		# 'FEEDS': {
		#     output_file: {
		#         'format': output_format,
		#         'overwrite': True,
		#         'fields': STANDARD_FIELDS,
		#     }
		# },
		'ITEM_PIPELINES': {
			'vehicle_data_tracker.pipelines.FormatPipeline': 300,
			'vehicle_data_tracker.pipelines.DuplicatePipeline': 400,
		}
	}

	def parse(self, response, **kwargs):
		"""
		Iterates through each vehicle card in the dropdown menu, getting the model and year from the JSON in the
		data-tracking attribute (it contains single quotes which must be replaced before passing to json.loads).
		Then, follows each link.

		:param response:
		:param kwargs:
		:return: an iterable of Requests
		"""
		for vehicleCard in response.xpath('//div[contains(@class, "vehicles")]//a[@data-tracking]'):
			modelData = json.loads(vehicleCard.attrib['data-tracking'].replace("\'", "\""))
			modelLink = vehicleCard.attrib['href']
			modelName = modelData['Model']['model_name'].upper()
			modelYear = modelData['Model']['model_year']
			modelBasePrice = ''.join(vehicleCard.xpath('.//span[contains(@class, "price")]//text()').getall())
			args = {'model': modelName, 'year': modelYear, 'price': modelBasePrice}
			yield response.follow(url=modelLink, callback=self.parse_models, cb_kwargs=args)

	def parse_models(self, response, **kwargs):
		"""
		Find the options listbox at the top of the page, then use that to find which years are available. Follow each
		link, with callback=parse_trims and dont_filter=True, passing in the year found in the text to cb_kwargs.

		If there is no options listbox, call parse_trims with the current url.

		:param response: an HTML document
		:param kwargs: should contain model, year, and base price
		:return: an iterable of Requests
		"""
		if response.xpath('//div[@role="listbox"]').get() is not None:
			for option in response.xpath('//div[@role="listbox"]/a'):
				args = kwargs
				args['year'] = option.xpath('text()').get()
				modelLink = option.attrib['href']
				yield response.follow(url=modelLink, callback=self.parse_trims, cb_kwargs=args, dont_filter=True)
		else:
			yield response.follow(url=response.url, callback=self.parse_trims, cb_kwargs=kwargs, dont_filter=True)

	def parse_trims(self, response, **kwargs):
		"""
		Parses each tab in the "packages" div on the overview page.

		:param response: an HTML document
		:param kwargs: should contain model, year, and base price
		:return: a list of vehicles
		"""
		vehicles = []

		if response.xpath('//div[@id="packages"]').get() is not None:
			for tab in response.xpath('//div[@id="packages"]//a[@role="tab"]'):
				trim = remove_html_tags(tab.attrib['aria-controls'])
				price = tab.xpath('span[@class="acr-paragraph-7"]/text()').get()  # span[last()] also works

				vehicle = Vehicle({'make': self.name.upper(),
								   'model': kwargs['model'],
								   'year': kwargs['year'],
								   'trim': trim,
								   'msrp': price})

				vehicles.append(vehicle)
		else:
			# If the vehicle has no packages, return a single trim (currently, only the NSX should meet this condition)
			vehicle = Vehicle({'make': self.name.upper(),
							   'model': kwargs['model'],
							   'year': kwargs['year'],
							   'trim': kwargs['model'],
							   'msrp': kwargs['price']})

			vehicles.append(vehicle)

		return vehicles
