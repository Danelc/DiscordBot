from lxml import html
from os import path
import concurrent.futures as conc
import requests, json, argparse, time


class NyaaReq():
    def __init__(self, verbose=False):
        self.site = 'https://nyaa.si'
        self.siteQuery = self.site + '/?f={criteria}&c={category}&q={query}&p={page}'
        with open(path.join(path.dirname(__file__), "types.json"),
                  "rt") as types:
            types = json.load(types)
            self.category = types['category']
            self.criteria = types['criteria']
        self.verboseprint = print if verbose else lambda *a, **k: None

    def get(self, query, criteria='0', category='0_0', multithread=True):
        if type(category) is list:
            content = list()
            for i in category:
                for data in self.get(query=query,
                                     criteria=criteria,
                                     category=i,
                                     multithread=multithread):
                    content.append(data)
            return content
        content = list()
        future_to_url = list()
        firstNyaaPage = requests.get(
            self.siteQuery.format(query=query,
                                  page=1,
                                  criteria=criteria,
                                  category=category))
        if (err := firstNyaaPage.status_code) >= 400:
            raise Exception(f"Error! Status code {err} raised!")
        firstNyaaPage = html.fromstring(firstNyaaPage.content)
        try:
            totalPage = firstNyaaPage.xpath(
                '//ul[@class="pagination"]/li[last()-1]/a')[0].text
        except IndexError:
            totalPage = 1
        self.verboseprint(f"Total page is {totalPage}")
        if multithread:
            with conc.ThreadPoolExecutor(5) as executor:
                for page in range(1, int(totalPage) + 1):
                    self.verboseprint(f"Parsing page {page}")
                    future_to_url.append(
                        executor.submit(self.get_page,
                                        query=query,
                                        criteria=criteria,
                                        category=category,
                                        page=page))
                for future in conc.as_completed(future_to_url):
                    self.verboseprint(f"Returning content for a page...")
                    for data in future.result():
                        content.append(data)
                return content
        else:
            for page in range(1, int(totalPage) + 1):
                self.verboseprint(f"Parsing page {page}")
                for data in self.get_page(query=query,
                                          criteria=criteria,
                                          category=category,
                                          page=page):
                    content.append(data)
            return content

    def get_page(self,
                 query,
                 criteria='0',
                 category='0_0',
                 page=1,
                 verbose=True):
        """
        Gets the table of torrents from query site. 
        Returns an lxml Element object with a <td> tag if autoparse is False. 
        Returns an array containing dictionaries that tells the info 
        of a torrent if autoparse is True. 
        """
        nyaaPage = requests.get(
            self.siteQuery.format(query=query,
                                  page=page,
                                  criteria=criteria,
                                  category=category))
        if (err := nyaaPage.status_code) >= 400:
            raise Exception(f"Error! Status code {err} raised!")
        nyaaPage = html.fromstring(nyaaPage.content)
        tableRow = nyaaPage.xpath('//tbody/tr')
        tableData = list()
        for tr in tableRow:
            tableData.append(tr.findall("td"))
        return self.parse(tableData)

    def parse(self, tableRow):
        """
        Parses the table data (<td> elements) to get the contents of it. 
        Returns a list containing dictionaries, 
        where a single dictionary contains information for a single torrent. 
        """
        content = list()
        for tableData in tableRow:
            category = tableData[0].find("a").attrib['href'][4:]
            name = tableData[1].find('a[last()]').attrib['title']
            url = self.site + tableData[1].find("a").attrib['href']
            torrent = self.site + tableData[2].findall("a")[0].attrib['href']
            magnet = tableData[2].findall("a")[1].attrib['href']
            size = tableData[3].text
            date = tableData[4].text
            seed = tableData[5].text
            leech = tableData[6].text
            downloads = tableData[7].text
            content.append({
                'name': name,
                'url': url,
                'category': self.translate(category),
                'torrent': torrent,
                'magnet': magnet,
                'size': size,
                'date': date,
                'seed': seed,
                'leech': leech,
                'downloads': downloads
            })
        return content

    def translate(self, string):
        """
        Translates nyaa's URL to readable strings
        """
        try:
            return self.category[string]
        except:
            try:
                return self.criteria[string]
            except:
                return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='NyaaRequest', 
                                     usage='NyaaReq.py query [--flags]')
    parser.add_argument("query", help="String to search for in nyaa.si")
    parser.add_argument("-cr",
                        "--criteria",
                        help="Criteria to search for",
                        nargs='?',
                        default="0")
    parser.add_argument("-ct",
                        "--category",
                        help="Categories to search in, can be multiple.",
                        nargs='*',
                        default="0_0")
    parser.add_argument("--multi",
                        help="Enables multithreading for faster parsing",
                        action="store_true")
    parser.add_argument("--verbose",
                        help="Enables verbose printing",
                        action='store_true')
    args = parser.parse_args()
    nyaa = NyaaReq(args.verbose)
    result = nyaa.get(args.query, args.criteria, args.category, args.multi)

    for torrent in result:
        print("\n")
        for key, data in torrent.items():
            print(f"{key} : {data}")