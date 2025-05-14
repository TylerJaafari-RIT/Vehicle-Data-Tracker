"""
Scrapes the Jaguar and Land Rover USA websites.

Author: Tyler Jaafari

Version: 0.9.0
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json
import re


class TataSpider(scrapy.Spider):
    name = 'tata'
    allowed_domains = ['www.jaguarusa.com', 'www.landroverusa.com']
    start_urls = ['https://www.jaguarusa.com/', 'https://www.landroverusa.com/']

    makes = {
        'jaguar': ('www.jaguarusa.com', 'https://www.jaguarusa.com/'),
        'land rover': ('www.landroverusa.com', 'https://www.landroverusa.com/')
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
        }
    }

    def start_requests(self):
        for make in self.makes:
            args = {'make': make}
            yield scrapy.Request(url=self.makes[make][1], callback=self.parse, cb_kwargs=args)

    def parse(self, response, **kwargs):
        siteMapLink = response.xpath('//a[contains(., "SITEMAP")]/@href').get()

        yield response.follow(url=siteMapLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        exploreModelTags = response.xpath('//ul[@class="SiteNavigationFirst"]/li[1]/ul/li/ul/li[contains(., "MODEL")]/a')
        for a in exploreModelTags:
            modelLink = a.attrib['href']
            yield response.follow(url=modelLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        fullModelName = response.xpath('//meta[@name="title"]/@content').get().split('|')[0].strip()
        modelData = fullModelName.split(' ', maxsplit=1)
        year = modelData[0]

        personalizationTags = response.xpath('//meta[@name="personalisation-tags"]/@content').get()
        if personalizationTags is not None:
            model = json.loads(personalizationTags)['tags'][0]
        else:
            model = modelData[1]

        trimDivs = response.xpath('//div[@class="Derivative__intro"]')

        for div in trimDivs:
            trimName = div.xpath('string(.//h2)').get()
            # there's a
            trimName = trimName.replace(model.upper(), '').replace('‑', '-').replace('\xa0', ' ').strip()
            if trimName == '':
                trimName = model.upper()  # can be changed to 'base' instead
            # DONE: it might be possible to have a pipeline remove make names from model names or model names from trim
            #  names
            msrp = div.xpath('.//span[@class="Derivative__from-price"]/text()').get()

            vehicle = Vehicle()
            vehicle['make'] = kwargs['make'].upper()
            vehicle['model'] = model
            vehicle['year'] = year
            vehicle['trim'] = trimName
            vehicle['msrp'] = msrp

            vehicles.append(vehicle)

        return vehicles
