"""
Handles the scraping and processing of data from the Audi USA website.

Author: Tyler Jaafari

Version: 1.5
    1.1 - improved string building and stripping of package names
    1.5 - rewrote parse method, updated other methods with simpler code
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *


class AudiSpider(scrapy.Spider):
    name = 'audi'
    allowed_domains = ['www.audiusa.com']
    start_urls = ['https://www.audiusa.com/us/web/en/models.html']

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
        Goes through each model on the All Models page and gets the model name and year from attributes. Then follows
        the Explore link for each model.

        :return: an iterable of Requests
        """
        # NOTE: e-tron GT and RS e-tron GT have two different buttons that link to the same page
        #       RS e-tron GT is just a package of the e-tron GT model
        for vehicleCard in response.xpath('//audi-modelfinder-car-model'):
            modelData = vehicleCard.attrib['data-model-name'].split(' ', maxsplit=1)
            modelYear = modelData[0]
            modelName = modelData[1]
            modelLink = vehicleCard.xpath('.//a[contains(., "Explore")]/@href').get()
            args = {'model': modelName, 'year': modelYear}
            yield response.follow(url=modelLink, callback=self.parse_model, cb_kwargs=args)

    def parse_model(self, response, **kwargs):
        """
        Follow the first build link on the page.

        :param response: an HTML document
        :param kwargs: should contain model and year
        :return: a Request
        """
        build_url = response.xpath('//a[contains(@href, "build")]/@href').get()
        if build_url is not None:
            yield response.follow(url=build_url, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Gets data on each trim from the text() attribute of tags within the containing divs.

        :param response: an HTML document
        :param kwargs: should contain model and year
        :return: a list of vehicles
        """
        vehicles = []
        divs = response.xpath('//div[@class="nm-module-trimline-engine-container"]')
        for div in divs:
            packageCategory = div.xpath('div/div/text()').get()
            for li in div.xpath('ul/li'):
                trim = Vehicle()
                trimName = ''
                for t in li.xpath('div[contains(@class, "engine-list")]//text()').getall():
                    trimName += ' ' + t.strip()
                if packageCategory not in trimName:
                    trimName = packageCategory + trimName
                price = li.xpath('div[@data-configurator-id]/text()').get()
                trim['make'] = self.name.upper()
                trim['model'] = kwargs['model']
                trim['year'] = kwargs['year']
                trim['trim'] = trimName.strip()
                trim['msrp'] = price
                vehicles.append(trim)
        return vehicles
