"""
Scrapes data from the Honda automobiles website.

Author: Tyler Jaafari

Version: 1.0
    0.9 - Can get the data on most models
    1.0 - Can get the data on models that don't have a trim group on their overview page
"""

import scrapy
import json
from vehicle_data_tracker.utilities import *
from vehicle_data_tracker.items import Vehicle


class HondaSpider(scrapy.Spider):
    name = 'honda'
    allowed_domains = ['www.honda.com', 'automobiles.honda.com']
    start_urls = ['https://automobiles.honda.com/']

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

    # So, Honda corp owns both Honda (who would have guessed) and Acura. Let's see what we can do here.

    # update: there are a few differences between the two sites, but this one seems to be pretty easy to crawl.

    # TODO: get data on Clarity Fuel Cell (no msrp)

    def parse(self, response, **kwargs):
        """
        Scrapes the big "Our Vehicles" carousel (or should I say... CARousel?) for each model and
        follows the Explore link in each section.

        :return: iterable of Request objects
        """

        vehicleCards = response.xpath('//section[@data-model-series]')
        for card in vehicleCards:
            modelName = card.attrib['data-model-series']
            modelYear = card.attrib['data-model-year']
            modelPage = card.xpath('.//div[@class="actions"]/a[contains(., "EXPLORE")]/@href').get()
            args = {'model': modelName, 'year': modelYear}
            if modelPage is not None:
                yield response.follow(url=modelPage, callback=self.parse_models, cb_kwargs=args)

    def parse_models(self, response: scrapy.http.TextResponse, **kwargs):
        vehicles = []

        trimCards = response.xpath('//div[@data-trim-group]')
        if trimCards.get() is not None:
            yield scrapy.Request(url=response.url, callback=self.parse_trims, cb_kwargs=kwargs, dont_filter=True)

        else:
            # In the case of the Clarity Fuel Cell, there is no data-trim-group div, but it has a separate specs
            # page with the desired information (and don't look for the msrp because it doesn't have one)
            specsLink = response.xpath('//a[contains(., "SPECS")]/@href').get()
            if specsLink is not None:
                yield response.follow(url=specsLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        trimCards = response.xpath('//div[@data-trim-group]')
        if trimCards.get() is not None:
            for card in trimCards:
                trimName = card.attrib['data-trim-group']
                msrp = card.xpath('.//span[@class="trim-label"]/span[@class="value"]/text()').get()
                trim = Vehicle()
                trim['make'] = self.name.upper()
                trim['model'] = kwargs['model']
                trim['year'] = kwargs['year']
                trim['trim'] = trimName
                trim['msrp'] = msrp

                vehicles.append(trim)
        else:
            specsSelections = response.xpath('//select[@id="trims-specs"]')
            for option in specsSelections.xpath('option'):
                trimName = option.attrib['value']

                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': ''})

                vehicles.append(vehicle)

        return vehicles
