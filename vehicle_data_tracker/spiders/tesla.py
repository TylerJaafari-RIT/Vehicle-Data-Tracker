"""
Scrapes data from the Tesla website. Like Elon Musk, this website is unique and a little hard to understand. Currently,
the best method I can contrive is to skip the home page and go straight to the compare page, where an id (which may
or may not change) can be found that must be used to access an api doc with all the models and trims.

Author: Tyler Jaafari
Version: 1.2
    1.1 - added handling of 403 status code
    1.2 - year is now set to current year + 1
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *
import json
import datetime
from scrapy import exceptions


class TeslaSpider(scrapy.Spider):
    name = 'tesla'
    allowed_domains = ['www.tesla.com']
    start_urls = ['https://www.tesla.com/compare']

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
        'HTTPERROR_ALLOWED_CODES': [403],
        'ITEM_PIPELINES': {
            'vehicle_data_tracker.pipelines.FormatPipeline': 300,
            'vehicle_data_tracker.pipelines.DuplicatePipeline': 400,
        }
    }

    def gen_api_link(self, compare_id: str):
        api_link = f'https://{self.allowed_domains[0]}/api/tesla/compare/v0/{compare_id}'
        return api_link

    def parse(self, response, **kwargs):
        """
        Sometimes, the response from the compare page is 403, which would normally prevent the program from proceeding
        entirely, and result in no vehicles being collected.
        [REDACTED] In the event this happens, simply use the hardcoded ID
        below, which has not changed from the time this spider was first written and yesterday, when this problem was
        addressed.

        It is unknown why the server refuses access very occasionally but allows it the majority of time, but in any
        case, this solution will have to be accepted due to the difficulty of reproducing the issue. [REDACTED]

        ...in the event this happens, the server will continue to refuse access for the duration of this process. There
        is no way to get around this issue when it happens, except to run the spider a second time. It is unknown why
        the server refuses access very occasionally but allows it the majority of the time, but in any case, the spider
        should run successfully the next time it is run.

        :return: a Request
        """
        if response.status != 200:
            print('===========================', response.status, '===========================')
            # dataCompareId = '256799'
            raise exceptions.CloseSpider('Server denied access. Please run again.')
        else:
            dataCompareId = response.xpath('//section[@data-compare-data-id]/@data-compare-data-id').get()
        api_link = self.gen_api_link(dataCompareId)

        yield scrapy.Request(url=api_link, callback=self.parse_trims)

    def parse_trims(self, response, **kwargs):
        """
        Parses the JSON data collected from the Tesla API. Since the website does not use years to categorize its
        vehicles, the year inserted in the database should be the current year + 1.

        :return: a list of vehicles
        """
        vehicles = []

        compareData = response.json()
        for modelData in compareData['vehicles']:
            model = modelData['label']
            for trimData in modelData['trims']:
                trimName = trimData['label']
                msrp = ''
                for spec in trimData['specs']:
                    if spec['type'] == 'price':
                        msrp = spec['lines'][0]['text']
                        break
                year = datetime.date.today().year + 1
                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': model,
                                   'year': year,
                                   'trim': trimName,
                                   'msrp': msrp})
                vehicles.append(vehicle)

        return vehicles
