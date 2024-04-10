import requests, subprocess
from bs4 import BeautifulSoup
import sys, numpy as np, re

args = sys.argv
if len(args) < 2:
    print("Usage: python3 scrape.py <url> [num chapters]")
    exit(1)

num_chap = 0
url = args[1]
rr = "https://www.royalroad.com"
title = []
tagRemove = ["p", "span", "em", "hr"]

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
        
        for tag in tagRemove:
            for item in page.findAll(tag):
                item.replaceWithChildren()
        
        con = page.find("div", class_="chapter-inner chapter-content")
        stripped_con = [line for line in con.contents if line is not None and line != "\u200b" and line != u"\xa0"]
        str_con = ''.join(str(line) for line in stripped_con)

        chapter["chapter_content"] = str_con.replace("\u200b", "").replace(u"\xa0", "").replace("\n", "\\par\n").replace("%", "\\%").replace("#", "\\#").replace("&", "\\&").replace("<strong>", "\\textbf{").replace("</strong>", "}").replace("\\&gt;", "\\textgreater").replace("\\&lt;", "\\textless").replace("The author\'s content has been appropriated; report any instances of this story on Amazon.", "")
    return chapter_list

def createLaTeX(chapter_list):
    latex = [t.replace("TITLE", title[0]) for t in np.loadtxt("latex_template.tex", dtype=str)]
    for chapter in chapter_list:
        latex.insert(-1, f'\\section*{{{chapter["title"]}}}\n\\addcontentsline{{toc}}{{section}}{{\\protect\\numberline{{}}{chapter["title"]}}}%')
        latex.insert(-1, f'{chapter["chapter_content"]}\n')
    
    file = open(f"{title[0]}.tex", 'w')
    for line in latex:
        file.write(line+'\n')
    file.close()

def createPDF(filename):
    subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{filename}.tex'])
    # subprocess.run('rm *out *aux *log', shell=True)


temp = getList(url)

if len(args) >= 3:
    num_chap = args[2]
else:
    num_chap = len(temp)

chapter_list = convertList(temp, num_chap)
createLaTeX(chapter_list)
createPDF(title[0])