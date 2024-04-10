import requests
from bs4 import BeautifulSoup
import sys, numpy as np

args = sys.argv
if len(args) < 2:
    print("Usage: python3 scrape.py <url>")
    exit(1)
url = args[1]
rr = "https://www.royalroad.com"

def getPage(url):
    page = requests.get(url)
    return  BeautifulSoup(page.content, 'html.parser')
    
def getList(url):
    soup = getPage(url)
    temp = None
    for element in soup.select('script'):
        if "window.chapters" in element.text:
            for line in element.text.split('\n'):
                if "window.chapters" in line:
                    temp = " ".join(line.split())

    if temp is None:
        print("No page found.")
        exit(1)
    temp = temp[temp.find("[")+1:temp.find("]")]
    
    return [[[s for s in sp.split(':')] for sp in chapter.split(',')] for chapter in temp[1:-1].split('},{')]

def convertList(url):
    chapter_list = getList(url)
    for i in np.arange(0, chapter_list):
        dict_chapters = {}
        for item in chapter_list[i]:
            dict_chapters[item[0].replace('"', '')] = item[1].replace('"', '')
        chapter_list[i] = dict_chapters
    
    for chapter in chapter_list:
        page = getPage(f"{rr}{chapter['url']}")
        text = page.find("div", class_="chapter-inner chapter-content").text
        chapter["chapter_content"] = text
    return chapter_list

chapter_list = convertList(url)

def createPDF(chapter_list):
    file = open(f"{chapter_list["title"]}", 'w')

print(chapter_list[0])