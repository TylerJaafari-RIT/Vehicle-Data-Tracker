"""
Scrapes data from the GMC website. Currently, there are enough differences in GM websites to warrant multiple
spiders, but that may change in the future.

Author: Tyler Jaafari

Version: 1.1
    1.1 - removed unnecessary duplicate checking
"""

import scrapy
import json
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle


class GmcSpider(scrapy.Spider):
    name = 'gmc'
    allowed_domains = ['www.gmc.com']
    start_urls = ['https://www.gmc.com/']

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

    def gen_api_link(self, modelName: str, modelYear: str, separate_category=True):
        """
        Currently, some of the GMC model names have spaces, and this throws an error. However, this behavior is
        desired as those trims are included in the base model data (i.e., every Acadia Denali trim is a trim of the
        Acadia).

        :param modelName:
        :param modelYear:
        :param separate_category:
        :return:
        """
        print_debuggery = False
        modelNameNoSpaces = modelName.replace(' ', '_')
        modelCategory = modelNameNoSpaces
        if '_' in modelNameNoSpaces:
            modelCategory = modelNameNoSpaces[0:modelNameNoSpaces.find('_')]
        modelID = modelName
        api_link = f'https://{self.allowed_domains[0]}/byo-vc/api/v2/trim-matrix/en/US/{self.name}/{modelCategory}/{modelYear}/{modelID}'
        return api_link

    def parse(self, response, **kwargs):
        """
        Follows the first "Build & Price" link on the homepage.

        :return: a Request
        """
        buildAllVehiclesLink = response.xpath('(//a[@title="Build & Price"] | //a[@title="BUILD & PRICE"])/@href').get()
        yield response.follow(url=buildAllVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        Gets the links to the Build & Price pages for each available year (including the current page) and follows them
        (duplicate request filtering will prevent this from looping indefinitely).
        Then, grabs the data from an attribute in each button oh for pete's sake you get the drill by now

        :param response: html
        :param kwargs:
        :return: Requestsss
        """
        if 'previous' in response.url:
            for buildYearLink in response.xpath('//a[@data-dtm="tertiary navigation"]/@href').getall():
                yield response.follow(url=buildYearLink, callback=self.parse_models, cb_kwargs=kwargs)
        buildButtons = response.xpath('body/adv-grid//a[@title="BUILD & PRICE"]')
        for a in buildButtons:
            modelData = a.attrib['data-dtm'].split(maxsplit=1)
            modelName = modelData[1]
            modelYear = modelData[0]
            args = {'model': modelName, 'year': modelYear}
            api_link = self.gen_api_link(modelName, modelYear)
            yield response.follow(url=api_link, callback=self.parse_trims, cb_kwargs=args)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        vehicleData = response.json()
        engines = {}
        transmissions = {}
        descriptor = 'engine'
        for engine in vehicleData['engines']:
            engines[engine['id']] = engine['description']
        if len(engines) == 1:
            for transmission in vehicleData['transmissions']:
                transmissions[transmission['id']] = transmission['description']
        for trimData in vehicleData['options']:
            trim = Vehicle()
            trim['make'] = self.name.upper()
            trim['model'] = kwargs['model']
            trim['year'] = kwargs['year']
            trimName = f"{trimData['trimName']} {trimData['driveType']} {engines[trimData['engine']]}"
            if len(engines) == 1 and len(transmissions) > 1:
                trimName += ' ' + transmissions[trimData['transmission']]
            trim['trim'] = trimName
            trim['msrp'] = trimData['msrp']['amount']['text']
            vehicles.append(trim)
        return vehicles
