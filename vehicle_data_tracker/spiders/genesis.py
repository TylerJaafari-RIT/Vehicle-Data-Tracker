"""
Scrapes data from the Genesis US website.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle
import json


class GenesisSpider(scrapy.Spider):
    name = 'genesis'
    allowed_domains = ['www.genesis.com']
    start_urls = ['https://www.genesis.com/us/en/']

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

    def gen_api_link(self, model: str, year: str, option=1):
        """
        There are two structures for api links, and the documents they link to have different structures. Some models
        do not have any

        :return: a link to a JSON document
        """
        if option == 1:
            api_link = f'/bin/api/v1/vehicleConfiguration/data.{model}-{year}?country=us&language=en'
        elif option == 2:
            api_link = f'/bin/api/v1/byoVehicleService?model={model}&year={year}&locale=US_en'
        else:
            raise ValueError('option should be 1 or 2')

        return api_link

    def parse(self, response, **kwargs):
        """
        On the homepage is a div with an attribute containing JSON data that has several API keys, some of which are not
        easily available anywhere else within the site. These links are processed after the site map, resulting in some
        duplicate links (which get automatically filtered out by Scrapy).

        :return: an iterable of Requests
        """
        siteMapLink = response.xpath('//a[@title="SITE MAP"]/@href').get()

        yield response.follow(url=siteMapLink, callback=self.parse_models, cb_kwargs=kwargs)

        car_data = dict(json.loads(response.xpath('//div[@data-component="car-configurator"]/@data-settings').get()))
        for key in car_data.keys():
            if key.startswith('g') and 'Endpoint' in key:
                endpoint = car_data[key]
                kwargs['trims_on_specs_page'] = False
                yield response.follow(url=endpoint, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        modelList = response.xpath('//div[contains(h2/text(), "VEHICLES")]/ul/li/a')
        for a in modelList:
            # the text contains the name of a model as: {model_year} GENESIS {model_name (may contain spaces)}
            # currently only the 2023 model has spaces within the model_name but as it may remain
            #  that way, this code will handle that by specifying a maxsplit of 2
            fullName = a.xpath('text()').get()
            modelData = fullName.split(maxsplit=2)
            modelYear = modelData[0]
            modelName = modelData[2].strip()
            args = {'model': modelName, 'year': modelYear, 'trims_on_specs_page': False}

            modelLink = self.gen_api_link(modelName, modelYear)
            yield response.follow(url=modelLink, callback=self.parse_trims, cb_kwargs=args)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        if kwargs['trims_on_specs_page']:
            for trimHeader in response.xpath('//section[@data-component="compare-table"]//span[@class="spanHeight"]//h1'):
                trimName = trimHeader.xpath('text()').get()
                msrp = trimHeader.xpath('../h2/text()').get()
                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': msrp})
                vehicles.append(vehicle)
        else:
            # aside from the conditional existence of a top-level 'data' key that contains all relevant... well, data,
            #  the vehicle data can be parsed in the same way for each type of document
            apiDoc = response.json()
            if 'status' in apiDoc.keys():
                if apiDoc['status'] == 'error':
                    altApiLink = self.gen_api_link(kwargs['model'], kwargs['year'], option=2)
                    # return scrapy.Request(url=altApiLink, callback=self.parse_trims, cb_kwargs=kwargs)
                    return response.follow(url=altApiLink, callback=self.parse_trims, cb_kwargs=kwargs)
                else:
                    vehicleData = apiDoc['data']
            else:
                vehicleData = apiDoc
            if 'model' in kwargs:
                model = kwargs['model']
            else:
                model = vehicleData['modelName']
            year = vehicleData['modelYear']
            for trimData in vehicleData['trim']:
                for powerTrain in trimData['powerTrain']:
                    trimName = ''
                    trimName = powerTrain['powertrainName']
                    if powerTrain['driveTrain'] not in trimName:
                        trimName += ' ' + powerTrain['driveTrain']
                    msrp = powerTrain['price']
                    trim = Vehicle()
                    trim['make'] = self.name.upper()
                    trim['model'] = model
                    trim['year'] = year
                    trim['trim'] = trimName
                    trim['msrp'] = msrp
                    vehicles.append(trim)

        return vehicles
