# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import pathlib

import scrapy
from itemadapter import ItemAdapter
from scrapy.exporters import CsvItemExporter

import re
import csv
from scrapy.exceptions import DropItem
from vehicle_data_tracker.utilities import STANDARD_FIELDS
from vehicle_data_tracker.utilities import MAKES_LIST


class FormatPipeline:
    def prettify_price(self, price: str):
        """
        Returns a copy of the provided string ``price`` with commas and a dollar sign included. Returns the string
        unchanged if these symbols are already present.
        """
        price = price.strip()
        if price != '':
            if ',' not in price:
                price_pretty = ''
                for i in range(0, len(price)):
                    if price[len(price) - (i + 1)].isdigit():
                        price_pretty += price[len(price) - (i + 1)]
                        if (i + 1) % 3 == 0 and (i + 1) < len(price):
                            price_pretty += ','
                price_pretty += '$'
                price_pretty = ''.join(reversed(list(price_pretty)))
                return price_pretty
            elif '$' not in price:
                price = '$' + price
        return price

    def process_item(self, vehicle, spider):
        vehicle['year'] = str(vehicle['year'])
        if vehicle['year'] != '' and not re.match('[0-9]', vehicle['year']):
            vehicle['year'] = ''.join(re.findall('[0-9]{4}', vehicle['year']))
            if vehicle['year'] == '':
                raise DropItem('invalid year')
        # remove extraneous characters from the price
        vehicle['msrp'] = str(vehicle['msrp'])
        priceStr = vehicle['msrp']
        if priceStr.find('.') != -1:
            priceStr = priceStr[0:priceStr.find('.')]
        vehicle['msrp'] = ''.join(re.findall('[$]|[0-9]|[,]', priceStr))
        vehicle['msrp'] = self.prettify_price(vehicle['msrp'])
        # remove any characters that are not alphanumeric, dashes, slashes, spaces, periods, or quotes (typically only
        #  included to represent feet/inches)
        trimFiltered = re.findall('[a-zA-Z0-9-/.\'\"]+', vehicle['trim'])
        modelFiltered = re.findall('[a-zA-Z0-9-/.]+', vehicle['model'])
        # while '' in trimFiltered:
        #     trimFiltered.remove('')  # get rid of empty matches
        # while '' in modelFiltered:
        #     modelFiltered.remove('')
        vehicle['trim'] = ' '.join(trimFiltered)
        vehicle['model'] = ' '.join(modelFiltered)

        # strip the make from the model name, for more concise data
        makePattern = re.compile(vehicle['make'] + '\s', re.IGNORECASE)
        vehicle['model'] = re.sub(makePattern, '', vehicle['model']).strip()

        # then, strip (case-insensitive) the make and model name from the trim name, for even more concise data
        vehicle['trim'] = re.sub(makePattern, '', vehicle['trim']).strip()
        modelPattern = re.compile(vehicle['model'] + '\s', re.IGNORECASE)
        if not re.fullmatch(modelPattern, vehicle['trim']):
            vehicle['trim'] = re.sub(modelPattern, '', vehicle['trim']).strip()
        # finally, strip the year from the make and trim, for those slippery edge cases
        #   (cough cough Jaguar 2021 F-Type cough)
        vehicle['make'] = vehicle['make'].replace(vehicle['year'], '').strip()
        vehicle['trim'] = vehicle['trim'].replace(vehicle['year'], '').strip()
        # print(f'FormatPipeline: item {vehicle["year"]} {vehicle["model"]} {vehicle["trim"]} has been processed by the Format Pipeline')
        return vehicle


