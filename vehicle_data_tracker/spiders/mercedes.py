import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json


class MercedesSpider(scrapy.Spider):
    name = 'mercedes'
    allowed_domains = ['www.mbusa.com']
    start_urls = ['https://www.mbusa.com/en/home']

    name_long = 'mercedes-benz'

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
        'long_name': name_long,
        'ITEM_PIPELINES': {
            'vehicle_data_tracker.pipelines.FormatPipeline': 300,
            'vehicle_data_tracker.pipelines.DuplicatePipeline': 400,
        }
    }

    def parse(self, response, **kwargs):
        allVehiclesLink = response.xpath('//*[contains(@id, "footer")]//a[contains(., "All Vehicles")]/@href').get()

        yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        """
        Mercedes-Benz is very nicely organized. The tiles on the All Vehicles page have drop-down menus listing
        their sub-models, including prices. The year requires a bit more digging though.

        :return:
        """
        for vehicleTile in response.xpath('//div[@class="all-vehicles__class module-separator"]'):
            fullModelName = vehicleTile.xpath('.//h3/text()').get()
            trimLink = vehicleTile.xpath('.//ul/li/a/@href').get()  # gets the first trim link from the drop-down list
            args = {'model': fullModelName}

            yield response.follow(url=trimLink, callback=self.parse_trims, cb_kwargs=args)

    def parse_trims(self, response, **kwargs):
        vehicles = []

        trimSelectorList = response.xpath('//li[contains(@class, "model-selector__menu-item")]')

        for trimTile in trimSelectorList:
            year = trimTile.attrib['data-year']
            trimName = trimTile.xpath('h5/text()').get()
            msrp = ''.join(trimTile.xpath('text()').getall()).strip()

            vehicle = Vehicle()
            vehicle['make'] = self.name_long.upper()
            vehicle['model'] = kwargs['model']
            vehicle['year'] = year
            vehicle['trim'] = trimName
            vehicle['msrp'] = msrp

            vehicles.append(vehicle)

        return vehicles
