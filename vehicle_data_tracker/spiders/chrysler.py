"""
Scrapes data from the Chrysler website. This spider was used as the template for the FCA spider and is no longer
necessary, unless a user wishes to only update the Chrysler vehicles.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle
import json


class ChryslerSpider(scrapy.Spider):
    name = 'chrysler'
    allowed_domains = ['www.chrysler.com']
    start_urls = ['https://www.chrysler.com/']

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
        'ROBOTSTXT_OBEY': False
    }

    def gen_api_link(self, modelCode:str):
        api_link = f'https://www.chrysler.com/hostd/api/cvd/{modelCode}/{modelCode}_CVD'
        return api_link

    # note: Chrysler is owned by Stellantis/FCA (Fiat Chrysler Automobiles). They also own Dodge, Fiat, Jeep, and Ram.

    # I'm seeing two ways of going about this:
    # a) going for the json that is sent to the browser in the Build & Price app, as with the approach for the GM sites
    # b) go to the model/specs page for each model and get the html
    #
    # option (b) is looking like the way to go

    # actually, path (b) leads to more dynamic elements, so I'll have to figure something out like in (a)
    # so far the only place I can find relevant data is at these links:
    # https://www.chrysler.com/hostd/api/cvd/CUC202105/CUC202105_CVD.json
    # (this is the api link for the 2021 Pacifica)

    def parse(self, response, **kwargs):
        allVehiclesLink = response.xpath('//a[contains(@data-lid, "all-vehicles")]/@href').get()
        yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        data_props = json.loads(response.xpath('//div[@id="all_vehicles_page"]/@data-props').get())
        for section in data_props['sections']:
            for navcard in section['navcards']:
                modelName = navcard['vehicle']
                modelYear = navcard['model_year']
                href = navcard['destination']
                args = {'model': modelName, 'year': modelYear}
                yield response.follow(url=href, callback=self.nav_to_specs, cb_kwargs=args)

    def nav_to_specs(self, response, **kwargs):
        href = response.xpath('//a[@data-lid="sec-nav-specs"]/@href').get()
        yield response.follow(url=href, callback=self.parse_specs, cb_kwargs=kwargs)

    def parse_specs(self, response, **kwargs):
        if response.xpath('//div[@id="model_specification_"]').get() is None:
            data_props = json.loads(response.xpath('//div[@id="all_vehicles_page_co"]/@data-props').get())
            for navcard in data_props['sections'][0]['navcards']:
                modelName = navcard['vehicle'].replace('_', ' ')
                modelYear = navcard['model_year']
                href = navcard['destination']
                args = {'model': modelName, 'year': modelYear}
                yield response.follow(url=href, callback=self.parse_specs, cb_kwargs=args)
        else:
            data_props = json.loads(response.xpath('//div[@id="model_specification_"]/@data-props').get())
            modelCode = data_props['vehiclesInfo'][0]['modelYearCode']
            url = self.gen_api_link(modelCode)
            yield response.follow(url=url, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        vehicleJsonList = response.json()['configurations']
        for vehicleData in vehicleJsonList:
            trim = Vehicle()
            trim['make'] = self.name.upper()
            trim['model'] = kwargs['model']
            trim['year'] = kwargs['year']
            trimName = vehicleData['descriptions']['desc']
            trim['trim'] = trimName.replace(kwargs['model'].upper(), '').strip()
            trim['msrp'] = vehicleData['price']['msrpAsConfigured']
            vehicles.append(trim)

        return vehicles
