all:
	/Users/marc/GitHub/pymplexes/pymp/bin/python build_tree_sosa_tikz.py
	pdflatex tree.tex
	makeindex tree.idx
	pdflatex tree.tex
