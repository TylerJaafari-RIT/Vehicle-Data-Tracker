"""
This is an experimental spider that will attempt to crawl multiple websites owned by the same corporation.

This will (hopefully) simplify program maintenance later. If the opposite effect is found to be the case,
new spiders for each make can be made based off of this one, since it works for all makes included.

Author: Tyler Jaafari

Version: 1.3
    1.1 - added Alfa Romeo
    1.2 - nav_to_specs() now checks if the data-props attribute is None before passing it to json.loads()
    1.3 - parse_trims() now gets the model name and year from the API JSON document
"""

import scrapy
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle
import json


class FcaSpider(scrapy.Spider):
    name = 'fca'
    allowed_domains = ['www.fiatusa.com', 'www.chrysler.com', 'www.dodge.com', 'www.jeep.com', 'www.ramtrucks.com',
                       'www.alfaromeousa.com']
    start_urls = ['https://www.fiatusa.com/', 'https://www.chrysler.com', 'https://www.dodge.com',
                  'https://www.jeep.com', 'https://www.ramtrucks.com', 'https://www.alfaromeousa.com/']

    makes = {
        'chrysler': ('www.chrysler.com', 'https://www.chrysler.com'),
        'dodge': ('www.dodge.com', 'https://www.dodge.com'),
        'fiat': ('www.fiatusa.com', 'https://www.fiatusa.com/'),
        'jeep': ('www.jeep.com', 'https://www.jeep.com'),
        'ram': ('www.ramtrucks.com', 'https://www.ramtrucks.com'),
        'alfa romeo': ('www.alfaromeousa.com', 'https://www.alfaromeousa.com/')
    }

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

    def gen_api_link(self, make: str, modelCode: str):
        api_link = f'https://{self.makes[make][0]}/hostd/api/cvd/{modelCode}/{modelCode}_CVD'
        return api_link

    def start_requests(self):
        for make in self.makes:
            args = {'make': make}
            yield scrapy.Request(url=self.makes[make][1], callback=self.find_all_vehicles, cb_kwargs=args)

    def find_all_vehicles(self, response, **kwargs):
        """
        For each FCA website, finds the link to the "All Vehicles" page on the homepage. In the case of Alfa Romeo,
        runs a loop on each model present in the Vehicles dropdown menu and skips straight to nav_to_specs().

        :param response:
        :param kwargs:
        :return: an iterable of Requests
        """
        allVehiclesLink = response.xpath('(//div[contains(@data-lid, "vehicles")]//a[contains(@data-lid, "all-")])'
                                         '[last()]/@href').get()
        if allVehiclesLink is None:
            # handles Alfa Romeo's lack of an "all vehicles" page
            vehicleLinks = response.xpath('//div[contains(@data-lid, "vehicles")]//a/@href').getall()
            for link in vehicleLinks:
                yield response.follow(url=link, callback=self.nav_to_specs, cb_kwargs=kwargs)
        else:
            allVehiclesLink = allVehiclesLink.strip()
            # it's worth noting that hard-coding the href as "/all-vehicles.html" would also work across the board
            # UPDATE: Alfa Romeo has no "all vehicles" page.
            yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        Every FCA website's All Vehicles page has a helpful attribute with JSON containing each model's name, year,
        and overview page link.

        :param response:
        :param kwargs:
        :return:
        """
        data_props = json.loads(response.xpath('//div[contains(@id, "all_vehicles_page")]/@data-props').get())
        for section in data_props['sections']:
            for navcard in section['navcards']:
                modelName = navcard['vehicle'].replace('_', ' ')
                modelYear = navcard['modelYear']
                href = navcard['destination']
                kwargs['model'] = modelName
                kwargs['year'] = modelYear
                yield response.follow(url=href, callback=self.nav_to_specs, cb_kwargs=kwargs)

    def nav_to_specs(self, response, **kwargs):
        """
        Find the "Specs" link in the navbar and follows it. If the link is not there, then use the overview page's
        data-props attribute to get the link.

        :param response: an HTML document
        :param kwargs: should contain model and year
        :return: a Request
        """
        # for the jeep, the wrangler 4xe has distinct trims from the wrangler BUT its navbar
        # is loaded in dynamically, meaning we can't find the specs link this way
        href = response.xpath('//a[contains(@data-lid, "specs")]/@href').get()
        if href is not None:
            yield response.follow(url=href, callback=self.parse_specs, cb_kwargs=kwargs)
        else:
            # print(response.url, ': ', response.xpath('//a[@data-lid="sec-nav-specs"]').get())
            data_props_attrib = response.xpath('//div[@id="secondary_navigation"]/@data-props').get()
            if data_props_attrib is not None:
                data_props = json.loads(data_props_attrib)
                for section in data_props['secondaryNavigation']['sectionList']:
                    if section['label'] == 'Specs':
                        href = section['destination']
                        break
                yield response.follow(url=href, callback=self.parse_specs, cb_kwargs=kwargs)

    def parse_specs(self, response, **kwargs):
        """
        If there is a model_specification div, get the JSON from its data-props attribute. Extract the model name,
        year, and API code, and use the code to generate an API link and follow it.

        :return: a Request
        """
        if response.xpath('//div[contains(@id, "model_specification_")]').get() is None:
            data_props = json.loads(response.xpath('//div[@id="all_vehicles_page_co"]/@data-props').get())
            for navcard in data_props['sections'][0]['navcards']:
                modelName = navcard['vehicle'].replace('_', ' ')
                modelYear = navcard['modelYear']
                href = navcard['destination']
                kwargs['model'] = modelName
                kwargs['year'] = modelYear
                yield response.follow(url=href, callback=self.parse_specs, cb_kwargs=kwargs)
        else:
            data_props = json.loads(response.xpath('//div[contains(@id, "model_specification_")]/@data-props').get())
            modelCode = data_props['vehiclesInfo'][0]['modelYearCode']
            if 'model' not in kwargs.keys():
                modelData = data_props['specHeaderLabel'].split(maxsplit=1)
                modelYear = modelData[0]
                modelName = modelData[1]
                kwargs['model'] = modelName
                kwargs['year'] = modelYear
            url = self.gen_api_link(kwargs['make'], modelCode)
            yield response.follow(url=url, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Parses the JSON response from the FCA API.

        :param response: a JSON document
        :param kwargs: does not need to contain model and year
        :return: a list of vehicles
        """
        vehicles = []

        vehicleJsonList = response.json()
        model = vehicleJsonList['vehicle']['description']
        year = vehicleJsonList['vehicle']['year']
        for vehicleData in vehicleJsonList['configurations']:
            trim = Vehicle()
            trim['make'] = kwargs['make'].upper()
            trim['model'] = model
            trim['year'] = year
            trimName = vehicleData['descriptions']['desc']
            trim['trim'] = trimName.strip()
            trim['msrp'] = vehicleData['price']['msrpAsConfigured']
            vehicles.append(trim)

        return vehicles
