from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

# This collects all dynamically imported scrapy modules and data files.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('scrapy')
# datas.append(('C:\\Users\\Tyler\\.virtualenvs\\fiwize_vehicle_data_tracker\\Scripts\\scrapy.exe', '.'))

hiddenimports = (
    collect_submodules('scrapy') +
    collect_submodules('scrapy.pipelines') +
    collect_submodules('scrapy.utils') +
    collect_submodules('scrapy.extensions')
)
