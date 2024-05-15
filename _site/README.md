### How to test the page locally?

Run the following command:
```
bundle exec jekyll serve
```

### How to convert Jupyter Notebook to HTML?

```
jupyter nbconvert --to html <prelude>.ipynb
```

### How to convert jupyter to markdown and have a separate page?

1.  Create a folder **folderName**, which then will be the sub-domain the page will be on.
    For example: We want a page for _regression_ then the url will be: _maindomain/regression_
2.  Move the written jupyterfile **jupyterFile** into the folder **folderName**.
3.  run the following command in the root folder: 
```bash
bash jupyterToMarkdown.sh <jupyterFile> <folderName>
```
4.  Add the new markdown file as a link onto the corresponding page with the following line: 
```
This is my cool new page [<jupyterFile>](<url>/<jupyterFile>)
```
The most important use case is redirecting from the main page (index.md) to the new page, which then boils down to the following command:
```
This is my cool new page [<jupyterFile>]({{ site.baseurl }}/<jupyterFile>)
```
Here the jupyterFile is meant without the .ipynb extension.

#### Some important remarks
1. Please make sure you have rerun the jupyternotebook everytime, because the conversion does not run the jupyternotebook automatically
2. For plotting it is better to use **plt.show()** at the end of every plot, because it makes the website more nice. (a certain matplotlib output message is then not visible)