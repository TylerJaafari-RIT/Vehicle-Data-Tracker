"""
Scrapes data from the Hyundai USA website. Currently, there are enough differences in the Hyundai and Kia websites to
warrant multiple spiders, but that may change in the future.

Author: Tyler Jaafari
Version: 1.1
    1.1 - changed source of trim data to eliminate duplicate trims
"""

import scrapy
import json
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import STANDARD_FIELDS


class HyundaiSpider(scrapy.Spider):
    name = 'hyundai'
    allowed_domains = ['www.hyundaiusa.com']
    start_urls = ['https://www.hyundaiusa.com/us/en/']

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
        allVehiclesLink = response.xpath('//header[contains(@id, "global")]//a[contains(., "Vehicles")]/@href').get()

        yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        vehicleItems = response.xpath('//div[@class="vbws-car"]//a[contains(@class, "car-link")]')
        for item in vehicleItems:
            # it appears that the json is contained within a single-item list... -_-
            modelData = json.loads(item.attrib['data-analytics-vehicles'])
            modelName = modelData[0]['nameplate']
            modelYear = modelData[0]['model_year']
            modelLink = item.attrib['href']
            args = {'model': modelName, 'year': modelYear}
            yield response.follow(url=modelLink, callback=self.nav_to_trims, cb_kwargs=args)

    def nav_to_trims(self, response, **kwargs):
        trimsLink = response.xpath('(//a[@aria-label="Trims"] | //a[@aria-label="TRIMS"])/@href').get()
        yield response.follow(url=trimsLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        trimButtons = response.xpath('//button[@data-trim-id]')
        for button in trimButtons:
            trimName = button.attrib['data-trim-name']
            msrp = button.xpath('.//div[@data-price="value"]/text()').get()
            vehicle = Vehicle({'make': self.name.upper(),
                               'model': kwargs['model'],
                               'year': kwargs['year'],
                               'trim': trimName,
                               'msrp': msrp})

            vehicles.append(vehicle)

        return vehicles
