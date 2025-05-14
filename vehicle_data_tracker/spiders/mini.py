import scrapy
from vehicle_data_tracker.items import Vehicle
from vehicle_data_tracker.utilities import *


class MiniSpider(scrapy.Spider):
    name = 'mini'
    allowed_domains = ['www.miniusa.com']
    start_urls = ['https://www.miniusa.com/']

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
        tiles = response.xpath('//div[contains(@class, "SiteNav")][contains(@class, "models")]'
                               '//div[contains(@class, "l-col-3")]')
        for modelTile in tiles:
            modelLink = modelTile.xpath('a/@href').get()
            modelName = modelTile.xpath('a/div/p/text()').get()
            args = {'model': modelName}

            yield response.follow(url=modelLink, callback=self.nav_to_specs, cb_kwargs=args)

    def nav_to_specs(self, response, **kwargs):
        specsLink = response.xpath('//a[contains(@href, "specs")]/@href').get()

        if specsLink is not None:
            yield response.follow(url=specsLink, callback=self.parse_trims, cb_kwargs=kwargs)

    def parse_trims(self, response, **kwargs):
        """
        The specs page has a large table with a variety of information. All that is needed here, however,
        is the first row.

        The crawl will most often parse the Electric models page first for some reason, and the
        "CHECK OUT THE FULL SPECS" link there goes to the exact same page as the one for the Hardtop 2-Door.
        Because of this, those trims are added with "Electric" as the model name, and sometimes when this spider
        is run again with purge off, it parses the Hardtop page first and adds them as separate models. For this
        reason, the model name used is the one found on the specs page itself, not in parse().

        It should be noted from this and the similar Alfa Romeo bug that there is no guarantee about the order in which
        subsequent requests are made and processed by scrapy, even though a list returned by response.xpath() will be
        in the order that the elements are found in the page source.

        Additionally, there is no way to get the Clubman from HTML, and the api cannot be accessed without a key.

        Finally, since the trims in the John Cooper Works lineup are all just variations of the other models, and there
        is no other way to catch these as duplicates, there must be a hard-coded check against them here.

        :return: a list of vehicles
        """
        model = response.xpath('//thead//h1/text()').get().replace('Specs', '').strip()
        if 'John Cooper Works' not in model:
            vehicles = []

            year = str(response.xpath('//thead//p[contains(., "Year")]/text()').get())
            year = year[year.rfind(' '):]
            priceRow = response.xpath('//tbody/tr[contains(., "Price")]')
            for col in priceRow.xpath('td[@data-grouplabel]'):
                trimName = col.attrib['data-grouplabel']
                msrp = col.xpath('text()').get()
                vehicle = Vehicle()
                vehicle['make'] = self.name.upper()
                vehicle['model'] = model
                vehicle['year'] = year
                vehicle['trim'] = trimName
                vehicle['msrp'] = msrp
                vehicles.append(vehicle)

            return vehicles
