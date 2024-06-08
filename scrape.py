import requests, subprocess
from bs4 import BeautifulSoup
import sys, numpy as np, json

def getPage(url):
    page = requests.get(url)
    return  BeautifulSoup(page.content, 'html.parser')
    
def getList(url):
    soup = getPage(url)
    global title
    title = " ".join(soup.title.text.split('|')[0].split())
    temp = None
    for element in soup.select('script'):
        if "window.chapters" in element.text:
            for line in element.text.split('\n'):
                if "window.chapters" in line:
                    temp = " ".join(line.split())

    if temp is None:
        print("No page found.")
        exit(1)
    return [json.loads(dic) for dic in ['{'+r+'}' for r in temp.replace("window.chapters = ", "")[2:-3].split("},{")]]

def convertList(chapter_list, num_chapters):    
    count = 0

    for chapter in chapter_list:
        if count >= num_chapters:
            break
        page = getPage(f"{rr}{chapter['url']}")
        
        for tag in tagRemove:
            for item in page.findAll(tag):
                item.replaceWithChildren()
        
        con = page.find("div", class_="chapter-inner chapter-content")
        for item in con.findAll("div"):
            item.replaceWithChildren()
        stripped_con = [line for line in con.contents if line is not None]
        str_con = ''.join(str(line) for line in stripped_con)
        for item in replaceList:
            str_con = str_con.replace(item[0], item[1])

        chapter["chapter_content"] = str_con
        count += 1

    return chapter_list

def createLaTeX(chapter_list, num_chapters, pdfTitle):
    latex = [t.replace("TITLE", title) for t in np.loadtxt("latex_template.tex", dtype=str)]
    count = 0
    for chapter in chapter_list:
        if count >= num_chapters:
            break
        latex.insert(-1, f'\\section*{{{chapter["title"]}}}\n\\addcontentsline{{toc}}{{section}}{{\\protect\\numberline{{}}{chapter["title"]}}}%')
        latex.insert(-1, f'{chapter["chapter_content"]}\n')
        count += 1
    
    file = open(f"{title}.tex", 'w')
    for line in latex:
        file.write(line+'\n')
    file.close()

def createPDF(filename):
    subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{filename}.tex'])
    subprocess.run('rm *out *aux *log', shell=True)

args = sys.argv
if len(args) < 2:
    print("Usage: python3 scrape.py [-l] [-c] <url> [pdf-title] [num chapters]")
    print("\n    -l    Declare PDF output file name.")
    print("    -c    Configure number of chapters scraped.")
    exit(1)


num_chap = 0
rr = "https://www.royalroad.com"
tagRemove = ["p", "span", "em", "hr"]
replaceList = [["$", "\\$"], ["\u200b", ""], [u"\xa0", ""], ["\n", "\\par\n"], ["%", "\\%"], ["#", "\\#"], ["&", "\\&"], 
               ["<strong>", "\\textbf{"], ["</strong>", "}"], ["<sup>", "$^{"], ["</sup>", "}$"], 
               ["<a", "%"], ["</a>", "\n"], ["\\&gt;", "\\textgreater"], ["\\&lt;", "\\textless"], 
               ["The author\'s content has been appropriated; report any instances of this story on Amazon.", ""], 
               ["Taken from Royal Road, this narrative should be reported if found on Amazon.", ""]]

if len(args) == 2:
    url = args[1]
elif len(args) == 4:
    url = args[2]
elif len(args) == 6:
    url = args[3]

temp = getList(url)
num_chap = len(temp)
if len(args) == 4 and args[1] == "-l":
    title = str(args[-1])
elif len(args) == 4 and args[1] == "-c":
    num_chap = int(args[-1])
elif len(args) == 6 and args[1] == "-l" and args[2] == "-c":
    title = str(args[-2])
    num_chap = int(args[-1])

chapter_list = convertList(temp, num_chap)
print(chapter_list)
createLaTeX(chapter_list, num_chap, title)
createPDF(title)