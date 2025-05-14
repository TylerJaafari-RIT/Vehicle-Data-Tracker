"""
Scrapes data from the Volkswagen website. Since the data on trims is loaded in dynamically, and there are some
messy API links, the most straight-forward way of handling this site is to directly access a JSON doc that contains
data on all the models and their trims.
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json
import re


class VwSpider(scrapy.Spider):
    name = 'vw'
    allowed_domains = ['www.vw.com', 'prod.services.ngw6apps.io']
    start_urls = ['https://www.vw.com/en.html']

    name_long = 'volkswagen'

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

    def gen_api_link(self, option=1):
        """
        There are two request links that can be used. One is just a dictionary containing each model and their trims.
        The other is a list of categories, and within each is a dictionary containing the models and their trims.

        :return: an API link to a JSON doc
        """
        if option != 1 and option != 2:
            raise ValueError("argument 'option' must be 1 or 2")
        linkA = 'https://prod.services.ngw6apps.io/modelsConfig?serviceConfigsServiceConfig=%7B%22key%22%3A%22service-config%22%2C%22urlOrigin%22%3A%22https%3A%2F%2Fwww.vw.com%22%2C%22urlPath%22%3A%22%2Fen.service-config.json%22%2C%22tenantCommercial%22%3Anull%2C%22tenantPrivate%22%3Anull%2C%22customConfig%22%3Anull%2C%22homePath%22%3Anull%2C%22credentials%22%3A%7B%22username%22%3A%22%22%2C%22password%22%3A%22%22%7D%7D&groupBy=carlineId&useGlobalConfig=true'
        linkB = 'https://prod.services.ngw6apps.io/modelsConfig?language=en&countryCode=US&currency=USD&serviceConfigsServiceConfig=%7B%22key%22%3A%22service-config%22%2C%22urlOrigin%22%3A%22https%3A%2F%2Fwww.vw.com%22%2C%22urlPath%22%3A%22%2Fen.service-config.json%22%2C%22tenantCommercial%22%3Anull%2C%22tenantPrivate%22%3Anull%2C%22customConfig%22%3Anull%2C%22homePath%22%3Anull%2C%22credentials%22%3A%7B%22username%22%3A%22%22%2C%22password%22%3A%22%22%7D%7D&useGlobalConfig=true&groupBy=category'
        if option == 1:
            return linkA
        else:
            return linkB

    def parse(self, response, **kwargs):
        option = 1
        api_link = self.gen_api_link(option=option)
        args = {'option': option}
        yield scrapy.Request(url=api_link, callback=self.parse_models, cb_kwargs=args)

    def parse_models(self, response, **kwargs):
        vehicles = []

        vehicleDict = response.json()
        if kwargs['option'] == 1:
            for carlineId in vehicleDict:
                modelData = vehicleDict[carlineId]
                for vehicle in self.parse_trims(modelData=modelData):
                    vehicles.append(vehicle)
        else:
            for category in vehicleDict:  # in this case, it will be a list of dicts
                for modelData in category['models']:
                    for vehicle in self.parse_trims(modelData=modelData):
                        vehicles.append(vehicle)

        return vehicles

    def parse_trims(self, modelData: dict):
        trims = []

        modelName = modelData['name']
        year = ''.join(re.findall('/\d{4}/', modelData['carImage']))
        if year == '':
            year = str(re.search('\d{4}/', modelData['carImage']))
        for trimData in modelData['modelTrims']:
            trimName = trimData['name']
            msrp = trimData['prices']['price']
            vehicle = Vehicle()
            vehicle['make'] = self.name_long.upper()
            vehicle['model'] = modelName
            vehicle['year'] = year
            vehicle['trim'] = trimName
            vehicle['msrp'] = msrp
            trims.append(vehicle)

        return trims
