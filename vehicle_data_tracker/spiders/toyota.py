import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *

# TODO: some trims have "2021" as their price, and some are missing their price entirely
class ToyotaSpider(scrapy.Spider):
    name = 'toyota'
    allowed_domains = ['www.toyota.com']
    start_urls = ['https://www.toyota.com/']

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
        allVehiclesLink = response.xpath('//a[contains(., "All")][contains(., "Vehicles")]/@href').get()

        yield response.follow(url=allVehiclesLink, callback=self.parse_models)

    def parse_models(self, response, **kwargs):
        """
        //div[@class="vehicles-grid"]//div[contains(@class, "vehicle-card")]
            .//a[@data-aa-link-text="Explore"]

        :return: a list of vehicles, eventually
        """
        for vehicleCard in response.xpath('//div[@class="vehicles-grid"]//div[contains(@class, "vehicle-card")]'):
            model = vehicleCard.attrib['data-display-name']
            year = vehicleCard.attrib['data-year']
            modelLink = vehicleCard.xpath('.//a[@data-aa-link-text="Explore"]/@href').get()
            args = {'model': model, 'year': year}

            yield response.follow(url=modelLink, callback=self.parse_trims, cb_kwargs=args)

    def parse_trims(self, response, **kwargs):
        """
        //div[@class="vehicle-card-v2"]/p/text()

        :return: a list of vehicles
        """
        vehicles = []

        if response.xpath('//div[@class="vehicle-card-v2"]').get() is not None:
            for vehicleCard in response.xpath('//div[@class="vehicle-card-v2"]'):
                trimName = vehicleCard.attrib['data-title']
                msrp = vehicleCard.attrib['data-msrp']
                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': msrp})
                vehicles.append(vehicle)

        elif response.xpath('//div[@class="vehicle-card-v1"]').get() is not None:
            for vehicleCard in response.xpath('//div[@class="vehicle-card-v1"]'):
                trimData = vehicleCard.xpath('.//div[@class="info"]')
                trimName = trimData.xpath('a[@class="title"]/text()').get()
                msrp = trimData.xpath('div[@class="description"]/text()').get()
                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': msrp})
                vehicles.append(vehicle)
        else:
            for vehicleCard in response.xpath('//div[contains(@class, "vehicle-card")][@data-series]'):
                trimName = vehicleCard.attrib['data-aa-series-grade']
                msrp = vehicleCard.attrib['data-aa-series-msrp']
                vehicle = Vehicle({'make': self.name.upper(),
                                   'model': kwargs['model'],
                                   'year': kwargs['year'],
                                   'trim': trimName,
                                   'msrp': msrp})
                vehicles.append(vehicle)

        return vehicles
