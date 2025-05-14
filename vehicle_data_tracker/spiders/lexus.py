"""
Lexus proved to be far less difficult than I had initially feared. Since practically all of the data on every
page of the Lexus website is loaded in dynamically, no data on vehicles can be gathered from scraping HTML. This
makes lexus.py the only spider to exclusively parse JSON data.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class LexusSpider(scrapy.Spider):
    name = 'lexus'
    allowed_domains = ['www.lexus.com']
    # start_urls = ['https://www.lexus.com/.model.json']

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
        },
    }

    def gen_api_link(self, model: str):
        if model == '':
            api_link = f'https://{self.allowed_domains[0]}/{model}.model.json'
        else:
            api_link = f'https://{self.allowed_domains[0]}/models/{model.replace(" ", "-")}.model.json'
        return api_link

    def start_requests(self):
        start_link = self.gen_api_link('')
        return [scrapy.Request(url=start_link, callback=self.parse)]

    def parse(self, response, **kwargs):
        """
        Parses the top-level model json doc

        :return: an iterable of Requests
        """
        pageData = response.json()
        for menuCategory in pageData[':items']['root'][':items']['header']['headerMenu']['headerMenuCategories']:
            for menuItem in menuCategory['headerMenuItems']:
                model = menuItem['menuName']
                modelLink = self.gen_api_link(model)
                yield scrapy.Request(url=modelLink, callback=self.parse_trims)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        pageData = response.json()
        gridItems = pageData[':items']['root'][':items']['responsivegrid'][':items']
        if 'styles_module' in gridItems.keys():
            stylesModule = gridItems['styles_module']
            for trimData in stylesModule['trims']:
                year = trimData['year']
                model = trimData['series']
                baseTrimName = trimData['name']
                for priceData in trimData['prices']:
                    trimName = baseTrimName
                    if priceData['drive'] is not None:
                        trimName += ' ' + priceData['drive']
                    msrp = priceData['price']['price']

                    vehicle = Vehicle({'make': self.name.upper(),
                                       'model': model,
                                       'year': year,
                                       'trim': trimName,
                                       'msrp': msrp})

                    vehicles.append(vehicle)

        return vehicles
