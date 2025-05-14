"""
This is going to be another group spider. Nissan Group owns Nissan and Infiniti.

There are two approaches immediately available. For both sites, there is a drop-down menu that contains divs with
all available vehicles, which contain helpful attributes identifying the models and years. Additionally, there is
a site map that contains an all vehicles link.

I'll probably go the site map route. It involves more steps for the crawl, but is closer to a more universal parsing
functionality.

Author: Tyler Jaafari
Version: 1.0.0
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class NissanSpider(scrapy.Spider):
    name = 'nissan'
    allowed_domains = ['www.nissanusa.com', 'www.infinitiusa.com']
    start_urls = ['https://www.nissanusa.com/', 'https://www.infinitiusa.com/']

    makes = {
        'nissan': ('www.nissanusa.com', 'https://www.nissanusa.com/'),
        'infiniti': ('www.infinitiusa.com', 'https://www.infinitiusa.com/')
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
        'ITEM_PIPELINES': {
            'vehicle_data_tracker.pipelines.FormatPipeline': 300,
            'vehicle_data_tracker.pipelines.DuplicatePipeline': 400,
        },
    }

    def start_requests(self):
        for make in self.makes:
            args = {'make': make}
            yield scrapy.Request(url=self.makes[make][1], callback=self.parse, cb_kwargs=args)

    def parse(self, response: scrapy.http.Response, **kwargs):
        """
        Finds the site map link and follows it.
        """
        siteMapLink = response.xpath('//a[text()="Site Map"]/@href').get()  # //a[contains(@href, "sitemap")] also works

        yield response.follow(url=siteMapLink, callback=self.find_all_vehicles, cb_kwargs=kwargs)

    def find_all_vehicles(self, response, **kwargs):
        allVehiclesLink = response.xpath('//a[contains(., "Vehicles")]/@href').get()

        yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        vehicleDivs = response.xpath('//ul//div[@data-vehicle-name]')

        for div in vehicleDivs:
            modelYear = div.attrib['data-vehicle-year']
            modelName = div.attrib['data-vehicle-name'].replace(modelYear, '').strip()
            exploreLink = div.xpath('a/@href').get()
            kwargs['model'] = modelName.strip('®')
            kwargs['year'] = modelYear

            yield response.follow(url=exploreLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Fetches and parses the hidden JSON data that is loaded onto the page.

        :return: a list of Vehicle items
        """
        vehicles = []

        vehicleData = json.loads(response.xpath('//iframe[@id="individualVehiclePriceJSON"]/text()').get())
        modelID = kwargs['year'] + '-' + kwargs['model'].lower().replace(' ', '-')
        modelCode = vehicleData[modelID]['modelCode']
        grades = vehicleData[modelID]['Retail']['grades']

        for grade in grades:
            trimName = grade.split('-', maxsplit=1)[1].replace('_', ' ')
            msrp = grades[grade]['gradePrice']
            trim = Vehicle()
            trim['make'] = kwargs['make'].upper()
            trim['model'] = kwargs['model']
            trim['year'] = kwargs['year']
            trim['trim'] = trimName
            trim['msrp'] = msrp
            vehicles.append(trim)

        return vehicles
