"""
Scrapes data from the Ford website. Currently, the msrp is difficult to obtain with scrapy, and is considered
out of scope for the current state of the project.

Author: Tyler Jaafari

Version: 1.0.1
"""

import scrapy
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle
import json


class FordSpider(scrapy.Spider):
    name = 'ford'
    allowed_domains = ['www.ford.com']
    start_urls = ['https://www.ford.com/']

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
        siteMapLink = response.xpath('//a[contains(., "Site Map")]/@href').get()
        yield response.follow(url=siteMapLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        Iterates through each link in the "All Vehicles" section of the site map.

        :return: an iterable of Requests
        """
        allVehiclesSection = response.xpath('//div[contains(@aria-label, "all")][contains(@aria-label, "vehicles")]')
        for a in allVehiclesSection.xpath('.//ul[@class="column"]/li/a'):
            href = a.attrib['href']
            modelDataStr = str(a.xpath('.//text()').get())
            modelData = modelDataStr.split(maxsplit=1)
            if len(modelData) > 1:
                modelYear = modelData[0]
                modelName = modelData[1]
                args = {'model': modelName, 'year': modelYear}
                yield response.follow(url=href, callback=self.parse_trims, cb_kwargs=args)

    def parse_trims(self, response, **kwargs):
        """
        Parses the model page to get each trim. Price is loaded in dynamically and cannot be retrieved this way.

        :return: a list of vehicles
        """
        # it's worth mentioning that you can also get the model name and year from each model overview page too
        vehicles = []
        modelsList = response.xpath('//ul[@class="md-models"]/li[@data-link-context]')
        for li in modelsList:
            trimName = json.loads(li.attrib['data-link-context'])['trim']
            msrp = li.xpath('.//span[@class="price"]/text()').get()
            trim = Vehicle()
            trim['make'] = self.name.upper()
            trim['model'] = kwargs['model']
            trim['year'] = kwargs['year']
            trim['trim'] = trimName
            trim['msrp'] = msrp  # msrp is loaded in dynamically, so this should be an empty string.
            vehicles.append(trim)
        return vehicles
