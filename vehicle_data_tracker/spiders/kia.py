"""
Scrapes data from the Kia US website. Currently, there are enough differences in the Hyundai and Kia websites to
warrant multiple spiders, but that may change in the future.

Author: Tyler Jaafari
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *


class KiaSpider(scrapy.Spider):
    name = 'kia'
    allowed_domains = ['www.kia.com']
    start_urls = ['https://www.kia.com/us/en']

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

    def gen_api_link(self, series_id: str, year: str):
        api_link = f'https://www.kia.com/us/services/en/bnpVehicle/{series_id}/{year}'
        return api_link

    def parse(self, response, **kwargs):
        allVehiclesLink = response.xpath('//a[contains(., "Vehicles")]/@href').get()
        # allVehiclesLink = allVehiclesLink.replace('http', 'https')

        yield response.follow(url=allVehiclesLink, callback=self.parse_models, cb_kwargs=kwargs)

    def parse_models(self, response, **kwargs):
        vehicleCards = response.xpath('//meet-the-fleet-card')

        for card in vehicleCards:
            # filter out the 'upcoming' section
            if card.xpath('template/div[contains(@class, "vehicle-info-order")]').get() is not None:
                modelYear = card.attrib[':year'].strip("\'")
                modelName = card.attrib[':name'].strip("\'")
                args = {'model': modelName, 'year': modelYear}
                modelLink = card.xpath('template/div/a/@href').get()
                yield response.follow(url=modelLink, callback=self.nav_to_specs, cb_kwargs=args)

    def nav_to_specs(self, response, **kwargs):
        # TODO: it seems that some specs pages don't work at all (including the user-facing side, this is an issue that
        #  KIA will have to fix) so additional parsing functionality must be added for accessing the API directly. If
        #  effective, this MAY replace the previous logic entirely.

        linkThatHasInfo = str(response.xpath('//a[contains(@href, "seriesId")]/@href').get())
        queryString = linkThatHasInfo[linkThatHasInfo.find('?'):]
        queryList = queryString.split('&')
        if 'year' in queryList[0]:
            year = queryList[0][queryList[0].find('=')+1:]
            seriesId = queryList[1][queryList[1].find('=')+1:]
        else:
            seriesId = queryList[0][queryList[0].find('=')+1:]
            year = queryList[1][queryList[1].find('=')+1:]
        api_link = self.gen_api_link(seriesId, year)
        yield response.follow(url=api_link, callback=self.parse_trims_api, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        Not currently in use, but should be kept in case something else changes with KIA's website.

        :return: a list of vehicles
        """
        vehicles = []

        if response.xpath('//div[@data-trim]').get() is not None:
            for trimData in response.xpath('//div[@data-trim]'):
                trimName = trimData.attrib['data-trim']
                msrp = trimData.xpath('../div[contains(@class, "trim-text")]/text()').get()

                trim = Vehicle()
                trim['make'] = self.name.upper()
                trim['model'] = kwargs['model']
                trim['year'] = kwargs['year']
                trim['trim'] = trimName
                trim['msrp'] = msrp

                vehicles.append(trim)
        else:
            for div in response.xpath('//tab-slider/div'):
                trimName = div.xpath('text()').get().strip()
                if trimName != '':
                    overview = response.xpath(f'//div[@class="single-spec__overview"][contains(@v-if, "{trimName}")]')
                    msrp = overview.xpath('//span[@class="hero-content__text-heading"]/text()').get()
                    vehicle = Vehicle({'make': self.name.upper(),
                                       'model': kwargs['model'],
                                       'year': kwargs['year'],
                                       'trim': trimName,
                                       'msrp': msrp})

                    vehicles.append(vehicle)

        return vehicles

    # DONE: have this method recursively check everything under 'children' in the value of the 'vehicle' key until it
    #  reaches a set of children whose type is "trim"
    def parse_trims_api(self, response, **kwargs):
        vehicleDoc = response.json()
        vehicles = []
        self.parse_trims_api_helper(vehicles, vehicleDoc['vehicle'], **kwargs)
        return vehicles

    def parse_trims_api_helper(self, vehicles: list, vehicle_data: dict, **kwargs):
        if vehicle_data['type'] != 'trim':
            for child in vehicle_data['children']:
                self.parse_trims_api_helper(vehicles, child, **kwargs)
        else:
            trimName = vehicle_data['code']
            msrp = vehicle_data['msrp']
            vehicle = Vehicle({'make': self.name.upper(),
                               'model': kwargs['model'],
                               'year': kwargs['year'],
                               'trim': trimName,
                               'msrp': msrp})
            vehicles.append(vehicle)
