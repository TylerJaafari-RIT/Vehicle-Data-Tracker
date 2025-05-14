"""
Scrapes data from the Subaru website. The API link template is generously simple, and can be used to access
trims from up to several years ago, depending on the model.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *


class SubaruSpider(scrapy.Spider):
    name = 'subaru'
    allowed_domains = ['www.subaru.com']
    start_urls = ['https://www.subaru.com/']

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

    def gen_api_link(self, code: str, year: str):
        api_link = f'https://{self.allowed_domains[0]}/services/vehicles/trims/details/{year}/{code}'
        return api_link

    def parse(self, response, **kwargs):
        for vehicleLink in response.xpath('//div[@class="vehicle-link"]'):
            modelName = vehicleLink.xpath('.//span[@class="model-name bold"]/text()').get()
            if modelName is not None:
                modelCode = vehicleLink.xpath('../@class').get().split()[1]
                modelYear = vehicleLink.xpath('a/@rel').get()
                kwargs['code'] = modelCode
                kwargs['model'] = modelName
                modelLink = vehicleLink.xpath('a/@href').get()

                yield response.follow(url=modelLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        kwargs['year'] = response.xpath('//span[@class="model-year"]/text()').get()
        previousYearLink = response.xpath('//a[@class="year-stick"]/@href').get()
        if previousYearLink is not None:
            yield response.follow(url=previousYearLink, callback=self.parse_models, cb_kwargs=kwargs)

        trimsLink = response.xpath('//li[contains(@class, "models")]/a/@href').get()
        if trimsLink is None:
            trimsLink = self.gen_api_link(kwargs['code'], kwargs['year'])

        yield response.follow(url=trimsLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        if response.xpath('//li[contains(@class, "trim")]').get() is not None:
            for trimCard in response.xpath('//li[contains(@class, "trim")]'):
                trimName = trimCard.xpath('.//h3[@class="trim-name"]/text()').get()
                msrp = ' '.join(trimCard.xpath('.//p[contains(@class, "description")]'
                                               '/text()').getall()).strip().split()[0]

                vehicle = Vehicle()
                vehicle['make'] = self.name.upper()
                vehicle['model'] = kwargs['model']
                vehicle['year'] = kwargs['year']
                vehicle['trim'] = trimName
                vehicle['msrp'] = msrp
                vehicles.append(vehicle)
        else:
            # it's a json doc
            vehicleData = response.json()
            for trimData in vehicleData:
                trimName = trimData['name']
                msrp = trimData['msrp']

                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': msrp})

                vehicles.append(vehicle)

        return vehicles
