import re

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class PorscheSpider(scrapy.Spider):
    name = 'porsche'
    allowed_domains = ['www.porsche.com']
    start_urls = ['https://www.porsche.com/usa/']

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
        Porsche has a lovely little bit of data on its website - an attribute of the body tag on every page which
        contains a massive amount of JSON data on every available model.

        :return: a list of vehicles, baby
        """
        vehicles = []

        data_models = json.loads(response.xpath('//body/@data-model').get())
        for model in data_models['models']:
            if 'modelname' in model.keys():
                modelName = model['modelrange']
                trimName = model['modelname']
                msrp = model['price'][0]['value']  # more simply, model['price_raw'] will also work
                carConfig = str(model['carconfigurator'])  # gets a link which has the model year
                yearStartIndex = carConfig.rfind('&MODELYEAR=')
                yearEndIndex = carConfig.find('&', yearStartIndex + 1)
                year = carConfig[yearStartIndex: yearEndIndex]

                trim = Vehicle()
                trim['make'] = self.name.upper()
                trim['model'] = modelName
                trim['year'] = year
                trim['trim'] = trimName
                trim['msrp'] = msrp
                vehicles.append(trim)

        return vehicles
