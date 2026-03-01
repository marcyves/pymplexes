#!/usr/bin/env python3

from ged4py.parser import GedcomReader
from pathlib import Path

# -------------------------
# index GED (clé stable)
# -------------------------

def build_index(reader):
    ged_content = {}
    for rec in reader.records0():
        if rec.xref_id:
            ged_content[rec.xref_id] = rec
    return ged_content


# -------------------------
# helpers GED
# -------------------------

def tag(rec, t):
    for s in rec.sub_tags(t):
        if s.value:
            return str(s.value)
    return ""


def name(p):
    return tag(p, "NAME").replace("/", "")

def full_name(p):
    return p.name.surname + ", " + p.name.given
 
def birth(p):
    for ev in p.sub_tags("BIRT"):
        return tag(ev, "DATE")
    return ""


def death(p):
    for ev in p.sub_tags("DEAT"):
        return tag(ev, "DATE")
    return ""

def parents(p, ged_content):

    fam_id = None

    # IMPORTANT : lire tous les sub_records
    for child in p.sub_records:
        if child.tag == "FAMC":
            fam_id = child.value
            break

    if not fam_id:
        return None, None

    fam = ged_content.get(fam_id)
    if not fam:
        return None, None

    father = mother = None

    for child in fam.sub_records:
        if child.tag == "HUSB":
            father = ged_content.get(child.value)
        elif child.tag == "WIFE":
            mother = ged_content.get(child.value)

    return father, mother

def esc(x):
    return x.replace("&","\\&").replace("_","\\_")


# -------------------------
# Sosa text report
# -------------------------

def build_person(p, ged_content, sosa, gen=0):
    if not p or gen > MAX_GEN:
        return ""

    pid = p.xref_id

    if pid in seen:
        first = seen[pid]
        return f"\\section{{{sosa}. {esc(name(p))}}}\nVoir \\hyperref[p{first}]{{{first}}}\n"

    seen[pid] = sosa

    tex = []

    tex.append(f"\\section{{{sosa}. {full_name(p)}}}")
    tex.append(f"\\label{{p{sosa}}}")
    tex.append(f"\\index{{{full_name(p)}}}")

    tex.append("\\begin{tabular}{ll}")
    tex.append(f"Naissance : & {esc(birth(p))} \\\\")
    tex.append(f"Décès : & {esc(death(p))} \\\\")
    tex.append("\\end{tabular}\n")

    father, mother = parents(p, ged_content)

    tex.append(build_person(father, ged_content, sosa*2, gen+1))
    tex.append(build_person(mother, ged_content, sosa*2+1, gen+1))

    return "\n".join(tex)


# -------------------------
# TikZ tree
# -------------------------
def tikz_tree(root, ged_content, max_gen_per_page=5):

    pages = []
    queue = [(root, 1, 0)]
    
    while queue:
        current_root, root_sosa, global_gen_start = queue.pop(0)
        
        nodes = []
        edges = []
        
        def walk(p, sosa, local_gen, global_gen, y=0, dy=6):
            if not p or global_gen > MAX_GEN:
                return

            node_text = f"{sosa} {esc(full_name(p))}"
            father, mother = parents(p, ged_content)
            
            is_leaf_of_page = (local_gen == max_gen_per_page - 1)
            
            if is_leaf_of_page and global_gen < MAX_GEN and (father or mother):
                node_text += r" \\ \textbf{$\Rightarrow$}"
                queue.append((p, sosa, global_gen))
                nodes.append(
                    f'\\node (n{sosa}) at ({local_gen*4.5},{y}) {{{node_text}}};'
                )
                return
                
            nodes.append(
                f'\\node (n{sosa}) at ({local_gen*4.5},{y}) {{{node_text}}};'
            )
            
            if father:
                edges.append(f'\\draw (n{sosa}) -- (n{sosa*2});')
                walk(father, sosa*2, local_gen+1, global_gen+1, y+dy/(2**local_gen))

            if mother:
                edges.append(f'\\draw (n{sosa}) -- (n{sosa*2+1});')
                walk(mother, sosa*2+1, local_gen+1, global_gen+1, y-dy/(2**local_gen))

        walk(current_root, root_sosa, 0, global_gen_start)
        
        title = "La racine" if root_sosa == 1 else f"Suite de la branche {root_sosa} ({esc(full_name(current_root))})"
        
        page_tex = r"""
\newpage
\section{""" + title + r"""}
\begin{center}
\begin{tikzpicture}[
every node/.style={draw, rounded corners, align=center, font=\tiny, minimum width=2.6cm}
]
""" + "\n".join(nodes) + "\n" + "\n".join(edges) + r"""
\end{tikzpicture}
\end{center}
"""
        pages.append(page_tex)

    return "\n".join(pages)

# -------------------------
# template
# -------------------------

def template(content):
    return f"""
\\documentclass[
	fontsize=12pt,
	twoside=false,
	secnumdepth=1,
	a4paper
]{{scrbook}}
\\usepackage[french]{{babel}}
\\usepackage{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{makeidx}}
\\usepackage{{tikz}}
\\geometry{{margin=2cm}}
\\makeindex

\\begin{{document}}
\\title{{Arbre généalogique}}
\\author{{Marc Augier}}
\\date{{\\today}}
\\maketitle

\\newpage
\\tableofcontents

\\chapter{{Les arbres de mes ancêtres}}

{content}

\\printindex
\\end{{document}}
"""


# -------------------------
# main
# -------------------------

GED_FILE = "tree.ged"
ROOT_XREF = "@I0123@"
MAX_GEN = 1000
OUTPUT_TEX = "tree.tex"

seen = {}

with GedcomReader(GED_FILE) as reader:
    ged_content = build_index(reader)
    
    root = ged_content[ROOT_XREF]

    graphic = tikz_tree(root, ged_content)
    report = build_person(root, ged_content, 1)

Path(OUTPUT_TEX).write_text(template(graphic + f"\\newpage\\chapter{{Les fiches de mes ancêtres}}" + report), encoding="utf8")

print("OK → pdflatex tree.tex x2")