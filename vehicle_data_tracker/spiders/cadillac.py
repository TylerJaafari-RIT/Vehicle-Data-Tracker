"""
Handles the scraping and processing of data from the Cadillac website. Currently, there are enough differences in GM
websites to warrant multiple spiders, but that may change in the future.

Author: Tyler Jaafari

Version: 1.1
    1.1 - removed unnecessary duplicate checking
"""

import scrapy
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle
import json


class CadillacSpider(scrapy.Spider):
    name = 'cadillac'
    allowed_domains = ['www.cadillac.com']
    start_urls = ['https://www.cadillac.com/']

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

    # note: CADILLAC HAS THE EXACT SAME "BUILD & PRICE" SYSTEM AS BUICK HOLY CRAP
    # and the divs on the vehicles page have "q-vehicle-tile" in their class too
    # I think I'll call these types "vehicle tiles" or "byo-vc" or something like that

    #nevermind that last bit because I'm avoid the vehicle tiles page

    # okay I learned why cadillac and buick are so similar, they're both owned by GM, so if I ever make a general
    # scraper for this kind of site it'll be called 'GM scraper'

    # NOTE: transmission M3W is for engine LGX and transmission M3G is for engine LSY

    # issue with api links: for cadillac, the first modelID is actually the more generic name,
    # e.g.  ...../cadillac/escalade/2021/escalade-esv is correct, but ...../cadillac/escalade-esv/2021/escalade-esv
    #       returns a 400 response
    # this is not the same case with buick, it seems

    def gen_api_link(self, model_name: str, model_year: str, print_debuggery=False):
        """
        The way some models are identified for the API links necessitates the following pile of confusion.

        :param model_name: gee I wonder what this parameter is supposed to be
        :param model_year: hmmmmmm
        :param print_debuggery: if True, print a bunch of details for debugging. May be helpful to keep if something
                                changes
        :return: a link
        """
        modelNameNoSpaces = model_name.replace(' ', '-')
        modelCategory = modelNameNoSpaces
        if '-' in modelNameNoSpaces:
            if print_debuggery:
                print(f'{model_name} without spaces becomes {modelNameNoSpaces}')
            modelCategory = modelNameNoSpaces[0:modelNameNoSpaces.find('-')]
            if print_debuggery:
                print(f'category of {model_name} is {modelCategory}')
        modelID = model_name
        if ' ' in model_name:
            if print_debuggery:
                print(f'====================== {model_name} has spaces, set model id to {modelNameNoSpaces} ===============================')
            modelID = modelNameNoSpaces
        elif '-' in model_name:
            if print_debuggery:
                print(f'=============================== {model_name} has hyphen at {model_name.find("-")} ===================================')
            modelID = model_name.replace('-', '')
        # now the name needs to be adjusted (ESCALADE ESV => escalade-esv, CT4-V BLACKWING => ct4v)
        api_link = f'https://{self.allowed_domains[0]}/byo-vc/api/v2/trim-matrix/en/US/{self.name}/{modelCategory}/{model_year}/{modelID}'
        return api_link

    def parse(self, response, **kwargs):
        """
        Follows the first "BUILD & PRICE" link on the homepage.

        :return: a Request
        """
        buildAllVehiclesLink = response.xpath('(//a[@title="BUILD & PRICE"] | //a[@title="Build & Price"])/@href').get()
        yield response.follow(url=buildAllVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        For each image link, get the model year and name from the title attribute, then pass them to gen_api_link and
        follow that link.

        :param response: an HTML document
        :param kwargs:
        :return: an iterable of Requests
        """
        vehicleTiles = response.xpath('//a[@class="stat-image-link"]')
        for tile in vehicleTiles:
            modelData = str(tile.attrib['title']).split(' ', 1)
            modelYear = modelData[0]
            modelName = ""
            try:
                modelName = modelData[1]
            except IndexError:
                continue  # the social media links will only have one word in their title
            args = {'model': modelName, 'year': modelYear}
            api_link = self.gen_api_link(modelName, modelYear)
            yield response.follow(url=api_link, callback=self.parse_trims, cb_kwargs=args)

    def parse_trims(self, response, **kwargs):
        """
        Parses the JSON response from Cadillac's API.

        :param response: a JSON document
        :param kwargs: should contain model and year
        :return: a list of vehicles
        """
        vehicles = []

        vehicleData = response.json()
        engines = {}
        transmissions = {}
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
