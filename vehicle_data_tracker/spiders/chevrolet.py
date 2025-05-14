"""
Scrapes data from the Chevrolet website. Currently, there are enough differences in GM websites to warrant multiple
spiders, but that may change in the future.

Author: Tyler Jaafari
Version: 1.3
    1.1 - removed unnecessary duplicate checking
    1.2 - reimplemented separate_category arg for gen_api_link so Bolt EV and Bolt EUV can be collected
        - added loop to get model and year based on dictionary keys/values rather than hard-coded list indexing
            (chevy why are these dictionaries organized like that)
    1.3 - added conditionals to filter out blank entries to the api
"""

import scrapy
import json
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle
import re


class ChevroletSpider(scrapy.Spider):
    name = 'chevrolet'
    allowed_domains = ['www.chevrolet.com']
    start_urls = ['https://www.chevrolet.com/']

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
        'ROBOTSTXT_OBEY': False,
        'ITEM_PIPELINES': {
            'vehicle_data_tracker.pipelines.FormatPipeline': 300,
            'vehicle_data_tracker.pipelines.DuplicatePipeline': 400,
        }
    }

    # chevrolet is also GM
    # this time we're looking for data-gm-filter in the models page
    # interestingly, GM doesn't want robots looking at anything under /byo-vc/ on the chevrolet site, even though
    # they allow it for buick and cadillac

    def gen_api_link(self, model_name: str, model_year: str, separate_category=True):
        """
        Fortunately, Chevy's system of passing model names to the API is a bit more consistent than Cadillac's.

        :param model_name: What could this be
        :param model_year: I truly wonder
        :param separate_category:
        :return: a link
        """
        print_debuggery = False
        if not (model_name == '' or model_year == ''):
            modelNameNoSpaces = model_name.replace(' ', '-')
            modelCategory = modelNameNoSpaces
            if separate_category and '-' in modelNameNoSpaces:
                modelCategory = modelNameNoSpaces[0:modelNameNoSpaces.find('-')]
            # modelID = model_name
            # if ' ' in model_name:
            #     modelID = modelNameNoSpaces
            # elif '-' in model_name:
            #     modelID = model_name.replace('-', '')
            api_link = f'https://{self.allowed_domains[0]}/byo-vc/api/v2/trim-matrix/en/US/{self.name}/{modelCategory}/{model_year}/{model_name}'
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
        For each vehicle tile, get the model and year from the JSON in the data-gm-filter attribute, then pass them
        to gen_api_link and follow the result. For electric cars, call gen_api_link with separate_Category set to False.

        :param response: an HTML document
        :param kwargs:
        :return: an iterable of Requests
        """
        vehicleTiles = response.xpath('//div[@data-gm-filter]')
        for tile in vehicleTiles:
            data_gm = json.loads(tile.attrib['data-gm-filter'])
            try:
                modelYear = ''
                modelName = ''
                vdcAttributes = data_gm['vdcAttributes']
                for i in range(len(vdcAttributes) - 1, 0, -1):
                    if vdcAttributes[i]['name'] == 'year':
                        modelYear = vdcAttributes[i]['value']
                    elif vdcAttributes[i]['name'] == 'bodystyleCode':
                        modelName = vdcAttributes[i]['value']
                    if not (modelName == '' or modelYear == ''):
                        break

                api_link = self.gen_api_link(modelName, modelYear)
                try:
                    if 'chevrolet_tags:segment/electric' in data_gm['tags']:
                        api_link = self.gen_api_link(modelName, modelYear, separate_category=False)
                except KeyError:
                    continue
                args = {'model': modelName, 'year': modelYear}
                if api_link is not None:
                    yield response.follow(url=api_link, callback=self.parse_trims, cb_kwargs=args)
            except IndexError:
                continue

    def parse_trims(self, response, **kwargs):
        """
        Parses the JSON document fetched from Chevrolet's API.

        :param response: a JSON document
        :param kwargs: should contain model and year
        :return: a list of vehicles
        """
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
        # print(vehicleData)
        for trimData in vehicleData['options']:
            trim = Vehicle()
            trim['make'] = self.name.upper()
            trim['model'] = kwargs['model']
            trim['year'] = kwargs['year']
            trimName = f"{trimData['trimName']} {trimData['driveType']}"
            if len(engines) > 1:
                trimName += ' ' + engines[trimData['engine']]
            transPattern = re.compile('manual|automatic', re.IGNORECASE)
            if len(engines) == 1 and len(transmissions) > 1 and not re.search(transPattern, trimName):
                trimName += ' ' + transmissions[trimData['transmission']]
            trim['trim'] = trimName
            trim['msrp'] = trimData['msrp']['amount']['text']
            vehicles.append(trim)
        return vehicles