class DuplicatePipeline:
    def __init__(self):
        self.ids_seen = set()

    # noinspection PyAttributeOutsideInit
    def open_spider(self, spider):
        """
        I would like to use this docstring to apologize for how incredibly inconsistent I am with my naming conventions.

        Anyhow, here's what this pipeline does. When the spider is opened, vehicles.csv is opened for reading if it
        exists. A csv reader reads each line, adding the entry to list_purged and to the set ids_seen if purge is
        disabled or if the make of the entry does not match the make(s) of the spider. Otherwise, the entry is ignored.
        Then, if purge is enabled, a csv writer overwrites vehicles.csv with the contents of list_purged.

        If vehicles.csv does not exist, it is created for appending.

        In either case, self.exporter is initialized with vehicles.csv as the target file. Finally, call
        exporter.start_exporting.
        """
        # output_dir = pathlib.Path(__file__).parent
        # if hasattr(spider, 'outputdir'):
        #     output_dir = spider.outputdir
        # output_file = os.sep.join((str(output_dir), 'vehicles.csv'))
        output_file = 'vehicles.csv'
        try:
            purge = False
            group_spider = spider.name in MAKES_LIST['groups']
            try:
                if int(spider.purge) == 0:
                    pass
                    # print('purge disabled')
                elif int(spider.purge) == 1:
                    purge = True
                    # print('purge enabled')
                else:
                    raise AttributeError
            except AttributeError:
                purge = False
                print('missing or invalid purge argument, defaulting to disabled')
            vehicles_csv_read = open(output_file, 'r', newline='')
            # print('====================( opened file vehicles.csv for reading )====================')
            vehicle_csv_reader = csv.reader(vehicles_csv_read)
            include_headers = False
            list_purged = []
            make = spider.name
            if hasattr(spider, 'name_long'):
                make = spider.name_long
            for row in vehicle_csv_reader:
                # print(f'row {vehicle_csv_reader.line_num}: {row}')
                if row[0].lower() == 'year':
                    list_purged.append(row)  # grabs the header at the beginning of the loop
                else:
                    if group_spider:
                        if not (purge and row[1].lower() in spider.makes):
                            list_purged.append(row)
                            self.ids_seen.add(''.join(row[0:4]))
                    else:
                        # If purge is disabled, add this entry to the list and id set.
                        # If purge is enabled and the make of the entry matches that of the spider currently running,
                        #  do NOT add it to the list or the id set.
                        if not (purge and row[1].lower() == make.lower()):
                            list_purged.append(row)
                            self.ids_seen.add(''.join(row[0:4]))
                            # print('id added: ', ''.join(row[0:4]))
            if vehicle_csv_reader.line_num == 0:
                include_headers = True
            vehicles_csv_read.close()
            if purge:
                vehicles_csv_write = open(output_file, 'w', newline='')
                # print('====================( opened file vehicles.csv for writing )====================')
                vehicle_csv_writer = csv.writer(vehicles_csv_write)
                vehicle_csv_writer.writerows(list_purged)
                vehicles_csv_write.close()

            # print('include_headers ==', include_headers)
            self.vehicles_csv = open(output_file, 'ab')
            self.exporter = CsvItemExporter(self.vehicles_csv,
                                            include_headers_line=include_headers,
                                            fields_to_export=STANDARD_FIELDS)
        except FileNotFoundError:
            print('vehicles.csv does not exist')
            self.vehicles_csv = open(output_file, 'ab')
            self.exporter = CsvItemExporter(self.vehicles_csv,
                                            include_headers_line=True,
                                            fields_to_export=STANDARD_FIELDS)
        self.exporter.start_exporting()
        # self.vehicles_csv.close()

    def close_spider(self, spider):
        if hasattr(self, 'exporter'):
            self.exporter.finish_exporting()
            self.vehicles_csv.close()

    def process_item(self, vehicle, spider):
        trim_id = vehicle['year'] + vehicle['make'] + vehicle['model'] + vehicle['trim']
        # if vehicle['year'] is not None:
        #     trim_id = vehicle['year'] + trim_id
        if trim_id in self.ids_seen:
            raise DropItem(f'Duplicate trim found:')
        else:
            self.ids_seen.add(trim_id)
            self.exporter.export_item(vehicle)
            # print(f'DuplicatePipeline: item {trim_id} has been processed by the Duplicate Pipeline')
            return vehicle
