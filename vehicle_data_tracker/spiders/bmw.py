"""
Handles the scraping and processing of data from the BMW USA website.

Author: Tyler Jaafari

Version: 1.3
    1.1 - model name now retrieved from data-vehicles JSON rather than HTML
    1.3 - removed 'base' trim names, added documentation
"""

import scrapy
from vehicle_data_tracker.items import Vehicle
import json
from vehicle_data_tracker.utilities import *


class BmwSpider(scrapy.Spider):
    name = 'bmw'
    allowed_domains = ['www.bmwusa.com']
    start_urls = ['https://www.bmwusa.com/']

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
        possible methods of parsing:
        a) go to Build Your Own page, from there we can access a list of all models which leads to pages which
          already have all the sub-models listed
        b) access Models menu from home page, go through each model from there (I'm really leaning towards this one
          because of how the tags are labelled) (YEAH WE'RE DOING THIS ONE)

        from the home page (or any page on the site, like with acura):
        1. Search for div with attribute @data-filer="all models"
        2. Within that div, get every div with a @data-default-tab attribute and get that value (it's JSON)
        3. json.loads
        4. use the json 'title' key and look for <a> tags with @title=[the title value]

        :return: a list of vehicles, eventually
        """
        allModelsDiv = response.xpath('//div[@data-filter="all models"]')
        modelDivs = allModelsDiv.xpath('.//div[@data-default-tab]')
        for div in modelDivs:
            modelData = json.loads(div.attrib['data-default-tab'])
            seriesName = modelData['title']
            modelPage = modelData['destinationUrl']
            args = {'series': seriesName}
            yield response.follow(url=modelPage, callback=self.parse_models, cb_kwargs=args)

    def parse_models(self, response, **kwargs):
        # update: THERE IS JSON FOR EACH MODEL IN THE 'Build Your Own' section OF EACH MODEL (not the 'Build Your Own'
        #       section that I mentioned earlier)

        # first, look for the navbar at the top of the page. if it's there, get the build link and follow it
        if response.xpath('//ul[@class="globalnav-local__links"]').get() is not None:
            navbar = response.xpath('//ul[@class="globalnav-local__links"]')
            href = navbar.xpath('.//a[contains(./text(), "Build")]/@href').get()
            if href is not None:
                yield response.follow(url=href, callback=self.parse_trims, cb_kwargs=kwargs)
            else:
                pass
        # if there is no navbar, then that means the series has further subdivisions of models (such as the 2),
        #  in which case follow each model link and call this function back
        elif response.xpath('//a[@aria-label="Explore Model"]').get() is not None:
            for a in response.xpath('//a[@aria-label="Explore Model"]'):
                href = a.attrib['href']
                yield response.follow(url=href, callback=self.parse_models, cb_kwargs=kwargs)
        # NOTE: the M models page should be ignored entirely
        else:
            print(f'Error with parsing series {kwargs["series"]}')

    def parse_trims(self, response, **kwargs):
        """
        Parses JSON data contained in the wrapper div on the 'Build Your Own' page of each model.

        :param response: the response received from the URL
        :param kwargs:
        :return: a list of vehicles
        """
        vehicles = []

        data_vehicles = response.xpath('//div[@data-vehicles]/@data-vehicles').get()
        dataJsonList = json.loads(data_vehicles)
        for trimData in dataJsonList:
            trim = Vehicle()
            modelName = trimData['modelOffer']['seriesName']
            trim['make'] = self.name.upper()
            trim['model'] = modelName
            trimName = trimData['modelOffer']['modelDescription']
            trim['trim'] = trimName
            trim['year'] = trimData['modelOffer']['year']
            trim['msrp'] = trimData['modelOffer']['price']
            vehicles.append(trim)

        return vehicles
