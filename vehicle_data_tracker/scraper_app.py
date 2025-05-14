"""
The application that ties everything together. GUI made with Tkinter, web crawling made with Scrapy.

Author: Tyler Jaafari
Version: 1.1.0
    0.5.0 - created basic GUI
    0.7.0 - refined GUI, implemented all spiders, added "Purge?" button
    0.8.0 - made the "Crawl!" button do something
    0.8.5 - gave the "Crawl!" button the ability to do all the things
    0.8.6 - updateLabel no longer says "done" after "Crawl!" is clicked if the label's text is red
    0.9.0 - added multi-threading to avoid app freezing during crawl
    0.9.2 - added progress bar
    0.9.3 - added help info + button to hide/reveal help info
    0.9.4 - added messagebox to display help info instead of a label

    1.0.0 - created scraper.spec
          - implemented console-less running of subprocesses
          - run "pyinstaller scraper.spec" from the inner vehicle_data_tracker directory to compile a single
            executable of the program.

    1.1.0 - okay that did not actually work
          - implemented dynamic creation of virtual environment for installing and launching scrapy
"""
import os
import pathlib
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
from utilities import MAKES_LIST
import subprocess
import threading


class ScraperApp:
    """
    To run from console, enter:

    scrapy runspider -a purge=(0 or 1) (make).py
    """
    UPDATE_ALL_TEXT = '[UPDATE ALL]'

    HELP_TEXT = ['Use the dropdown menu to select a make (or make group) to collect data from.',

                 'Check the box labeled "Purge" to remove old entries of the chosen make (recommended after'
                 ' app is updated). Leave it unchecked for duplicate-checking instead.',

                 'When you are ready, click the "Crawl!" button. Running the process on all makes can take several minutes.',

                 'Please do not close the app until the process is complete.']

    OUTPUT_DIR = pathlib.Path(__file__).parent

    def __init__(self, master: Tk):
        master.title('S.C.R.A.P.E.R.')
        self.parentPath = pathlib.Path(__file__).parent
        iconPath = os.sep.join((str(self.parentPath), 'media', 'FiWize_Symbol-smiley.png'))
        master.iconphoto(True, [PhotoImage(file=iconPath)])
        master.rowconfigure(0, weight=1)
        master.rowconfigure(1, weight=1)
        master.rowconfigure(2, weight=1)
        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=2)
        master.columnconfigure(2, weight=1)
        master.minsize(width=650, height=380)
        self.headerLabel = ttk.Label(master,
                                     text='Welcome to the Selective Car Retrieval And Processing Efficient Robot')
        self.headerLabel.config(wraplength=250, justify=CENTER, font=('Courier', 12))
        self.headerLabel.grid(row=0, column=1, padx=40, pady=5, ipady=5, stick='n')

        self.logoLabel = ttk.Label(master, text='[LOGO]')
        logoPath = os.sep.join((str(self.parentPath), 'media', 'FiWize-Logo.png'))
        logo = Image.open(logoPath)
        self.logoSmall = ImageTk.PhotoImage(logo.resize((150, 42)))
        self.logoLabel.config(image=self.logoSmall)
        self.logoLabel.grid(row=0, column=2, padx=5, pady=5, ipadx=5, stick='ne')

        self.authorLabel = ttk.Label(master, text='Created by Tyler Jaafari')
        self.authorLabel.config(font=('Arial', 8))
        self.authorLabel.grid(row=2, column=0, padx=2, pady=2, stick='sw', rowspan=2)

        self.helpButton = ttk.Button(master, text='Help', command=self.show_help_text)
        self.helpButton.grid(row=0, column=0, stick='nw')

        self.helpLabel = ttk.Label(master, wraplength=170)
        self.helpLabel.grid(row=0, column=1, rowspan=2, columnspan=2, padx=5, stick='se')

        self.updateFrame = ttk.LabelFrame(master, height=200, width=200, text='Update Database')
        self.updateFrame.grid(row=1, column=1, ipadx=20, ipady=20, padx=45, pady=40)

        self.purgeFlag = IntVar(value=0)
        self.purgeCheckButton = ttk.Checkbutton(self.updateFrame, text='Purge', variable=self.purgeFlag)
        self.purgeCheckButton.pack(anchor=NE)

        makes = [self.UPDATE_ALL_TEXT]
        longest = 0
        for make in MAKES_LIST['available']:
            makes.append(make)
            if len(make) > longest:
                longest = len(make)
        for make in MAKES_LIST['unavailable']:
            makes.append(make + ' (NOT IMPLEMENTED)')
            if len(make) > longest:
                longest = len(make)

        self.selectedMake = StringVar()
        self.comboBox = ttk.Combobox(self.updateFrame, textvariable=self.selectedMake)
        self.comboBox.config(values=makes, width=longest)
        self.comboBox.pack()

        self.updateLabel = ttk.Label(self.updateFrame, wraplength=200)
        self.crawlButton = ttk.Button(self.updateFrame, text='Crawl!', command=self.crawl_button_click)
        self.crawlButton.pack()
        self.updateLabel.pack()

        self.closeAppCautionLabel = ttk.Label(master, text='', justify=CENTER)
        self.closeAppCautionLabel.grid(row=2, column=1)

        self.progressBar = ttk.Progressbar(self.updateFrame, orient='horizontal', mode='indeterminate', length=200)

        if pathlib.Path(__file__).parent.joinpath('vehicle_data_tracker').exists():
            self.spidersPath = os.sep.join((str(pathlib.Path(__file__).parent), 'vehicle_data_tracker', 'spiders'))
        else:
            self.spidersPath = os.sep.join((str(pathlib.Path(__file__).parent), 'spiders'))

        self.disable_critical_controls()
        self.closeAppCautionLabel.config(text='Initializing, please wait...')
        init_venv_thread = threading.Thread(group=None, target=self.install_venv, name='init_venv_thread')
        init_venv_thread.start()

    def install_venv(self):
        if not self.parentPath.joinpath('scraper_env').exists():
            if sys.platform == "win32":
                subprocess.run('where python', shell=True)
                subprocess.run(f'py -m venv "{self.parentPath.joinpath("scraper_env")}"', shell=True)
            else:
                subprocess.run(f'python3 -m venv "{self.parentPath.joinpath("scraper_env")}"', shell=True)

            parentPathStr = str(self.parentPath)
            if sys.platform == "win32":
                pip_command = os.sep.join((parentPathStr, 'scraper_env', 'Scripts', 'pip'))
                subprocess.run(f'"{pip_command}" install --upgrade pip', shell=True)
                print('--------------------------------------------------------------------------------')

                subprocess.run(f'"{pip_command}" install scrapy', shell=True)
                print('--------------------------------------------------------------------------------')
            else:
                activate_command = f'source {os.sep.join(("scraper_env", "bin", "activate"))}'
                p = subprocess.Popen(activate_command, universal_newlines=True)
                print(p.communicate(input='which python'))
        self.closeAppCautionLabel.config(text='')
        self.enable_critical_controls()

    def crawl_button_click(self):
        """
        Runs the spider selected in the combo box. Displays an error message if the selection is invalid.
        """
        if self.selectedMake.get() == self.UPDATE_ALL_TEXT:
            spiders = []
            for make in MAKES_LIST['available']:
                spiders.append((make, MAKES_LIST['available'][make]))
            args = {'spiders': spiders}
            self.disable_critical_controls()
            self.closeAppCautionLabel.config(text='This process may take several minutes.'
                                                  '\nPlease do not close the app while this is running.')
            self.progressBar.pack()
            self.progressBar.start()
            crawl_all_thread = threading.Thread(group=None, target=self.crawl_multiple_spiders, name='crawl_all',
                                                kwargs=args)
            crawl_all_thread.start()
        else:
            try:
                spider = MAKES_LIST['available'][self.selectedMake.get()]
                spiderPath = os.sep.join((str(self.spidersPath), spider))
                scrapyPath = os.sep.join((str(self.parentPath), 'scraper_env', 'Scripts', 'scrapy'))
                process_args = f'"{scrapyPath}" runspider -a purge={self.purgeFlag.get()} "{spiderPath}"'
                args = {'process_args': process_args}
                self.updateLabel.config(text='Running ' + self.selectedMake.get() + '...', foreground='black')
                self.disable_critical_controls()
                self.closeAppCautionLabel.config(text='Please do not close the app while this is running.')
                self.progressBar.pack()
                self.progressBar.start(interval=20)
                crawl_thread = threading.Thread(group=None, target=self.start_crawl,
                                                name=f'crawl_{spider.replace(".py", "")}', kwargs=args)
                crawl_thread.start()
            except KeyError:
                self.updateLabel.config(text='Please enter a valid make or choose from the list.', foreground='red')

    def crawl_multiple_spiders(self, spiders: list, **kwargs):
        """
        Helper method for running multiple spiders consecutively. Runs on a separate thread to avoid the app freezing
        while crawling is in progress.

        :param spiders: a list of tuples containing the full make name followed by the corresponding spider
        :param kwargs: I don't know why I included this
        """
        self.updateLabel.config(foreground='black')
        for spider in spiders:
            self.updateLabel.config(text='Running ' + spider[0] + '...')
            spiderPath = os.sep.join((str(self.spidersPath), spider[1]))
            scrapyPath = os.sep.join((str(self.parentPath), 'scraper_env', 'Scripts', 'scrapy'))
            process_args = f'"{scrapyPath}" runspider -a purge={self.purgeFlag.get()} "{spiderPath}"'
            self.start_crawl(process_args, single_crawl=False)
        self.progressBar.stop()
        self.updateLabel.config(text='Done.')
        self.closeAppCautionLabel.config(text='It is safe to close this window.'
                                              '\nNote: Occasionally, no Tesla data will be retrieved on the first run.'
                                              '\nCheck the output file and run Tesla again if needed.')
        self.enable_critical_controls()

    def start_crawl(self, process_args, single_crawl=True):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        p = subprocess.Popen(process_args,
                             shell=True,
                             startupinfo=startupinfo,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if single_crawl:
            self.progressBar.stop()
            self.updateLabel.config(text=self.updateLabel.cget('text') + ' done.')
            self.closeAppCautionLabel.config(text='It is safe to close this window.')
            self.enable_critical_controls()

    def disable_critical_controls(self):
        """
        Disable the input objects that should not be interacted with during crawling.
        """
        state = ['disabled']
        self.crawlButton.state(state)
        self.purgeCheckButton.state(state)
        self.comboBox.state(state)

    def enable_critical_controls(self):
        """
        Enable the input objects that should not be interacted with during crawling.
        """
        state = ['!disabled']
        self.crawlButton.state(state)
        self.purgeCheckButton.state(state)
        self.comboBox.state(state)

    def show_help_text(self):
        messagebox.showinfo(title='How to use S.C.R.A.P.E.R.', message='\n\n'.join(self.HELP_TEXT))


def main():
    root = Tk()
    app = ScraperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
