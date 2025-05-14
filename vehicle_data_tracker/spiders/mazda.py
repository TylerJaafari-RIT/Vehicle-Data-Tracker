"""
Scrapes data from the Mazda USA website. Because of how different trims may be sorted based on what transmissions/
engines/drive trains are available, this spider contains logic to efficiently (at least, I think it's efficient)
decide which pieces of data to append to the trim name. Previous spiders that had this issue should be updated with
this logic.

Author: Tyler Jaafari
Version: 1.0
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class MazdaSpider(scrapy.Spider):
    name = 'mazda'
    allowed_domains = ['www.mazdausa.com']
    start_urls = ['https://www.mazdausa.com/']

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

    def gen_api_link(self, modelCode: str, trimCode: str = None):
        api_link = ''
        if trimCode:
            api_link = f'https://{self.allowed_domains[0]}/api/bp?m={modelCode}&t={trimCode}'
        else:
            api_link = f'https://{self.allowed_domains[0]}/api/bp/ts?m={modelCode}'
        return api_link

    def parse(self, response, **kwargs):
        """
        Gets the names, years, and API codes of each model from the vehicles drop-down menu.

        :return: an iterable of vehicles, eventually
        """
        for vehicleBlock in response.xpath('//li[@data-model]/div[@data-year]'):
            model = vehicleBlock.xpath('../@data-model').get()
            year = vehicleBlock.attrib['data-year']
            buildLink = vehicleBlock.xpath('.//a[contains(@href, "build")]/@href').get()
            if buildLink is not None:
                modelCode = buildLink[buildLink.rfind('/')+1:]
                api_link = self.gen_api_link(modelCode)
                args = {'model': model, 'year': year, 'code': modelCode}
                yield response.follow(url=api_link, callback=self.parse_models, cb_kwargs=args)

    def parse_models(self, response, **kwargs):
        """
        Gets the first trim code from the trim-selection JSON doc and goes to the corresponding build & price doc.

        :return: an iterable of vehicles, eventually
        """
        trimSelData = response.json()
        trimCode = trimSelData['response']['trims'][0]['code']
        api_link = self.gen_api_link(kwargs['code'], trimCode)
        yield response.follow(url=api_link, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Gets the trims from the current model's build & price JSON doc.

        :return: a list of vehicles
        """
        vehicles = []

        trimsJson = dict(response.json())
        appendDriveTrain = len(trimsJson['response']['powertrain']['drivetrain']['options']) > 1
        appendEngine = len(trimsJson['response']['powertrain']['engine']['options']) > 1
        appendTransmission = len(trimsJson['response']['powertrain']['transmission']['options']) > 1
        for trimData in trimsJson['response']['trims']:
            trimName = trimData['title']
            if appendDriveTrain:
                trimName += ' ' + trimData['drivetrainCode']
            if appendEngine:
                for engine in trimsJson['response']['powertrain']['engine']['options']:
                    if engine['code'] == trimData['engineCode']:
                        trimName += ' ' + engine['title']
                        break
            if appendTransmission:
                trimName += ' ' + trimData['transmissionCode']

            msrp = str(trimData['basePrice']['amount'])

            vehicle = Vehicle()  # I think I will go back to calling this variable 'vehicle' instead of 'trim'
            vehicle['make'] = self.name.upper()
            vehicle['model'] = kwargs['model']
            vehicle['year'] = kwargs['year']
            vehicle['trim'] = trimName
            vehicle['msrp'] = msrp
            vehicles.append(vehicle)

        return vehicles
