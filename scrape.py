import requests
from bs4 import BeautifulSoup
import sys, numpy as np, re

args = sys.argv
if len(args) < 2:
    print("Usage: python3 scrape.py <url>")
    exit(1)
url = args[1]
rr = "https://www.royalroad.com"
title = []

def getPage(url):
    page = requests.get(url)
    return  BeautifulSoup(page.content, 'html.parser')
    
def getList(url):
    soup = getPage(url)
    title.append(" ".join(soup.title.text.split('|')[0].split()))
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

def convertList(chapter_list, num_chapters):
    for i in np.arange(len(chapter_list)):
        dict_chapters = {}

        if i >= num_chapters:
            break

        for item in chapter_list[i]:
            dict_chapters[item[0].replace('"', '')] = item[1].replace('"', '')
        chapter_list[i] = dict_chapters
    
    for chapter in chapter_list:
        page = getPage(f"{rr}{chapter['url']}")
        chapter["chapter_content"] = page.find("div", class_="chapter-inner chapter-content").text.replace("\n", "\\par\n").replace("%", "\\%").replace("\u200b", "").replace("#", "\\#").replace(u'\xa0', '')
    return chapter_list

temp = getList(url)
chapter_list = convertList(temp, len(temp))


def createLaTeX(chapter_list):
    latex = [t.replace("TITLE", title[0]) for t in np.loadtxt("latex_template.tex", dtype=str)]
    for chapter in chapter_list:
        latex.insert(-1, f'\\section{{{chapter["title"]}}}')
        latex.insert(-1, f'{chapter["chapter_content"]}\n')
    
    file = open(f"{title[0]}.tex", 'w')
    for line in latex:
        file.write(line+'\n')
    file.close()

# def createPDF(chapter_list):
#     file = open(f"{chapter_list["title"]}", 'r')

createLaTeX(chapter_list)
