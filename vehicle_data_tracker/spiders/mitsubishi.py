"""
Scrapes data from the Mitsubishi website.

Author: Tyler Jaafari
Version: 1.0
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class MitsubishiSpider(scrapy.Spider):
    name = 'mitsubishi'
    allowed_domains = ['www.mitsubishicars.com']
    start_urls = ['https://www.mitsubishicars.com/']

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
        Follows each model link in the Vehicles drop-down menu on the home page.

        :return: a list of vehicles, eventually
        """
        vehicleTiles = response.xpath('(//div[@class="nav-dropdown"])[1]//div[@class="vehicle-item__model"]//a')

        for tile in vehicleTiles:
            modelLink = tile.attrib['href']
            yield response.follow(url=modelLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        The model name and year can also be retrieved from this page, and would probably be cleaner that way.

        :return: a list of vehicles, eventually
        """
        trimsNav = response.xpath('//nav[contains(@class, "nav-sub")]//a[contains(@href, "models")]')
        trimsLink = trimsNav.attrib['href']
        yield response.follow(url=trimsLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        The model name and year can be retrieved from THIS page too, and is definitely the cleanest way.
        Eh, screw it.
        //div[@class="drivetrains"]//div/p[@class="price-label"]/*/text()

        :return: a list of vehicles
        """
        vehicles = []

        trimsAndSpecsSection = response.xpath('//section[@data-role="trims-and-specifications"]')
        model = trimsAndSpecsSection.attrib['data-modelname']
        year = trimsAndSpecsSection.attrib['data-modelyear']

        if response.xpath('//div[@role="tabpanel"]').get() is not None:
            for tab in response.xpath('//div[@class="content-container"]/div[@role="tabpanel"]'):
                trimName = tab.xpath('h3/text()').get()
                msrp = tab.xpath('div[@class="price"]/p/text()').get()

                vehicle = Vehicle()
                vehicle['make'] = self.name.upper()
                vehicle['model'] = model
                vehicle['year'] = year
                vehicle['trim'] = trimName
                vehicle['msrp'] = msrp
                vehicles.append(vehicle)
        else:
            for trimDiv in response.xpath('//div[@class="trims-overview default"]//div[@data-trim]'):
                for driveTrain in trimDiv.xpath('//div[@class="drivetrain"]'):
                    trimName = driveTrain.xpath('a/@data-drivetrain').get()
                    msrp = driveTrain.xpath('p[@class="price-label"]/*/text()').get()
                    vehicle = Vehicle()
                    vehicle['make'] = self.name.upper()
                    vehicle['model'] = model
                    vehicle['year'] = year
                    vehicle['trim'] = trimName
                    vehicle['msrp'] = msrp
                    vehicles.append(vehicle)

        return vehicles
