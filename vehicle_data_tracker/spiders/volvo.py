"""
Scrapes data from the Volvo website.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class VolvoSpider(scrapy.Spider):
    name = 'volvo'
    allowed_domains = ['www.volvocars.com']
    start_urls = ['https://www.volvocars.com/us']

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

    def parse(self, response, **kwargs):
        """
        Gets the link to and name of each model from the options in the "Our Cars" dropdown menu, then follows the link.

        :return: an iterable of Requests
        """
        for carContainer in response.xpath('//a[@data-autoid="nav:carContainer"]'):
            modelLink = carContainer.attrib['href']
            modelName = carContainer.xpath('.//em[@data-autoid="nav:carName"]/text()').get()
            args = {'model': modelName}

            yield response.follow(url=modelLink, callback=self.nav_to_shop, cb_kwargs=args)

    def nav_to_shop(self, response, **kwargs):
        """
        Follows the link to the model's "Shop" page.

        :param kwargs: should contain the model name
        :return: a Request
        """
        shopLink = response.xpath('//a[contains(@aria-label, "Shop")]/@href').get()
        if shopLink is not None:
            yield response.follow(url=shopLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        Gets the model year from the data-track-context JSON in the root div, then follows the "Build your own" link.

        :param kwargs: should contain the model name
        :return: a Request
        """
        modelData = json.loads(response.xpath('//div[@id="root"]//div[@data-track-context]/@data-track-context').get())
        modelYear = modelData['carModelYear']
        buildLink = response.xpath('(//a[contains(@aria-label, "Build")] | //a[contains(@href, "build")])/@href').get()
        kwargs['year'] = modelYear
        yield response.follow(url=buildLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Gets the trim names and prices from the divs labeled "familyStageCard".

        :param response:
        :param kwargs: should contain the model name and year
        :return: a list of vehicles
        """
        vehicles = []

        versionFamilyCards = response.xpath('//div[@data-testid="familyStageCard"]')
        if len(versionFamilyCards) > 0:
            for versionFamily in versionFamilyCards:
                trimName = versionFamily.xpath('.//p[contains(@data-sources, "displayName")]/text()').get()
                msrp = versionFamily.xpath('.//p[@data-autoid="price"]//text()').get()

                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': msrp})

                vehicles.append(vehicle)
        else:
            trimName = response.xpath('//p[contains(@data-sources, "displayName")]/text()').get()
            msrp = response.xpath('//p[@data-autoid="price"]//text()').get()

            vehicle = Vehicle({'make': self.name.upper(),
                               'model': kwargs['model'],
                               'year': kwargs['year'],
                               'trim': trimName,
                               'msrp': msrp})

            vehicles.append(vehicle)

        return vehicles
