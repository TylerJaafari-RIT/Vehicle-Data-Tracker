"""
Scrapes data from the Lincoln website. Although owned by Ford, this website's HTML has many differences from Ford's,
and requires a separate spider. Like Ford's, however, the msrp is difficult to obtain, and is considered out of scope
for the current state of the project.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class LincolnSpider(scrapy.Spider):
    name = 'lincoln'
    allowed_domains = ['www.lincoln.com']
    start_urls = ['https://www.lincoln.com/']

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
        siteMapLink = response.xpath('//a[contains(., "SITE MAP")]/@href').get()
        yield response.follow(url=siteMapLink, callback=self.parse_site_map, cb_kwargs=kwargs)

    def parse_site_map(self, response, **kwargs):
        allVehiclesLink = response.xpath('//a[contains(., "ALL VEHICLES")]/@href').get()
        yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        vehicleLinkTags = response.xpath('//div[@class="multiYearVehicleTileContainer section"][1]'
                                         '//ul[@class="carousel-inner"]//a[contains(@aria-label, "Explore")]')

        # just like with Ford, both models and years can be gathered from the all vehicles page as well as
        # the trims pages themselves, but here we're doing it the latter way because it's easier
        for a in vehicleLinkTags:
            modelLink = a.attrib['href']
            yield response.follow(url=modelLink, callback=self.nav_to_specs, cb_kwargs=kwargs)

    def nav_to_specs(self, response, **kwargs):
        specsLink = response.xpath('//a[contains(@data-title-text, "Specifications")]/@href').get()
        kwargs['first_pass'] = True
        yield response.follow(url=specsLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Somewhat "hacky" way of getting the data on each trim. For each entry in the "hotspot list" of each specs page,
        there is a hidden string written as "View {year} Lincoln[(r)|] {model} {trim} [M|m]odel". Any occurrences of
        the characters in "ViewMmodel" are stripped from both ends, the string is split and the data is sorted.

        :return: a list of vehicles
        """
        vehicles = []

        trimInfoList = response.xpath('//ul[@class="hotspot-list"]/li/a[1]/span/text()').getall()
        for trimInfo in trimInfoList:
            trimInfo = trimInfo.strip('ViewMmodel').replace('®', '')  # 'ViewMmodel' is not a typo
            trimData = trimInfo.split(maxsplit=3)
            trim = Vehicle()
            trim['year'] = trimData[0]
            trim['make'] = self.name.upper()
            trim['model'] = trimData[2]
            trim['trim'] = trimData[3]
            trim['msrp'] = ''
            vehicles.append(trim)

        return vehicles
