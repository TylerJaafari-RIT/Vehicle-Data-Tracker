"""
Handles the scraping and processing of data from the Acura website.

Author: Tyler Jaafari

Version: 1.1
"""

import scrapy
from scrapy.spiders import CrawlSpider, Rule, SitemapSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.http.response import Response
from vehicle_data_tracker.items import Vehicle
import json
import time
import re
from vehicle_data_tracker.utilities import *


class AcuraSpiderOld(scrapy.Spider):
    """
    First spider written for this project. Kept for sentiment.
    """
    name = 'acura_old'
    allowed_domains = ['www.acura.com']
    start_urls = ['https://www.acura.com/']
    # sitemap_urls = ['https://www.acura.com/sitemap.xml']

    # start_url = 'https://' + allowed_domains[0] + '/'
    urls = []

    output_format = 'csv'
    output_file = 'individual_outputs/' + name + '_output.' + output_format

    custom_settings = {
        'FEEDS': {
            output_file: {
                'format': output_format,
                'overwrite': True,
                'fields': STANDARD_FIELDS,
            },
            # 'vehicles.csv': {
            #     'format': 'csv',
            #     'fields': STANDARD_FIELDS,
            #     'item_export_kwargs': {
            #         'include_headers_line': False
            #     }
            # }
        }
    }

    # def start_requests(self):
    #     yield scrapy.Request(url=self.start_url, callback=self.get_models)

    #    # print('urls: ', self.urls)
    #    # for url in self.urls:
    #    #     scrapy.Request(url=url, callback=self.parse)

    def parse(self, response, **kwargs):
        vehicles = []
        vehicleJson = []
        vehicleJson = response.xpath('//a[@data-tracking]/@data-tracking').getall()
        vehicleJsonProcessed = []
        vehicleDataTrackingDict = {}
        count = 0
        for i in range(0, len(vehicleJson)):
            if '\'model_name\'' in vehicleJson[i] and 'no model' not in vehicleJson[i]:
                vehicleJsonRaw = vehicleJson[i]
                vehicleJson[i] = str(vehicleJson[i]).replace('\'', '\"')
                vehicleJsonProcessed.append(vehicleJson[i])
                # print('----------------------(' + str(count) + ')---------------------\n'
                #       + vehicleTags[i] +
                #       '\n----------------------------------------------\n')
                data_tracking = json.loads(vehicleJson[i])
                vehicle = Vehicle()
                try:
                    vehicle['model'] = data_tracking['Model']['model_name']
                    vehicle['year'] = data_tracking['Model']['model_year']
                    if vehicle not in vehicles and re.match('[0-9]', vehicle['year']):
                        vehicleDataTrackingDict[vehicle['model']] = vehicleJsonRaw
                        # print('vehicle Json = ', vehicleJsonRaw)
                        count += 1
                        vehicles.append(vehicle)
                        # print('added vehicle: ', vehicle)
                    # else:
                    #     print('duplicate detected: ', vehicle)
                except KeyError:
                    print('not a car')
        # print('==============================================\n')
        # print(f'found {count} models: {vehicles}')
        # print('vehicleDataTrackingDict = ', vehicleDataTrackingDict)
        for baseModel in vehicles:
            url = self.start_urls[0] + baseModel['model']
            href = response.xpath('//a[@data-tracking="' + vehicleDataTrackingDict[baseModel['model']] + '"]/@href').get()
            # print('href: ', href)
            args = {'stop': False, 'model': baseModel['model']}
            # yield scrapy.Request(url=url, callback=self.parse_models, cb_kwargs=args)
            yield response.follow(url=href, callback=self.parse_models, cb_kwargs=args)

    def parse_models(self, response, **kwargs):
        args = kwargs
        args['stop'] = True
        options = response.xpath('//div[@role="listbox"]/a[@role="option"]/@href').getall()
        for href in options:
            # print('href: ', href)
            yield response.follow(href, callback=self.parse_trims, cb_kwargs=args, dont_filter=True)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        # on ilx page, packages div starts at line 2734

        package_ids = response.xpath('//div[@id="packages"]//a[@role="tab"]/@tab-id').getall()

        for i in range(0, len(package_ids)):
            packageNameXpath = '//div[@id="packages"]//a[@tab-id="' + package_ids[i] + '"]'
            package = response.xpath(packageNameXpath + '/@aria-controls').get()
            msrp = str(response.xpath(packageNameXpath + '/span[@class="acr-paragraph-7"]/text()').get())
            msrp = msrp[msrp.find('$'):].strip()

            vehicle = Vehicle()
            vehicle['make'] = self.name.upper()
            url = str(response.url)
            # vehicle['model'] = url[url.rfind('/')+1:]  # DONE: find a better way to do this
            vehicle['model'] = kwargs['model']
            year = response.xpath('//div[@role="listbox"]/a[@role="option"]/text()').get()
            vehicle['year'] = year
            if vehicle['model'] == package.lower():
                vehicle['trim'] = 'base'
            else:
                vehicle['trim'] = remove_html_tags(package)
            vehicle['msrp'] = msrp
            vehicles.append(vehicle)

        # packageNames = response.xpath('//div[@id="packages"]//a[@role="tab"]/@aria-controls').getall()
        #
        # for i in range(0, len(packageNames)):
        #     packageNames[i] = remove_html_tags(packageNames[i])
        #
        # print(packageNames)

        return vehicles
